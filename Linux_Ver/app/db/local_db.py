"""
local_db.py — MedicAItion v3.0
==================================
Esquema completo de base de datos local SQLite (SQLAlchemy).

Tablas:
  - Patient          : 25+ campos (demografia, contacto, seguros, métricas físicas)
  - EventoClinico    : Evento clínico agrupador (un padecimiento)
  - Consulta         : Cada visita; nota/receta/entidades en columnas separadas (NOM-004 inmutable)
  - Alergia          : Alergias del paciente (editable)
  - Antecedente      : Antecedentes médicos (editable)
  - Recordatorio     : Recordatorios/alertas del perfil (editable)

Notas de diseño:
  - BMI y edad NO se guardan; se calculan al vuelo (altura/peso → BMI, fecha_nacimiento → edad).
  - Consultas son INMUTABLES una vez creadas (NOM-004-SSA3-2012).
  - Datos demográficos/contacto del paciente SÍ son editables.
  - La indexación semántica en ChromaDB se hace por separado y de forma asíncrona.
"""

from sqlalchemy import (
    create_engine, Column, String, Text, DateTime,
    Float, ForeignKey, Boolean
)
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


# ─────────────────────────────────────────────────────────────────
# MODELO: Patient
# ─────────────────────────────────────────────────────────────────

class Patient(Base):
    """
    Tabla maestra de pacientes.
    Todos los datos demográficos, de contacto y métricas físicas viven aquí.
    BMI y edad se calculan al vuelo — nunca se persisten.
    """
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # ── Obligatorios ──────────────────────────────────────────────
    primer_apellido  = Column(String, nullable=False, default="")
    segundo_apellido = Column(String, nullable=False, default="")
    nombres          = Column(String, nullable=False, default="")
    fecha_nacimiento = Column(String, nullable=True)          # ISO date string: "YYYY-MM-DD"
    sexo             = Column(String, nullable=True)          # "M" / "F" / "Otro"
    curp             = Column(String, unique=True, index=True, nullable=False)
    folio_hospital   = Column(String, nullable=True)          # Pendiente de definir generación
    ubicacion_casa   = Column(String, nullable=True)

    # ── Identificadores ────────────────────────────────────────────
    rfc                 = Column(String, nullable=True)
    nss                 = Column(String, nullable=True)
    expediente_externo  = Column(String, nullable=True)
    nacionalidad        = Column(String, nullable=True, default="Mexicana")
    lugar_nacimiento    = Column(String, nullable=True)

    # ── Perfil social ──────────────────────────────────────────────
    estado_civil     = Column(String, nullable=True)
    ocupacion        = Column(String, nullable=True)
    tipo_paciente    = Column(String, nullable=True)
    programa_medico  = Column(String, nullable=True)

    # ── Comunicación ───────────────────────────────────────────────
    telefono_local  = Column(String, nullable=True)
    celular         = Column(String, nullable=True)
    email           = Column(String, nullable=True)

    # ── Emergencias ────────────────────────────────────────────────
    contacto_emergencia_nombre = Column(String, nullable=True)
    contacto_emergencia_tel    = Column(String, nullable=True)

    # ── Seguros / Anotaciones ─────────────────────────────────────
    aseguradoras         = Column(Text, nullable=True)   # JSON array de strings
    anotaciones_generales = Column(Text, nullable=True)

    # ── Métricas físicas (editables post-registro) ────────────────
    altura_cm   = Column(Float, nullable=True)
    peso_kg     = Column(Float, nullable=True)
    tipo_sangre = Column(String, nullable=True)

    # ── Resumen IA (caché, regenerado al crear nuevas consultas) ──
    resumen_ia        = Column(Text, nullable=True)
    resumen_ia_fecha  = Column(DateTime, nullable=True)

    # ── CLUES de la institución ────────────────────────────────────
    clues_institucion = Column(String, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relaciones ────────────────────────────────────────────────
    eventos      = relationship("EventoClinico", back_populates="patient",
                                cascade="all, delete-orphan",
                                order_by="EventoClinico.updated_at.desc()")
    alergias     = relationship("Alergia",     back_populates="patient", cascade="all, delete-orphan")
    antecedentes = relationship("Antecedente", back_populates="patient", cascade="all, delete-orphan")
    recordatorios = relationship("Recordatorio", back_populates="patient", cascade="all, delete-orphan")

    # ── Propiedad derivada: nombre completo ───────────────────────
    @property
    def nombre_completo(self):
        parts = [self.primer_apellido, self.segundo_apellido, self.nombres]
        return " ".join(p for p in parts if p).strip()


# ─────────────────────────────────────────────────────────────────
# MODELO: EventoClinico
# ─────────────────────────────────────────────────────────────────

class EventoClinico(Base):
    """
    Agrupa consultas de un paciente bajo un mismo padecimiento/motivo.
    Un evento puede tener N consultas (visitas médicas).
    El nombre del evento es editable; las consultas son inmutables.
    """
    __tablename__ = "eventos_clinicos"

    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_curp  = Column(String, ForeignKey("patients.curp"), nullable=False, index=True)
    nombre_evento = Column(String, nullable=False)
    doctor_creador = Column(String, nullable=True)
    fecha_hora_creacion = Column(DateTime, default=datetime.utcnow)
    resumen       = Column(Text, nullable=True)    # Resumen inicial (editable)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient    = relationship("Patient", back_populates="eventos")
    consultas  = relationship("Consulta", back_populates="evento",
                              cascade="all, delete-orphan",
                              order_by="Consulta.fecha_hora.asc()")


# ─────────────────────────────────────────────────────────────────
# MODELO: Consulta  (INMUTABLE por NOM-004-SSA3-2012)
# ─────────────────────────────────────────────────────────────────

class Consulta(Base):
    """
    Cada visita médica genera una consulta.
    Los documentos médicos (nota, receta) son INMUTABLES una vez creados.

    Columnas separadas (en lugar de un blob JSON único):
      - nota_medica_json  : Estructura NOM-004 (motivo, evolución, dx, plan, etc.)
      - receta_json       : Medicamentos, dosis, instrucciones
      - entidades_json    : CIE-10, síntomas detectados, diagnósticos
      - texto_original    : Transcripción cruda de audio o texto dictado

    Para correcciones, se crea una nota addendum en `notas_addendum`
    (campo de texto libre) — nunca se modifica la nota original.
    """
    __tablename__ = "consultas"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evento_id    = Column(String, ForeignKey("eventos_clinicos.id"), nullable=False, index=True)
    patient_curp = Column(String, ForeignKey("patients.curp"), nullable=False, index=True)

    doctor_nombre      = Column(String, nullable=True)
    cedula_profesional = Column(String, nullable=True)
    fecha_hora         = Column(DateTime, default=datetime.utcnow)
    resumen_doctor  = Column(Text, nullable=True)    # Notas del doctor (opcional)

    # ── Documentos médicos (columnas separadas) ──────────────────
    nota_medica_json = Column(Text, nullable=True)   # JSON: estructura NOM-004
    receta_json      = Column(Text, nullable=True)   # JSON: medicamentos + instrucciones
    entidades_json   = Column(Text, nullable=True)   # JSON: CIE-10 + síntomas + dx
    texto_original   = Column(Text, nullable=True)   # Transcripción cruda
    texto_redactado  = Column(Text, nullable=True)   # Resumen formal de la IA

    # ── Addenda (no modifica la nota original, solo agrega) ──────
    notas_addendum = Column(Text, nullable=True)

    # ── Timestamp de creación (NUNCA se modifica) ────────────────
    created_at = Column(DateTime, default=datetime.utcnow)

    evento  = relationship("EventoClinico", back_populates="consultas")


# ─────────────────────────────────────────────────────────────────
# MODELOS AUXILIARES DEL PERFIL
# ─────────────────────────────────────────────────────────────────

class Alergia(Base):
    """Alergias del paciente. Editables desde el perfil."""
    __tablename__ = "alergias"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_curp = Column(String, ForeignKey("patients.curp"), nullable=False, index=True)
    descripcion  = Column(String, nullable=False)
    tipo         = Column(String, nullable=True)   # "Medicamento", "Alimento", "Ambiental", etc.
    severidad    = Column(String, nullable=True)   # "Leve", "Moderada", "Severa"
    created_at   = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="alergias")


