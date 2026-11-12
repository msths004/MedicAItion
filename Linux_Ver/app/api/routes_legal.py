"""
routes_legal.py — MedicAItion Marco Legal, Privacidad y Cifrado
=================================================================
Cumplimiento regulatorio para México y el Estado de Yucatán (con
arquitectura multi-CLUES escalable a nivel nacional e internacional):
  • CPEUM Arts. 4° y 16
  • LFPDPPP (Consentimiento expreso datos sensibles de salud + Derechos ARCO)
  • LGPDPPSO / INAIP Yucatán (Sujetos obligados y ámbito estatal)
  • NOM-004-SSA3-2012 (Expediente Clínico inmutable, firma, custodia 5 años)
  • NOM-024-SSA3-2012 (SIRES, bitácora, RBAC, HL7 FHIR R4)
  • COFEPRIS (Soporte clínico SaMD bajo supervisión médica)
"""

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.routes_security import require_permission
from app.db.local_db import (
    get_latest_consent,
    get_patient_audit_logs,
    get_patient_full_history,
    revoke_consent_record,
    upsert_consent_record,
    verify_encryption_and_integrity_audit,
)

router = APIRouter(prefix="/api/legal", tags=["Legal, Privacidad & Cifrado"])

LEGAL_FRAMEWORK_MX_YUC = {
    "version": "v2.0-MX-YUC-LFPDPPP",
    "jurisdiccion_inicial": "Mérida, Yucatán, Estados Unidos Mexicanos (Sede Piloto CLUES YUC-CR-001)",
    "alcance_expansion": "Arquitectura multi-CLUES y HL7 FHIR R4 escalable a las 32 entidades federativas de México y jurisdicciones internacionales homologadas.",
    "normatividad": [
        {
            "codigo": "LFPDPPP (Arts. 8°, 15–17, 22–28)",
            "titulo": "Protección de Datos Personales Sensibles de Salud",
            "aplicacion": "Requiere consentimiento expreso y por escrito para expediente, telemetría y transferencias opcionales a nube externa; habilita Derechos ARCO.",
        },
        {
            "codigo": "NOM-004-SSA3-2012 (Numeral 5.4 y 5.10)",
            "titulo": "Del Expediente Clínico",
            "aplicacion": "Notas médicas inmutables con sello criptográfico HMAC-SHA256, addenda trazables, Cédula Profesional del médico y conservación mínima obligatoria de 5 años.",
        },
        {
            "codigo": "NOM-024-SSA3-2012",
            "titulo": "Sistemas de Información de Registro Electrónico para la Salud (SIRES)",
            "aplicacion": "Control de acceso basado en roles (RBAC), bitácora de auditoría inmutable, catálogos oficiales CIE-10 / CIE-9MC y exportación HL7 FHIR R4.",
        },
        {
            "codigo": "Marco Estatal de Yucatán (SSY / INAIP Yucatán)",
            "titulo": "Jurisdicción Sanitaria y Protección Estatal Inicial",
            "aplicacion": "Alineación con Servicios de Salud de Yucatán (SSY), vigilancia epidemiológica estatal (ej. arbovirosis/Dengue), INAIP Yucatán y legislación civil/penal estatal vigente, adaptable por CLUES en expansión nacional.",
        },
        {
            "codigo": "LGS & Criterio COFEPRIS (CDSS)",
            "titulo": "Seguridad del Paciente y Responsabilidad Profesional",
            "aplicacion": "MedicAItion opera como Sistema de Apoyo a la Decisión Clínica (CDSS); la valoración diagnóstica, prescripción y justificación clínica corresponden exclusivamente al profesional titulado.",
        },
    ],
    "aviso_privacidad_resumen": (
        "En cumplimiento con la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP) "
        "y su Reglamento, la LGPDPPSO y las Normas Oficiales Mexicanas NOM-004-SSA3-2012 y NOM-024-SSA3-2012, el establecimiento "
        "responsable ubicado inicialmente en Mérida, Yucatán, México (con capacidad de operación multi-sede en toda la República Mexicana "
        "y expansión internacional) trata sus datos personales y datos personales sensibles de salud bajo cifrado autenticado en reposo "
        "(ChaCha20 + HMAC-SHA256 de 256 bits) exclusivamente para: (I) atención médica, triaje y seguridad farmacológica salva-vidas; "
        "(II) integración del Expediente Clínico Electrónico inmutable; y (III) previo consentimiento específico, Pasaporte de Emergencia QR (ICE), "
        "monitoreo de dispositivos wearables o procesamiento asistido por IA. Sus datos clínicos NO se transfieren a servidores externos en la nube "
        "sin su autorización expresa y verificable. Puede ejercer sus Derechos ARCO (Acceso, Rectificación, Cancelación y Oposición) directamente "
        "en la plataforma, observando el plazo de custodia clínica obligatoria de 5 años previsto en el numeral 5.4 de la NOM-004-SSA3-2012."
    ),
    "descargo_clinico": (
        "AVISO DE SEGURIDAD CLÍNICA: Las alertas de alergias, interacciones medicamentosas, códigos CIE-10 y niveles de triaje constituyen "
        "apoyo automatizado basado en reglas clínicas y evidencia vinculada. No sustituyen el criterio médico ni la exploración física directa. "
        "Cualquier omisión de alerta crítica roja requiere justificación médica firmada y queda registrada en bitácora auditada."
    ),
}


