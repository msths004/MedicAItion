# -*- coding: utf-8 -*-
"""
scripts/seed_demo_patients.py
=============================
Generates and seeds 22+ diverse clinical test patients into MedicAItion v3.0:
- Mexican CURPs, RFCs, NSS, contacts and demographic diversity.
- Specific medical conditions / diseases spanning multiple specialties.
- Structured allergies, medical history (antecedentes), and clinical events.
- NOM-004 compliant SOAP consultations with CIE-10 codes, medical notes and prescriptions.
- Wearable telemetries (VitalReading) and upcoming appointments.
- ChromaDB semantic embedding indexing for instant search.
"""

import sys
import os
import uuid
from datetime import datetime, timedelta
import random

# Ensure app root is on python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from app.db.local_db import (
    SessionLocal,
    Patient,
    EventoClinico,
    Consulta,
    Alergia,
    Antecedente,
    Appointment,
    VitalReading,
    register_patient,
    add_alergia,
    add_antecedente,
    create_evento_clinico,
    create_consulta,
    get_all_patients,
)
from app.db.chroma_store import get_collection
from app.core.cie10_mapper import _get_embedder

PATIENTS_DATA = [
    {
        "nombres": "Elena",
        "primer_apellido": "Vázquez",
        "segundo_apellido": "Solís",
        "curp": "VASE820412MMNZLL09",
        "rfc": "VASE8204127K4",
        "nss": "67048291032",
        "sexo": "F",
        "fecha_nacimiento": "1982-04-12",
        "altura_cm": 162.0,
        "peso_kg": 76.5,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0101",
        "ubicacion_casa": "Calle 45 #210 x 28 y 30, Fracc. Las Américas, Mérida, Yucatán",
        "lugar_nacimiento": "Mérida, Yucatán",
        "nacionalidad": "Mexicana",
        "ocupacion": "Contadora Pública",
        "telefono_local": "9999238471",
        "celular": "529991238471",
        "email": "elena.vazquez.solis@gmail.com",
        "contacto_emergencia_nombre": "Roberto Morales Solís (Hermano)",
        "contacto_emergencia_tel": "9999482103",
        "disease_name": "Diabetes Mellitus Tipo 2 no insulinodependiente",
        "cie10_code": "E11.9",
        "specialty": "Endocrinología",
        "alergias": [
            {"descripcion": "Penicilina G sódica (rash y eritema)", "tipo": "medicamento", "severidad": "severa"},
            {"descripcion": "Sulfamidas", "tipo": "medicamento", "severidad": "moderada"}
        ],
        "antecedentes": [
            {"tipo": "heredofamiliar", "descripcion": "Madre con Diabetes Mellitus Tipo 2 e Hipertensión Arterial", "fecha": "2015-05-10"},
            {"tipo": "patologico", "descripcion": "Dislipidemia mixta diagnosticada hace 4 años", "fecha": "2022-08-14"}
        ],
        "subjetivo": "Paciente femenina de 44 años acude a control de Diabetes Tipo 2. Refiere polidipsia ocasional, nicturia x2 y astenia vespertina. Manifiesta adherencia irregular a la dieta.",
        "objetivo": "TA: 125/82 mmHg, FC: 78 lpm, FR: 18 rpm, Temp: 36.6 °C, SpO2: 98%, Glucosa capilar en ayunas: 168 mg/dL, HbA1c reciente: 8.2%. Fondo de ojo sin datos de retinopatía proliferativa.",
        "analisis": "Diabetes Mellitus Tipo 2 descompensada con glucemia en ayunas elevada. Requiere optimización terapéutica con adición de iSGLT2 y ajuste de dosis de metformina.",
        "plan": "Se inicia Empagliflozina 10 mg cada 24 h en el desayuno. Se mantiene Metformina 850 mg cada 12 h con alimentos. Plan nutricional hipocalórico bajo en carbohidratos refinados. Cita con laboratorio en 6 semanas.",
        "rx": [
            {"medicamento": "Metformina", "presentacion": "Tabletas 850 mg", "dosis": "1 tableta", "frecuencia": "Cada 12 horas con alimentos", "duracion": "90 días"},
            {"medicamento": "Empagliflozina", "presentacion": "Tabletas 10 mg", "dosis": "1 tableta", "frecuencia": "Cada 24 horas por la mañana", "duracion": "90 días"}
        ],
        "vitals": {"hr": 78, "spo2": 98, "sys": 125, "dia": 82, "temp": 36.6, "steps": 6240, "device": "Apple Watch Series 9"}
    },
    {
        "nombres": "Arturo",
        "primer_apellido": "Mendoza",
        "segundo_apellido": "Castillo",
        "curp": "MECA680925HDFNT01",
        "rfc": "MECA680925J31",
        "nss": "14896821345",
        "sexo": "M",
        "fecha_nacimiento": "1968-09-25",
        "altura_cm": 174.0,
        "peso_kg": 88.0,
        "tipo_sangre": "A+",
        "folio_hospital": "EXP-2026-0102",
        "ubicacion_casa": "Av. Insurgentes Sur 1450, Del Valle, Benito Juárez, CDMX",
        "lugar_nacimiento": "Ciudad de México",
        "nacionalidad": "Mexicana",
        "ocupacion": "Arquitecto Perito",
        "telefono_local": "5556781290",
        "celular": "525556781290",
        "email": "arq.arturo.mendoza@proyectos.mx",
        "contacto_emergencia_nombre": "Patricia Castillo (Esposa)",
        "contacto_emergencia_tel": "5554129800",
        "disease_name": "Hipertensión Arterial Sistémica Primaria (Estadio 2)",
        "cie10_code": "I10",
        "specialty": "Cardiología",
        "alergias": [
            {"descripcion": "Ácido Acetilsalicílico (Aspirina) - broncoespasmo", "tipo": "medicamento", "severidad": "severa"}
        ],
        "antecedentes": [
            {"tipo": "heredofamiliar", "descripcion": "Padre finado por infarto agudo al miocardio a los 62 años", "fecha": "2010-03-12"},
            {"tipo": "patologico", "descripcion": "Hipertensión arterial diagnosticada en 2018", "fecha": "2018-06-20"}
        ],
        "subjetivo": "Masculino de 57 años acude por cefalea holocraneana pulsátil de 3 días de evolución acompañada de acúfenos bilaterales tras jornadas de alta carga laboral.",
        "objetivo": "TA: 158/96 mmHg en brazo derecho, 154/94 mmHg en brazo izquierdo. FC: 84 lpm regular. Ruidos cardíacos rítmicos sin soplos. Campos pulmonares limpios. Sin edema en miembros inferiores.",
        "analisis": "Hipertensión Arterial Sistémica Estadio 2 descontrolada. Cefalea hipertensiva sin datos de focalización neurológica ni daño agudo a órgano blanco.",
        "plan": "Se incrementa Losartán a 100 mg c/24 h y se agrega Hidroclorotiazida 12.5 mg c/24 h. MAPA (Monitoreo Ambulatorio de Presión) de 24 horas y perfil lipídico completo.",
        "rx": [
            {"medicamento": "Losartán / Hidroclorotiazida", "presentacion": "Comprimidos 100mg / 12.5mg", "dosis": "1 comprimido", "frecuencia": "Cada 24 horas en ayunas", "duracion": "60 días"}
        ],
        "vitals": {"hr": 84, "spo2": 97, "sys": 158, "dia": 96, "temp": 36.5, "steps": 4820, "device": "Omron Complete Cuff"}
    },
    {
        "nombres": "Sofía",
        "primer_apellido": "Ríos",
        "segundo_apellido": "Navarrete",
        "curp": "RINS031108MNLRVF05",
        "rfc": "RINS0311088D2",
        "nss": "45210389104",
        "sexo": "F",
        "fecha_nacimiento": "2003-11-08",
        "altura_cm": 158.0,
        "peso_kg": 54.0,
        "tipo_sangre": "B+",
        "folio_hospital": "EXP-2026-0103",
        "ubicacion_casa": "Calle Hidalgo 892, Col. Obispado, Monterrey, Nuevo León",
        "lugar_nacimiento": "Monterrey, Nuevo León",
        "nacionalidad": "Mexicana",
        "ocupacion": "Estudiante Universitaria de Bioquímica",
        "telefono_local": "8183401928",
        "celular": "528183401928",
        "email": "sofia.rios.nav@outlook.com",
        "contacto_emergencia_nombre": "Gabriela Navarrete (Madre)",
        "contacto_emergencia_tel": "8181293847",
        "disease_name": "Asma Bronquial Alérgica Persistente Moderada",
        "cie10_code": "J45.0",
        "specialty": "Neumología",
        "alergias": [
            {"descripcion": "Polen de olivo y pastos", "tipo": "ambiental", "severidad": "moderada"},
            {"descripcion": "Ácaros del polvo doméstico", "tipo": "ambiental", "severidad": "moderada"},
            {"descripcion": "Ibuprofeno y Naproxeno (AINEs)", "tipo": "medicamento", "severidad": "severa"}
        ],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Rinitis alérgica estacional desde la infancia", "fecha": "2012-04-01"}
        ],
        "subjetivo": "Paciente femenina de 22 años que presenta tos seca nocturna, sibilancias audibles y disnea mMRC 2 tras exposición a clima frío y ejercicio en exteriores.",
        "objetivo": "FR: 22 rpm, FC: 86 lpm, SpO2: 94% al aire ambiente. A la auscultación se aprecian sibilancias tele-espiratorias bilaterales diseminadas. FEV1 basal 72% del predicho.",
        "analisis": "Exacerbación asmática leve-moderada secundaria a factores climáticos. FEV1 con respuesta broncodilatadora positiva.",
        "plan": "Ciclo de mantenimiento con Budesonida/Formoterol 160/4.5 mcg 1 inhalación cada 12 h más rescate según necesidad. Salbutamol de rescate. Revisión espirométrica en 1 mes.",
        "rx": [
            {"medicamento": "Budesonida / Formoterol", "presentacion": "Polvo para inhalación 160/4.5 mcg", "dosis": "1 inhalación", "frecuencia": "Cada 12 horas fija", "duracion": "30 días"},
            {"medicamento": "Salbutamol aerosol", "presentacion": "Inhalador 100 mcg/dosis", "dosis": "2 disparos con espaciador", "frecuencia": "En caso de crisis de sibilancias o disnea", "duracion": "Prn"}
        ],
        "vitals": {"hr": 86, "spo2": 94, "sys": 112, "dia": 74, "temp": 36.7, "steps": 7890, "device": "Garmin Venu 3"}
    },
    {
        "nombres": "Mateo",
        "primer_apellido": "López",
        "segundo_apellido": "Estrada",
        "curp": "LOEM740618HJCRT08",
        "rfc": "LOEM740618AA9",
        "nss": "28947412903",
        "sexo": "M",
        "fecha_nacimiento": "1974-06-18",
        "altura_cm": 170.0,
        "peso_kg": 72.0,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0104",
        "ubicacion_casa": "Calle Morelos 340, Zona Centro, Guadalajara, Jalisco",
        "lugar_nacimiento": "Guadalajara, Jalisco",
        "nacionalidad": "Mexicana",
        "ocupacion": "Profesor de Preparatoria",
        "telefono_local": "3336128490",
        "celular": "523336128490",
        "email": "mlopez_estrada@udg.mx",
        "contacto_emergencia_nombre": "Maricela Estrada (Hermana)",
        "contacto_emergencia_tel": "3338901234",
        "disease_name": "Neumonía Bacteriana Adquirida en la Comunidad (NAC)",
        "cie10_code": "J18.9",
        "specialty": "Neumología / Infectología",
        "alergias": [
            {"descripcion": "Amoxicilina / Ampicilina (urticaria generalizada)", "tipo": "medicamento", "severidad": "severa"}
        ],
        "antecedentes": [
            {"tipo": "no patologico", "descripcion": "Ex-fumador de 5 paquetes-año, suspendido hace 8 años", "fecha": "2018-01-01"}
        ],
        "subjetivo": "Masculino de 51 años con cuadro de 5 días con fiebre de hasta 38.8 °C, escalofríos, tos productiva con expectoración herrumbrosa y dolor torácico pleurítico en hemitórax derecho.",
        "objetivo": "Temp: 38.6 °C, FC: 102 lpm, FR: 24 rpm, SpO2: 91% aire ambiente, TA: 118/76 mmHg. Estertores crepitantes en base pulmonar derecha con aumento del frémito vocal y submatidez.",
        "analisis": "Neumonía bacteriana adquirida en la comunidad, CURB-65 = 1 punto (edad < 65, FR 24, TA normal). Alérgico a penicilinas, requiere macrólido o quinolona respiratoria.",
        "plan": "Manejo ambulatorio estrecho con Levofloxacino 500 mg c/24 h por 7 días. Paracetamol para control térmico. Rx de tórax AP y lateral de control. Acudir a urgencias si SpO2 < 90%.",
        "rx": [
            {"medicamento": "Levofloxacino", "presentacion": "Comprimidos 500 mg", "dosis": "1 comprimido", "frecuencia": "Cada 24 horas por 7 días", "duracion": "7 días"},
            {"medicamento": "Paracetamol", "presentacion": "Tabletas 500 mg", "dosis": "1 tableta", "frecuencia": "Cada 8 horas en caso de fiebre > 38 °C", "duracion": "5 días"}
        ],
        "vitals": {"hr": 102, "spo2": 91, "sys": 118, "dia": 76, "temp": 38.6, "steps": 1420, "device": "Withings ScanWatch"}
    },
    {
        "nombres": "Camila",
        "primer_apellido": "Hernández",
        "segundo_apellido": "Salazar",
        "curp": "HESC050814MDFRL02",
        "rfc": "HESC0508149T1",
        "nss": "89230578129",
        "sexo": "F",
        "fecha_nacimiento": "2005-08-14",
        "altura_cm": 165.0,
        "peso_kg": 58.0,
        "tipo_sangre": "A-",
        "folio_hospital": "EXP-2026-0105",
        "ubicacion_casa": "Calle 60 Norte #312, Fracc. Campestre, Mérida, Yucatán",
        "lugar_nacimiento": "Mérida, Yucatán",
        "nacionalidad": "Mexicana",
        "ocupacion": "Diseñadora Gráfica Jr.",
        "telefono_local": "9999441188",
        "celular": "529999441188",
        "email": "camila.hdz.sal@design.io",
        "contacto_emergencia_nombre": "Enrique Hernández (Padre)",
        "contacto_emergencia_tel": "9999120033",
        "disease_name": "Apendicitis Aguda Focal / Abdomen Agudo",
        "cie10_code": "K35.8",
        "specialty": "Cirugía General",
        "alergias": [],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Gastritis erosiva tratada con IBP en 2024", "fecha": "2024-02-10"}
        ],
        "subjetivo": "Femenina de 20 años acude por dolor abdominal de inicio periumbilical hace 16 horas, con posterior migración a fosa ilíaca derecha. Acompañado de náuseas, vómito de contenido gastrobiliar en 2 ocasiones e hiporexia.",
        "objetivo": "Temp: 37.8 °C, FC: 98 lpm, TA: 110/70 mmHg. Abdomen plano, con dolor intenso a la palpación en punto de McBurney (+), signo de Blumberg (+) franco, Rovsing (+). Peristalsis disminuida.",
        "analisis": "Cuadro clínico y signología altamente sugestivos de Apendicitis Aguda (Escala de Alvarado: 8 puntos - Probabilidad Alta). Urgencia quirúrgica.",
        "plan": "Ayuno inmediato, canalización de vía venosa periférica con Hartman 1000 cc para 8 horas. Laboratorios prequirúrgicos (BH, TP, TTP, Grupo y Rh) y valoración urgente por Cirugía General para apendicectomía laparoscópica.",
        "rx": [
            {"medicamento": "Ketorolaco trometamina", "presentacion": "Solución inyectable 30 mg / 1 ml", "dosis": "30 mg IV dosis única", "frecuencia": "Previa valoración quirúrgica", "duracion": "1 dosis"}
        ],
        "vitals": {"hr": 98, "spo2": 98, "sys": 110, "dia": 70, "temp": 37.8, "steps": 850, "device": "Monitor Clínico Urgencias"}
    },
    {
        "nombres": "Ignacio",
        "primer_apellido": "Fuentes",
        "segundo_apellido": "Beltrán",
        "curp": "FUBI600305HPLEL07",
        "rfc": "FUBI600305K99",
        "nss": "12786034981",
        "sexo": "M",
        "fecha_nacimiento": "1960-03-05",
        "altura_cm": 168.0,
        "peso_kg": 69.0,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0106",
        "ubicacion_casa": "Calle 5 de Mayo #78, Centro Histórico, Puebla, Puebla",
        "lugar_nacimiento": "Puebla, Puebla",
        "nacionalidad": "Mexicana",
        "ocupacion": "Jubilado del Sector Educativo",
        "telefono_local": "2222458901",
        "celular": "522222458901",
        "email": "ignacio.fuentes.b@gmail.com",
        "contacto_emergencia_nombre": "Rosario Beltrán (Hija)",
        "contacto_emergencia_tel": "2221098472",
        "disease_name": "Artritis Reumatoide Seropositiva",
        "cie10_code": "M05.9",
        "specialty": "Reumatología",
        "alergias": [
            {"descripcion": "Metoclopramida (síntomas extrapiramidales)", "tipo": "medicamento", "severidad": "moderada"}
        ],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Diagnóstico de Artritis Reumatoide hace 7 años", "fecha": "2019-03-15"}
        ],
        "subjetivo": "Masculino de 66 años con dolor articular simétrico en articulaciones metacarpofalángicas e interfalángicas proximales de ambas manos, asociado a rigidez matutina de 90 minutos de duración.",
        "objetivo": "Sinovitis y tumefacción palpable en 2da y 3ra MCF bilaterales. Desviación cubital incipiente sin anquilosis. VSG: 42 mm/h, PCR: 28 mg/L, Factor Reumatoide: 140 UI/mL, Anti-CCP positivo >200.",
        "analisis": "Artritis Reumatoide activa con actividad inflamatoria moderada-alta (DAS28 = 4.8). Requiere optimización de FARME.",
        "plan": "Metotrexato 15 mg VO semanal más Ácido Fólico 5 mg semanal (24 h después). Prednisona 5 mg c/24 h como terapia puente. Control de biometría hemática y enzimas hepáticas mensual.",
        "rx": [
            {"medicamento": "Metotrexato", "presentacion": "Tabletas 2.5 mg", "dosis": "6 tabletas (15 mg)", "frecuencia": "Una vez a la semana los días lunes", "duracion": "90 días"},
            {"medicamento": "Ácido Fólico", "presentacion": "Tabletas 5 mg", "dosis": "1 tableta", "frecuencia": "Una vez a la semana los días martes", "duracion": "90 días"}
        ],
        "vitals": {"hr": 72, "spo2": 96, "sys": 128, "dia": 78, "temp": 36.4, "steps": 3200, "device": "Omron Wrist 7 Series"}
    },
    {
        "nombres": "Valeria",
        "primer_apellido": "Pantoja",
        "segundo_apellido": "Canto",
        "curp": "PACV950119MYNLR03",
        "rfc": "PACV9501198A4",
        "nss": "78169524018",
        "sexo": "F",
        "fecha_nacimiento": "1995-01-19",
        "altura_cm": 160.0,
        "peso_kg": 52.0,
        "tipo_sangre": "AB+",
        "folio_hospital": "EXP-2026-0107",
        "ubicacion_casa": "Calle 21 #145, Col. Chuburná de Hidalgo, Mérida, Yucatán",
        "lugar_nacimiento": "Tizimín, Yucatán",
        "nacionalidad": "Mexicana",
        "ocupacion": "Bióloga Marina",
        "telefono_local": "9999812499",
        "celular": "529999812499",
        "email": "valeria.pantoja@ciencias.unam.mx",
        "contacto_emergencia_nombre": "Carlos Pantoja (Padre)",
        "contacto_emergencia_tel": "9861029384",
        "disease_name": "Dengue con Signos de Alarma",
        "cie10_code": "A90",
        "specialty": "Medicina Interna / Infectología",
        "alergias": [],
        "antecedentes": [
            {"tipo": "no patologico", "descripcion": "Trabajo de campo reciente en zona costera de Yucatán", "fecha": "2026-10-25"}
        ],
        "subjetivo": "Femenina de 31 años con fiebre de 4 días de evolución (39.5 °C), cefalea retroocular intensa, mialgias y artralgias intensas (fiebre quebrantahuesos). Hoy presenta dolor abdominal continuo y epistaxis leve.",
        "objetivo": "Temp: 38.1 °C, TA: 100/65 mmHg, FC: 94 lpm. Petequias en miembros superiores. Prueba de torniquete (+). Abdomen con dolor a la palpación en epigastrio y cuadrante superior derecho. Laboratorio: Plaquetas 65,000/uL, Hematocrito 44% (hemoconcentración), Leucocitos 2,800/uL.",
        "analisis": "Dengue con Signos de Alarma (dolor abdominal intenso, hemoconcentración, plaquetopenia y sangrado mucoso). Requiere ingreso hospitalario para fluidoterapia parenteral estricta.",
        "plan": "Hospitalización para hidratación con solución salina al 0.9% a 7 ml/kg/h. Monitoreo horario de signos vitales y diuresis. Biometría hemática de control cada 12 horas. Contraindicados totalmente AINEs y ácido acetilsalicílico.",
        "rx": [
            {"medicamento": "Paracetamol", "presentacion": "Solución IV 1 g / 100 ml", "dosis": "1 g IV", "frecuencia": "Cada 8 horas en infusión de 20 min si dolor/fiebre", "duracion": "3 días"}
        ],
        "vitals": {"hr": 94, "spo2": 97, "sys": 100, "dia": 65, "temp": 38.1, "steps": 410, "device": "Monitor Piso Medicina Interna"}
    },
    {
        "nombres": "Guillermo",
        "primer_apellido": "Orozco",
        "segundo_apellido": "Villarreal",
        "curp": "OOVG531201HTSNLN08",
        "rfc": "OOVG5312012M9",
        "nss": "09735312984",
        "sexo": "M",
        "fecha_nacimiento": "1953-12-01",
        "altura_cm": 172.0,
        "peso_kg": 81.0,
        "tipo_sangre": "O-",
        "folio_hospital": "EXP-2026-0108",
        "ubicacion_casa": "Calzada del Valle 405, San Pedro Garza García, Nuevo León",
        "lugar_nacimiento": "Hermosillo, Sonora",
        "nacionalidad": "Mexicana",
        "ocupacion": "Ingeniero Industrial Consultor",
        "telefono_local": "8183569012",
        "celular": "528183569012",
        "email": "gorozco.v@consultores.com",
        "contacto_emergencia_nombre": "Silvia Villarreal (Esposa)",
        "contacto_emergencia_tel": "8182774910",
        "disease_name": "Enfermedad Renal Crónica Estadio G3b A2",
        "cie10_code": "N18.3",
        "specialty": "Nefrología",
        "alergias": [
            {"descripcion": "Medios de contraste yodados (reacción anafilactoide)", "tipo": "medicamento", "severidad": "severa"}
        ],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Hipertensión arterial sistémica de 20 años de evolución", "fecha": "2006-05-18"},
            {"tipo": "patologico", "descripcion": "Hiperuricemia con episodios de gota", "fecha": "2015-11-04"}
        ],
        "subjetivo": "Masculino de 72 años en seguimiento nefrológico. Refiere edema bimaleolar vespertino que cede con el decúbito, nicturia x3 y sabor metálico ocasional en boca.",
        "objetivo": "TA: 138/84 mmHg, FC: 70 lpm. Edema pretibial con fóvea grado I (+). Creatinina sérica: 1.95 mg/dL, Urea: 68 mg/dL, TFG estimada por CKD-EPI: 36 mL/min/1.73m2. Albuminuria en orina de 24 h: 180 mg/día.",
        "analisis": "Enfermedad Renal Crónica Estadio 3b (TFG 30-44) categoría A2 de albuminuria secundaria a nefroangioesclerosis hipertensiva. Control de progresión prioritario.",
        "plan": "Ajuste de dosis de IECA/ARA-II con vigilancia estrecha de potasio sérico. Restricción proteica a 0.8 g/kg/día y de sodio a < 2 g/día. Alopurinol 100 mg para manejo de hiperuricemia.",
        "rx": [
            {"medicamento": "Telmisartán", "presentacion": "Tabletas 40 mg", "dosis": "1 tableta", "frecuencia": "Cada 24 horas matutina", "duracion": "60 días"},
            {"medicamento": "Alopurinol", "presentacion": "Comprimidos 100 mg", "dosis": "1 comprimido", "frecuencia": "Cada 24 horas después del almuerzo", "duracion": "60 días"}
        ],
        "vitals": {"hr": 70, "spo2": 97, "sys": 138, "dia": 84, "temp": 36.3, "steps": 2890, "device": "Omron Evolv Wireless"}
    },
    {
        "nombres": "Beatriz",
        "primer_apellido": "Salgado",
        "segundo_apellido": "Ponce",
        "curp": "SAPB640703MGRNL06",
        "rfc": "SAPB640703HP2",
        "nss": "25846491035",
        "sexo": "F",
        "fecha_nacimiento": "1964-07-03",
        "altura_cm": 155.0,
        "peso_kg": 68.0,
        "tipo_sangre": "A+",
        "folio_hospital": "EXP-2026-0109",
        "ubicacion_casa": "Costera Miguel Alemán #120, Acapulco, Guerrero",
        "lugar_nacimiento": "Chilpancingo, Guerrero",
        "nacionalidad": "Mexicana",
        "ocupacion": "Comerciante",
        "telefono_local": "7444829104",
        "celular": "527444829104",
        "email": "beatriz.salgado.p@hotmail.com",
        "contacto_emergencia_nombre": "Mario Salgado (Hijo)",
        "contacto_emergencia_tel": "7441029481",
        "disease_name": "Insuficiencia Cardíaca Congestiva NYHA II FEy reducida",
        "cie10_code": "I50.9",
        "specialty": "Cardiología",
        "alergias": [],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Infarto previo no Q de cara inferior en 2021", "fecha": "2021-09-10"}
        ],
        "subjetivo": "Femenina de 62 años que acude a revisión cardiológica. Manifiesta disnea de medianos esfuerzos al subir un piso de escaleras (NYHA II) y ortopnea que requiere 2 almohadas.",
        "objetivo": "TA: 115/72 mmHg, FC: 66 lpm, SpO2: 96%. Ingurgitación yugular grado I a 45 grados. Ruidos cardíacos con ritmo de galope por tercer ruido (S3). Estertores basales finos bilaterales. Ecocardiograma: FEVI 38%.",
        "analisis": "Insuficiencia cardíaca con fracción de eyección reducida (IC-FEr) secundaria a cardiopatía isquémica. Estabilidad clínica relativa.",
        "plan": "Continuar con cuádruple terapia neurohumoral: Sacubitrilo/Valsartán 24/26 mg c/12h, Bisoprolol 2.5 mg c/24h, Espironolactona 25 mg c/24h y Dapagliflozina 10 mg c/24h. Restricción hídrica a 1.5 L/día.",
        "rx": [
            {"medicamento": "Sacubitrilo / Valsartán", "presentacion": "Comprimidos 24/26 mg", "dosis": "1 comprimido", "frecuencia": "Cada 12 horas", "duracion": "30 días"},
            {"medicamento": "Bisoprolol", "presentacion": "Tabletas 2.5 mg", "dosis": "1 tableta", "frecuencia": "Cada 24 horas por la mañana", "duracion": "30 días"}
        ],
        "vitals": {"hr": 66, "spo2": 96, "sys": 115, "dia": 72, "temp": 36.5, "steps": 3100, "device": "Apple Watch Ultra 2"}
    },
    {
        "nombres": "Diego",
        "primer_apellido": "Canto",
        "segundo_apellido": "Alcocer",
        "curp": "CAAD080530HYNLR04",
        "rfc": "CAAD080530AA1",
        "nss": "98260812904",
        "sexo": "M",
        "fecha_nacimiento": "2008-05-30",
        "altura_cm": 171.0,
        "peso_kg": 63.0,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0110",
        "ubicacion_casa": "Calle 33-A #402, Fracc. Chenkú, Mérida, Yucatán",
        "lugar_nacimiento": "Mérida, Yucatán",
        "nacionalidad": "Mexicana",
        "ocupacion": "Estudiante de Bachillerato",
        "telefono_local": "9999201948",
        "celular": "529999201948",
        "email": "diego.canto.alc@gmail.com",
        "contacto_emergencia_nombre": "Verónica Alcocer (Madre)",
        "contacto_emergencia_tel": "9991827364",
        "disease_name": "Gastroenteritis Infecciosa Aguda / Deshidratación Grado II",
        "cie10_code": "A09",
        "specialty": "Pediatría / Medicina General",
        "alergias": [
            {"descripcion": "Trimetoprima con Sulfametoxazol", "tipo": "medicamento", "severidad": "moderada"}
        ],
        "antecedentes": [
            {"tipo": "no patologico", "descripcion": "Consumo de alimentos en vía pública hace 24 horas", "fecha": "2026-11-15"}
        ],
        "subjetivo": "Adolescente de 18 años con inicio brusco de evacuaciones diarreicas líquidas abundantes (8 en las últimas 12 horas) sin moco ni sangre visible, cólico abdominal difuso y náuseas intensas.",
        "objetivo": "Temp: 37.9 °C, FC: 104 lpm, TA: 105/65 mmHg. Mucosa oral seca, signo del pliegue cutáneo levemente positivo (+), ojos ligeramente hundidos. Abdomen blando pero doloroso difusamente.",
        "analisis": "Gastroenteritis aguda probablemente infecciosa bacteriana con deshidratación isotónica moderada.",
        "plan": "Rehidratación oral activa con Suero Vida Oral a libre demanda (150-200 ml tras cada evacuación líquida). Probióticos de Saccharomyces boulardii. Ciprofloxacino 500 mg c/12h por 3 días si persisten fiebres y cólicos.",
        "rx": [
            {"medicamento": "Sales de Rehidratación Oral (Vida Suero Oral)", "presentacion": "Sobres para 1 Litro", "dosis": "1 sobre diluido en 1L de agua hervida", "frecuencia": "Tomar a sorbos continuos", "duracion": "5 días"},
            {"medicamento": "Saccharomyces boulardii", "presentacion": "Cápsulas 250 mg", "dosis": "1 cápsula", "frecuencia": "Cada 12 horas por 5 días", "duracion": "5 días"}
        ],
        "vitals": {"hr": 104, "spo2": 98, "sys": 105, "dia": 65, "temp": 37.9, "steps": 1200, "device": "Fitbit Charge 6"}
    },
    {
        "nombres": "Lucía",
        "primer_apellido": "Morales",
        "segundo_apellido": "Zavala",
        "curp": "MOZL891012MDFRN07",
        "rfc": "MOZL8910127Y8",
        "nss": "31098947210",
        "sexo": "F",
        "fecha_nacimiento": "1989-10-12",
        "altura_cm": 167.0,
        "peso_kg": 60.0,
        "tipo_sangre": "A+",
        "folio_hospital": "EXP-2026-0111",
        "ubicacion_casa": "Calle Colima 230, Col. Roma Norte, Cuauhtémoc, CDMX",
        "lugar_nacimiento": "Ciudad de México",
        "nacionalidad": "Mexicana",
        "ocupacion": "Editora en Jefe de Revista Digital",
        "telefono_local": "5552093841",
        "celular": "525552093841",
        "email": "lucia.morales.zavala@media.com",
        "contacto_emergencia_nombre": "Esteban Zavala (Hermano)",
        "contacto_emergencia_tel": "5551928374",
        "disease_name": "Migraña Crónica con Aura Oftálmica",
        "cie10_code": "G43.1",
        "specialty": "Neurología",
        "alergias": [
            {"descripcion": "Codeína / Tramadol (náusea severa y vértigo)", "tipo": "medicamento", "severidad": "moderada"}
        ],
        "antecedentes": [
            {"tipo": "heredofamiliar", "descripcion": "Madre y tía materna con antecedente de migraña con aura", "fecha": "2010-01-01"},
            {"tipo": "patologico", "descripcion": "Cefalea episódica que evolucionó a patrón crónico (>15 días/mes)", "fecha": "2023-04-10"}
        ],
        "subjetivo": "Femenina de 37 años que refiere crisis incapacitante precedida de escotomas centellantes en hemicampo visual derecho de 20 minutos de duración, seguidos de hemicránea izquierda punzante 9/10, fotofobia y sonofobia.",
        "objetivo": "TA: 120/75 mmHg, FC: 76 lpm. Examen neurológico completo sin signos meníngeos ni focalización motora o sensitiva interictal. Reflejos osteotendinosos normales.",
        "analisis": "Migraña episódica de alta frecuencia con aura típica que cumple criterios de migraña crónica según la ICHD-3.",
        "plan": "Tratamiento abortivo agudo con Zolmitriptán 2.5 mg al inicio de la fase de dolor. Profilaxis con Topiramato 25 mg c/24h con titulación progresiva. Higiene del sueño y diario de cefaleas.",
        "rx": [
            {"medicamento": "Zolmitriptán", "presentacion": "Comprimidos bucodispersables 2.5 mg", "dosis": "1 comprimido", "frecuencia": "Al iniciar el dolor agudo (máx 2 al día)", "duracion": "Prn"},
            {"medicamento": "Topiramato", "presentacion": "Tabletas 25 mg", "dosis": "1 tableta por la noche", "frecuencia": "Cada 24 horas por 30 días", "duracion": "30 días"}
        ],
        "vitals": {"hr": 76, "spo2": 99, "sys": 120, "dia": 75, "temp": 36.6, "steps": 5400, "device": "Oura Ring Gen 3"}
    },
    {
        "nombres": "Fabiola",
        "primer_apellido": "Guerrero",
        "segundo_apellido": "Maldonado",
        "curp": "GUMF780224MCLNS02",
        "rfc": "GUMF7802245T2",
        "nss": "58987823410",
        "sexo": "F",
        "fecha_nacimiento": "1978-02-24",
        "altura_cm": 159.0,
        "peso_kg": 74.0,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0112",
        "ubicacion_casa": "Av. Venustiano Carranza 1820, Col. Tequisquiapan, San Luis Potosí, SLP",
        "lugar_nacimiento": "San Luis Potosí, SLP",
        "nacionalidad": "Mexicana",
        "ocupacion": "Directora Administrativa Escolar",
        "telefono_local": "4448139045",
        "celular": "524448139045",
        "email": "fabiola.guerrero.m@educacion.mx",
        "contacto_emergencia_nombre": "Jaime Maldonado (Hermano)",
        "contacto_emergencia_tel": "4441920394",
        "disease_name": "Hipotiroidismo Primario Autoinmune (Hashimoto)",
        "cie10_code": "E03.9",
        "specialty": "Endocrinología",
        "alergias": [],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Bocio difuso grado I detectado en chequeo anual 2023", "fecha": "2023-07-20"}
        ],
        "subjetivo": "Femenina de 48 años que refiere fatiga marcada progresiva, aumento de peso de 4 kg en 3 meses a pesar de dieta habitual, intolerancia severa al frío, caída de cabello y estreñimiento crónico.",
        "objetivo": "TA: 110/70 mmHg, FC: 58 lpm (bradicardia sinusal), Temp: 36.1 °C. Piel seca, áspera y fría. Tiroides palpable, difusamente aumentada de consistencia, no dolorosa. TSH: 14.8 uUI/mL (muy elevada), T4 Libre: 0.62 ng/dL (baja), Anti-TPO positivos >600.",
        "analisis": "Hipotiroidismo primario manifiesto por tiroiditis autoinmune crónica de Hashimoto. Requiere inicio de terapia de reemplazo hormonal tiroideo.",
        "plan": "Levotiroxina sódica 75 mcg vía oral en ayunas estricto, 30 minutos antes del desayuno con agua natural. Control de perfil tiroideo (TSH y T4L) en 8 semanas.",
        "rx": [
            {"medicamento": "Levotiroxina sódica", "presentacion": "Tabletas 75 mcg", "dosis": "1 tableta en ayuno estricto", "frecuencia": "Cada 24 horas por la mañana", "duracion": "60 días"}
        ],
        "vitals": {"hr": 58, "spo2": 98, "sys": 110, "dia": 70, "temp": 36.1, "steps": 3950, "device": "Apple Watch Series 8"}
    },
    {
        "nombres": "Fernando",
        "primer_apellido": "Soto",
        "segundo_apellido": "Campos",
        "curp": "SOCF510410HDFMS05",
        "rfc": "SOCF510410KK1",
        "nss": "11715104921",
        "sexo": "M",
        "fecha_nacimiento": "1951-04-10",
        "altura_cm": 169.0,
        "peso_kg": 62.0,
        "tipo_sangre": "B+",
        "folio_hospital": "EXP-2026-0113",
        "ubicacion_casa": "Calle Tlaxcala 102, Col. Roma Sur, Cuauhtémoc, CDMX",
        "lugar_nacimiento": "Ciudad de México",
        "nacionalidad": "Mexicana",
        "ocupacion": "Mecánico Automotriz Retirado",
        "telefono_local": "5555748920",
        "celular": "525555748920",
        "email": "fernando.soto.c@gmail.com",
        "contacto_emergencia_nombre": "Rosa Soto Campos (Hija)",
        "contacto_emergencia_tel": "5558901243",
        "disease_name": "Enfermedad Pulmonar Obstructiva Crónica (EPOC) GOLD 2 B",
        "cie10_code": "J44.9",
        "specialty": "Neumología",
        "alergias": [],
        "antecedentes": [
            {"tipo": "no patologico", "descripcion": "Tabaquismo intenso: 35 paquetes-año (20 cigarrillos al día por 35 años)", "fecha": "2015-01-01"}
        ],
        "subjetivo": "Masculino de 75 años con disnea progresiva de esfuerzo al caminar 100 metros en terreno llano, tos crónica matutina productiva con esputo blanquecino y fatiga generalizada.",
        "objetivo": "FR: 20 rpm, SpO2: 89% al aire ambiente, FC: 80 lpm. Tórax en tonel con disminución de la expansión torácica. Ruidos respiratorios disminuidos globalmente con espiración prolongada. Espirometría post-broncodilatador: FEV1/FVC 0.58, FEV1 54%.",
        "analisis": "EPOC fenotipo no agudizador estadio GOLD 2 grupo B. Hipoxemia leve que requiere optimización broncodilatadora dual.",
        "plan": "Terapia broncodilatadora dual LAMA/LABA con Tiotropio/Olodaterol 2.5/2.5 mcg (2 inhalaciones c/24h). Vacunación antineumocócica y anti-influenza actualizada. Rehabilitación pulmonar.",
        "rx": [
            {"medicamento": "Tiotropio / Olodaterol", "presentacion": "Solución para inhalación Respimat 2.5/2.5 mcg", "dosis": "2 inhalaciones", "frecuencia": "Cada 24 horas a la misma hora", "duracion": "30 días"}
        ],
        "vitals": {"hr": 80, "spo2": 89, "sys": 126, "dia": 76, "temp": 36.4, "steps": 2100, "device": "Pulsoxímetro Nonin Bluetooth"}
    },
    {
        "nombres": "Mariana",
        "primer_apellido": "Ibarra",
        "segundo_apellido": "Castañeda",
        "curp": "IACM920315MJCLNR01",
        "rfc": "IACM9203154P3",
        "nss": "67129204918",
        "sexo": "F",
        "fecha_nacimiento": "1992-03-15",
        "altura_cm": 164.0,
        "peso_kg": 57.0,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0114",
        "ubicacion_casa": "Paseo de los Leones 2410, Cumbres 4to Sector, Monterrey, Nuevo León",
        "lugar_nacimiento": "Guadalajara, Jalisco",
        "nacionalidad": "Mexicana",
        "ocupacion": "Ejecutiva de Cuentas Financieras",
        "telefono_local": "8183120945",
        "celular": "528183120945",
        "email": "mariana.ibarra.c@banca.com",
        "contacto_emergencia_nombre": "Javier Castañeda (Primo)",
        "contacto_emergencia_tel": "8184901283",
        "disease_name": "Pielonefritis Aguda No Complicada / Infección de Vías Urinarias Altas",
        "cie10_code": "N10",
        "specialty": "Urología / Nefrología",
        "alergias": [
            {"descripcion": "Sulfamidas (reacción cutánea y fotosensibilidad)", "tipo": "medicamento", "severidad": "moderada"}
        ],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Episodios de cistitis recurrente en 2025", "fecha": "2025-06-12"}
        ],
        "subjetivo": "Femenina de 34 años acude con fiebre alta de 39.0 °C, escalofríos intensos con temblor, dolor punzante en fosa renal izquierda de 36 h de evolución, disuria, polaquiuria y náusea sin vómito.",
        "objetivo": "Temp: 38.9 °C, TA: 112/68 mmHg, FC: 106 lpm. Puñopercusión lumbar izquierda francamente positiva (Signo de Giordano izquierdo +++). EGO: Piuria abundante, leucocitos >50 x campo, nitritos positivos, bacteriuria abundante.",
        "analisis": "Pielonefritis aguda izquierda sin datos de sepsis ni compromiso hemodinámico. Candidata a antibioticoterapia ambulatoria con seguimiento estricto.",
        "plan": "Ceftriaxona 1 g IM dosis inicial en consultorio y continuar con Ciprofloxacino 500 mg VO c/12h por 7 días. Hidratación abundante (2.5 litros de agua al día). Urocultivo de control.",
        "rx": [
            {"medicamento": "Ceftriaxona", "presentacion": "Solución inyectable 1 g / 3.5 ml", "dosis": "1 g intramuscular", "frecuencia": "Dosis única hoy", "duracion": "1 dosis"},
            {"medicamento": "Ciprofloxacino", "presentacion": "Comprimidos 500 mg", "dosis": "1 comprimido", "frecuencia": "Cada 12 horas por 7 días", "duracion": "7 días"}
        ],
        "vitals": {"hr": 106, "spo2": 97, "sys": 112, "dia": 68, "temp": 38.9, "steps": 1650, "device": "Fitbit Versa 4"}
    },
    {
        "nombres": "Rodrigo",
        "primer_apellido": "Vega",
        "segundo_apellido": "Montero",
        "curp": "VEMR850820HDFNTS03",
        "rfc": "VEMR8508202Q1",
        "nss": "24058512940",
        "sexo": "M",
        "fecha_nacimiento": "1985-08-20",
        "altura_cm": 178.0,
        "peso_kg": 84.0,
        "tipo_sangre": "AB-",
        "folio_hospital": "EXP-2026-0115",
        "ubicacion_casa": "Calle Eugenia 612, Col. Del Valle Centro, Benito Juárez, CDMX",
        "lugar_nacimiento": "Ciudad de México",
        "nacionalidad": "Mexicana",
        "ocupacion": "Programador Senior de Software",
        "telefono_local": "5555430981",
        "celular": "525555430981",
        "email": "rodrigo.vega.mon@dev.io",
        "contacto_emergencia_nombre": "Adriana Montero (Hermana)",
        "contacto_emergencia_tel": "5559812401",
        "disease_name": "COVID-19 Agudo con Síntomas Respiratorios",
        "cie10_code": "U07.1",
        "specialty": "Infectología",
        "alergias": [],
        "antecedentes": [
            {"tipo": "no patologico", "descripcion": "Vacunación COVID-19 con esquema primario completo y 2 refuerzos", "fecha": "2023-11-10"}
        ],
        "subjetivo": "Masculino de 41 años con inicio de odinofagia intensa hace 3 días, fiebre cuantificada en 38.4 °C, rinorrea hialina profusa, mialgias en espalda baja y pérdida súbita del olfato (anosmia).",
        "objetivo": "Temp: 38.2 °C, FC: 88 lpm, SpO2: 96% al aire ambiente, TA: 122/80 mmHg. Faringe hiperémica con exudado no purulento. Prueba rápida de antígeno SARS-CoV-2 en exudado nasofaríngeo: POSITIVA.",
        "analisis": "Infección por SARS-CoV-2 (COVID-19) confirmada por prueba de antígeno, cuadro respiratorio agudo leve sin datos de neumonía ni desaturación.",
        "plan": "Aislamiento domiciliario por 5 días. Tratamiento sintomático con Paracetamol 500 mg c/8h y lavado nasal con solución salina isotónica. Monitoreo de SpO2 3 veces al día con oxímetro.",
        "rx": [
            {"medicamento": "Paracetamol", "presentacion": "Tabletas 500 mg", "dosis": "1 tableta", "frecuencia": "Cada 8 horas si hay fiebre o dolor muscular", "duracion": "5 días"}
        ],
        "vitals": {"hr": 88, "spo2": 96, "sys": 122, "dia": 80, "temp": 38.2, "steps": 2400, "device": "Garmin Forerunner 265"}
    },
    {
        "nombres": "Paola",
        "primer_apellido": "Treviño",
        "segundo_apellido": "Garza",
        "curp": "TRGP900604MNLRRN09",
        "rfc": "TRGP9006041L8",
        "nss": "49109028471",
        "sexo": "F",
        "fecha_nacimiento": "1990-06-04",
        "altura_cm": 163.0,
        "peso_kg": 56.0,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0116",
        "ubicacion_casa": "Calle Río Mississippi 310, Col. Del Valle, San Pedro Garza García, NL",
        "lugar_nacimiento": "Monterrey, Nuevo León",
        "nacionalidad": "Mexicana",
        "ocupacion": "Psicóloga Clínica",
        "telefono_local": "8183789012",
        "celular": "528183789012",
        "email": "paola.trevino.g@saludmental.com",
        "contacto_emergencia_nombre": "Raúl Treviño (Padre)",
        "contacto_emergencia_tel": "8181029341",
        "disease_name": "Trastorno Depresivo Mayor Episodio Recurrente / Ansiedad Generalizada",
        "cie10_code": "F33.1",
        "specialty": "Psiquiatría",
        "alergias": [],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Primer episodio depresivo en 2021 tratado exitosamente con ISRS", "fecha": "2021-04-10"}
        ],
        "subjetivo": "Femenina de 36 años que refiere anhedonia profunda desde hace 6 semanas, tristeza persistente, insomnio de mantenimiento con despertar precoz (04:00 AM), fatiga mental intensa y crisis de angustia con opresión precordial.",
        "objetivo": "Escala de Depresión PHQ-9: 18 puntos (Depresión moderadamente severa). Escala de Ansiedad GAD-7: 15 puntos (Ansiedad severa). Juicio de realidad conservado, sin ideación suicida activa estructurada.",
        "analisis": "Trastorno Depresivo Mayor episodio recurrente de intensidad moderada-severa con componente de ansiedad generalizada comórbido.",
        "plan": "Reintroducción de Escitalopram 10 mg c/24h matutino (incrementar a 20 mg tras 2 semanas). Clonazepam 0.5 mg 1/2 tableta por las noches por 3 semanas para insomnio inicial. Psicoterapia cognitivo-conductual semanal.",
        "rx": [
            {"medicamento": "Escitalopram", "presentacion": "Tabletas 10 mg", "dosis": "1 tableta en el desayuno", "frecuencia": "Cada 24 horas por la mañana", "duracion": "30 días"},
            {"medicamento": "Clonazepam", "presentacion": "Comprimidos 0.5 mg", "dosis": "1/2 comprimido nocturno", "frecuencia": "Cada 24 horas al acostarse por 15 días", "duracion": "15 días"}
        ],
        "vitals": {"hr": 74, "spo2": 99, "sys": 118, "dia": 76, "temp": 36.5, "steps": 6120, "device": "Apple Watch SE"}
    },
    {
        "nombres": "Santiago",
        "primer_apellido": "Paredes",
        "segundo_apellido": "Ochoa",
        "curp": "PAOS120722HDFRNT05",
        "rfc": "PAOS120722K72",
        "nss": "19301284910",
        "sexo": "M",
        "fecha_nacimiento": "2012-07-22",
        "altura_cm": 150.0,
        "peso_kg": 43.0,
        "tipo_sangre": "A+",
        "folio_hospital": "EXP-2026-0117",
        "ubicacion_casa": "Calle Durango 185, Col. Condesa, Cuauhtémoc, CDMX",
        "lugar_nacimiento": "Ciudad de México",
        "nacionalidad": "Mexicana",
        "ocupacion": "Estudiante de Secundaria",
        "telefono_local": "5552119045",
        "celular": "525552119045",
        "email": "familia.paredes.ochoa@gmail.com",
        "contacto_emergencia_nombre": "Claudia Ochoa (Madre)",
        "contacto_emergencia_tel": "5551829034",
        "disease_name": "Dermatitis Atópica Severa / Eccema Flexural",
        "cie10_code": "L20.9",
        "specialty": "Dermatología / Alergología",
        "alergias": [
            {"descripcion": "Látex y gomas naturales", "tipo": "ambiental", "severidad": "moderada"},
            {"descripcion": "Nuez de castilla y frutos secos", "tipo": "alimento", "severidad": "severa"}
        ],
        "antecedentes": [
            {"tipo": "heredofamiliar", "descripcion": "Padre con rinitis alérgica y asma infantil", "fecha": "2014-06-01"}
        ],
        "subjetivo": "Paciente masculino de 14 años acompañado de su madre. Presenta prurito generalizado muy intenso (8/10) que interfiere con el sueño escolar, con placas eritematosas, liquenificación y descamación en pliegues antecubitales y poplíteos.",
        "objetivo": "Eritema confluente y placas liquenificadas con costras hemáticas por rascado en ambos pliegues de codos y huecos poplíteos. SCORAD calculado: 48 puntos (severa).",
        "analisis": "Dermatitis atópica de fenotipo flexural de intensidad severa con sobreinfección superficial mínima por rascado.",
        "plan": "Emolientes con ceramidas 3 veces al día en todo el cuerpo inmediatamente tras baño tibio corto (<5 min). Hidrocortisona al 1% en crema tópica dos veces al día en lesiones activas por 7 días. Cetirizina 10 mg noche.",
        "rx": [
            {"medicamento": "Hidrocortisona crema", "presentacion": "Tubo 30 g al 1%", "dosis": "Capa fina sobre áreas con eritema", "frecuencia": "Cada 12 horas por 7 días", "duracion": "7 días"},
            {"medicamento": "Cetirizina", "presentacion": "Tabletas 10 mg", "dosis": "1 tableta por la noche", "frecuencia": "Cada 24 horas por 14 días", "duracion": "14 días"}
        ],
        "vitals": {"hr": 82, "spo2": 99, "sys": 108, "dia": 68, "temp": 36.6, "steps": 7400, "device": "Fitbit Ace 3"}
    },
    {
        "nombres": "Rosaura",
        "primer_apellido": "Macías",
        "segundo_apellido": "del Toro",
        "curp": "MATR691129MJCLSR08",
        "rfc": "MATR6911293Y1",
        "nss": "28896912048",
        "sexo": "F",
        "fecha_nacimiento": "1969-11-29",
        "altura_cm": 157.0,
        "peso_kg": 79.0,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0118",
        "ubicacion_casa": "Av. Patria 1250, Col. Jardines del Tepeyac, Zapopan, Jalisco",
        "lugar_nacimiento": "Guadalajara, Jalisco",
        "nacionalidad": "Mexicana",
        "ocupacion": "Comerciante Gastronómica",
        "telefono_local": "3336471928",
        "celular": "523336471928",
        "email": "rosaura.macias@saborjalisco.mx",
        "contacto_emergencia_nombre": "Enrique del Toro (Hijo)",
        "contacto_emergencia_tel": "3338192039",
        "disease_name": "Colecistitis Crónica Litiásica con Cólico Biliar",
        "cie10_code": "K80.2",
        "specialty": "Cirugía General / Gastroenterología",
        "alergias": [],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Dislipidemia y sobrepeso grado I desde hace 10 años", "fecha": "2016-09-05"}
        ],
        "subjetivo": "Femenina de 56 años con dolor cólico postprandial tardío en hipocondrio derecho de 4 horas de evolución tras ingesta de comida rica en grasas (carnitas). Dolor irradiado a región interescapular con náusea y diaforesis.",
        "objetivo": "Temp: 37.0 °C, TA: 130/85 mmHg, FC: 80 lpm. Dolor intenso a la palpación profunda en hipocondrio derecho con detención de la inspiración profunda (Signo de Murphy positivo). Sin ictericia en escleras. Ultrasonido hepatobiliar: Litos múltiples de hasta 12 mm en vesícula con pared de 4.2 mm.",
        "analisis": "Colelitiasis sintomática con cuadro de cólico biliar y signos de colecistitis crónica litiásica agudizada. Sin colangitis.",
        "plan": "Manejo antiespasmódico con Butilhioscina más metamizol. Dieta estricta colecistoquinética cero grasas. Programación electiva prioritaria para Colecistectomía Laparoscópica.",
        "rx": [
            {"medicamento": "Butilhioscina / Metamizol", "presentacion": "Comprimidos 10mg / 250mg", "dosis": "1 comprimido", "frecuencia": "Cada 8 horas en caso de dolor cólico", "duracion": "5 días"}
        ],
        "vitals": {"hr": 80, "spo2": 98, "sys": 130, "dia": 85, "temp": 37.0, "steps": 3600, "device": "Omron Healthcare Connect"}
    },
    {
        "nombres": "Emilio",
        "primer_apellido": "Solís",
        "segundo_apellido": "Quintal",
        "curp": "SOQE170310HYNLR06",
        "rfc": "SOQE170310P99",
        "nss": "89351720491",
        "sexo": "M",
        "fecha_nacimiento": "2017-03-10",
        "altura_cm": 128.0,
        "peso_kg": 27.5,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0119",
        "ubicacion_casa": "Calle 41 #520 x 64 y 66, Centro, Mérida, Yucatán",
        "lugar_nacimiento": "Mérida, Yucatán",
        "nacionalidad": "Mexicana",
        "ocupacion": "Estudiante de Primaria",
        "telefono_local": "9999283741",
        "celular": "529999283741",
        "email": "padres.emilio.solis@gmail.com",
        "contacto_emergencia_nombre": "Diana Quintal (Madre)",
        "contacto_emergencia_tel": "9991203948",
        "disease_name": "Otitis Media Aguda Supurativa Derecha",
        "cie10_code": "H66.0",
        "specialty": "Otorrinolaringología / Pediatría",
        "alergias": [],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Resfriado común previo hace 7 días", "fecha": "2026-11-10"}
        ],
        "subjetivo": "Escolar masculino de 9 años acude con su madre por otalgia derecha intensa y punzante de inicio nocturno que le impidió dormir, acompañada de fiebre de 38.5 °C y otorrea sero-purulenta matutina.",
        "objetivo": "Temp: 38.3 °C, FC: 96 lpm. Otoscopía derecha: Membrana timpánica abombada, francamente hiperémica, con pequeña perforación puntual en cuadrante posteroinferior con salida de líquido purulento no fétido. Oído izquierdo íntegro.",
        "analisis": "Otitis media aguda supurada derecha con perforación timpánica aguda secundaria a infección por germen encapsulado habitual de vía aérea.",
        "plan": "Amoxicilina con Ácido Clavulánico suspensión a 90 mg/kg/día por 10 días. Ibuprofeno suspensión para control de fiebre y otalgia. Prohibido mojarse el conducto auditivo externo durante el baño.",
        "rx": [
            {"medicamento": "Amoxicilina / Ácido Clavulánico", "presentacion": "Suspensión 400mg/57mg por 5ml", "dosis": "7.5 ml vía oral", "frecuencia": "Cada 12 horas por 10 días", "duracion": "10 días"},
            {"medicamento": "Ibuprofeno suspensión", "presentacion": "Frasco 100mg / 5ml", "dosis": "10 ml vía oral", "frecuencia": "Cada 8 horas si hay dolor u otalgia", "duracion": "5 días"}
        ],
        "vitals": {"hr": 96, "spo2": 99, "sys": 102, "dia": 64, "temp": 38.3, "steps": 5100, "device": "Smartwatch Infantil"}
    },
    {
        "nombres": "Claudia",
        "primer_apellido": "Navarro",
        "segundo_apellido": "Bermejo",
        "curp": "NABC870811MDFRL09",
        "rfc": "NABC8708119X2",
        "nss": "14078729104",
        "sexo": "F",
        "fecha_nacimiento": "1987-08-11",
        "altura_cm": 166.0,
        "peso_kg": 61.0,
        "tipo_sangre": "A-",
        "folio_hospital": "EXP-2026-0120",
        "ubicacion_casa": "Calle Sonora 140, Hipódromo Condesa, Cuauhtémoc, CDMX",
        "lugar_nacimiento": "Ciudad de México",
        "nacionalidad": "Mexicana",
        "ocupacion": "Abogada Fiscalista",
        "telefono_local": "5552861920",
        "celular": "525552861920",
        "email": "lic.claudia.navarro@despacho.com",
        "contacto_emergencia_nombre": "Rodrigo Bermejo (Hermano)",
        "contacto_emergencia_tel": "5551920491",
        "disease_name": "Lupus Eritematoso Sistémico (LES) con Afectación Articular",
        "cie10_code": "M32.9",
        "specialty": "Reumatología / Inmunología",
        "alergias": [
            {"descripcion": "Sulfametoxazol / Trimetoprima (desencadenante de brote lúpico)", "tipo": "medicamento", "severidad": "severa"}
        ],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Diagnóstico de LES establecido en 2020 con anticuerpos ANA y Anti-DNA positivos", "fecha": "2020-11-18"}
        ],
        "subjetivo": "Femenina de 39 años que acude a valoración reumatológica por eritema malar en alas de mariposa tras exposición solar, poliartralgias en manos y muñecas sin deformidad y fatiga extrema incapacitante.",
        "objetivo": "Eritema malar respetando surcos nasogenianos. Sinovitis leve en carpos bilaterales. Complemento C3: 65 mg/dL (bajo), C4: 8 mg/dL (bajo) indicativos de consumo de complemento. Examen de orina: proteinuria leve 30 mg/dL.",
        "analisis": "Lupus Eritematoso Sistémico con reactivación articular y cutánea moderada (SLEDAI de 8 puntos). Requiere ajuste de terapia inmunomoduladora.",
        "plan": "Hidroxicloroquina 200 mg c/24h fija. Prednisona 15 mg c/24h con reducción gradual. Fotoprotección estricta FPS 50+ cada 3 horas. Cuantificación de proteinuria en orina de 24 horas.",
        "rx": [
            {"medicamento": "Hidroxicloroquina", "presentacion": "Tabletas 200 mg", "dosis": "1 tableta con la cena", "frecuencia": "Cada 24 horas", "duracion": "90 días"},
            {"medicamento": "Prednisona", "presentacion": "Tabletas 5 mg", "dosis": "3 tabletas juntas (15 mg)", "frecuencia": "Cada 24 horas por las mañanas", "duracion": "30 días"}
        ],
        "vitals": {"hr": 78, "spo2": 98, "sys": 114, "dia": 74, "temp": 36.8, "steps": 4200, "device": "Apple Watch Series 7"}
    },
    {
        "nombres": "Javier",
        "primer_apellido": "Miranda",
        "segundo_apellido": "Peña",
        "curp": "MIPJ761005HCLNR03",
        "rfc": "MIPJ7610053K1",
        "nss": "38967610492",
        "sexo": "M",
        "fecha_nacimiento": "1976-10-05",
        "altura_cm": 181.0,
        "peso_kg": 95.0,
        "tipo_sangre": "O+",
        "folio_hospital": "EXP-2026-0121",
        "ubicacion_casa": "Calle Galeana 840, Col. Centro, Saltillo, Coahuila",
        "lugar_nacimiento": "Saltillo, Coahuila",
        "nacionalidad": "Mexicana",
        "ocupacion": "Ingeniero de Manufactura Automotriz",
        "telefono_local": "8444158920",
        "celular": "528444158920",
        "email": "jmiranda.auto@manufactura.mx",
        "contacto_emergencia_nombre": "Silvia Peña (Hermana)",
        "contacto_emergencia_tel": "8441029482",
        "disease_name": "Hernia Discal L4-L5 con Radiculopatía Lumbar / Ciática",
        "cie10_code": "M51.1",
        "specialty": "Ortopedia / Traumatología",
        "alergias": [],
        "antecedentes": [
            {"tipo": "patologico", "descripcion": "Lumbalgia mecánica recurrente tras levantamiento de carga pesada", "fecha": "2023-05-14"}
        ],
        "subjetivo": "Masculino de 50 años que acude por dolor lumbosacro agudizado que se irradia por la cara posterolateral del muslo y pierna izquierda hasta el dorso del pie, con parestesias y sensación de corriente eléctrica.",
        "objetivo": "TA: 130/80 mmHg, FC: 74 lpm. Maniobra de Lasègue positiva izquierda a 35 grados. Maniobra de Bragard (+). Hipoestesia en dermatoma L5 izquierdo. Reflejo rotuliano y aquíleo simétricos.",
        "analisis": "Compresión radicular L5 izquierda compatible con hernia discal foraminal o posterolateral L4-L5. Dolor neuropático y radiculopatía activa.",
        "plan": "Resonancia magnética lumbar simple de control. Reposo relativo, evitar cargar peso. Manejo farmacológico con Pregabalina 75 mg c/24h nocturna y Meloxicam 15 mg c/24h por 7 días. Fisioterapia.",
        "rx": [
            {"medicamento": "Pregabalina", "presentacion": "Cápsulas 75 mg", "dosis": "1 cápsula nocturna", "frecuencia": "Cada 24 horas por 30 días", "duracion": "30 días"},
            {"medicamento": "Meloxicam", "presentacion": "Tabletas 15 mg", "dosis": "1 tableta con alimentos", "frecuencia": "Cada 24 horas por 7 días", "duracion": "7 días"}
        ],
        "vitals": {"hr": 74, "spo2": 98, "sys": 130, "dia": 80, "temp": 36.5, "steps": 2600, "device": "Garmin Instinct 2"}
    },
    {
        "nombres": "Teresa",
        "primer_apellido": "Alvarado",
        "segundo_apellido": "Villaseñor",
        "curp": "AAVT560918MDFLNN02",
        "rfc": "AAVT5609185J7",
        "nss": "09765610294",
        "sexo": "F",
        "fecha_nacimiento": "1956-09-18",
        "altura_cm": 156.0,
        "peso_kg": 64.0,
        "tipo_sangre": "A+",
        "folio_hospital": "EXP-2026-0122",
        "ubicacion_casa": "Calle Montes Urales 510, Lomas de Chapultepec, Miguel Hidalgo, CDMX",
        "lugar_nacimiento": "Ciudad de México",
        "nacionalidad": "Mexicana",
        "ocupacion": "Traductora Literaria Jubilada",
        "telefono_local": "5555209384",
        "celular": "525555209384",
        "email": "teresa.alvarado.v@letras.com",
        "contacto_emergencia_nombre": "Enrique Alvarado (Hijo)",
        "contacto_emergencia_tel": "5559120491",
        "disease_name": "Glaucoma Primario de Ángulo Abierto Bilateral",
        "cie10_code": "H40.1",
        "specialty": "Oftalmología",
        "alergias": [
            {"descripcion": "Ciprofloxacino en colirio (blefaritis alérgica)", "tipo": "medicamento", "severidad": "moderada"}
        ],
        "antecedentes": [
            {"tipo": "heredofamiliar", "descripcion": "Madre ciega por glaucoma no diagnosticado a tiempo", "fecha": "2008-04-12"}
        ],
        "subjetivo": "Femenina de 70 años en revisión oftalmológica rutinaria. Asintomática desde el punto de vista del dolor; nota leve dificultad para ver objetos periféricos al conducir o bajar escalones.",
        "objetivo": "Tonometría de aplanación de Goldmann: Presión intraocular (PIO) ojo derecho 24 mmHg, ojo izquierdo 26 mmHg (límite normal < 21 mmHg). Gonioscopía: ángulo abierto Shaffer grado IV en 360°. Fondo de ojo: Excavación papilar 0.7 en OD y 0.8 en OI.",
        "analisis": "Glaucoma primario de ángulo abierto con daño estructural moderado en la cabeza del nervio óptico bilateralmente.",
        "plan": "Iniciar análogo de prostaglandinas Latanoprost al 0.005% colirio 1 gota en ambos ojos por las noches. Campimetría visual computarizada Humphrey 24-2 y tomografía de coherencia óptica (OCT) de fibras nerviosas en 1 mes.",
        "rx": [
            {"medicamento": "Latanoprost solución oftálmica", "presentacion": "Frasco gotero 2.5 ml al 0.005%", "dosis": "1 gota en cada ojo", "frecuencia": "Cada 24 horas por las noches", "duracion": "60 días"}
        ],
        "vitals": {"hr": 68, "spo2": 97, "sys": 124, "dia": 78, "temp": 36.4, "steps": 4100, "device": "Omron Upper Arm 5"}
    }
]

