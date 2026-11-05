from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

GLOBAL_DB_PATH = os.getenv("GLOBAL_DB_PATH", "data/medicaition_global.db")
DATABASE_URL = f"sqlite:///{GLOBAL_DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Institution(Base):
    __tablename__ = "institutions"

    clues = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    ubicacion = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PatientIndex(Base):
    __tablename__ = "patient_index"

    curp = Column(String, primary_key=True)
    clues_institucion = Column(String, nullable=False)
    nombre = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


def register_institution(clues: str, nombre: str, ubicacion: str = None) -> dict:
    db = SessionLocal()
    try:
        inst = db.query(Institution).filter(Institution.clues == clues).first()
        if not inst:
            inst = Institution(clues=clues, nombre=nombre, ubicacion=ubicacion)
            db.add(inst)
            db.commit()
        return {"clues": inst.clues, "nombre": inst.nombre, "ubicacion": inst.ubicacion}
    finally:
        db.close()


def index_patient(curp: str, clues: str, nombre: str = None):
    db = SessionLocal()
    try:
        existing = db.query(PatientIndex).filter(PatientIndex.curp == curp).first()
        if existing:
            existing.clues_institucion = clues
            existing.nombre = nombre
            existing.updated_at = datetime.utcnow()
        else:
            db.add(PatientIndex(curp=curp, clues_institucion=clues, nombre=nombre))
        db.commit()
    finally:
        db.close()


def find_patient_institution(curp: str) -> str | None:
    db = SessionLocal()
    try:
        entry = db.query(PatientIndex).filter(PatientIndex.curp == curp).first()
        return entry.clues_institucion if entry else None
    finally:
        db.close()


def get_all_institutions() -> list:
    db = SessionLocal()
    try:
        return [
            {"clues": i.clues, "nombre": i.nombre, "ubicacion": i.ubicacion}
            for i in db.query(Institution).all()
        ]
    finally:
        db.close()
