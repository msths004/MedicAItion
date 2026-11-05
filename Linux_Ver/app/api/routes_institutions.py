from fastapi import APIRouter
from app.db.global_db import get_all_institutions, register_institution
from app.models.schemas import InstitutionCreate

router = APIRouter(prefix="/api/institutions", tags=["Institutions"])


@router.get("/")
def list_institutions():
    return get_all_institutions()


@router.post("/")
def create_institution(data: InstitutionCreate):
    return register_institution(data.clues, data.nombre, data.ubicacion)
