"""
setup_interhospital_network.py — Configuración y Carga de la Red Interhospitalaria MedicAItion
=============================================================================================
"""

import os
import sys
from datetime import datetime, timedelta
import uuid
import hashlib

# Asegurar path de importación
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.global_db import (
    create_tables, SessionLocal, Institution, PatientIndex,
    InterHospitalReferral, InterHospitalAudit, register_institution
)
from app.db.local_db import SessionLocal as LocalSession, Patient, Alergia, EventoClinico, Consulta

INSTITUCIONES_RED = [
    {
        "clues": "YUC-CR-001",
        "nombre": "Cruz Roja Mexicana Delegación Mérida",
        "ubicacion": "Mérida, Yucatán (Centro)",
        "nivel": "Nivel 1 / Atención Prehospitalaria & Urgencias",
        "red": "Red Cruz Roja Sureste",
        "estado_conexion": "En Línea - Nodo Local Activo",
        "latencia_ms": 2,
        "ip_nodo": "127.0.0.1 (LocalHost)",
        "clave_publica_sha256": "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
    },
    {
        "clues": "YCSSA000024",
        "nombre": "Hospital General Dr. Agustín O'Horán",
        "ubicacion": "Mérida, Yucatán (Av. Jacinto Canek)",
        "nivel": "Tercer Nivel / Alta Complejidad & Trauma",
        "red": "Servicios de Salud de Yucatán (SSY)",
        "estado_conexion": "En Línea - Nodo Federado",
        "latencia_ms": 11,
        "ip_nodo": "10.24.100.15",
        "clave_publica_sha256": "sha256:4a8b98e1f0e2b4d1b73e89a5e12f6c8d9e0b1a2c3d4e5f6a7b8c9d0e1f2a3b4c"
    },
    {
        "clues": "IMS0001092",
        "nombre": "HGR N° 1 T-1 Lic. Ignacio García Téllez",
        "ubicacion": "Mérida, Yucatán (Ex-Fénix)",
        "nivel": "Segundo Nivel / Especialidades Médicas IMSS",
        "red": "Instituto Mexicano del Seguro Social (IMSS)",
        "estado_conexion": "En Línea - Nodo Federado",
        "latencia_ms": 14,
        "ip_nodo": "10.15.20.88",
        "clave_publica_sha256": "sha256:9c8b7a6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b"
    },
    {
        "clues": "YCSSA000671",
        "nombre": "Hospital Materno-Infantil de Mérida",
        "ubicacion": "Mérida, Yucatán (Sur)",
        "nivel": "Segundo Nivel / Ginecología & Pediatría",
        "red": "Servicios de Salud de Yucatán (SSY)",
        "estado_conexion": "En Línea - Nodo Federado",
        "latencia_ms": 18,
        "ip_nodo": "10.24.102.32",
        "clave_publica_sha256": "sha256:3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c"
    },
    {
        "clues": "YCSSA001890",
        "nombre": "Centro de Salud Urbano Kanasín",
        "ubicacion": "Kanasín, Yucatán",
        "nivel": "Primer Nivel / Medicina Familiar & Preventiva",
        "red": "Servicios de Salud de Yucatán (SSY)",
        "estado_conexion": "En Línea - Nodo Federado",
        "latencia_ms": 24,
        "ip_nodo": "10.24.108.05",
        "clave_publica_sha256": "sha256:5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f"
    },
    {
        "clues": "ISS0003412",
        "nombre": "Hospital Regional Mérida ISSSTE",
        "ubicacion": "Mérida, Yucatán (Pensiones)",
        "nivel": "Tercer Nivel / Especialidades Quirúrgicas",
        "red": "ISSSTE Nacional",
        "estado_conexion": "En Línea - Nodo Federado",
        "latencia_ms": 16,
        "ip_nodo": "10.30.50.12",
        "clave_publica_sha256": "sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b"
    },
    {
        "clues": "YUC-HRA-003",
        "nombre": "Hospital Regional de Alta Especialidad (HRAEPY)",
        "ubicacion": "Mérida, Yucatán (Altabrisa)",
        "nivel": "Tercer Nivel / Alta Especialidad e Investigación",
        "red": "IMSS-Bienestar / Federal",
        "estado_conexion": "En Línea - Nodo Federado",
        "latencia_ms": 13,
        "ip_nodo": "10.40.70.02",
        "clave_publica_sha256": "sha256:8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e"
    }
]

