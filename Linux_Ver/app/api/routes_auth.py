"""
routes_auth.py — Autenticación por Roles y Separación Stricta Personal vs. Paciente
===================================================================================
- Personal de Salud (Médico, Enfermería / Triaje, Recepción, Administrador):
  * Login con Rol + PIN local (PBKDF2-HMAC-SHA256).
  * Compromiso de Confidencialidad / Secreto Profesional NOM-024 + Responsabilidad CDSS
    (en lugar de pedirle Aviso de Privacidad como si fuera paciente).
- Paciente ("Mi Salud Hoy"):
  * Login exclusivo con CURP + Fecha de Nacimiento (o Folio Hospitalario).
  * Token HMAC-SHA256 de sesión restringido exclusivamente a su propio CURP.
  * Cero acceso a lista de pacientes, expedientes de terceros, CIE-10 o configuración clínica.
"""

from fastapi import APIRouter, Body, HTTPException, Request

from app.core.crypto_vault import sign_session_token, verify_session_token
from app.db.local_db import (
    accept_staff_confidentiality,
    authenticate_patient_portal,
    authenticate_staff_profile,
    get_active_practitioner,
    get_latest_consent,
    get_patient_upcoming_appointments,
    get_staff_login_roles,
    update_staff_pin,
)
from app.api.routes_security import ROLE_PERMISSIONS

router = APIRouter(prefix="/api/auth", tags=["Auth & Role Separation"])


@router.get("/roles")
def list_login_roles():
    """Lista pública (sin credenciales ni datos clínicos) de roles de personal para Login."""
    return {
        "staff_roles": get_staff_login_roles(),
        "default_demo_pin_hint": "PIN inicial por defecto: 1234 (editable en Configuración)",
    }


@router.post("/staff-login")
def staff_login(data: dict = Body(...)):
    """Autentica a un integrante del personal clínico y emite token de sesión."""
    role = (data.get("role") or "").strip()
    pin = str(data.get("pin") or "").strip()
    if not role or not pin:
        raise HTTPException(status_code=400, detail="Selecciona un rol e ingresa tu PIN.")

    profile = authenticate_staff_profile(role, pin)
    if not profile:
        raise HTTPException(status_code=401, detail="Rol no encontrado o PIN incorrecto.")

    token = sign_session_token({
        "type": "staff",
        "role": profile["role"],
        "name": profile["full_name"],
        "cedula": profile.get("cedula_profesional") or "",
    })
    return {
        "status": "authenticated",
        "user_type": "staff",
        "token": token,
        "profile": profile,
        "permissions": ROLE_PERMISSIONS.get(profile["role"], {}),
        "requires_confidentiality_ack": not bool(profile.get("confidentiality_accepted")),
    }


@router.post("/staff-confidentiality")
def staff_accept_confidentiality(data: dict = Body(...)):
    """
    Registra la aceptación del Compromiso de Confidencialidad (Secreto Profesional NOM-024 / LGS)
    y descargo clínico CDSS del personal de salud. No pide Aviso de Privacidad de paciente.
    """
    role = (data.get("role") or get_active_practitioner().get("role") or "Médico").strip()
    accepted_secret = bool(data.get("accepted_confidentiality"))
    accepted_cdss = bool(data.get("accepted_cdss_responsibility"))
    if not accepted_secret or not accepted_cdss:
        raise HTTPException(
            status_code=422,
            detail="Debes aceptar el secreto profesional NOM-024 y el uso de apoyo clínico CDSS.",
        )

    operator_name = (data.get("full_name") or "").strip()
    updated = accept_staff_confidentiality(role, operator_name)
    if not updated:
        raise HTTPException(status_code=404, detail="Perfil de personal no encontrado.")

    return {
        "status": "signed",
        "profile": updated,
    }


@router.post("/staff-pin")
def change_staff_pin(data: dict = Body(...), request: Request = None):
    """Permite cambiar el PIN de acceso de un rol de personal."""
    role = (data.get("role") or "").strip()
    current_pin = str(data.get("current_pin") or "").strip()
    new_pin = str(data.get("new_pin") or "").strip()
    if not role or not current_pin or len(new_pin) < 4:
        raise HTTPException(status_code=400, detail="Rol, PIN actual y PIN nuevo (mín. 4 dígitos) requeridos.")
    try:
        res = update_staff_pin(role, current_pin, new_pin)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return {"status": "updated", "role": res["role"]}


@router.post("/patient-login")
def patient_login(data: dict = Body(...)):
    """
    Autentica al paciente exclusivamente para su Portal Personal básico ("Mi Salud Hoy").
    Exige CURP + Fecha de Nacimiento (YYYY-MM-DD o DD/MM/YYYY) o Folio Hospitalario.
    """
    curp = (data.get("curp") or "").strip().upper()
    secret = str(data.get("verification_secret") or "").strip()
    if not curp or not secret:
        raise HTTPException(
            status_code=400,
            detail="Ingresa tu CURP y tu fecha de nacimiento (o folio de expediente).",
        )

    patient = authenticate_patient_portal(curp, secret)
    if not patient:
        raise HTTPException(
            status_code=401,
            detail="CURP o dato de verificación (fecha de nacimiento / folio) incorrecto.",
        )

    consent = get_latest_consent(curp)
    token = sign_session_token({
        "type": "patient",
        "role": "Paciente",
        "sub": curp,
        "name": patient["nombre_corto"],
    })
    return {
        "status": "authenticated",
        "user_type": "patient",
        "role": "Paciente",
        "token": token,
        "patient": patient,
        "has_privacy_consent": bool(
            consent and consent.get("status") == "active" and consent.get("accepted_privacy_notice")
        ),
        "consent": consent,
        "permissions": ROLE_PERMISSIONS["Paciente"],
    }


@router.get("/patient-appointments/{curp}")
def patient_own_appointments(curp: str):
    """Citas básicas seguras visibles en el portal exclusivo del paciente."""
    target = curp.upper()
    return {
        "curp": target,
        "appointments": get_patient_upcoming_appointments(target),
    }


@router.get("/me")
def current_session_info(request: Request):
    """Inspección rápida de token de sesión (staff o paciente)."""
    token = (request.headers.get("X-Session-Token") or "").strip()
    claims = verify_session_token(token) if token else None
    if not claims:
        return {"authenticated": False, "user_type": "anonymous"}
    return {"authenticated": True, "claims": claims}
