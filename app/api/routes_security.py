"""
routes_security.py — MedicAItion Sprint 4
=================================================================
Control de acceso por roles (RBAC), Cédula Profesional NOM-004,
visor de Bitácora de Auditoría NOM-024 y Verificador Offline-First.
"""

import time
import unicodedata
from urllib.parse import unquote
from fastapi import APIRouter, Body, HTTPException, Request

from app.core.entity_extractor import _heuristic_extract
from app.core.fhir_exporter import build_fhir_bundle
from app.core.qr_svg import generate_qr_svg
from app.core.safety_engine import evaluate_clinical_safety
from app.db.chroma_store import get_collection
from app.db.local_db import (
    AuditLog,
    Appointment,
    Consulta,
    Patient,
    SessionLocal,
    VitalReading,
    get_active_practitioner,
    get_all_audit_logs,
    get_practitioner_profiles,
    upsert_practitioner_profile,
    verify_encryption_and_integrity_audit,
)

router = APIRouter(prefix="/api/security", tags=["Security & NOM-024"])

ROLE_PERMISSIONS = {
    "Médico": {
        "view_clinical": True,
        "register_patient": True,
        "manage_appointments": True,
        "record_vitals": True,
        "sign_consultation": True,
        "add_addendum": True,
        "prescribe": True,
        "read_audit": True,
        "manage_config": True,
        "delete_patient": False,
    },
    "Enfermería / Triaje": {
        "view_clinical": True,
        "register_patient": True,
        "manage_appointments": True,
        "record_vitals": True,
        "sign_consultation": False,
        "add_addendum": False,
        "prescribe": False,
        "read_audit": False,
        "manage_config": False,
        "delete_patient": False,
    },
    "Recepción": {
        "view_clinical": False,
        "register_patient": True,
        "manage_appointments": True,
        "record_vitals": False,
        "sign_consultation": False,
        "add_addendum": False,
        "prescribe": False,
        "read_audit": False,
        "manage_config": False,
        "delete_patient": False,
    },
    "Administrador": {
        "view_clinical": True,
        "register_patient": True,
        "manage_appointments": True,
        "record_vitals": True,
        "sign_consultation": True,
        "add_addendum": True,
        "prescribe": True,
        "read_audit": True,
        "manage_config": True,
        "delete_patient": True,
    },
}

_PERMISSION_LABELS = {
    "sign_consultation": "Firmar consultas médicas y emitir recetas (NOM-004)",
    "add_addendum": "Agregar addenda a consultas firmadas",
    "prescribe": "Prescribir medicamentos",
    "record_vitals": "Registrar signos vitales y wearables",
    "register_patient": "Registrar o editar pacientes",
    "manage_appointments": "Gestionar agenda y triaje",
    "read_audit": "Consultar bitácora de auditoría NOM-024",
    "delete_patient": "Eliminar expedientes",
}


def _strip_accents(value: str) -> str:
    s = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def normalize_role(raw_role: str | None) -> str:
    """Normaliza encabezados de rol hacia una clave canónica de ROLE_PERMISSIONS."""
    if not raw_role or not raw_role.strip():
        return "Médico"
    norm = _strip_accents(raw_role)
    if "medico" in norm or "doctor" in norm:
        return "Médico"
    if "enferm" in norm or "triaje" in norm:
        return "Enfermería / Triaje"
    if "recep" in norm or "admision" in norm:
        return "Recepción"
    if "admin" in norm or "director" in norm:
        return "Administrador"
    return raw_role.strip()


