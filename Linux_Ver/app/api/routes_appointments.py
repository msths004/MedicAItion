"""
routes_appointments.py — MedicAItion Sprint 2
==============================================
Agenda médica persistente en SQLite + flujo de Sala de Espera / Triaje.

Endpoints:
  GET    /api/appointments/                 — Listar citas (filtros: year, date, curp)
  GET    /api/appointments/today            — Cola del día ordenada por prioridad de triaje
  POST   /api/appointments/                 — Crear cita
  PATCH  /api/appointments/{id}             — Actualizar estado / triaje / datos
  DELETE /api/appointments/{id}             — Eliminar cita
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, HTTPException

from app.db.local_db import SessionLocal, Appointment

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

VALID_STATUS = ["Programada", "En Sala / Triaje", "En Consulta", "Atendida", "No asistió"]
VALID_TRIAGE = ["ROJO", "NARANJA", "AMARILLO", "VERDE"]
TRIAGE_ORDER = {"ROJO": 0, "NARANJA": 1, "AMARILLO": 2, "VERDE": 3}
STATUS_ORDER = {"En Consulta": 0, "En Sala / Triaje": 1, "Programada": 2, "Atendida": 3, "No asistió": 4}


def appointment_to_dict(a: Appointment) -> dict:
    return {
        "id": a.id,
        "curp": a.patient_curp or "",
        "patientName": a.patient_name,
        "date": a.date_str,
        "time": a.time_str,
        "reason": a.reason,
        "status": a.status,
        "triage": a.triage_level,
        "wearable": bool(a.wearable),
        "wearableText": a.wearable_text or "",
        "doctor": a.doctor_nombre,
        "clues": a.clues_institucion,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _validate_date(date_str: str) -> str:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Fecha inválida. Formato requerido: YYYY-MM-DD")
    return date_str


def _validate_time(time_str: str) -> str:
    try:
        datetime.strptime(time_str, "%H:%M")
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Hora inválida. Formato requerido: HH:MM")
    return time_str


@router.get("/")
def list_appointments(year: Optional[int] = None, date: Optional[str] = None, curp: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(Appointment)
        if year:
            q = q.filter(Appointment.date_str.like(f"{year}-%"))
        if date:
            q = q.filter(Appointment.date_str == date)
        if curp:
            q = q.filter(Appointment.patient_curp == curp.upper())
        rows = q.order_by(Appointment.date_str.asc(), Appointment.time_str.asc()).all()
        return [appointment_to_dict(a) for a in rows]
    finally:
        db.close()


@router.get("/today")
def today_queue():
    """Cola de trabajo del día: primero en consulta, luego sala por prioridad de triaje y hora."""
    today = datetime.now().strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        rows = db.query(Appointment).filter(Appointment.date_str == today).all()
        items = [appointment_to_dict(a) for a in rows]
        items.sort(key=lambda x: (
            STATUS_ORDER.get(x["status"], 9),
            TRIAGE_ORDER.get(x["triage"], 9),
            x["time"],
        ))
        pending = [i for i in items if i["status"] in ("Programada", "En Sala / Triaje", "En Consulta")]
        return {
            "date": today,
            "total": len(items),
            "pendientes": len(pending),
            "atendidas": len([i for i in items if i["status"] == "Atendida"]),
            "en_sala": len([i for i in items if i["status"] == "En Sala / Triaje"]),
            "criticos": len([i for i in pending if i["triage"] in ("ROJO", "NARANJA")]),
            "items": items,
        }
    finally:
        db.close()


@router.post("/", status_code=201)
def create_appointment(data: dict = Body(...)):
    name = (data.get("patientName") or data.get("patient_name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="El nombre del paciente es obligatorio")
    date_str = _validate_date(data.get("date"))
    time_str = _validate_time(data.get("time") or "09:00")
    reason = (data.get("reason") or "Consulta general").strip()
    status = data.get("status") or "Programada"
    triage = (data.get("triage") or "VERDE").upper()
    if status not in VALID_STATUS:
        raise HTTPException(status_code=422, detail=f"Estado inválido. Opciones: {VALID_STATUS}")
    if triage not in VALID_TRIAGE:
        raise HTTPException(status_code=422, detail=f"Triaje inválido. Opciones: {VALID_TRIAGE}")

    db = SessionLocal()
    try:
        appt = Appointment(
            patient_curp=(data.get("curp") or "").strip().upper() or None,
            patient_name=name,
            date_str=date_str,
            time_str=time_str,
            reason=reason,
            status=status,
            triage_level=triage,
            wearable=bool(data.get("wearable")),
            wearable_text=data.get("wearableText") or ("Wearable vinculado" if data.get("wearable") else None),
            doctor_nombre=data.get("doctor") or "Dr. Roberto M.",
            clues_institucion=data.get("clues") or "YUC-CR-001",
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)
        return appointment_to_dict(appt)
    finally:
        db.close()


@router.patch("/{appt_id}")
def update_appointment(appt_id: str, data: dict = Body(...)):
    db = SessionLocal()
    try:
        appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
        if not appt:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

        if "status" in data:
            if data["status"] not in VALID_STATUS:
                raise HTTPException(status_code=422, detail=f"Estado inválido. Opciones: {VALID_STATUS}")
            appt.status = data["status"]
        if "triage" in data:
            tri = str(data["triage"]).upper()
            if tri not in VALID_TRIAGE:
                raise HTTPException(status_code=422, detail=f"Triaje inválido. Opciones: {VALID_TRIAGE}")
            appt.triage_level = tri
        if "date" in data:
            appt.date_str = _validate_date(data["date"])
        if "time" in data:
            appt.time_str = _validate_time(data["time"])
        if "reason" in data and str(data["reason"]).strip():
            appt.reason = str(data["reason"]).strip()
        if "patientName" in data and str(data["patientName"]).strip():
            appt.patient_name = str(data["patientName"]).strip()
        if "curp" in data:
            appt.patient_curp = (str(data["curp"]).strip().upper() or None)

        appt.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(appt)
        return appointment_to_dict(appt)
    finally:
        db.close()


@router.delete("/{appt_id}")
def delete_appointment(appt_id: str):
    db = SessionLocal()
    try:
        appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
        if not appt:
            raise HTTPException(status_code=404, detail="Cita no encontrada")
        db.delete(appt)
        db.commit()
        return {"status": "deleted", "id": appt_id}
    finally:
        db.close()