def seed_all():
    print("[1/4] Creando tablas en base de datos global...")
    create_tables()

    db = SessionLocal()
    try:
        print("[2/4] Registrando nodos de la Red Hospitalaria...")
        for inst in INSTITUCIONES_RED:
            existing = db.query(Institution).filter(Institution.clues == inst["clues"]).first()
            if existing:
                existing.nombre = inst["nombre"]
                existing.ubicacion = inst["ubicacion"]
                existing.nivel = inst["nivel"]
                existing.red = inst["red"]
                existing.estado_conexion = inst["estado_conexion"]
                existing.latencia_ms = inst["latencia_ms"]
                existing.ip_nodo = inst["ip_nodo"]
                existing.clave_publica_sha256 = inst["clave_publica_sha256"]
            else:
                db.add(Institution(**inst))
        db.commit()
        print(f"  -> {len(INSTITUCIONES_RED)} instituciones conectadas.")

        print("[3/4] Indexando pacientes locales y federados...")
        local_db = LocalSession()
        local_patients = local_db.query(Patient).all()
        print(f"  -> {len(local_patients)} pacientes en base local.")

        # Limpiar índice previo para reindexar limpiamente
        db.query(PatientIndex).delete()
        db.commit()

        # Indexar pacientes locales bajo Cruz Roja Mérida
        for p in local_patients:
            alergias = local_db.query(Alergia).filter(Alergia.patient_curp == p.curp).all()
            alergias_txt = ", ".join([f"{a.descripcion} ({a.severidad or 'Riesgo'})" for a in alergias]) if alergias else "Sin alergias documentadas"
            
            # Indexar en Cruz Roja Mérida
            idx_cr = PatientIndex(
                id=str(uuid.uuid4()),
                curp=p.curp,
                nombre=f"{p.nombres} {p.primer_apellido} {p.segundo_apellido or ''}".strip(),
                clues_institucion="YUC-CR-001",
                institucion_nombre="Cruz Roja Mexicana Delegación Mérida",
                expediente_tipo="Urgencias & Consulta Prehospitalaria",
                alergias_criticas=alergias_txt,
                tipo_sangre=p.tipo_sangre or "Desconocido",
                diagnosticos_clave="Registro activo en expediente local",
                medicacion_activa="Tratamiento ambulatorio en curso",
                contacto_emergencia=f"{p.contacto_emergencia_nombre or 'Familiar directo'} ({p.contacto_emergencia_tel or '999-000-0000'})",
                consentimiento_estado="Otorgado"
            )
            db.add(idx_cr)

            # Para pacientes clave, crear su historial federado en otros hospitales de la red
            if "Kevin" in p.nombres or p.curp == "MOBK070228HYNRTVA3":
                idx_ohoran = PatientIndex(
                    id=str(uuid.uuid4()),
                    curp=p.curp,
                    nombre=f"{p.nombres} {p.primer_apellido} {p.segundo_apellido or ''}".strip(),
                    clues_institucion="YCSSA000024",
                    institucion_nombre="Hospital General Dr. Agustín O'Horán",
                    expediente_tipo="Traumatología & Urgencias Quirúrgicas",
                    alergias_criticas="Penicilina (Anafilaxia), Ketorolaco / AINEs",
                    tipo_sangre="A+",
                    diagnosticos_clave="S82.2 Fractura de tibia derecha (Resuelta 2024)",
                    medicacion_activa="Ninguna de uso crónico",
                    contacto_emergencia="Madre: Sra. Bautista (999-234-5678)",
                    consentimiento_estado="Otorgado"
                )
                db.add(idx_ohoran)

            if "Teresa" in p.nombres or "Alvarado" in p.primer_apellido:
                idx_imss = PatientIndex(
                    id=str(uuid.uuid4()),
                    curp=p.curp,
                    nombre=f"{p.nombres} {p.primer_apellido} {p.segundo_apellido or ''}".strip(),
                    clues_institucion="IMS0001092",
                    institucion_nombre="HGR N° 1 T-1 Lic. Ignacio García Téllez",
                    expediente_tipo="Endocrinología & Medicina Interna",
                    alergias_criticas="Sulfamidas / Sulfametoxazol",
                    tipo_sangre="O+",
                    diagnosticos_clave="E11.9 Diabetes Mellitus Tipo 2, I10 Hipertensión Arterial Primaria",
                    medicacion_activa="Metformina 850mg c/12h, Losartán 50mg c/24h",
                    contacto_emergencia="Hijo: Roberto Alvarado (999-112-3344)",
                    consentimiento_estado="Otorgado"
                )
                db.add(idx_imss)

            if "Rosaura" in p.nombres or "Macías" in p.primer_apellido:
                idx_ohoran2 = PatientIndex(
                    id=str(uuid.uuid4()),
                    curp=p.curp,
                    nombre=f"{p.nombres} {p.primer_apellido} {p.segundo_apellido or ''}".strip(),
                    clues_institucion="YCSSA000024",
                    institucion_nombre="Hospital General Dr. Agustín O'Horán",
                    expediente_tipo="Infectología & Medicina Crítica",
                    alergias_criticas="Aspirina / Ácido Acetilsalicílico (Contraindicado absoluto en Dengue)",
                    tipo_sangre="B+",
                    diagnosticos_clave="A90 Fiebre del Dengue con Signos de Alarma, Trombocitopenia",
                    medicacion_activa="Paracetamol 1g IV PRN, Soluciones cristaloides",
                    contacto_emergencia="Esposo: Juan Macías (999-556-7788)",
                    consentimiento_estado="Otorgado"
                )
                db.add(idx_ohoran2)

            if "Diego" in p.nombres or "Canto" in p.primer_apellido:
                idx_kanasin = PatientIndex(
                    id=str(uuid.uuid4()),
                    curp=p.curp,
                    nombre=f"{p.nombres} {p.primer_apellido} {p.segundo_apellido or ''}".strip(),
                    clues_institucion="YCSSA001890",
                    institucion_nombre="Centro de Salud Urbano Kanasín",
                    expediente_tipo="Medicina Familiar & Control Crónico",
                    alergias_criticas="Sin alergias medicamentosas",
                    tipo_sangre="O+",
                    diagnosticos_clave="J45 Asma bronquial intermitente",
                    medicacion_activa="Salbutamol aerosol 100mcg rescate",
                    contacto_emergencia="Esposa: María Canto (999-778-9900)",
                    consentimiento_estado="Otorgado"
                )
                db.add(idx_kanasin)

        db.commit()
        local_db.close()
        print(f"  -> Total de registros federados en red: {db.query(PatientIndex).count()}")

        print("[4/4] Sembrando referencias y contrarreferencias interhospitalarias...")
        db.query(InterHospitalReferral).delete()
        
        # Referencia 1: Cruz Roja -> Hospital O'Horán
        ref1 = InterHospitalReferral(
            id="REF-2026-0042",
            patient_curp="MOBK070228HYNRTVA3",
            patient_nombre="Kevin Enrique Morales Bautista",
            clues_origen="YUC-CR-001",
            hospital_origen_nombre="Cruz Roja Mexicana Delegación Mérida",
            clues_destino="YCSSA000024",
            hospital_destino_nombre="Hospital General Dr. Agustín O'Horán",
            motivo_envio="Traslado urgente para Tomografía Computarizada Craneal e interconsulta de Neurocirugía por TCE leve con pérdida transitoria de alerta.",
            diagnostico_cie10="S06.0 Conmoción cerebral / Traumatismo craneoencefálico leve",
            prioridad="Urgencia",
            estado="En_Transito",
            medico_solicitante="Dr. Roberto Morales",
            cedula_solicitante="CED-9482710",
            detalles_clinicos="Glasgow 14/15, pupilas isocóricas reactivas, sin signos de focalización motora. TA 120/78, FC 82 lpm, SpO2 98%. Alergia confirmada a Penicilina y Ketorolaco.",
            folio_fhir="FHIR-BUNDLE-YUC-2026-9941",
            created_at=datetime.utcnow() - timedelta(minutes=25),
            updated_at=datetime.utcnow() - timedelta(minutes=5)
        )
        db.add(ref1)

        # Referencia 2: Centro de Salud Kanasín -> Cruz Roja / O'Horán
        ref2 = InterHospitalReferral(
            id="REF-2026-0038",
            patient_curp="MATR691129MJCLSR08",
            patient_nombre="Rosaura Macías del Toro",
            clues_origen="YCSSA001890",
            hospital_origen_nombre="Centro de Salud Urbano Kanasín",
            clues_destino="YUC-CR-001",
            hospital_destino_nombre="Cruz Roja Mexicana Delegación Mérida",
            motivo_envio="Paciente con cuadro de Dengue de 5 días de evolución con inicio de signos de alarma (dolor abdominal intenso continuo y plaquetopenia de 65,000/uL). Requiere estabilización hemodinámica.",
            diagnostico_cie10="A97.1 Dengue con signos de alarma",
            prioridad="Urgencia",
            estado="Aceptada",
            medico_solicitante="Dra. Mariana Pech G.",
            cedula_solicitante="CED-8127390",
            detalles_clinicos="Hipotensión postural, deshidratación moderada. Hematocrito en 44%, plaquetas 65,000. NO administrar AINEs ni Aspirina.",
            folio_fhir="FHIR-BUNDLE-YUC-2026-9812",
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(minutes=45)
        )
        db.add(ref2)

        # Referencia 3: Cruz Roja -> IMSS T-1 (Contrarreferencia programada)
        ref3 = InterHospitalReferral(
            id="REF-2026-0019",
            patient_curp="AAVT560918MDFLNN02",
            patient_nombre="Teresa Alvarado Villaseñor",
            clues_origen="YUC-CR-001",
            hospital_origen_nombre="Cruz Roja Mexicana Delegación Mérida",
            clues_destino="IMS0001092",
            hospital_destino_nombre="HGR N° 1 T-1 Lic. Ignacio García Téllez",
            motivo_envio="Contrarreferencia por cuadro de descompensación hiperglucémica resuelto ambulatoriamente con insulina regular y rehidratación. Se envía a su UMF de adscripción para ajuste de hipoglucemiantes orales.",
            diagnostico_cie10="E11.65 Diabetes tipo 2 con hiperglucemia",
            prioridad="Ordinaria",
            estado="Completada",
            medico_solicitante="Dr. Roberto Morales",
            cedula_solicitante="CED-9482710",
            detalles_clinicos="Glucosa de egreso 134 mg/dL. Se reinicia metformina y se sugiere valoración por nutrición y medicina interna en su clínica.",
            folio_fhir="FHIR-BUNDLE-YUC-2026-9501",
            created_at=datetime.utcnow() - timedelta(days=2),
            updated_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(ref3)

        # Auditorías de prueba NOM-024
        db.query(InterHospitalAudit).delete()
        audit1 = InterHospitalAudit(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow() - timedelta(minutes=24),
            doctor_nombre="Dr. Roberto Morales",
            doctor_cedula="CED-9482710",
            clues_solicitante="YUC-CR-001",
            hospital_solicitante="Cruz Roja Mexicana Delegación Mérida",
            patient_curp="MOBK070228HYNRTVA3",
            patient_nombre="Kevin Enrique Morales Bautista",
            tipo_acceso="URGENCIAS_ROJO",
            justificacion="Paciente ingresa a triage de urgencias con traumatismo; verificación de alergias mortales a Penicilina.",
            datos_entregados="ICE_CRITICAL_CORE (Tipo de sangre, alergias severas, medicación de rescate)",
            firma_digital_hmac="hmac-sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        db.add(audit1)

        db.commit()
        print("  -> Referencias y auditorías sembradas exitosamente.")

    finally:
        db.close()

    print("[COMPLETADO] Red Interhospitalaria configurada con éxito.")

if __name__ == "__main__":
    seed_all()