def require_permission(request: Request, permission: str) -> dict:
    """
    Evalúa el rol del operador desde headers HTTP (`X-Operator-Role`, `X-Operator-Name`,
    `X-Operator-Cedula`). Si no se envía encabezado (clientes legados/tests sin rol),
    opera por defecto como `Médico`.
    """
    raw_role = unquote(request.headers.get("X-Operator-Role") or "")
    role = normalize_role(raw_role)
    perms = ROLE_PERMISSIONS.get(role)
    if perms is None:
        raise HTTPException(
            status_code=403,
            detail=f"Rol no reconocido '{raw_role}' para la operación '{permission}'.",
        )
    if not perms.get(permission, False):
        action_desc = _PERMISSION_LABELS.get(permission, permission)
        raise HTTPException(
            status_code=403,
            detail=f"Acceso denegado para rol '{role}': no autorizado para '{action_desc}'.",
        )
    active = get_active_practitioner() if not raw_role else {}
    return {
        "role": role,
        "name": unquote(request.headers.get("X-Operator-Name") or active.get("full_name") or role).strip(),
        "cedula_profesional": unquote(
            request.headers.get("X-Operator-Cedula")
            or active.get("cedula_profesional")
            or ""
        ).strip(),
    }


@router.get("/profile")
def get_security_profile():
    """Devuelve el operador activo, la lista de roles configurables y la matriz RBAC."""
    return {
        "active": get_active_practitioner(),
        "profiles": get_practitioner_profiles(),
        "permissions_matrix": ROLE_PERMISSIONS,
    }


@router.post("/profile")
def update_security_profile(data: dict = Body(...)):
    """Actualiza datos/cédula profesional de un rol y opcionalmente lo activa."""
    role = normalize_role(data.get("role"))
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"Rol inválido: {data.get('role')}")
    payload = dict(data)
    payload["role"] = role
    saved = upsert_practitioner_profile(payload)
    return {
        "status": "ok",
        "active": get_active_practitioner(),
        "saved": saved,
        "profiles": get_practitioner_profiles(),
        "permissions_matrix": ROLE_PERMISSIONS,
    }


@router.get("/audit-logs")
def list_global_audit_logs(limit: int = 100, action: str | None = None, curp: str | None = None):
    """Visor global de Bitácora de Auditoría NOM-024."""
    logs = get_all_audit_logs(limit=limit, action=action, curp=curp)
    db = SessionLocal()
    try:
        total_logs = db.query(AuditLog).count()
        total_consultas = db.query(Consulta).count()
        total_patients = db.query(Patient).count()
    finally:
        db.close()

    return {
        "logs": logs,
        "summary": {
            "total_audit_events": total_logs,
            "total_consultas_inmutables": total_consultas,
            "total_pacientes": total_patients,
        },
    }


