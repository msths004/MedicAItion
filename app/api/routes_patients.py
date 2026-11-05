"""
routes_patients.py — MedicAItion v3.0
=============================================
Endpoints para gestión de pacientes, perfiles, alergias, antecedentes y recordatorios.

Endpoints:
  GET    /api/patients/                        — Listar todos los pacientes
  POST   /api/patients/register                — Registrar nuevo paciente
  GET    /api/patients/search/semantic         — Búsqueda semántica (Nivel 1)
  GET    /api/patients/{curp}                  — Perfil completo del paciente
  PUT    /api/patients/{curp}                  — Editar datos del paciente
  GET    /api/patients/{curp}/exists           — Verificar si el paciente existe
  GET    /api/patients/{curp}/events           — Listar eventos del paciente
  POST   /api/patients/{curp}/events           — Crear nuevo evento clínico
  PUT    /api/patients/{curp}/events/{id}      — Renombrar / actualizar evento
  GET    /api/patients/{curp}/summary-ia       — Obtener/generar resumen IA

  # Auxiliares del perfil:
  POST   /api/patients/{curp}/alergias         — Agregar alergia
  DELETE /api/patients/{curp}/alergias/{id}    — Eliminar alergia
  POST   /api/patients/{curp}/antecedentes     — Agregar antecedente
  DELETE /api/patients/{curp}/antecedentes/{id} — Eliminar antecedente
  POST   /api/patients/{curp}/recordatorios    — Agregar recordatorio
  PATCH  /api/patients/{curp}/recordatorios/{id}/toggle — Marcar completado
  DELETE /api/patients/{curp}/recordatorios/{id} — Eliminar recordatorio
  POST   /api/patients/events/rename           — Renombrar evento (compat. legacy)
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Optional

from app.db.local_db import (
    register_patient,
    update_patient,
    get_patient_by_curp,
    get_all_patients,
    check_patient_exists,
    get_patient_events,
    create_evento_clinico,
    rename_clinical_event,
    search_patients_semantically,
    search_events_semantically,
    add_alergia,
    delete_alergia,
    add_antecedente,
    delete_antecedente,
    add_recordatorio,
    toggle_recordatorio,
    delete_recordatorio,
    delete_patient,
    get_patient_audit_logs,
)

router = APIRouter(prefix="/api/patients", tags=["Patients"])


# ── LISTADO Y BÚSQUEDA ───────────────────────────────────────────

@router.get("/")
def list_patients():
    return get_all_patients()


@router.get("/search/semantic")
def search_semantic(q: str):
    if not q or not q.strip():
        return []
    return search_patients_semantically(q)


# ── REGISTRO Y EDICIÓN ───────────────────────────────────────────

@router.post("/register", status_code=201)
def register_patient_endpoint(data: dict = Body(...)):
    """Registra un nuevo paciente con el formulario completo (25+ campos)."""
    try:
        return register_patient(data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar paciente: {str(e)}")


@router.get("/{curp}/exists")
def patient_exists(curp: str):
    """Verifica rápidamente si un paciente está registrado."""
    return {"exists": check_patient_exists(curp.upper())}


@router.get("/{curp}")
def get_patient(curp: str):
    """Devuelve el perfil completo del paciente incluyendo alergias, antecedentes y recordatorios."""
    patient = get_patient_by_curp(curp.upper())
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient


@router.put("/{curp}")
def edit_patient(curp: str, data: dict = Body(...)):
    """Edita los datos demográficos y de contacto del paciente (NUNCA las notas médicas)."""
    result = update_patient(curp.upper(), data)
    if not result:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return result


# ── EVENTOS CLÍNICOS ─────────────────────────────────────────────

@router.get("/{curp}/events")
def get_events(curp: str):
    """Lista todos los Eventos Clínicos de un paciente con conteo de consultas."""
    return get_patient_events(curp.upper())


@router.post("/{curp}/events", status_code=201)
def create_event(curp: str, data: dict = Body(...)):
    """Crea un nuevo Evento Clínico para un paciente registrado."""
    data["patient_curp"] = curp.upper()
    try:
        return create_evento_clinico(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear evento: {str(e)}")


@router.put("/{curp}/events/{event_id}")
def update_event(curp: str, event_id: str, data: dict = Body(...)):
    """Actualiza el nombre u otros campos editables del Evento Clínico."""
    new_name = data.get("nombre_evento")
    if not new_name or not new_name.strip():
        raise HTTPException(status_code=400, detail="El nombre del evento no puede estar vacío")
    success = rename_clinical_event(event_id, new_name.strip())
    if not success:
        raise HTTPException(status_code=404, detail="Evento clínico no encontrado")
    return {"status": "success", "message": "Evento actualizado exitosamente"}


@router.get("/{curp}/events/search")
def search_patient_events(curp: str, q: str):
    """Búsqueda semántica de eventos clínicos de un paciente (Nivel 2)."""
    if not q or not q.strip():
        return []
    return search_events_semantically(q, patient_curp=curp.upper())


# Endpoint legacy — compatible con el app.js actual
@router.post("/events/rename")
def rename_event(event_id: str = None, new_name: str = None, data: dict = Body(default={})):
    """[Legacy] Renombra un evento clínico. Soporta Form y JSON."""
    eid = event_id or data.get("event_id")
    name = new_name or data.get("new_name")
    if not eid or not name:
        raise HTTPException(status_code=400, detail="event_id y new_name son requeridos")
    success = rename_clinical_event(eid, name.strip())
    if not success:
        raise HTTPException(status_code=404, detail="Evento clínico no encontrado")
    return {"status": "success", "message": "Evento renombrado exitosamente"}


# ── RESUMEN IA ───────────────────────────────────────────────────

@router.get("/{curp}/summary-ia")
def get_summary_ia(curp: str):
    """Retorna el resumen IA cacheado del paciente (si existe)."""
    patient = get_patient_by_curp(curp.upper())
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return {
        "resumen_ia": patient.get("resumen_ia"),
        "resumen_ia_fecha": patient.get("resumen_ia_fecha"),
    }


# ── ALERGIAS ─────────────────────────────────────────────────────

@router.post("/{curp}/alergias", status_code=201)
def crear_alergia(curp: str, data: dict = Body(...)):
    if not check_patient_exists(curp.upper()):
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return add_alergia(curp.upper(), data)


@router.delete("/{curp}/alergias/{alergia_id}")
def eliminar_alergia(curp: str, alergia_id: str):
    success = delete_alergia(alergia_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alergia no encontrada")
    return {"status": "success"}


# ── ANTECEDENTES ─────────────────────────────────────────────────

@router.post("/{curp}/antecedentes", status_code=201)
def crear_antecedente(curp: str, data: dict = Body(...)):
    if not check_patient_exists(curp.upper()):
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return add_antecedente(curp.upper(), data)


@router.delete("/{curp}/antecedentes/{antecedente_id}")
def eliminar_antecedente(curp: str, antecedente_id: str):
    success = delete_antecedente(antecedente_id)
    if not success:
        raise HTTPException(status_code=404, detail="Antecedente no encontrado")
    return {"status": "success"}


# ── RECORDATORIOS ────────────────────────────────────────────────

@router.post("/{curp}/recordatorios", status_code=201)
def crear_recordatorio(curp: str, data: dict = Body(...)):
    if not check_patient_exists(curp.upper()):
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return add_recordatorio(curp.upper(), data)


@router.patch("/{curp}/recordatorios/{recordatorio_id}/toggle")
def toggle_rec(curp: str, recordatorio_id: str):
    success = toggle_recordatorio(recordatorio_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recordatorio no encontrado")
    return {"status": "success"}


@router.delete("/{curp}/recordatorios/{recordatorio_id}")
def eliminar_recordatorio(curp: str, recordatorio_id: str):
    success = delete_recordatorio(recordatorio_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recordatorio no encontrado")
    return {"status": "success"}


# ── AUDITORÍA Y ELIMINACIÓN ──────────────────────────────────────

@router.delete("/{curp}")
def delete_patient_endpoint(curp: str):
    """Elimina físicamente al paciente y todos sus registros en cascada."""
    success = delete_patient(curp.upper())
    if not success:
        raise HTTPException(status_code=404, detail="Paciente no encontrado o error al eliminar")
    return {"status": "success", "message": f"Paciente con CURP {curp} eliminado exitosamente."}


@router.get("/{curp}/audit-logs")
def get_audit_logs(curp: str):
    """Devuelve los logs de auditoría para un paciente específico."""
    return get_patient_audit_logs(curp.upper())
