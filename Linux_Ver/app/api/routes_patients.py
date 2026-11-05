from fastapi import APIRouter, HTTPException
from app.db.local_db import get_patient_by_curp, get_all_patients

router = APIRouter(prefix="/api/patients", tags=["Patients"])


@router.get("/")
def list_patients():
    return get_all_patients()


@router.get("/{curp}")
def get_patient(curp: str):
    patient = get_patient_by_curp(curp)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient
