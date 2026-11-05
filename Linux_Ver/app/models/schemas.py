from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class DatosDemograficos(BaseModel):
    nombre: Optional[str] = None
    curp: Optional[str] = None
    edad: Optional[str] = None
    sexo: Optional[str] = None


class MedicamentoDetallado(BaseModel):
    nombre: str
    dosis: Optional[str] = None
    via: Optional[str] = None
    periodicidad: Optional[str] = None


class NotaClinica(BaseModel):
    motivo_consulta: str = "No especificado"
    evolucion_padecimiento: str = "No especificado"
    exploracion_fisica: str = "No especificado"
    diagnostico_integral: str = "No especificado"
    pronostico: str = "No especificado"
    plan_tratamiento: str = "No especificado"


class EntidadesClinicas(BaseModel):
    demograficos: DatosDemograficos = DatosDemograficos()
    padecimientos: List[str] = []
    sintomas: List[str] = []
    signos_vitales: List[str] = []
    tratamientos: List[str] = []
    medicamentos: List[Any] = []  # Can be str or MedicamentoDetallado
    nota_clinica: NotaClinica = NotaClinica()


class CodigoCIE10(BaseModel):
    termino_original: str
    codigo: Optional[str] = None
    descripcion: Optional[str] = None
    similitud: float = 0.0


class ExpedientePaciente(BaseModel):
    id: str
    curp: str
    clues_institucion: str
    timestamp: str
    texto_original: str
    datos_demograficos: DatosDemograficos
    entidades_extraidas: Dict[str, Any]
    codigos_cie10: Dict[str, List[Dict[str, Any]]]
    nota_clinica: NotaClinica = NotaClinica()
    nota_medica_html: Optional[str] = None
    version: str = "2.0-NOM004"


class TextInputRequest(BaseModel):
    text: str
    curp: str
    clues: str


class InstitutionCreate(BaseModel):
    clues: str
    nombre: str
    ubicacion: Optional[str] = None


class PatientSearchResult(BaseModel):
    curp: str
    nombre: Optional[str]
    clues_institucion: str
    timestamp: str

