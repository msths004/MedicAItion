from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
import json
import uuid
import os

load_dotenv()

LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "data/medicaition_local.db")
DATABASE_URL = f"sqlite:///{LOCAL_DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Patient(Base):
    """Tabla maestra de pacientes. Un registro por CURP."""
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    curp = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=True)
    clues_institucion = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con las notas de evolución
    notas = relationship("NotaEvolucion", back_populates="patient", order_by="NotaEvolucion.created_at.desc()")


class NotaEvolucion(Base):
    """
    Cada consulta/visita genera una nota de evolución.
    Conforme a la NOM-004-SSA3-2012, TODAS las notas deben preservarse.
    Un paciente puede tener múltiples notas a lo largo del tiempo.
    """
    __tablename__ = "notas_evolucion"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_curp = Column(String, ForeignKey("patients.curp"), nullable=False, index=True)
    texto_original = Column(Text)
    json_record = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="notas")


def create_tables():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


def save_patient(record: dict) -> dict:
    """
    Guarda un nuevo registro de paciente.
    - Si el paciente (CURP) ya existe, AGREGA una nueva nota de evolución.
    - Si es nuevo, crea el paciente Y la primera nota.
    Nunca sobreescribe datos anteriores (requisito NOM-004).
    """
    db = SessionLocal()
    try:
        curp = record["curp"]
        existing = db.query(Patient).filter(Patient.curp == curp).first()

        if existing:
            # Actualizar nombre si el LLM lo extrajo ahora
            nombre = record.get("datos_demograficos", {}).get("nombre")
            if nombre:
                existing.nombre = nombre
            existing.updated_at = datetime.utcnow()
        else:
            # Crear paciente nuevo
            patient = Patient(
                id=record["id"],
                curp=curp,
                nombre=record.get("datos_demograficos", {}).get("nombre"),
                clues_institucion=record["clues_institucion"],
            )
            db.add(patient)

        # SIEMPRE crear una nueva nota de evolución (append, nunca overwrite)
        nota = NotaEvolucion(
            id=str(uuid.uuid4()),
            patient_curp=curp,
            texto_original=record.get("texto_original", ""),
            json_record=json.dumps(record, ensure_ascii=False),
        )
        db.add(nota)
        db.commit()
        return record
    finally:
        db.close()


def get_patient_by_curp(curp: str) -> dict | None:
    """
    Devuelve la nota de evolución MÁS RECIENTE del paciente.
    Esto mantiene la compatibilidad con el resto de la app.
    """
    db = SessionLocal()
    try:
        nota = (
            db.query(NotaEvolucion)
            .filter(NotaEvolucion.patient_curp == curp)
            .order_by(NotaEvolucion.created_at.desc())
            .first()
        )
        return json.loads(nota.json_record) if nota else None
    finally:
        db.close()


def get_patient_history(curp: str) -> list:
    """Devuelve TODAS las notas de evolución de un paciente, de más reciente a más antigua."""
    db = SessionLocal()
    try:
        notas = (
            db.query(NotaEvolucion)
            .filter(NotaEvolucion.patient_curp == curp)
            .order_by(NotaEvolucion.created_at.desc())
            .all()
        )
        return [json.loads(n.json_record) for n in notas]
    finally:
        db.close()


def get_all_patients() -> list:
    db = SessionLocal()
    try:
        patients = db.query(Patient).order_by(Patient.updated_at.desc()).all()
        return [
            {
                "curp": p.curp,
                "nombre": p.nombre,
                "clues_institucion": p.clues_institucion,
                "timestamp": p.updated_at.isoformat() if p.updated_at else None,
                "num_notas": len(p.notas),
            }
            for p in patients
        ]
    finally:
        db.close()