class Antecedente(Base):
    """Antecedentes médicos del paciente. Editables desde el perfil."""
    __tablename__ = "antecedentes"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_curp = Column(String, ForeignKey("patients.curp"), nullable=False, index=True)
    tipo         = Column(String, nullable=True)   # "Hereditario", "Patológico", "Quirúrgico", etc.
    descripcion  = Column(Text, nullable=False)
    fecha        = Column(String, nullable=True)   # Fecha aproximada (libre)
    created_at   = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="antecedentes")


class Recordatorio(Base):
    """Recordatorios / alertas del perfil del paciente. Editables."""
    __tablename__ = "recordatorios"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_curp = Column(String, ForeignKey("patients.curp"), nullable=False, index=True)
    titulo       = Column(String, nullable=False)
    descripcion  = Column(Text, nullable=True)
    fecha_alerta = Column(DateTime, nullable=True)
    completado   = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="recordatorios")


class AuditLog(Base):
    """
    Tabla de logs de auditoría para trazabilidad.
    No se elimina el log cuando se elimina el paciente.
    """
    __tablename__ = "audit_logs"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp    = Column(DateTime, default=datetime.utcnow)
    action       = Column(String, nullable=False)   # "REGISTRO", "ACTUALIZACION", "ELIMINACION"
    patient_curp = Column(String, nullable=False, index=True)
    operator     = Column(String, nullable=False, default="Médico")
    details      = Column(Text, nullable=True)      # JSON: datos o cambios


class Appointment(Base):
    """
    Citas médicas y flujo de sala de espera / triaje persistidas en SQLite.
    """
    __tablename__ = "appointments"

    id                = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_curp      = Column(String, nullable=True, index=True)
    patient_name      = Column(String, nullable=False)
    date_str          = Column(String, nullable=False, index=True)   # "YYYY-MM-DD"
    time_str          = Column(String, nullable=False, default="09:00")
    reason            = Column(String, nullable=False, default="Consulta general")
    status            = Column(String, nullable=False, default="Programada")  # Programada | En Sala / Triaje | En Consulta | Atendida | No asistió
    triage_level      = Column(String, nullable=False, default="VERDE")       # ROJO | NARANJA | AMARILLO | VERDE
    wearable          = Column(Boolean, default=False)
    wearable_text     = Column(String, nullable=True)
    doctor_nombre     = Column(String, nullable=True, default="Dr. Roberto M.")
    clues_institucion = Column(String, nullable=True, default="YUC-CR-001")
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VitalReading(Base):
    """
    Lecturas biométricas de Wearables (Web Bluetooth BLE / CSV / JSON / Manual).
    """
    __tablename__ = "vital_readings"

    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_curp  = Column(String, nullable=True, index=True)
    patient_name  = Column(String, nullable=True)
    device_name   = Column(String, nullable=False, default="Sensor BLE")
    source        = Column(String, nullable=False, default="wearable")  # ble | csv | manual | wearable
    heart_rate    = Column(Float, nullable=True)
    spo2          = Column(Float, nullable=True)
    systolic_bp   = Column(Float, nullable=True)
    diastolic_bp  = Column(Float, nullable=True)
    temperature   = Column(Float, nullable=True)
    steps         = Column(Float, nullable=True)
    alert_flag    = Column(Boolean, default=False)
    alert_message = Column(String, nullable=True)
    recorded_at   = Column(DateTime, default=datetime.utcnow, index=True)


class PatientDailyLog(Base):
    """
    Bitácora diaria del ciudadano / paciente ("Mi Salud Hoy"):
    automedición de presión, glucosa, temperatura, peso, adherencia a medicamentos y síntomas.
    """
    __tablename__ = "patient_daily_logs"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_curp     = Column(String, ForeignKey("patients.curp"), nullable=False, index=True)
    systolic_bp      = Column(Float, nullable=True)
    diastolic_bp     = Column(Float, nullable=True)
    glucose_mg_dl    = Column(Float, nullable=True)
    temperature_c    = Column(Float, nullable=True)
    weight_kg        = Column(Float, nullable=True)
    medication_taken = Column(Boolean, default=True)
    mood_or_pain     = Column(String, nullable=True)
    symptoms_note    = Column(Text, nullable=True)
    alert_flag       = Column(Boolean, default=False)
    alert_message    = Column(String, nullable=True)
    recorded_at      = Column(DateTime, default=datetime.utcnow, index=True)


