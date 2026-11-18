from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query, Body, HTTPException
from app.db.global_db import (
    get_network_hospital_capacities,
    update_hospital_live_capacity,
    get_all_institutions,
    register_institution,
    get_network_health,
    search_patient_network,
    create_referral,
    get_referrals,
    update_referral_status,
    get_network_audits,
)
from app.models.schemas import (
    InstitutionCreate,
    NetworkSearchRequest,
    ReferralCreateRequest,
    ReferralStatusUpdateRequest,
)

router = APIRouter(prefix="/api/institutions", tags=["Institutions"])


@router.get("/")
def list_institutions():
    """Lista todos los nodos hospitalarios federados en la red."""
    return get_all_institutions()


@router.post("/")
def create_institution(data: InstitutionCreate):
    """Registra un nuevo hospital o clínica en el directorio interhospitalario."""
    return register_institution(
        clues=data.clues,
        nombre=data.nombre,
        ubicacion=data.ubicacion,
        nivel=data.nivel or "Segundo Nivel",
        red=data.red or "Red Sureste / SSY",
    )


@router.get("/status")
def network_status():
    """Estado en tiempo real de la Red Interhospitalaria (seguridad, cifrado y latencia)."""
    return get_network_health()


@router.post("/network-search")
def network_patient_search(req: NetworkSearchRequest):
    """
    Búsqueda federada de pacientes en todos los hospitales de la red.
    Aplica el Doble Envolvente de Privacidad:
    - Urgencias (Código Rojo): Safe Harbor con núcleo vital inmediato (sin notas confidenciales).
    - Interconsulta: Requiere consentimiento informado y habilita exportación FHIR.
    Registra de forma inmutable la auditoría NOM-024.
    """
    return search_patient_network(
        query=req.query,
        access_mode=req.access_mode,
        doctor_nombre=req.doctor_nombre or "Dr. Roberto Morales",
        doctor_cedula=req.doctor_cedula or "CED-9482710",
        clues_solicitante=req.clues_solicitante or "YUC-CR-001",
        hospital_solicitante=req.hospital_solicitante or "Cruz Roja Mexicana Delegación Mérida",
        justificacion=req.justificacion or "Atención médica hospitalaria"
    )


@router.get("/referrals")
def list_referrals(clues: Optional[str] = Query(None)):
    """Lista las referencias y contrarreferencias interhospitalarias NOM-004."""
    return get_referrals(clues_filtro=clues)


@router.post("/referrals")
def emit_referral(data: ReferralCreateRequest):
    """Emite una orden de referencia de paciente entre dos hospitales."""
    return create_referral(
        patient_curp=data.patient_curp,
        patient_nombre=data.patient_nombre,
        clues_origen=data.clues_origen,
        hospital_origen_nombre=data.hospital_origen_nombre,
        clues_destino=data.clues_destino,
        hospital_destino_nombre=data.hospital_destino_nombre,
        motivo_envio=data.motivo_envio,
        diagnostico_cie10=data.diagnostico_cie10,
        prioridad=data.prioridad,
        medico_solicitante=data.medico_solicitante,
        cedula_solicitante=data.cedula_solicitante,
        detalles_clinicos=data.detalles_clinicos
    )


@router.put("/referrals/{ref_id}/status")
def update_status(ref_id: str, data: ReferralStatusUpdateRequest):
    """Actualiza el estado de traslado o recepción de una referencia."""
    return update_referral_status(ref_id=ref_id, new_status=data.estado)


@router.get("/audits")
def list_audits(limit: int = Query(50)):
    """Bitácora inmutable de accesos interhospitalarios para cumplimiento NOM-024."""
    return get_network_audits(limit=limit)


@router.get("/capacity")
def get_live_hospital_capacity():
    """Monitoreo en tiempo real del censo de camas y personal médico activo por hospital."""
    capacities = get_network_hospital_capacities()
    tot_camas = sum(c["camas_totales"] for c in capacities)
    disp_camas = sum(c["camas_disponibles"] for c in capacities)
    disp_uci = sum(c["camas_uci_disp"] for c in capacities)
    med_activos = sum(c["medicos_turno"] for c in capacities)
    med_disp = sum(c["medicos_disponibles"] for c in capacities)
    
    return {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "total_hospitales": len(capacities),
        "resumen_red": {
            "camas_totales": tot_camas,
            "camas_disponibles": disp_camas,
            "camas_ocupadas": tot_camas - disp_camas,
            "camas_uci_disponibles": disp_uci,
            "medicos_en_turno": med_activos,
            "medicos_disponibles": med_disp,
            "tasa_ocupacion_promedio": round(((tot_camas - disp_camas) / tot_camas) * 100, 1) if tot_camas else 0
        },
        "hospitales": capacities
    }


@router.post("/capacity/{clues}")
def update_live_capacity_endpoint(clues: str, data: dict = Body(...)):
    """Actualiza el conteo de camas o médicos en tiempo real para un hospital."""
    res = update_hospital_live_capacity(clues, data)
    if not res:
        raise HTTPException(status_code=404, detail="Hospital CLUES no encontrado")
    return {"success": True, "hospital": res}