@router.get("/offline-readiness")
def check_offline_readiness():
    """
    Verifica en tiempo real sin red externa que todos los subsistemas críticos
    de MedicAItion operan 100% en modo local/offline.
    """
    t0 = time.perf_counter()
    checks = []

    # 1. SQLite Local NOM-004 / NOM-024
    db = SessionLocal()
    try:
        p_cnt = db.query(Patient).count()
        c_cnt = db.query(Consulta).count()
        a_cnt = db.query(Appointment).count()
        v_cnt = db.query(VitalReading).count()
        log_cnt = db.query(AuditLog).count()
        checks.append({
            "id": "sqlite",
            "name": "Base de Datos SQLite Local (NOM-004/024)",
            "ok": True,
            "detail": f"{p_cnt} pacientes, {c_cnt} consultas inmutables, {a_cnt} citas, {v_cnt} vitales, {log_cnt} eventos auditados",
        })
    except Exception as e:
        checks.append({"id": "sqlite", "name": "Base de Datos SQLite Local", "ok": False, "detail": str(e)})
    finally:
        db.close()

    # 2. ChromaDB Terminología Oficial CIE-10 / CIE-9MC
    try:
        dx_col = get_collection("cie10_mexico_2024_diagnosticos")
        px_col = get_collection("cie10_mexico_2024_procedimientos")
        dx_cnt = dx_col.count()
        px_cnt = px_col.count()
        ok_chroma = dx_cnt > 0 and px_cnt > 0
        checks.append({
            "id": "chromadb",
            "name": "Motor Vectorial ChromaDB CIE-10 / CIE-9MC",
            "ok": ok_chroma,
            "detail": f"{dx_cnt:,} diagnósticos CIE-10 y {px_cnt:,} procedimientos CIE-9MC indexados localmente",
        })
    except Exception as e:
        checks.append({"id": "chromadb", "name": "Motor Vectorial ChromaDB", "ok": False, "detail": str(e)})

    # 3. Extractor Clínico Offline (heurístico local)
    try:
        sample = _heuristic_extract("Fiebre 39 C, dolor abdominal intenso y Ketorolaco 10 mg cada 8 horas.")
        ok_ext = len(sample.get("sintomas_referidos", [])) >= 1 and len(sample.get("medicamentos", [])) >= 1
        checks.append({
            "id": "extractor",
            "name": "Extractor Clínico Estructurado Offline",
            "ok": ok_ext,
            "detail": "Extracción sintomática y farmacológica funcional sin API externa",
        })
    except Exception as e:
        checks.append({"id": "extractor", "name": "Extractor Clínico Offline", "ok": False, "detail": str(e)})

    # 4. Guardián Clínico CDSS Determinista
    try:
        cdss = evaluate_clinical_safety(
            entities={
                "sintomas_referidos": ["Fiebre"],
                "diagnosticos_tentativos": [],
                "signos_vitales": [],
                "medicamentos": [{"nombre": "Amoxicilina", "dosis": "500 mg", "periodicidad": "cada 8 horas"}],
            },
            patient_data={"alergias": [{"sustancia": "Penicilina", "severidad": "Severa"}]},
            texto_original="Fiebre y Amoxicilina",
        )
        checks.append({
            "id": "cdss",
            "name": "Guardián Clínico CDSS (Alergias / DDI / Triaje)",
            "ok": bool(cdss.get("bloqueo_seguridad")),
            "detail": "Detección local de alergia cruzada Penicilina ↔ Amoxicilina verificada",
        })
    except Exception as e:
        checks.append({"id": "cdss", "name": "Guardián Clínico CDSS", "ok": False, "detail": str(e)})

    # 5. Generador QR SVG y Exportación HL7 FHIR R4 Locales
    try:
        svg = generate_qr_svg("MEDICAI-OFFLINE-CHECK")
        bundle = build_fhir_bundle(
            patient={"curp": "OFFLINE010190HYN01", "nombres": "Demo", "primer_apellido": "Offline", "sexo": "M"},
            eventos=[],
            vitals=[],
            daily_logs=[],
        )
        ok_interop = svg.startswith("<svg") and bundle.get("resourceType") == "Bundle"
        checks.append({
            "id": "qr_fhir",
            "name": "Generador QR ICE/Receta + HL7 FHIR R4",
            "ok": ok_interop,
            "detail": "Generación SVG QR sin internet y Bundle FHIR R4 listos",
        })
    except Exception as e:
        checks.append({"id": "qr_fhir", "name": "Generador QR + HL7 FHIR R4", "ok": False, "detail": str(e)})

    # 6. Bóveda de Cifrado en Reposo ChaCha20-HMAC-SHA256 y Sellos NOM-004
    try:
        enc_audit = verify_encryption_and_integrity_audit()
        checks.append({
            "id": "encryption_nom004",
            "name": "Cifrado en Reposo (ChaCha20-HMAC-SHA256) y Sellos NOM-004",
            "ok": bool(enc_audit.get("patient_safety_ok")),
            "detail": (
                f"{enc_audit['patients_sensitive_encrypted']}/{enc_audit['patients_with_sensitive']} expedientes con PII cifrada, "
                f"{enc_audit['consultas_seal_verified']}/{enc_audit['consultas_total']} consultas selladas sin alteración"
            ),
        })
    except Exception as e:
        checks.append({"id": "encryption_nom004", "name": "Cifrado en Reposo", "ok": False, "detail": str(e)})

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    offline_capable = all(c["ok"] for c in checks)
    return {
        "offline_capable": offline_capable,
        "checked_at_ms": elapsed_ms,
        "external_network_required": False,
        "checks": checks,
    }