@router.get("/framework")
def get_legal_framework():
    """Devuelve el marco legal completo (México + Yucatán + escalabilidad) y el estado de cifrado."""
    audit = verify_encryption_and_integrity_audit()
    return {
        "framework": LEGAL_FRAMEWORK_MX_YUC,
        "security_status": audit,
        "system_consent": get_latest_consent("SISTEMA"),
    }


@router.get("/consent/{curp}")
def read_consent(curp: str):
    """Consulta el consentimiento informado vigente de un paciente o de SISTEMA."""
    rec = get_latest_consent(curp.upper())
    return {
        "patient_curp": curp.upper(),
        "has_consent": rec is not None and not rec.get("revoked"),
        "consent": rec,
    }


@router.post("/consent/{curp}", status_code=201)
def sign_consent(curp: str, request: Request, data: dict = Body(...)):
    """Registra el permiso expreso del usuario/paciente para el uso cifrado de sus datos."""
    op = require_permission(request, "register_patient")
    payload = dict(data)
    payload.setdefault("operator_name", f"{op.get('name')} [{op.get('role')}]")
    try:
        saved = upsert_consent_record(curp.upper(), payload)
        return {"status": "signed", "consent": saved}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/consent/{curp}/revoke")
def revoke_consent(curp: str, request: Request, data: dict = Body(default={})):
    """
    Aplica oposición / revocación ARCO sobre usos opcionales (IA nube, QR ICE, wearables),
    manteniendo el bloqueo legal de custodia NOM-004 (5 años).
    """
    op = require_permission(request, "register_patient")
    reason = str(data.get("reason") or "Solicitud de Derechos ARCO (Oposición/Cancelación) del titular")
    revoked = revoke_consent_record(
        curp.upper(),
        reason=reason,
        operator=f"{op.get('name')} [{op.get('role')}]",
    )
    return {
        "status": "revoked_optional_uses",
        "nom004_custody_lock": "Expediente bloqueado en custodia legal mínima de 5 años (NOM-004-SSA3-2012 Numeral 5.4).",
        "consent": revoked,
    }


@router.get("/arco/{curp}/export")
def export_arco_package(curp: str, download: bool = False):
    """Derecho ARCO de Acceso y Portabilidad: entrega expediente descifrado, consentimientos y auditoría."""
    target = curp.upper()
    history = get_patient_full_history(target)
    if not history:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    consent = get_latest_consent(target)
    logs = get_patient_audit_logs(target)
    pkg = {
        "arco_document_type": "PORTABILIDAD_Y_ACCESO_LFPDPPP",
        "jurisdiction": LEGAL_FRAMEWORK_MX_YUC["jurisdiccion_inicial"],
        "privacy_notice_version": LEGAL_FRAMEWORK_MX_YUC["version"],
        "consent": consent,
        "patient": history["patient"],
        "eventos_clinicos": history["eventos"],
        "vital_readings": history["vital_readings"],
        "patient_daily_logs": history["patient_daily_logs"],
        "audit_logs": logs,
    }
    if download:
        return JSONResponse(
            content=pkg,
            headers={"Content-Disposition": f'attachment; filename="{target}_ARCO_LFPDPPP.json"'},
        )
    return pkg


@router.get("/security-audit")
def get_security_and_encryption_audit():
    """Audita en vivo cifrado en reposo ChaCha20-HMAC-SHA256 y sellos de integridad NOM-004."""
    return verify_encryption_and_integrity_audit()