class PractitionerProfile(Base):
    """
    Perfiles profesionales y control de acceso por roles (Médico, Enfermería, Recepción, Administrador)
    con registro de Cédula Profesional para trazabilidad NOM-004 / NOM-024.
    """
    __tablename__ = "practitioner_profiles"

    id                 = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    role               = Column(String, nullable=False, unique=True, index=True)
    full_name          = Column(String, nullable=False)
    cedula_profesional = Column(String, nullable=True)
    specialty          = Column(String, nullable=True)
    clues_institucion  = Column(String, nullable=True, default="YUC-CR-001")
    is_active          = Column(Boolean, default=False)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _seed_sprint2_defaults():
    """Siembra citas y lecturas iniciales si las tablas nuevas están vacías."""
    db = SessionLocal()
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        if db.query(Appointment).count() == 0:
            from datetime import timedelta
            y = datetime.now().year
            plus3 = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
            seeds = [
                Appointment(
                    patient_curp="GOPC790814HYNCLN04",
                    patient_name="Carlos Manuel G.",
                    date_str=today_str,
                    time_str="09:00",
                    reason="Consulta de seguimiento",
                    status="En Sala / Triaje",
                    triage_level="VERDE",
                    wearable=True,
                    wearable_text="Garmin Active • ❤️ 72 lpm",
                ),
                Appointment(
                    patient_curp="MOBK070228HYNRTVA3",
                    patient_name="Kevin Enrique M.",
                    date_str=today_str,
                    time_str="09:45",
                    reason="Dolor abdominal",
                    status="Programada",
                    triage_level="AMARILLO",
                    wearable=True,
                    wearable_text="Apple Watch S9 • Wearable conectado",
                ),
                Appointment(
                    patient_curp="TESTCURP1234567890",
                    patient_name="Juan Pérez G.",
                    date_str=today_str,
                    time_str="10:30",
                    reason="Control general",
                    status="Programada",
                    triage_level="VERDE",
                    wearable=True,
                    wearable_text="Galaxy Watch 6 • Sincronizado",
                ),
                Appointment(
                    patient_curp="GOPC790814HYNCLN04",
                    patient_name="Carlos Manuel G.",
                    date_str=plus3,
                    time_str="11:15",
                    reason="Revisión de laboratorios (HbA1c y Lípidos)",
                    status="Programada",
                    triage_level="VERDE",
                    wearable=True,
                    wearable_text="Garmin Active conectado",
                ),
                Appointment(
                    patient_curp="TESTCURP1234567890",
                    patient_name="Juan Pérez G.",
                    date_str=f"{y}-12-10",
                    time_str="10:00",
                    reason="Control hipertensión trimestral",
                    status="Programada",
                    triage_level="VERDE",
                    wearable=False,
                ),
            ]
            db.add_all(seeds)

        if db.query(VitalReading).count() == 0:
            vitals_seeds = [
                VitalReading(
                    patient_curp="GOPC790814HYNCLN04",
                    patient_name="Carlos Manuel G.",
                    device_name="Garmin Active",
                    source="wearable",
                    heart_rate=72,
                    spo2=98,
                    systolic_bp=122,
                    diastolic_bp=78,
                    temperature=36.5,
                    steps=5840,
                    alert_flag=False,
                ),
                VitalReading(
                    patient_curp="MOBK070228HYNRTVA3",
                    patient_name="Kevin Enrique M.",
                    device_name="Apple Watch S9",
                    source="wearable",
                    heart_rate=82,
                    spo2=98,
                    systolic_bp=120,
                    diastolic_bp=78,
                    temperature=36.8,
                    steps=4120,
                    alert_flag=False,
                ),
                VitalReading(
                    patient_curp="TESTCURP1234567890",
                    patient_name="Juan Pérez G.",
                    device_name="Galaxy Watch 6",
                    source="wearable",
                    heart_rate=74,
                    spo2=99,
                    systolic_bp=124,
                    diastolic_bp=80,
                    temperature=36.5,
                    steps=6420,
                    alert_flag=False,
                ),
            ]
            db.add_all(vitals_seeds)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB] Error sembrando datos iniciales Sprint 2: {e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# INICIALIZACIÓN DE TABLAS
# ─────────────────────────────────────────────────────────────────

def create_tables():
    """Crea todas las tablas si no existen. Es idempotente (seguro de llamar múltiples veces)."""
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    
    # Migración automática para la columna texto_redactado en consultas
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("consultas")]
    if "texto_redactado" not in columns:
        print("[DB] Migración: Agregando columna 'texto_redactado' a la tabla 'consultas'...")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE consultas ADD COLUMN texto_redactado TEXT;"))
        print("[DB] Migración completada: Columna 'texto_redactado' agregada ✅")

    if "cedula_profesional" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE consultas ADD COLUMN cedula_profesional TEXT;"))

    p_columns = [col["name"] for col in inspector.get_columns("patients")]
    if "tipo_sangre" not in p_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE patients ADD COLUMN tipo_sangre TEXT;"))

    _seed_sprint2_defaults()
    _seed_sprint3_defaults()
    _seed_sprint4_defaults()
    print("[DB] Tablas verificadas/creadas correctamente.")


# ─────────────────────────────────────────────────────────────────
# FUNCIONES: PACIENTES
# ─────────────────────────────────────────────────────────────────

def register_patient(data: dict) -> dict:
    """
    Registra un nuevo paciente en el sistema.
    Si ya existe un paciente con ese CURP, lanza ValueError.
    """
    db = SessionLocal()
    try:
        curp = data.get("curp", "").strip().upper()
        if not curp:
            raise ValueError("El CURP/ID del paciente es obligatorio.")

        existing = db.query(Patient).filter(Patient.curp == curp).first()
        if existing:
            raise ValueError(f"Ya existe un paciente registrado con CURP/ID: {curp}")

        patient = Patient(
            id=str(uuid.uuid4()),
            curp=curp,
            primer_apellido=data.get("primer_apellido", "").strip(),
            segundo_apellido=data.get("segundo_apellido", "").strip(),
            nombres=data.get("nombres", "").strip(),
            fecha_nacimiento=data.get("fecha_nacimiento"),
            sexo=data.get("sexo"),
            folio_hospital=data.get("folio_hospital"),
            ubicacion_casa=data.get("ubicacion_casa"),
            rfc=data.get("rfc"),
            nss=data.get("nss"),
            expediente_externo=data.get("expediente_externo"),
            nacionalidad=data.get("nacionalidad", "Mexicana"),
            lugar_nacimiento=data.get("lugar_nacimiento"),
            estado_civil=data.get("estado_civil"),
            ocupacion=data.get("ocupacion"),
            tipo_paciente=data.get("tipo_paciente"),
            programa_medico=data.get("programa_medico"),
            telefono_local=data.get("telefono_local"),
            celular=data.get("celular"),
            email=data.get("email"),
            contacto_emergencia_nombre=data.get("contacto_emergencia_nombre"),
            contacto_emergencia_tel=data.get("contacto_emergencia_tel"),
            aseguradoras=json.dumps(data.get("aseguradoras", []), ensure_ascii=False),
            anotaciones_generales=data.get("anotaciones_generales"),
            altura_cm=data.get("altura_cm"),
            peso_kg=data.get("peso_kg"),
            tipo_sangre=data.get("tipo_sangre"),
            clues_institucion=data.get("clues_institucion"),
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        # Log audit action
        log_audit_action(
            action="REGISTRO",
            patient_curp=curp,
            operator="Personal Administrativo",
            details_dict=data,
            db=db
        )

        try:
            index_patient_profile_semantically(data)
        except Exception:
            pass

        return _patient_to_dict(patient)
    finally:
        db.close()


def update_patient(curp: str, data: dict) -> dict | None:
    """
    Actualiza datos demográficos y de contacto del paciente.
    NUNCA toca consultas ni notas médicas.
    """
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.curp == curp).first()
        if not patient:
            return None

        diff = {}
        editable_fields = [
            "primer_apellido", "segundo_apellido", "nombres", "fecha_nacimiento",
            "sexo", "folio_hospital", "ubicacion_casa", "rfc", "nss",
            "expediente_externo", "nacionalidad", "lugar_nacimiento", "estado_civil",
            "ocupacion", "tipo_paciente", "programa_medico", "telefono_local",
            "celular", "email", "contacto_emergencia_nombre", "contacto_emergencia_tel",
            "anotaciones_generales", "altura_cm", "peso_kg", "tipo_sangre", "clues_institucion",
        ]
        for field in editable_fields:
            if field in data:
                old_val = getattr(patient, field)
                new_val = data[field]
                if old_val != new_val:
                    diff[field] = {"old": old_val, "new": new_val}

        if "aseguradoras" in data:
            old_aseg = json.loads(patient.aseguradoras) if patient.aseguradoras else []
            new_aseg = data["aseguradoras"]
            if old_aseg != new_aseg:
                diff["aseguradoras"] = {"old": old_aseg, "new": new_aseg}

        # Apply updates
        for field in editable_fields:
            if field in data:
                setattr(patient, field, data[field])

        if "aseguradoras" in data:
            patient.aseguradoras = json.dumps(data["aseguradoras"], ensure_ascii=False)

        if diff:
            log_audit_action(
                action="ACTUALIZACION",
                patient_curp=curp,
                operator="Médico",
                details_dict=diff,
                db=db
            )

        patient.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(patient)
        return _patient_to_dict(patient)
    finally:
        db.close()