def seed():
    print(f"=== INICIANDO SIEMBRA DE {len(PATIENTS_DATA)} PACIENTES CLÍNICOS DIVERSOS ===")
    
    db = SessionLocal()
    embedder = _get_embedder()
    chroma_col = get_collection("patients_semantic")

    created_count = 0
    updated_count = 0

    for idx, pdata in enumerate(PATIENTS_DATA, start=1):
        curp = pdata["curp"]
        existing = db.query(Patient).filter(Patient.curp == curp).first()

        full_name = f"{pdata['nombres']} {pdata['primer_apellido']} {pdata['segundo_apellido']}"
        print(f"\n[{idx}/{len(PATIENTS_DATA)}] Procesando: {full_name} ({curp})")
        print(f"    Diagnóstico principal: {pdata['disease_name']} [{pdata['cie10_code']}] ({pdata['specialty']})")

        if existing:
            print(f"    -> Paciente ya existe en base de datos. Actualizando...")
            patient_obj = existing
            updated_count += 1
        else:
            patient_dict = {
                "curp": curp,
                "nombres": pdata["nombres"],
                "primer_apellido": pdata["primer_apellido"],
                "segundo_apellido": pdata["segundo_apellido"],
                "fecha_nacimiento": pdata["fecha_nacimiento"],
                "sexo": pdata["sexo"],
                "altura_cm": pdata["altura_cm"],
                "peso_kg": pdata["peso_kg"],
                "tipo_sangre": pdata["tipo_sangre"],
                "folio_hospital": pdata["folio_hospital"],
                "ubicacion_casa": pdata["ubicacion_casa"],
                "lugar_nacimiento": pdata["lugar_nacimiento"],
                "nacionalidad": pdata["nacionalidad"],
                "ocupacion": pdata["ocupacion"],
                "rfc": pdata["rfc"],
                "nss": pdata["nss"],
                "telefono_local": pdata["telefono_local"],
                "celular": pdata["celular"],
                "email": pdata["email"],
                "contacto_emergencia_nombre": pdata["contacto_emergencia_nombre"],
                "contacto_emergencia_tel": pdata["contacto_emergencia_tel"],
                "anotaciones_generales": f"Diagnóstico clínico principal: {pdata['disease_name']} ({pdata['cie10_code']}) - Especialidad: {pdata['specialty']}.",
                "clues_institucion": "YUC-CR-001"
            }
            register_patient(patient_dict)
            patient_obj = db.query(Patient).filter(Patient.curp == curp).first()
            created_count += 1
            print(f"    -> Paciente registrado con éxito.")

        # Alergias
        existing_alergias = db.query(Alergia).filter(Alergia.patient_curp == curp).count()
        if existing_alergias == 0:
            for al in pdata.get("alergias", []):
                add_alergia(curp, al)
            print(f"    -> {len(pdata.get('alergias', []))} alergias registradas.")

        # Antecedentes
        existing_ants = db.query(Antecedente).filter(Antecedente.patient_curp == curp).count()
        if existing_ants == 0:
            for ant in pdata.get("antecedentes", []):
                add_antecedente(curp, ant)
            print(f"    -> {len(pdata.get('antecedentes', []))} antecedentes clínicos registrados.")

        # Evento Clínico
        evento = db.query(EventoClinico).filter(EventoClinico.patient_curp == curp).first()
        if not evento:
            evento_dict = {
                "patient_curp": curp,
                "nombre_evento": f"Atención Especializada - {pdata['specialty']}",
                "doctor_creador": "Dra. Sofía Mendoza Ramos",
                "resumen": f"Control y seguimiento integral de {pdata['disease_name']} (CIE-10 {pdata['cie10_code']})."
            }
            evento = db.query(EventoClinico).filter(
                EventoClinico.id == create_evento_clinico(evento_dict)["id"]
            ).first()
            print(f"    -> Evento clínico creado: {evento.nombre_evento}")

        # Consulta NOM-004
        consulta = db.query(Consulta).filter(Consulta.patient_curp == curp).first()
        if not consulta and evento:
            now_dt = datetime.utcnow() - timedelta(days=random.randint(1, 14), hours=random.randint(1, 8))
            nota_json = {
                "subjetivo": pdata["subjetivo"],
                "objetivo": pdata["objetivo"],
                "analisis": pdata["analisis"],
                "plan": pdata["plan"],
                "diagnostico_principal": {
                    "codigo": pdata["cie10_code"],
                    "descripcion": pdata["disease_name"]
                }
            }
            receta_json = {
                "medicamentos": pdata["rx"],
                "indicaciones_generales": "Mantener hábitos higiénico-dietéticos prescritos y acudir a valoración inmediata en caso de datos de alarma."
            }
            entidades_json = {
                "cie10": [{"codigo": pdata["cie10_code"], "descripcion": pdata["disease_name"]}],
                "medicamentos": [r["medicamento"] for r in pdata["rx"]]
            }
            consulta_dict = {
                "evento_id": evento.id,
                "patient_curp": curp,
                "doctor_nombre": "Dra. Sofía Mendoza Ramos",
                "cedula_profesional": "12489620",
                "fecha_hora": now_dt.isoformat(),
                "resumen_doctor": f"Consulta de {pdata['specialty']} por {pdata['disease_name']}. Plan terapéutico establecido.",
                "nota_medica_json": nota_json,
                "receta_json": receta_json,
                "entidades_json": entidades_json,
                "texto_original": f"S: {pdata['subjetivo']}\nO: {pdata['objetivo']}\nA: {pdata['analisis']}\nP: {pdata['plan']}"
            }
            create_consulta(consulta_dict)
            print(f"    -> Consulta NOM-004 y receta médica generadas.")

        # Telemetría Wearable (VitalReading)
        vt = pdata.get("vitals", {})
        if vt:
            reading = VitalReading(
                id=str(uuid.uuid4()),
                patient_curp=curp,
                patient_name=full_name,
                device_name=vt.get("device", "Smart Health Monitor"),
                source="Wearable Bluetooth HealthKit",
                heart_rate=vt.get("hr", 75),
                spo2=vt.get("spo2", 98),
                systolic_bp=vt.get("sys", 120),
                diastolic_bp=vt.get("dia", 80),
                temperature=vt.get("temp", 36.5),
                steps=vt.get("steps", 5000),
                alert_flag=(vt.get("sys", 120) > 140 or vt.get("spo2", 98) < 92 or vt.get("temp", 36.5) > 38.0),
                alert_message=(f"Alerta: parámetro fuera de rango fisiológico ({pdata['disease_name']})" if (vt.get("sys", 120) > 140 or vt.get("spo2", 98) < 92 or vt.get("temp", 36.5) > 38.0) else None),
                recorded_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 120))
            )
            db.add(reading)
            db.commit()
            print(f"    -> Telemetría vital sincronizada: {vt.get('hr')} lpm, SpO2 {vt.get('spo2')}%, {vt.get('sys')}/{vt.get('dia')} mmHg.")

        # Cita Agendada (Appointment)
        existing_appt = db.query(Appointment).filter(Appointment.patient_curp == curp).first()
        if not existing_appt:
            appt_date = (datetime.now() + timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d")
            appt = Appointment(
                id=str(uuid.uuid4()),
                patient_curp=curp,
                patient_name=full_name,
                date_str=appt_date,
                time_str=f"{random.randint(9, 17):02d}:00",
                reason=f"Control clínico de {pdata['disease_name']}",
                status="Programada",
                triage_level="AMARILLO" if (vt.get("sys", 120) > 140 or vt.get("spo2", 98) < 92) else "VERDE",
                wearable=True if vt.get("device") else False,
                wearable_text=f"{vt.get('device')} (FC: {vt.get('hr')} lpm, SpO2: {vt.get('spo2')}%)",
                doctor_nombre="Dra. Sofía Mendoza Ramos",
                clues_institucion="YUC-CR-001"
            )
            db.add(appt)
            db.commit()
            print(f"    -> Cita médica programada para {appt_date}.")

        # Indexación Semántica en ChromaDB
        doc_text = (
            f"Paciente: {full_name}. "
            f"CURP: {curp}. "
            f"Enfermedad y Diagnóstico: {pdata['disease_name']} ({pdata['cie10_code']}). "
            f"Especialidad médica: {pdata['specialty']}. "
            f"Ocupación: {pdata['ocupacion']}. "
            f"Ubicación: {pdata['ubicacion_casa']}. "
            f"Alergias: {', '.join(a['descripcion'] for a in pdata.get('alergias', []))}. "
            f"Tratamiento farmacológico: {', '.join(r['medicamento'] for r in pdata['rx'])}."
        )
        try:
            emb = embedder.encode([doc_text]).tolist()
            chroma_col.upsert(
                ids=[curp],
                embeddings=emb,
                documents=[doc_text],
                metadatas=[{
                    "patient_curp": curp,
                    "nombre_paciente": full_name,
                    "diagnostico": pdata["disease_name"],
                    "cie10": pdata["cie10_code"],
                    "especialidad": pdata["specialty"]
                }]
            )
            print(f"    -> Indizado semántico en ChromaDB OK.")
        except Exception as e:
            print(f"    [Advertencia Chroma]: {e}")

    total_patients = len(get_all_patients())
    print("\n==================================================")
    print(f" SIEMBRA FINALIZADA CON ÉXITO")
    print(f" Total de Pacientes Registrados en el Sistema: {total_patients}")
    print(f" Pacientes Nuevos Creados: {created_count}")
    print(f"==================================================")
    db.close()

if __name__ == "__main__":
    seed()