def get_patient_by_curp(curp: str) -> dict | None:
    """Devuelve el perfil completo del paciente (sin consultas)."""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.curp == curp).first()
        if not patient:
            return None
        return _patient_to_dict(patient, include_auxiliaries=True)
    finally:
        db.close()


def check_patient_exists(curp: str) -> bool:
    """Verifica rápido si el paciente existe en la BD."""
    db = SessionLocal()
    try:
        return db.query(Patient.id).filter(Patient.curp == curp).scalar() is not None
    finally:
        db.close()


def get_all_patients() -> list:
    """Lista todos los pacientes con info básica para la lista del Gestor."""
    db = SessionLocal()
    try:
        patients = db.query(Patient).order_by(Patient.updated_at.desc()).all()
        return [
            {
                "curp": p.curp,
                "nombre": p.nombre_completo,
                "nombre_completo": p.nombre_completo,
                "primer_apellido": p.primer_apellido,
                "segundo_apellido": p.segundo_apellido,
                "nombres": p.nombres,
                "sexo": p.sexo,
                "fecha_nacimiento": p.fecha_nacimiento,
                "folio_hospital": p.folio_hospital,
                "clues_institucion": p.clues_institucion,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "num_eventos": len(p.eventos),
            }
            for p in patients
        ]
    finally:
        db.close()


def _patient_to_dict(patient: Patient, include_auxiliaries: bool = False) -> dict:
    """Serializa un objeto Patient a dict, calculando BMI/edad al vuelo."""
    bmi = None
    if patient.altura_cm and patient.peso_kg and patient.altura_cm > 0:
        bmi = round(patient.peso_kg / ((patient.altura_cm / 100) ** 2), 1)

    edad = None
    if patient.fecha_nacimiento:
        try:
            from datetime import date
            nacimiento = date.fromisoformat(patient.fecha_nacimiento)
            hoy = date.today()
            edad = hoy.year - nacimiento.year - (
                (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
            )
        except Exception:
            edad = None

    result = {
        "id": patient.id,
        "curp": patient.curp,
        "nombre": patient.nombre_completo,
        "nombre_completo": patient.nombre_completo,
        "primer_apellido": patient.primer_apellido,
        "segundo_apellido": patient.segundo_apellido,
        "nombres": patient.nombres,
        "fecha_nacimiento": patient.fecha_nacimiento,
        "sexo": patient.sexo,
        "folio_hospital": patient.folio_hospital,
        "ubicacion_casa": patient.ubicacion_casa,
        "rfc": patient.rfc,
        "nss": patient.nss,
        "expediente_externo": patient.expediente_externo,
        "nacionalidad": patient.nacionalidad,
        "lugar_nacimiento": patient.lugar_nacimiento,
        "estado_civil": patient.estado_civil,
        "ocupacion": patient.ocupacion,
        "tipo_paciente": patient.tipo_paciente,
        "programa_medico": patient.programa_medico,
        "telefono_local": patient.telefono_local,
        "celular": patient.celular,
        "email": patient.email,
        "contacto_emergencia_nombre": patient.contacto_emergencia_nombre,
        "contacto_emergencia_tel": patient.contacto_emergencia_tel,
        "aseguradoras": json.loads(patient.aseguradoras) if patient.aseguradoras else [],
        "anotaciones_generales": patient.anotaciones_generales,
        "altura_cm": patient.altura_cm,
        "peso_kg": patient.peso_kg,
        "tipo_sangre": patient.tipo_sangre,
        "bmi": bmi,             # Calculado al vuelo
        "edad": edad,           # Calculado al vuelo
        "clues_institucion": patient.clues_institucion,
        "resumen_ia": patient.resumen_ia,
        "resumen_ia_fecha": patient.resumen_ia_fecha.isoformat() if patient.resumen_ia_fecha else None,
        "created_at": patient.created_at.isoformat() if patient.created_at else None,
        "updated_at": patient.updated_at.isoformat() if patient.updated_at else None,
    }

    if include_auxiliaries:
        result["alergias"] = [
            {
                "id": a.id, "descripcion": a.descripcion, "tipo": a.tipo,
                "severidad": a.severidad, "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in patient.alergias
        ]
        result["antecedentes"] = [
            {
                "id": a.id, "tipo": a.tipo, "descripcion": a.descripcion,
                "fecha": a.fecha, "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in patient.antecedentes
        ]
        result["recordatorios"] = [
            {
                "id": r.id, "titulo": r.titulo, "descripcion": r.descripcion,
                "fecha_alerta": r.fecha_alerta.isoformat() if r.fecha_alerta else None,
                "completado": r.completado,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in patient.recordatorios
        ]

    return result


def log_audit_action(action: str, patient_curp: str, operator: str, details_dict: dict, db=None) -> None:
    """Registra un evento en la tabla de logs de auditoría."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        log = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            action=action,
            patient_curp=patient_curp,
            operator=operator,
            details=json.dumps(details_dict, ensure_ascii=False)
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"[AuditLog] Error al registrar auditoría: {e}")
        if close_db:
            db.rollback()
    finally:
        if close_db:
            db.close()


def get_patient_audit_logs(curp: str) -> list:
    """Devuelve los logs de auditoría para un CURP ordenados de más reciente a antiguo."""
    db = SessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.patient_curp == curp).order_by(AuditLog.timestamp.desc()).all()
        return [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "action": log.action,
                "patient_curp": log.patient_curp,
                "operator": log.operator,
                "details": json.loads(log.details) if log.details else {}
            }
            for log in logs
        ]
    finally:
        db.close()


def delete_patient(curp: str) -> bool:
    """
    Elimina físicamente al paciente y todos sus registros en cascada.
    Conserva los logs de auditoría y limpia ChromaDB.
    """
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.curp == curp).first()
        if not patient:
            return False

        # Registrar el log de ELIMINACION antes de borrar
        log_audit_action(
            action="ELIMINACION",
            patient_curp=curp,
            operator="Médico",
            details_dict={
                "nombre_completo": patient.nombre_completo,
                "curp": patient.curp,
                "folio_hospital": patient.folio_hospital
            },
            db=db
        )

        db.delete(patient)
        db.commit()

        # Limpiar de ChromaDB
        try:
            from app.db.chroma_store import get_collection
            
            p_col = get_collection("patients_semantic")
            p_col.delete(ids=[curp])
            
            e_col = get_collection("events_semantic")
            e_col.delete(where={"patient_curp": curp})
            
            c_col = get_collection("consultations_semantic")
            c_col.delete(where={"patient_curp": curp})
        except Exception as ce:
            print(f"[ChromaDB] Error al eliminar índices de paciente {curp}: {ce}")

        return True
    except Exception as e:
        db.rollback()
        print(f"[DB] Error al eliminar paciente: {e}")
        return False
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# FUNCIONES: AUXILIARES DEL PERFIL
# ─────────────────────────────────────────────────────────────────

def add_alergia(curp: str, data: dict) -> dict:
    db = SessionLocal()
    try:
        alergia = Alergia(
            patient_curp=curp,
            descripcion=data.get("descripcion", ""),
            tipo=data.get("tipo"),
            severidad=data.get("severidad"),
        )
        db.add(alergia)
        db.commit()
        db.refresh(alergia)
        return {"id": alergia.id, "descripcion": alergia.descripcion,
                "tipo": alergia.tipo, "severidad": alergia.severidad}
    finally:
        db.close()


def delete_alergia(alergia_id: str) -> bool:
    db = SessionLocal()
    try:
        obj = db.query(Alergia).filter(Alergia.id == alergia_id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False
    finally:
        db.close()


def add_antecedente(curp: str, data: dict) -> dict:
    db = SessionLocal()
    try:
        ant = Antecedente(
            patient_curp=curp,
            tipo=data.get("tipo"),
            descripcion=data.get("descripcion", ""),
            fecha=data.get("fecha"),
        )
        db.add(ant)
        db.commit()
        db.refresh(ant)
        return {"id": ant.id, "tipo": ant.tipo, "descripcion": ant.descripcion, "fecha": ant.fecha}
    finally:
        db.close()


def delete_antecedente(antecedente_id: str) -> bool:
    db = SessionLocal()
    try:
        obj = db.query(Antecedente).filter(Antecedente.id == antecedente_id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False
    finally:
        db.close()


def add_recordatorio(curp: str, data: dict) -> dict:
    db = SessionLocal()
    try:
        rec = Recordatorio(
            patient_curp=curp,
            titulo=data.get("titulo", ""),
            descripcion=data.get("descripcion"),
            fecha_alerta=datetime.fromisoformat(data["fecha_alerta"]) if data.get("fecha_alerta") else None,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return {"id": rec.id, "titulo": rec.titulo, "descripcion": rec.descripcion,
                "fecha_alerta": rec.fecha_alerta.isoformat() if rec.fecha_alerta else None,
                "completado": rec.completado}
    finally:
        db.close()


def toggle_recordatorio(recordatorio_id: str) -> bool:
    db = SessionLocal()
    try:
        obj = db.query(Recordatorio).filter(Recordatorio.id == recordatorio_id).first()
        if obj:
            obj.completado = not obj.completado
            db.commit()
            return True
        return False
    finally:
        db.close()


def delete_recordatorio(recordatorio_id: str) -> bool:
    db = SessionLocal()
    try:
        obj = db.query(Recordatorio).filter(Recordatorio.id == recordatorio_id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# FUNCIONES: EVENTOS CLÍNICOS
# ─────────────────────────────────────────────────────────────────

def create_evento_clinico(data: dict) -> dict:
    """
    Crea un nuevo Evento Clínico para un paciente existente.
    Lanza ValueError si el paciente no está registrado.
    """
    db = SessionLocal()
    try:
        curp = data.get("patient_curp", "").strip().upper()
        patient = db.query(Patient).filter(Patient.curp == curp).first()
        if not patient:
            raise ValueError(f"Paciente no registrado: {curp}")

        evento = EventoClinico(
            id=str(uuid.uuid4()),
            patient_curp=curp,
            nombre_evento=data.get("nombre_evento", "Evento Clínico"),
            doctor_creador=data.get("doctor_creador"),
            resumen=data.get("resumen"),
        )
        if data.get("fecha_hora_creacion"):
            try:
                evento.fecha_hora_creacion = datetime.fromisoformat(data["fecha_hora_creacion"])
            except Exception:
                pass

        db.add(evento)
        db.commit()
        db.refresh(evento)
        return _evento_to_dict(evento)
    finally:
        db.close()


def get_patient_events(curp: str) -> list:
    """
    Devuelve todos los Eventos Clínicos de un paciente con el conteo
    de consultas y metadata básica (sin el contenido de notas/recetas).
    """
    db = SessionLocal()
    try:
        eventos = (
            db.query(EventoClinico)
            .filter(EventoClinico.patient_curp == curp)
            .order_by(EventoClinico.updated_at.desc())
            .all()
        )
        return [_evento_to_dict(e) for e in eventos]
    finally:
        db.close()


def rename_clinical_event(event_id: str, new_name: str) -> bool:
    """Renombra un Evento Clínico. El nombre sí es editable."""
    db = SessionLocal()
    try:
        evento = db.query(EventoClinico).filter(EventoClinico.id == event_id).first()
        if evento:
            evento.nombre_evento = new_name
            evento.updated_at = datetime.utcnow()
            db.commit()
            return True
        return False
    finally:
        db.close()


def _evento_to_dict(evento: EventoClinico) -> dict:
    """Serializa un EventoClinico a dict con metadatos de sus consultas."""
    num_consultas = len(evento.consultas) if evento.consultas else 0
    ultima_consulta = None
    if evento.consultas:
        ultima = sorted(evento.consultas, key=lambda c: c.fecha_hora or datetime.min, reverse=True)[0]
        ultima_consulta = ultima.fecha_hora.isoformat() if ultima.fecha_hora else None

    return {
        "id": evento.id,
        "patient_curp": evento.patient_curp,
        "nombre_evento": evento.nombre_evento,
        "doctor_creador": evento.doctor_creador,
        "fecha_hora_creacion": evento.fecha_hora_creacion.isoformat() if evento.fecha_hora_creacion else None,
        "resumen": evento.resumen,
        "num_consultas": num_consultas,
        "ultima_consulta": ultima_consulta,
        "created_at": evento.created_at.isoformat() if evento.created_at else None,
        "updated_at": evento.updated_at.isoformat() if evento.updated_at else None,
    }


# ─────────────────────────────────────────────────────────────────
# FUNCIONES: CONSULTAS (INMUTABLES)
# ─────────────────────────────────────────────────────────────────

def create_consulta(data: dict) -> dict:
    """
    Crea una nueva Consulta y la asocia a un Evento Clínico.
    Los documentos (nota, receta, entidades) son INMUTABLES una vez creados.
    Lanza ValueError si el evento no existe.
    """
    db = SessionLocal()
    try:
        evento_id = data.get("evento_id")
        evento = db.query(EventoClinico).filter(EventoClinico.id == evento_id).first()
        if not evento:
            raise ValueError(f"Evento Clínico no encontrado: {evento_id}")

        fecha_hora = datetime.utcnow()
        if data.get("fecha_hora"):
            try:
                fecha_hora = datetime.fromisoformat(data["fecha_hora"])
            except Exception:
                pass

        consulta = Consulta(
            id=str(uuid.uuid4()),
            evento_id=evento_id,
            patient_curp=evento.patient_curp,
            doctor_nombre=data.get("doctor_nombre"),
            cedula_profesional=data.get("cedula_profesional"),
            fecha_hora=fecha_hora,
            resumen_doctor=data.get("resumen_doctor"),
            nota_medica_json=json.dumps(data.get("nota_medica", {}), ensure_ascii=False),
            receta_json=json.dumps(data.get("receta", {}), ensure_ascii=False),
            entidades_json=json.dumps(data.get("entidades", {}), ensure_ascii=False),
            texto_original=data.get("texto_original", ""),
            texto_redactado=data.get("texto_redactado", ""),
        )
        db.add(consulta)

        # Actualizar updated_at del evento padre
        evento.updated_at = datetime.utcnow()

        op_label = data.get("doctor_nombre") or "Médico"
        if data.get("cedula_profesional"):
            op_label = f"{op_label} (Céd. {data.get('cedula_profesional')})"
        log_audit_action(
            action="FIRMA_CONSULTA",
            patient_curp=evento.patient_curp,
            operator=op_label,
            details_dict={
                "consulta_id": consulta.id,
                "evento_id": evento_id,
                "doctor_nombre": consulta.doctor_nombre,
                "cedula_profesional": consulta.cedula_profesional,
            },
            db=db,
        )

        db.commit()
        db.refresh(consulta)
        return _consulta_to_dict(consulta)
    finally:
        db.close()


def get_consultas_by_evento(evento_id: str) -> list:
    """Devuelve todas las consultas de un evento, ordenadas cronológicamente."""
    db = SessionLocal()
    try:
        consultas = (
            db.query(Consulta)
            .filter(Consulta.evento_id == evento_id)
            .order_by(Consulta.fecha_hora.asc())
            .all()
        )
        return [_consulta_to_dict(c) for c in consultas]
    finally:
        db.close()


def get_consulta_by_id(consulta_id: str) -> dict | None:
    """Devuelve una consulta específica con todos sus datos."""
    db = SessionLocal()
    try:
        consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
        return _consulta_to_dict(consulta) if consulta else None
    finally:
        db.close()


def _consulta_to_dict(consulta: Consulta) -> dict:
    """Serializa una Consulta a dict, con documentos parseados desde JSON."""
    def _safe_parse(text):
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    return {
        "id": consulta.id,
        "evento_id": consulta.evento_id,
        "patient_curp": consulta.patient_curp,
        "doctor_nombre": consulta.doctor_nombre,
        "cedula_profesional": consulta.cedula_profesional,
        "fecha_hora": consulta.fecha_hora.isoformat() if consulta.fecha_hora else None,
        "resumen_doctor": consulta.resumen_doctor,
        "nota_medica": _safe_parse(consulta.nota_medica_json),
        "receta": _safe_parse(consulta.receta_json),
        "entidades": _safe_parse(consulta.entidades_json),
        "texto_original": consulta.texto_original,
        "texto_redactado": consulta.texto_redactado or "",
        "notas_addendum": consulta.notas_addendum,
        "created_at": consulta.created_at.isoformat() if consulta.created_at else None,
    }


# ─────────────────────────────────────────────────────────────────
# FUNCIONES: PIPELINE LEGACY (compatibilidad con routes_input.py)
# ─────────────────────────────────────────────────────────────────

def save_patient(record: dict, event_id: str = None) -> dict:
    """
    Función de compatibilidad para el pipeline de procesamiento existente.
    Registra o actualiza al paciente y crea una entrada temporal del record.
    En el nuevo flujo, el guardado definitivo ocurre en create_consulta().

    Esta función se mantiene para que el pipeline de text/audio no rompa.
    En el rediseño completo, el pipeline solo retorna el borrador en memoria
    y no lo persiste hasta que el médico confirme en el modal de "Asociar".
    """
    db = SessionLocal()
    try:
        curp = record.get("curp", "")
        if not curp:
            return record

        # Crear o actualizar el registro básico del paciente
        existing = db.query(Patient).filter(Patient.curp == curp).first()
        if not existing:
            demo = record.get("datos_demograficos", {})
            nombre_raw = demo.get("nombre", "")
            parts = nombre_raw.split() if nombre_raw else []
            patient = Patient(
                curp=curp,
                primer_apellido=parts[0] if len(parts) > 0 else "",
                segundo_apellido=parts[1] if len(parts) > 1 else "",
                nombres=" ".join(parts[2:]) if len(parts) > 2 else nombre_raw,
                clues_institucion=record.get("clues_institucion", ""),
            )
            db.add(patient)
            db.commit()

        record["event_id"] = event_id
        return record
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────
# FUNCIONES: BÚSQUEDA SEMÁNTICA (ChromaDB)
# ─────────────────────────────────────────────────────────────────

def index_event_semantically(record: dict):
    """
    Indiza un registro en ChromaDB (colección Nivel 1: patients_semantic).
    Llamado de forma asíncrona desde el pipeline para no bloquear la UI.
    """
    try:
        from app.core.cie10_mapper import _get_embedder
        from app.db.chroma_store import get_collection

        curp = record.get("curp")
        if not curp:
            return

        nombre = record.get("datos_demograficos", {}).get("nombre") or ""
        motivo = record.get("nota_clinica", {}).get("motivo_consulta") or ""
        diagnostico = record.get("nota_clinica", {}).get("diagnostico_integral") or ""
        sintomas = ", ".join(record.get("entidades_extraidas", {}).get("sintomas_referidos", []))
        diagnosticos_list = ", ".join(record.get("entidades_extraidas", {}).get("diagnosticos_tentativos", []))

        doc_text = " | ".join(filter(None, [
            f"Paciente: {nombre}",
            f"CURP: {curp}",
            f"Motivo: {motivo}",
            f"Síntomas: {sintomas}",
            f"Diagnósticos: {diagnosticos_list}",
            f"Diagnóstico Integral: {diagnostico}",
        ]))

        col = get_collection("patients_semantic")
        embedder = _get_embedder()
        embedding = embedder.encode([doc_text]).tolist()

        col.upsert(
            ids=[curp],
            embeddings=embedding,
            documents=[doc_text],
            metadatas=[{
                "patient_curp": curp,
                "nombre_paciente": nombre,
            }]
        )
    except Exception as e:
        print(f"[SemanticIndex] Error al indizar: {e}")


def index_patient_profile_semantically(data: dict):
    """Indiza un perfil de paciente en ChromaDB (colección patients_semantic)."""
    try:
        from app.core.cie10_mapper import _get_embedder
        from app.db.chroma_store import get_collection

        curp = (data.get("curp") or "").strip().upper()
        if not curp:
            return

        nombre = data.get("nombre_completo") or f"{data.get('nombres', '')} {data.get('primer_apellido', '')} {data.get('segundo_apellido', '')}".strip()
        doc_text = " ".join(filter(None, [
            f"Paciente: {nombre}.",
            f"CURP: {curp}.",
            f"Folio: {data.get('folio_hospital') or ''}.",
            f"Ocupación: {data.get('ocupacion') or ''}.",
            f"Ubicación y Domicilio: {data.get('ubicacion_casa') or ''}.",
            f"Lugar de Nacimiento: {data.get('lugar_nacimiento') or ''}.",
            f"Anotaciones y Antecedentes Clínicos: {data.get('anotaciones_generales') or ''}."
        ]))

        col = get_collection("patients_semantic")
        embedder = _get_embedder()
        embedding = embedder.encode([doc_text]).tolist()

        col.upsert(
            ids=[curp],
            embeddings=embedding,
            documents=[doc_text],
            metadatas=[{
                "patient_curp": curp,
                "nombre_paciente": nombre,
            }]
        )
    except Exception as e:
        print(f"[SemanticIndex] Error al indizar perfil: {e}")



def index_evento_semantically(evento_id: str, patient_curp: str, nombre_evento: str, consultas_text: str = ""):
    """
    Indiza un Evento Clínico en ChromaDB (colección Nivel 2: events_semantic).
    """
    try:
        from app.core.cie10_mapper import _get_embedder
        from app.db.chroma_store import get_collection

        doc_text = " | ".join(filter(None, [
            f"Evento: {nombre_evento}",
            f"CURP: {patient_curp}",
            consultas_text,
        ]))

        col = get_collection("events_semantic")
        embedder = _get_embedder()
        embedding = embedder.encode([doc_text]).tolist()

        col.upsert(
            ids=[evento_id],
            embeddings=embedding,
            documents=[doc_text],
            metadatas=[{"event_id": evento_id, "patient_curp": patient_curp}]
        )
    except Exception as e:
        print(f"[SemanticIndex] Error al indizar evento: {e}")


def index_consulta_semantically(consulta_id: str, evento_id: str, patient_curp: str, consulta_text: str):
    """
    Indiza una Consulta en ChromaDB (colección Nivel 3: consultations_semantic).
    """
    try:
        from app.core.cie10_mapper import _get_embedder
        from app.db.chroma_store import get_collection

        col = get_collection("consultations_semantic")
        embedder = _get_embedder()
        embedding = embedder.encode([consulta_text]).tolist()

        col.upsert(
            ids=[consulta_id],
            embeddings=embedding,
            documents=[consulta_text],
            metadatas=[{
                "consulta_id": consulta_id,
                "event_id": evento_id,
                "patient_curp": patient_curp,
            }]
        )
    except Exception as e:
        print(f"[SemanticIndex] Error al indizar consulta: {e}")


def search_patients_semantically(query: str, n_results: int = 10) -> list:
    """Búsqueda semántica de Nivel 1: busca pacientes por similitud."""
    try:
        from app.core.cie10_mapper import _get_embedder
        from app.db.chroma_store import get_collection

        col = get_collection("patients_semantic")
        if col.count() == 0:
            return []

        embedder = _get_embedder()
        query_embedding = embedder.encode([query]).tolist()
        results = col.query(query_embeddings=query_embedding, n_results=n_results)

        out = []
        if results["metadatas"] and results["metadatas"][0]:
            for i, meta in enumerate(results["metadatas"][0]):
                distance = results["distances"][0][i]
                similitud = round(max(0.0, 1.0 - distance), 3)
                out.append({
                    "patient_curp": meta.get("patient_curp"),
                    "nombre_paciente": meta.get("nombre_paciente"),
                    "match_text": results["documents"][0][i],
                    "similitud": similitud,
                })
        return out
    except Exception as e:
        print(f"[SemanticSearch] Error: {e}")
        return []


def search_events_semantically(query: str, patient_curp: str = None, n_results: int = 10) -> list:
    """Búsqueda semántica de Nivel 2: busca eventos dentro de un paciente."""
    try:
        from app.core.cie10_mapper import _get_embedder
        from app.db.chroma_store import get_collection

        col = get_collection("events_semantic")
        if col.count() == 0:
            return []

        embedder = _get_embedder()
        query_embedding = embedder.encode([query]).tolist()

        where = {"patient_curp": patient_curp} if patient_curp else None
        results = col.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where,
        )

        out = []
        if results["metadatas"] and results["metadatas"][0]:
            for i, meta in enumerate(results["metadatas"][0]):
                distance = results["distances"][0][i]
                similitud = round(max(0.0, 1.0 - distance), 3)
                out.append({
                    "event_id": meta.get("event_id"),
                    "patient_curp": meta.get("patient_curp"),
                    "match_text": results["documents"][0][i],
                    "similitud": similitud,
                })
        return out
    except Exception as e:
        print(f"[SemanticSearch] Error eventos: {e}")
        return []



# ─────────────────────────────────────────────────────────────────
# FUNCIONES SPRINT 3: PORTAL PACIENTE, HISTORIAL COMPLETO Y FHIR
# ─────────────────────────────────────────────────────────────────

def _daily_log_to_dict(row: PatientDailyLog) -> dict:
    return {
        "id": row.id,
        "patient_curp": row.patient_curp,
        "systolic_bp": row.systolic_bp,
        "diastolic_bp": row.diastolic_bp,
        "glucose_mg_dl": row.glucose_mg_dl,
        "temperature_c": row.temperature_c,
        "weight_kg": row.weight_kg,
        "medication_taken": bool(row.medication_taken),
        "mood_or_pain": row.mood_or_pain,
        "symptoms_note": row.symptoms_note,
        "alert_flag": bool(row.alert_flag),
        "alert_message": row.alert_message,
        "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
    }


def _evaluate_daily_log_alerts(data: dict) -> tuple[bool, str]:
    alerts = []
    sys_bp = data.get("systolic_bp")
    dia_bp = data.get("diastolic_bp")
    gluc = data.get("glucose_mg_dl")
    temp = data.get("temperature_c")
    mood = (data.get("mood_or_pain") or "").lower()

    if sys_bp is not None and (sys_bp >= 160 or sys_bp < 90):
        alerts.append(f"Presión sistólica fuera de rango seguro ({sys_bp:.0f} mmHg)")
    if dia_bp is not None and dia_bp >= 100:
        alerts.append(f"Presión diastólica elevada ({dia_bp:.0f} mmHg)")
    if gluc is not None and gluc < 70:
        alerts.append(f"Hipoglucemia ({gluc:.0f} mg/dL) — acudir o tratar de inmediato")
    elif gluc is not None and gluc >= 250:
        alerts.append(f"Hiperglucemia severa ({gluc:.0f} mg/dL) — valorar urgencias")
    if temp is not None and temp >= 38.5:
        alerts.append(f"Fiebre alta ({temp:.1f} °C)")
    if "importante" in mood or "alarma" in mood:
        alerts.append("Paciente reporta síntomas importantes en casa")

    return (len(alerts) > 0, " • ".join(alerts))


def add_patient_daily_log(curp: str, data: dict) -> dict:
    db = SessionLocal()
    try:
        alert_flag, alert_msg = _evaluate_daily_log_alerts(data)
        row = PatientDailyLog(
            id=str(uuid.uuid4()),
            patient_curp=curp.upper(),
            systolic_bp=data.get("systolic_bp"),
            diastolic_bp=data.get("diastolic_bp"),
            glucose_mg_dl=data.get("glucose_mg_dl"),
            temperature_c=data.get("temperature_c"),
            weight_kg=data.get("weight_kg"),
            medication_taken=bool(data.get("medication_taken", True)),
            mood_or_pain=data.get("mood_or_pain") or "Bien",
            symptoms_note=data.get("symptoms_note"),
            alert_flag=alert_flag,
            alert_message=alert_msg or None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _daily_log_to_dict(row)
    finally:
        db.close()


def get_patient_daily_logs(curp: str, limit: int = 30) -> list:
    db = SessionLocal()
    try:
        rows = (
            db.query(PatientDailyLog)
            .filter(PatientDailyLog.patient_curp == curp.upper())
            .order_by(PatientDailyLog.recorded_at.desc())
            .limit(limit)
            .all()
        )
        return [_daily_log_to_dict(r) for r in rows]
    finally:
        db.close()


def get_patient_full_history(curp: str) -> dict | None:
    """Retorna el expediente completo longitudinal del paciente para FHIR, ICE, Portal y Ask-Expediente."""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.curp == curp.upper()).first()
        if not patient:
            return None

        p_dict = _patient_to_dict(patient, include_auxiliaries=True)
        eventos_list = []
        for ev in patient.eventos:
            ev_dict = _evento_to_dict(ev)
            ev_dict["consultas"] = [_consulta_to_dict(c) for c in ev.consultas]
            eventos_list.append(ev_dict)

        vitals_rows = (
            db.query(VitalReading)
            .filter(VitalReading.patient_curp == patient.curp)
            .order_by(VitalReading.recorded_at.desc())
            .limit(30)
            .all()
        )
        vitals = [
            {
                "id": v.id,
                "device": v.device_name,
                "source": v.source,
                "heart_rate": v.heart_rate,
                "spo2": v.spo2,
                "systolic_bp": v.systolic_bp,
                "diastolic_bp": v.diastolic_bp,
                "temperature": v.temperature,
                "steps": v.steps,
                "alert": bool(v.alert_flag),
                "alert_message": v.alert_message,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            }
            for v in vitals_rows
        ]

        logs_rows = (
            db.query(PatientDailyLog)
            .filter(PatientDailyLog.patient_curp == patient.curp)
            .order_by(PatientDailyLog.recorded_at.desc())
            .limit(30)
            .all()
        )
        daily_logs = [_daily_log_to_dict(r) for r in logs_rows]

        return {
            "patient": p_dict,
            "eventos": eventos_list,
            "vital_readings": vitals,
            "patient_daily_logs": daily_logs,
        }
    finally:
        db.close()


def _seed_sprint3_defaults():
    """Asigna tipo de sangre demostrativo y siembra registros diarios iniciales si faltan."""
    db = SessionLocal()
    try:
        blood_defaults = {
            "GOPC790814HYNCLN04": "O+",
            "MOBK070228HYNRTVA3": "A+",
            "TESTCURP1234567890": "B+",
        }
        patients = db.query(Patient).all()
        for p in patients:
            if not p.tipo_sangre and p.curp in blood_defaults:
                p.tipo_sangre = blood_defaults[p.curp]

        if db.query(PatientDailyLog).count() == 0 and patients:
            sample_curps = [p.curp for p in patients[:2]]
            for idx, curp in enumerate(sample_curps):
                db.add(PatientDailyLog(
                    id=str(uuid.uuid4()),
                    patient_curp=curp,
                    systolic_bp=126 if idx == 0 else 118,
                    diastolic_bp=80 if idx == 0 else 76,
                    glucose_mg_dl=112 if idx == 0 else 96,
                    temperature_c=36.5,
                    medication_taken=True,
                    mood_or_pain="Bien",
                    symptoms_note="Sin síntomas agudos, apego normal al tratamiento.",
                    alert_flag=False,
                ))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB] Error sembrando datos iniciales Sprint 3: {e}")
    finally:
        db.close()



# ─────────────────────────────────────────────────────────────────
# SPRINT 4: PERFILES DE ROL, CÉDULA PROFESIONAL Y BITÁCORA NOM-024
# ─────────────────────────────────────────────────────────────────

def _profile_to_dict(p: PractitionerProfile) -> dict:
    return {
        "id": p.id,
        "role": p.role,
        "full_name": p.full_name,
        "cedula_profesional": p.cedula_profesional or "",
        "specialty": p.specialty or "",
        "clues_institucion": p.clues_institucion or "YUC-CR-001",
        "is_active": bool(p.is_active),
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _seed_sprint4_defaults():
    """Siembra los 4 roles profesionales por defecto si la tabla está vacía."""
    db = SessionLocal()
    try:
        if db.query(PractitionerProfile).count() == 0:
            seeds = [
                PractitionerProfile(
                    role="Médico",
                    full_name="Dr. Roberto Morales",
                    cedula_profesional="CED-9482710",
                    specialty="Medicina General / Urgencias",
                    clues_institucion="YUC-CR-001",
                    is_active=True,
                ),
                PractitionerProfile(
                    role="Enfermería / Triaje",
                    full_name="Enf. Mariana López",
                    cedula_profesional="ENF-7319042",
                    specialty="Enfermería y Triaje Hospitalario",
                    clues_institucion="YUC-CR-001",
                    is_active=False,
                ),
                PractitionerProfile(
                    role="Recepción",
                    full_name="Lic. Sofía Hernández",
                    cedula_profesional="ADM-REC-014",
                    specialty="Admisión y Agenda Clínica",
                    clues_institucion="YUC-CR-001",
                    is_active=False,
                ),
                PractitionerProfile(
                    role="Administrador",
                    full_name="Dir. Alejandro Pech",
                    cedula_profesional="DIR-0012026",
                    specialty="Dirección Médica NOM-024",
                    clues_institucion="YUC-CR-001",
                    is_active=False,
                ),
            ]
            db.add_all(seeds)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB] Error sembrando roles Sprint 4: {e}")
    finally:
        db.close()


def get_practitioner_profiles() -> list:
    db = SessionLocal()
    try:
        rows = db.query(PractitionerProfile).all()
        return [_profile_to_dict(r) for r in rows]
    finally:
        db.close()


def get_active_practitioner() -> dict:
    db = SessionLocal()
    try:
        row = db.query(PractitionerProfile).filter(PractitionerProfile.is_active == True).first()
        if not row:
            row = db.query(PractitionerProfile).first()
        if row:
            return _profile_to_dict(row)
        return {
            "role": "Médico",
            "full_name": "Dr. Roberto Morales",
            "cedula_profesional": "CED-9482710",
            "specialty": "Medicina General / Urgencias",
            "clues_institucion": "YUC-CR-001",
            "is_active": True,
        }
    finally:
        db.close()


def upsert_practitioner_profile(data: dict) -> dict:
    """Actualiza datos/cédula del rol indicado y opcionalmente lo activa como sesión actual."""
    db = SessionLocal()
    try:
        role = (data.get("role") or "Médico").strip()
        row = db.query(PractitionerProfile).filter(PractitionerProfile.role == role).first()
        if not row:
            row = PractitionerProfile(
                id=str(uuid.uuid4()),
                role=role,
                full_name=(data.get("full_name") or role).strip(),
                cedula_profesional=(data.get("cedula_profesional") or "").strip(),
                specialty=(data.get("specialty") or "").strip(),
                clues_institucion=(data.get("clues_institucion") or "YUC-CR-001").strip(),
                is_active=True,
            )
            db.add(row)
        else:
            if data.get("full_name") is not None and str(data.get("full_name")).strip():
                row.full_name = str(data.get("full_name")).strip()
            if "cedula_profesional" in data and data.get("cedula_profesional") is not None:
                row.cedula_profesional = str(data.get("cedula_profesional")).strip()
            if "specialty" in data and data.get("specialty") is not None:
                row.specialty = str(data.get("specialty")).strip()
            if "clues_institucion" in data and data.get("clues_institucion") is not None:
                row.clues_institucion = str(data.get("clues_institucion")).strip() or "YUC-CR-001"

        if data.get("activate", True):
            db.query(PractitionerProfile).update({"is_active": False})
            row.is_active = True

        row.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(row)

        log_audit_action(
            action="CAMBIO_PERFIL_ROL",
            patient_curp="SISTEMA",
            operator=f"{row.full_name} [{row.role}]",
            details_dict={
                "role": row.role,
                "cedula_profesional": row.cedula_profesional,
                "clues_institucion": row.clues_institucion,
            },
            db=db,
        )
        return _profile_to_dict(row)
    finally:
        db.close()


def get_all_audit_logs(limit: int = 100, action: str | None = None, curp: str | None = None) -> list:
    """Devuelve registros globales de la bitácora de auditoría NOM-024."""
    db = SessionLocal()
    try:
        q = db.query(AuditLog)
        if action and action.strip() and action.strip().upper() != "ALL":
            q = q.filter(AuditLog.action == action.strip().upper())
        if curp and curp.strip():
            q = q.filter(AuditLog.patient_curp.ilike(f"%{curp.strip().upper()}%"))
        logs = q.order_by(AuditLog.timestamp.desc()).limit(max(1, min(limit, 500))).all()
        out = []
        for log in logs:
            try:
                details = json.loads(log.details) if log.details else {}
            except Exception:
                details = {"raw": log.details}
            out.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "action": log.action,
                "patient_curp": log.patient_curp,
                "operator": log.operator,
                "details": details,
            })
        return out
    finally:
        db.close()
