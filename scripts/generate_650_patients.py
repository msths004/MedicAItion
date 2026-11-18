"""
generate_650_patients.py — Generador Masivo de más de 600 Pacientes Clínicos
============================================================================
Genera más de 650 pacientes realistas con diversas patologías, especialidades
médicas y asignados a los 7 hospitales de la Red Interhospitalaria de Yucatán.
Pobla tanto la base local (local_db) como el registro federado (global_db).
"""

import os
import sys
import uuid
import random
from datetime import datetime, timedelta

# Asegurar path de la app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from app.db.local_db import (
    SessionLocal as LocalSession, Patient, Alergia, Antecedente,
    EventoClinico, Consulta, create_tables as create_local_tables
)
from app.db.global_db import (
    SessionLocal as GlobalSession, PatientIndex, Institution,
    InterHospitalReferral, create_tables as create_global_tables
)

# ── Catálogos Demográficos ──────────────────────────────────────────
NOMBRES_HOMBRES = [
    "Alejandro", "Bernardo", "Carlos", "Daniel", "Emilio", "Fernando", "Gabriel",
    "Héctor", "Ignacio", "Javier", "Kevin", "Luis", "Manuel", "Nicolás", "Óscar",
    "Pablo", "Rodrigo", "Santiago", "Tomás", "Víctor", "Álvaro", "Benjamín",
    "César", "Diego", "Eduardo", "Fabián", "Gerardo", "Hugo", "Ismael", "Jorge",
    "Leonardo", "Mauricio", "Néstor", "Patricio", "Rafael", "Salvador", "Ulises",
    "Vicente", "Arturo", "Mateo", "Adrián", "Bruno", "Cristian", "Damián",
    "Esteban", "Gonzalo", "Iván", "Joaquín", "Lorenzo", "Mario", "Raúl", "Rubén"
]

NOMBRES_MUJERES = [
    "Adriana", "Beatriz", "Camila", "Diana", "Elena", "Fabiola", "Gabriela",
    "Helena", "Irene", "Julia", "Karla", "Lucía", "Mariana", "Natalia", "Olga",
    "Paola", "Rosaura", "Sofía", "Teresa", "Valeria", "Alicia", "Brenda",
    "Claudia", "Daniela", "Estefanía", "Fernanda", "Giselle", "Ingrid", "Jimena",
    "Lorena", "Marisol", "Nadia", "Patricia", "Rebeca", "Silvia", "Tania",
    "Verónica", "Yolanda", "Ana", "Mónica", "Andrea", "Carolina", "Cecilia",
    "Esperanza", "Guadalupe", "Leticia", "Miriam", "Paloma", "Rocío", "Susana", "Victoria"
]

APELLIDOS = [
    # Yucatecos / Mayas
    "Pech", "Canche", "Dzul", "Chan", "May", "Canto", "Quintal", "Balam", "Tuz",
    "Dzib", "Puc", "Ek", "Couoh", "Chuc", "Tun", "Yah", "Uc", "Pool", "Hau", "Cocom",
    # Mexicanos / Españoles
    "Morales", "González", "Vázquez", "Mendoza", "Alvarado", "Miranda", "Navarro",
    "Solís", "Macías", "Paredes", "Treviño", "Vega", "Ibarra", "Soto", "Guerrero",
    "Salgado", "Orozco", "Pantoja", "Fuentes", "Hernández", "López", "Ríos", "Castillo",
    "Bautista", "Ramírez", "Cruz", "Gómez", "Flores", "Díaz", "Reyes", "Gutiérrez",
    "Ortiz", "Chávez", "Torres", "Romero", "Álvarez", "Ruiz", "Vargas", "Jiménez",
    "Castro", "Silva", "Medina", "Rojas", "Delgado", "Aguilar", "Peña", "Molina"
]

ESTADOS_CURP = ["YN", "QR", "CM", "TB", "VZ", "DF", "JC", "NL", "PL", "GT"]

HOSPITALES_RED = [
    {"clues": "YUC-CR-001", "nombre": "Cruz Roja Mexicana Delegación Mérida", "nivel": "Nivel 1 / Urgencias & Trauma"},
    {"clues": "YCSSA000024", "nombre": "Hospital General Dr. Agustín O'Horán", "nivel": "Tercer Nivel / Alta Complejidad"},
    {"clues": "IMS0001092", "nombre": "HGR N° 1 T-1 Lic. Ignacio García Téllez", "nivel": "Segundo Nivel / Especialidades"},
    {"clues": "YCSSA000671", "nombre": "Hospital Materno-Infantil de Mérida", "nivel": "Segundo Nivel / Gineco-Pediatría"},
    {"clues": "YCSSA001890", "nombre": "Centro de Salud Urbano Kanasín", "nivel": "Primer Nivel / Medicina Familiar"},
    {"clues": "ISS0003412", "nombre": "Hospital Regional Mérida ISSSTE", "nivel": "Tercer Nivel / Quirúrgico"},
    {"clues": "YUC-HRA-003", "nombre": "Hospital Regional de Alta Especialidad (HRAEPY)", "nivel": "Alta Especialidad e Investigación"}
]

# ── Catálogo de Patologías & Especialidades Clínicas ───────────────
PATOLOGIAS = [
    # 1. Endocrinología & Metabólico
    {
        "enfermedad": "Diabetes Mellitus Tipo 2 no insulinodependiente",
        "cie10": "E11.9",
        "especialidad": "Endocrinología",
        "alergia_prob": "Sulfamidas",
        "medicacion": "Metformina 850mg c/12h, Empagliflozina 10mg c/24h",
        "motivo": "Control glucémico periódico y ajuste de hipoglucemiantes orales.",
        "subjetivo": "Paciente refiere polidipsia moderada y nicturia de 2 ocasiones por noche. Sin síntomas de hipoglucemia.",
        "objetivo": "Glucosa capilar 142 mg/dL. TA 128/80 mmHg, FC 74 lpm. Fondo de ojo sin retinopatía proliferativa.",
        "analisis": "Diabetes Mellitus Tipo 2 con control metabólico subóptimo.",
        "plan": "Mantener metformina e insistir en plan nutricional con restricción de azúcares simples.",
        "tipo_exp": "Consulta Externa / Control Metabólico"
    },
    {
        "enfermedad": "Diabetes Mellitus Tipo 1 con cetosis leve",
        "cie10": "E10.1",
        "especialidad": "Endocrinología",
        "alergia_prob": "Sin alergias documentadas",
        "medicacion": "Insulina Glargina 18 UI nocturna, Insulina Lispro preprandial",
        "motivo": "Ajuste de esquema basal-bolo por hiperglucemias matutinas.",
        "subjetivo": "Paciente refiere cifras matutinas entre 180 y 220 mg/dL a pesar de respetar dosis.",
        "objetivo": "Glucosa 198 mg/dL, cetonas en orina trazas (+), TA 118/74 mmHg, FC 80 lpm.",
        "analisis": "Fenómeno del alba versus sobrebasalización en DM1.",
        "plan": "Ajustar insulina glargina a 20 UI y monitorizar glucemias a las 03:00 am.",
        "tipo_exp": "Consulta Especializada"
    },
    {
        "enfermedad": "Hipotiroidismo Primario no especificado",
        "cie10": "E03.9",
        "especialidad": "Endocrinología",
        "alergia_prob": "Yodo / Medios de contraste",
        "medicacion": "Levotiroxina sódica 75 mcg en ayunas",
        "motivo": "Revisión semestral de perfil tiroideo y ajuste de dosis.",
        "subjetivo": "Refiere astenia leve matutina y piel seca en extremidades. Niega intolerancia marcada al frío.",
        "objetivo": "TSH: 4.8 mUI/L, T4 libre: 1.1 ng/dL. TA 120/75 mmHg, FC 66 lpm. Sin bocio palpable.",
        "analisis": "Hipotiroidismo primario en rango limítrofe superior.",
        "plan": "Aumentar levotiroxina a 88 mcg diarios de lunes a viernes y 75 mcg fines de semana.",
        "tipo_exp": "Consulta Externa"
    },
    {
        "enfermedad": "Síndrome Metabólico y Dislipidemia Mixta",
        "cie10": "E88.8 / E78.2",
        "especialidad": "Medicina Interna",
        "alergia_prob": "Atorvastatina (Mialgias)",
        "medicacion": "Rosuvastatina 10mg c/24h, Ezetimiba 10mg",
        "motivo": "Chequeo preventivo por hipertrigliceridemia y perímetro abdominal aumentado.",
        "subjetivo": "Asintomático. Refiere sedentarismo laboral prolongado.",
        "objetivo": "IMC 31.4 kg/m2, Perímetro abdominal 102 cm. Triglicéridos 240 mg/dL, HDL 36 mg/dL. TA 130/85 mmHg.",
        "analisis": "Síndrome metabólico de riesgo cardiovascular intermedio.",
        "plan": "Prescripción de ejercicio aeróbico 150 min/semana y dieta mediterránea modificada.",
        "tipo_exp": "Medicina Preventiva"
    },

    # 2. Cardiología & Vascular
    {
        "enfermedad": "Hipertensión Arterial Primaria (Esencial)",
        "cie10": "I10",
        "especialidad": "Cardiología",
        "alergia_prob": "Captopril / Enalapril (Tos refractaria)",
        "medicacion": "Losartán 50mg c/12h, Amlodipino 5mg c/24h",
        "motivo": "Monitoreo tensional y seguimiento de cifras ambulatorias.",
        "subjetivo": "Refiere cefalea occipital ocasional al despertar que cede espontáneamente.",
        "objetivo": "TA promedio en consulta: 138/84 mmHg. FC: 72 lpm rítmico. Ruidos cardíacos sin soplos.",
        "analisis": "Hipertensión arterial esencial Estadio 1 controlada.",
        "plan": "Mantener terapia dual. Reducción estricta de sodio en dieta (&lt; 2 g/día).",
        "tipo_exp": "Consulta de Cardiología"
    },
    {
        "enfermedad": "Insuficiencia Cardíaca Congestiva con Fracción de Eyección Reducida",
        "cie10": "I50.9",
        "especialidad": "Cardiología",
        "alergia_prob": "Espironolactona",
        "medicacion": "Sacubitrilo/Valsartán 49/51mg c/12h, Empagliflozina 10mg, Furosemida 40mg",
        "motivo": "Evaluación de clase funcional y edemas en miembros inferiores.",
        "subjetivo": "Disnea de medianos esfuerzos (NYHA II), ortopnea con 2 almohadas.",
        "objetivo": "Edema bimaleolar (+) con fóvea. Ingurgitación yugular Grado I. Estertores basales leves.",
        "analisis": "Falla cardíaca crónica compensada en cuádruple terapia.",
        "plan": "Continuar cuádruple pilar y ajuste de diurético de asa según balance hídrico matutino.",
        "tipo_exp": "Cardiología Avanzada"
    },
    {
        "enfermedad": "Fibrilación Auricular Paroxística",
        "cie10": "I48.0",
        "especialidad": "Cardiología",
        "alergia_prob": "Amiodarona",
        "medicacion": "Apixabán 5mg c/12h, Metoprolol succinato 50mg c/24h",
        "motivo": "Revisión de ritmo y seguridad del anticoagulante oral directo (DOAC).",
        "subjetivo": "Refiere palpitaciones rápidas autolimitadas de 10 minutos de duración hace 3 días.",
        "objetivo": "ECG en consulta: Ritmo sinusal regular 68 lpm, sin arritmia activa al momento de la toma.",
        "analisis": "Fibrilación auricular paroxística CHA2DS2-VASc 3, anticoagulada adecuadamente.",
        "plan": "Mantener apixabán y betabloqueador. Cita para Holter 24 horas.",
        "tipo_exp": "Urgencias / Electrofisiología"
    },

    # 3. Infectología & Medicina Tropical
    {
        "enfermedad": "Fiebre del Dengue con Signos de Alarma",
        "cie10": "A97.1",
        "especialidad": "Infectología",
        "alergia_prob": "Ácido Acetilsalicílico / AINEs (Contraindicación absoluta)",
        "medicacion": "Paracetamol 1g c/8h IV, Solución Hartmann a requerimiento",
        "motivo": "Ingreso a sala de observación por trombocitopenia y dolor abdominal intenso.",
        "subjetivo": "Fiebre de 39°C de 4 días de evolución, mialgias intensas, dolor retroocular y vómitos.",
        "objetivo": "Plaquetas: 62,000 /µL, Hematocrito: 44.8%. Petequias en extremidades inferiores. Sin sangrado activo.",
        "analisis": "Dengue con signos de alarma (extravasación plasmática incipiente).",
        "plan": "Hidratación endovenosa guiada por hematocrito cada 6 horas. NO administrar AINEs.",
        "tipo_exp": "Urgencias / Triage Rojo"
    },
    {
        "enfermedad": "Dengue Clásico no grave",
        "cie10": "A97.0",
        "especialidad": "Medicina Familiar",
        "alergia_prob": "Metamizol sódico",
        "medicacion": "Paracetamol 500mg c/6h, Vida Suero Oral",
        "motivo": "Cuadro febril agudo con artralgias incapacitantes.",
        "subjetivo": "Fiebre súbita, cefalea frontal y exantema pruriginoso.",
        "objetivo": "Temp: 38.2 °C, FC: 86 lpm. Plaquetas: 165,000 /µL, Hematocrito: 39%. Torniquete negativo.",
        "analisis": "Dengue sin datos de alarma. Manejo ambulatorio estricto.",
        "plan": "Vigilancia de signos de alarma (dolor abdominal, vómito persistente, sangrado de mucosas).",
        "tipo_exp": "Consulta Ambulatoria"
    },
    {
        "enfermedad": "Neumonía Adquirida en la Comunidad (CURB-65 1)",
        "cie10": "J18.9",
        "especialidad": "Neumología",
        "alergia_prob": "Penicilina (Anafilaxia)",
        "medicacion": "Levofloxacino 750mg c/24h VO por 7 días",
        "motivo": "Tos productiva con expectoración mucopurulenta y fiebre de 5 días.",
        "subjetivo": "Dolor torácico tipo pleurítico en hemitórax derecho y disnea leve.",
        "objetivo": "Temp: 38.5 °C, SpO2: 94% al aire ambiente. Estertores crepitantes en base pulmonar derecha.",
        "analisis": "Neumonía bacteriana comunitaria de bajo riesgo para manejo ambulatorio.",
        "plan": "Antibioticoterapia con quinolona respiratoria por alergia severa a betalactámicos.",
        "tipo_exp": "Urgencias / Consulta Externa"
    },
    {
        "enfermedad": "Faringoamigdalitis Aguda Estreptocócica",
        "cie10": "J02.0",
        "especialidad": "Medicina General",
        "alergia_prob": "Eritromicina",
        "medicacion": "Amoxicilina con Ácido Clavulánico 875/125mg c/12h por 10 días",
        "motivo": "Odinofagia intensa y fiebre de 48 horas de evolución.",
        "subjetivo": "Dificultad para deglutir sólidos. Niega rinorrea o tos.",
        "objetivo": "Amígdalas hiperémicas e hipertróficas Grado III con placas exudativas blanquecinas. Adenopatías cervicales dolorosas.",
        "analisis": "Faringoamigdalitis bacteriana confirmada por criterios de Centor (4/4).",
        "plan": "Ciclo completo de antibiótico oral, paracetamol e hidratación constante.",
        "tipo_exp": "Consulta General"
    },

    # 4. Neumología
    {
        "enfermedad": "Asma Bronquial Alérgica no controlada",
        "cie10": "J45.0",
        "especialidad": "Neumología",
        "alergia_prob": "Polvo / Ácaros / Humedad",
        "medicacion": "Budesonida/Formoterol 160/4.5 mcg 2 inhalaciones c/12h, Salbutamol rescate",
        "motivo": "Sibilancias nocturnas frecuentes y opresión torácica.",
        "subjetivo": "Refiere despertar 3 veces por semana con tos seca y silbidos de pecho tras cambios de clima.",
        "objetivo": "Espirometría previa: FEV1 68% con reversibilidad del 14% post-broncodilatador. Sibilancias espiratorias bilaterales.",
        "analisis": "Asma persistente moderada en descontrol por exposición ambiental.",
        "plan": "Escalamiento terapéutico con esteroide inhalado a dosis medias y técnica inhalatoria correcta.",
        "tipo_exp": "Consulta Especializada"
    },
    {
        "enfermedad": "Enfermedad Pulmonar Obstructiva Crónica (EPOC) GOLD 2",
        "cie10": "J44.1",
        "especialidad": "Neumología",
        "alergia_prob": "Sin alergias documentadas",
        "medicacion": "Tiotropio 18 mcg c/24h, Salmeterol/Fluticasona c/12h",
        "motivo": "Tos crónica matutina con esputo blanquecino y disnea de esfuerzo.",
        "subjetivo": "Ex-fumador de 30 paquetes/año. Disnea al subir un piso de escaleras.",
        "objetivo": "Tórax en tonel, murmullo vesicular disminuido generalizado. SpO2 93% aire ambiente.",
        "analisis": "EPOC fenotipo no agudizador en terapia broncodilatadora dual.",
        "plan": "Rehabilitación pulmonar domiciliaria y vacunación anual contra influenza y neumococo.",
        "tipo_exp": "Consulta Externa"
    },

    # 5. Traumatología & Urgencias
    {
        "enfermedad": "Traumatismo Craneoencefálico Leve / Conmoción Cerebral",
        "cie10": "S06.0",
        "especialidad": "Traumatología",
        "alergia_prob": "Ketorolaco / AINEs",
        "medicacion": "Paracetamol 1g c/8h IV, Solución Salina 0.9%",
        "motivo": "Colisión vehicular en motocicleta con pérdida transitoria de alerta.",
        "subjetivo": "Cefalea holocraneal, náusea leve y amnesia del evento.",
        "objetivo": "Glasgow 14/15 (desorientación temporal leve). Pupilas isocóricas reactivas. Sin déficit motor focal.",
        "analisis": "TCE leve con indicación de observación neurológica estrecha.",
        "plan": "TAC de cráneo simple de urgencia y vigilancia de signos de deterioro neurológico.",
        "tipo_exp": "Urgencias / Trauma"
    },
    {
        "enfermedad": "Fractura cerrada de diáfisis de tibia y peroné",
        "cie10": "S82.2",
        "especialidad": "Traumatología",
        "alergia_prob": "Tramadol (Náusea severa)",
        "medicacion": "Buprenorfina parche 10mcg, Cefazolina profiláctica IV",
        "motivo": "Caída de propia altura con dolor e incapacidad funcional en pierna derecha.",
        "subjetivo": "Dolor de intensidad 9/10, edema severo y deformidad visible.",
        "objetivo": "Pulsos pedios y tibial posterior palpables. Sensibilidad distal conservada. Sin exposición ósea.",
        "analisis": "Fractura diafisaria de tibia derecha desplazada candidata a osteosíntesis con clavo centromedular.",
        "plan": "Inmovilización con férula muslopedio, analgesia y programación quirúrgica.",
        "tipo_exp": "Traumatología Quirúrgica"
    },
    {
        "enfermedad": "Esguince de Tobillo Grado II (Ligamento peroneoastragalino anterior)",
        "cie10": "S93.4",
        "especialidad": "Traumatología",
        "alergia_prob": "Diclofenaco",
        "medicacion": "Celecoxib 200mg c/24h por 5 días, Paracetamol 500mg",
        "motivo": "Inversión forzada de tobillo durante práctica deportiva.",
        "subjetivo": "Sensación de chasquido seguido de edema inmediato y dolor a la marcha.",
        "objetivo": "Edema bimaleolar moderado, equimosis perimaleolar externa, dolor exquisito a la palpación.",
        "analisis": "Esguince de tobillo Grado II sin fractura en radiografías bajo criterios de Ottawa.",
        "plan": "Vendaje funcional de soporte, crioterapia local 15 min c/4h y elevación de extremidad.",
        "tipo_exp": "Urgencias / Ortopedia"
    },

    # 6. Nefrología & Urología
    {
        "enfermedad": "Enfermedad Renal Crónica Estadio 3b (TFG 38 mL/min/1.73m2)",
        "cie10": "N18.3",
        "especialidad": "Nefrología",
        "alergia_prob": "Medios de contraste yodados",
        "medicacion": "Furosemida 20mg matutina, Bicarbonato sódico 1g c/12h, Eritropoyetina mensual",
        "motivo": "Monitoreo de función renal y control de proteinuria.",
        "subjetivo": "Nicturia x1, sin astenia marcada ni calambres en extremidades.",
        "objetivo": "Creatinina 1.9 mg/dL, Urea 68 mg/dL, K+ 4.6 mEq/L. TA 124/76 mmHg. Sin edemas periféricos.",
        "analisis": "ERC secundaria a nefropatía diabética e hipertensiva estable.",
        "plan": "Ajuste estricto de fármacos de excreción renal y dieta baja en fósforo y potasio.",
        "tipo_exp": "Consulta Especializada"
    },
    {
        "enfermedad": "Litiasis Renal con Cólico Nefrítico Agudo",
        "cie10": "N20.0",
        "especialidad": "Urología",
        "alergia_prob": "Metamizol",
        "medicacion": "Ketorolaco 30mg IV dosis única, Tamsulosina 0.4mg c/24h por 14 días",
        "motivo": "Dolor lumbar unilateral de inicio súbito tipo cólico que irradia a fosa ilíaca y genitales.",
        "subjetivo": "Dolor 10/10 acompañado de náusea y disuria con hematuria macroscópica.",
        "objetivo": "Giordano positivo derecho. Abdomen blando depresible sin rebote. EGO con abundantes eritrocitos.",
        "analisis": "Cólico renoureteral derecho probablemente por cálculo de tercio distal.",
        "plan": "Terapia expulsiva médica con alfa-bloqueador e hidratación abundante.",
        "tipo_exp": "Urgencias"
    },

    # 7. Gastroenterología
    {
        "enfermedad": "Enfermedad por Reflujo Gastroesofágico (ERGE) Grado B",
        "cie10": "K21.9",
        "especialidad": "Gastroenterología",
        "alergia_prob": "Omeprazol (Cefalea intensa)",
        "medicacion": "Esomeprazol 40mg 30 min antes del desayuno, Magaldrato/Dimeticona PRN",
        "motivo": "Pirosis retroesternal diaria y regurgitación ácida nocturna.",
        "subjetivo": "Sensación de ardor detrás del esternón empeorada al inclinarse o tras comidas grasas.",
        "objetivo": "Abdomen plano, blando, dolor leve en epigastrio a la palpación profunda, sin visceromegalias.",
        "analisis": "ERGE con respuesta parcial a IBP de primera generación.",
        "plan": "Cambio a esomeprazol y medidas higiénico-dietéticas (no acostarse antes de 2 horas postprandiales).",
        "tipo_exp": "Consulta Externa"
    },
    {
        "enfermedad": "Colecistitis Crónica Litiásica agudizada",
        "cie10": "K80.2",
        "especialidad": "Cirugía General",
        "alergia_prob": "Ciprofloxacino",
        "medicacion": "Butilhioscina/Metamizol IV, Ceftriaxona 1g c/24h IV",
        "motivo": "Dolor tipo cólico en hipocondrio derecho de 8 horas de evolución tras ingesta de alimentos colecistoquinéticos.",
        "subjetivo": "Dolor en barra en hemiabdomen superior con náuseas y vómito de contenido biliar.",
        "objetivo": "Signo de Murphy positivo. Ictericia ausente. Ultrasonido: Litiasis vesicular múltiple con pared de 4 mm.",
        "analisis": "Colecistitis litiásica aguda Tokyo Grado I. Candidata a colecistectomía laparoscópica.",
        "plan": "Ayuno, antibioticoterapia profiláctica y valoración por turno quirúrgico.",
        "tipo_exp": "Cirugía / Hospitalización"
    },

    # 8. Reumatología
    {
        "enfermedad": "Artritis Reumatoide Seropositiva (Factor Reumatoide y Anti-CCP +)",
        "cie10": "M05.9",
        "especialidad": "Reumatología",
        "alergia_prob": "Metotrexato (Elevación transaminasas)",
        "medicacion": "Leflunomida 20mg c/24h, Prednisona 5mg matutina, Ácido Fólico 5mg semanal",
        "motivo": "Dolor y rigidez articular matutina de 45 minutos en manos y muñecas.",
        "subjetivo": "Dificultad para abrir frascos y escribir en computadora por las mañanas.",
        "objetivo": "Sinovitis palpable en 2da y 3ra MCF bilaterales. Desviación cubital incipiente sin anquilosis.",
        "analisis": "Artritis reumatoide con actividad moderada (DAS28 3.8).",
        "plan": "Mantener DMARD sintético convencional y valorar adición de terapia biológica si persiste actividad.",
        "tipo_exp": "Consulta Reumatológica"
    },

    # 9. Neurología & Salud Mental
    {
        "enfermedad": "Migraña Clásica episódica con aura visual",
        "cie10": "G43.1",
        "especialidad": "Neurología",
        "alergia_prob": "Ergotamina",
        "medicacion": "Zolmitriptán 2.5mg rescate, Propranolol 40mg c/12h preventivo",
        "motivo": "Crisis migrañosas incapacitantes precedidas de escotomas centellantes.",
        "subjetivo": "Refiere dolor pulsátil hemicraneal izquierdo acompañado de fotofobia y sonofobia severas.",
        "objetivo": "Exploración neurológica intercrítica completamente normal. Fondo de ojo normal.",
        "analisis": "Migraña con aura visual típica de alta frecuencia.",
        "plan": "Diario de cefaleas, terapia abortiva temprana al inicio del aura y profilaxis betabloqueadora.",
        "tipo_exp": "Neurología"
    },
    {
        "enfermedad": "Trastorno de Ansiedad Generalizada con Somatización",
        "cie10": "F41.1",
        "especialidad": "Salud Mental / Psiquiatría",
        "alergia_prob": "Sertralina (Diarrea severa)",
        "medicacion": "Escitalopram 10mg c/24h por la mañana, Clonazepam 0.5mg temporal nocturno",
        "motivo": "Preocupación excesiva incontrolable, tensión muscular y opresión precordial.",
        "subjetivo": "Insomnio de conciliación y sensación constante de catástrofe inminente. ECG previo normal.",
        "objetivo": "Paciente orientado, discurso coherente, afecto ansioso con hiperhidrosis palmar.",
        "analisis": "Trastorno de ansiedad generalizada moderado-grave (escala GAD-7: 15 puntos).",
        "plan": "Inicio de ISRS, retiro gradual de benzodiacepina a las 3 semanas y derivación a psicoterapia TCC.",
        "tipo_exp": "Consulta de Salud Mental"
    },

    # 10. Ginecología & Obstetricia
    {
        "enfermedad": "Embarazo normoevolutivo de 14 semanas de gestación",
        "cie10": "Z34.0",
        "especialidad": "Ginecología & Obstetricia",
        "alergia_prob": "Sin alergias conocidas",
        "medicacion": "Ácido Fólico 5mg, Sulfato Ferroso 200mg, Calcio 500mg",
        "motivo": "Control prenatal de segundo trimestre.",
        "subjetivo": "Movimientos fetales aún no percibidos claramente. Náuseas en franca remisión.",
        "objetivo": "TA 110/70 mmHg, Peso 58 kg (+1.5 kg en trimestre). Fondo uterino a 12 cm sobre sínfisis. FCF audible a 148 lpm.",
        "analisis": "Primigesta de 24 años con embarazo normoevolutivo de bajo riesgo.",
        "plan": "Solicitud de ultrasonido estructural de semanas 18-22 y tamizaje de curva de tolerancia a la glucosa.",
        "tipo_exp": "Control Prenatal"
    }
]

DOCTORES_FIRMA = [
    {"nombre": "Dr. Roberto Morales Solís", "cedula": "CED-9482710", "esp": "Medicina Interna"},
    {"nombre": "Dra. Mariana Pech González", "cedula": "CED-8127390", "esp": "Urgencias Médicas"},
    {"nombre": "Dr. Carlos Manuel Dzul Canto", "cedula": "CED-7654321", "esp": "Traumatología y Ortopedia"},
    {"nombre": "Dra. Elena Vázquez Solís", "cedula": "CED-6543210", "esp": "Medicina Familiar"},
    {"nombre": "Dr. Javier Miranda Peña", "cedula": "CED-5432109", "esp": "Cardiología"},
    {"nombre": "Dra. Beatriz Salgado Ponce", "cedula": "CED-4321098", "esp": "Ginecología y Obstetricia"}
]

TIPOS_SANGRE = ["O+", "O+", "O+", "A+", "A+", "B+", "AB+", "O-", "A-"]

def generar_curp_rfc(nombre, ap1, ap2, sexo, f_nac, estado):
    # Reglas aproximadas de CURP
    c1 = (ap1[:2] if len(ap1) >= 2 else "XX").upper()
    c2 = (ap2[:1] if ap2 else "X").upper()
    c3 = (nombre[:1] if nombre else "X").upper()
    yy = f_nac[2:4]
    mm = f_nac[5:7]
    dd = f_nac[8:10]
    sex = "H" if sexo == "M" else "M"
    rnd_num = f"{random.randint(10, 99)}"
    curp = f"{c1}{c2}{c3}{yy}{mm}{dd}{sex}{estado}{rnd_num[0]}A{rnd_num[1]}"
    rfc = f"{c1}{c2}{c3}{yy}{mm}{dd}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.randint(10, 99)}"
    nss = f"{random.randint(10, 99)}{yy}{random.randint(1000000, 9999999)}"
    return curp[:18], rfc[:13], nss[:11]

def seed_masivo(target_count=650):
    print(f"=================================================================")
    print(f"[START] INICIANDO GENERACION MASIVA DE {target_count}+ PACIENTES CLINICOS")
    print(f"=================================================================")

    create_local_tables()
    create_global_tables()

    db_local = LocalSession()
    db_global = GlobalSession()

    try:
        # Contar pacientes existentes
        existing_count = db_local.query(Patient).count()
        print(f"[*] Pacientes existentes en base local: {existing_count}")
        
        needed = max(target_count - existing_count, 620)
        print(f"[*] Generando {needed} nuevos pacientes para superar los 600 pacientes requeridos...")

        nuevos_pacientes = []
        nuevas_alergias = []
        nuevos_antecedentes = []
        nuevos_eventos = []
        nuevas_consultas = []
        nuevos_indices = []

        now = datetime.utcnow()

        for i in range(needed):
            folio_num = existing_count + i + 101
            sexo = random.choice(["M", "F"])
            if sexo == "M":
                nombres = random.choice(NOMBRES_HOMBRES)
                if random.random() < 0.4:
                    nombres += f" {random.choice(NOMBRES_HOMBRES)}"
            else:
                nombres = random.choice(NOMBRES_MUJERES)
                if random.random() < 0.4:
                    nombres += f" {random.choice(NOMBRES_MUJERES)}"

            ap1 = random.choice(APELLIDOS)
            ap2 = random.choice(APELLIDOS)
            while ap2 == ap1:
                ap2 = random.choice(APELLIDOS)

            # Edad entre 6 y 84 años
            edad = random.randint(6, 84)
            birth_year = now.year - edad
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)
            f_nac = f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}"

            estado = random.choice(ESTADOS_CURP)
            curp, rfc, nss = generar_curp_rfc(nombres, ap1, ap2, sexo, f_nac, estado)

            # Evitar colisión de CURP agregando sufijo si existe
            curp = f"{curp[:14]}{i:04d}"

            patologia = random.choice(PATOLOGIAS)
            hospital_origen = random.choice(HOSPITALES_RED)
            doctor = random.choice(DOCTORES_FIRMA)
            tipo_sangre = random.choice(TIPOS_SANGRE)

            altura = round(random.uniform(150.0, 186.0), 1) if sexo == "M" else round(random.uniform(142.0, 172.0), 1)
            peso = round(random.uniform(55.0, 102.0), 1) if sexo == "M" else round(random.uniform(46.0, 88.0), 1)

            ubicaciones = [
                f"Calle {random.randint(10, 80)} #{random.randint(100, 999)} x {random.randint(10, 90)}, Col. Centro, Mérida, Yuc.",
                f"Calle {random.randint(10, 120)} #{random.randint(100, 999)}, Fracc. Las Américas, Mérida, Yuc.",
                f"Calle {random.randint(10, 80)} #{random.randint(100, 999)}, Fracc. Ciudad Caucel, Mérida, Yuc.",
                f"Calle {random.randint(10, 50)} #{random.randint(100, 999)}, Kanasín, Yucatán",
                f"Calle {random.randint(10, 60)} #{random.randint(100, 999)}, Umán, Yucatán",
                f"Calle {random.randint(20, 90)} #{random.randint(100, 999)}, Progreso, Yucatán"
            ]

            p_obj = Patient(
                id=str(uuid.uuid4()),
                nombres=nombres,
                primer_apellido=ap1,
                segundo_apellido=ap2,
                curp=curp,
                rfc=rfc,
                nss=nss,
                sexo=sexo,
                fecha_nacimiento=f_nac,
                altura_cm=altura,
                peso_kg=peso,
                tipo_sangre=tipo_sangre,
                folio_hospital=f"EXP-2026-{folio_num:04d}",
                ubicacion_casa=random.choice(ubicaciones),
                lugar_nacimiento=f"Mérida, Yucatán" if estado == "YN" else "México",
                nacionalidad="Mexicana",
                ocupacion=random.choice(["Comerciante", "Docente", "Contador", "Estudiante", "Ama de casa", "Empleado", "Ingeniero", "Jubilado"]),
                telefono_local=f"999{random.randint(1000000, 9999999)}",
                celular=f"52999{random.randint(1000000, 9999999)}",
                email=f"{nombres.lower().split()[0]}.{ap1.lower()}{random.randint(1, 99)}@gmail.com",
                contacto_emergencia_nombre=f"Familiar de {nombres} {ap1}",
                contacto_emergencia_tel=f"999{random.randint(1000000, 9999999)}",
                anotaciones_generales=f"Diagnóstico clínico principal: {patologia['enfermedad']} (CIE-10: {patologia['cie10']}) - Atención en {hospital_origen['nombre']}.",
                clues_institucion=hospital_origen["clues"],
                created_at=now - timedelta(days=random.randint(1, 90))
            )
            nuevos_pacientes.append(p_obj)

            # Alergia
            if patologia["alergia_prob"] != "Sin alergias documentadas":
                nuevas_alergias.append(Alergia(
                    id=str(uuid.uuid4()),
                    patient_curp=curp,
                    descripcion=patologia["alergia_prob"],
                    tipo="medicamento" if "Aspirina" in patologia["alergia_prob"] or "Penicilina" in patologia["alergia_prob"] else "ambiental",
                    severidad="severa" if "Penicilina" in patologia["alergia_prob"] or "Aspirina" in patologia["alergia_prob"] else "moderada",
                    created_at=now
                ))

            # Antecedente
            nuevos_antecedentes.append(Antecedente(
                id=str(uuid.uuid4()),
                patient_curp=curp,
                tipo="patologico",
                descripcion=f"Diagnóstico previo de {patologia['enfermedad']}",
                fecha=f"{now.year - random.randint(1, 5)}-06-15"
            ))

            # Evento clínico
            ev_id = str(uuid.uuid4())
            nuevos_eventos.append(EventoClinico(
                id=ev_id,
                patient_curp=curp,
                nombre_evento=f"Atención por {patologia['enfermedad']}",
                doctor_creador=doctor["nombre"],
                created_at=now - timedelta(days=random.randint(0, 30))
            ))

            # Consulta SOAP
            nota_medica_payload = f'{{"motivo_consulta": "{patologia["motivo"]}", "subjetivo": "{patologia["subjetivo"]}", "objetivo": "{patologia["objetivo"]}", "analisis": "{patologia["analisis"]}", "plan_tratamiento": "{patologia["plan"]}", "diagnostico": "{patologia["enfermedad"]}", "cie10": "{patologia["cie10"]}"}}'
            receta_payload = f'{{"medicamentos": [{{"nombre": "{patologia["medicacion"]}", "dosis": "Según indicación", "via": "Oral"}}], "instrucciones": "Tomar puntualmente con agua."}}'
            entidades_payload = f'{{"codigos_cie10": {{"{patologia["enfermedad"]}": "{patologia["cie10"]}"}}}}'

            nuevas_consultas.append(Consulta(
                id=str(uuid.uuid4()),
                evento_id=ev_id,
                patient_curp=curp,
                doctor_nombre=doctor["nombre"],
                cedula_profesional=doctor["cedula"],
                nota_medica_json=nota_medica_payload,
                receta_json=receta_payload,
                entidades_json=entidades_payload,
                texto_original=f"Consulta médica de seguimiento por {patologia['enfermedad']}.",
                created_at=now - timedelta(days=random.randint(0, 30))
            ))

            # Índice Federado en Red (Global DB)
            nombre_completo = f"{nombres} {ap1} {ap2}"
            alergias_txt = patologia["alergia_prob"]
            
            # Nodo Primario
            nuevos_indices.append(PatientIndex(
                id=str(uuid.uuid4()),
                curp=curp,
                nombre=nombre_completo,
                clues_institucion=hospital_origen["clues"],
                institucion_nombre=hospital_origen["nombre"],
                expediente_tipo=patologia["tipo_exp"],
                alergias_criticas=alergias_txt,
                tipo_sangre=tipo_sangre,
                diagnosticos_clave=f"{patologia['cie10']} {patologia['enfermedad']}",
                medicacion_activa=patologia["medicacion"],
                contacto_emergencia=f"Familiar ({p_obj.contacto_emergencia_tel})",
                consentimiento_estado="Otorgado",
                updated_at=now
            ))

            # ~35% de los pacientes tienen expediente cruzado en un segundo hospital (ej. O'Horán o Cruz Roja)
            if random.random() < 0.35:
                segundo_hosp = random.choice([h for h in HOSPITALES_RED if h["clues"] != hospital_origen["clues"]])
                nuevos_indices.append(PatientIndex(
                    id=str(uuid.uuid4()),
                    curp=curp,
                    nombre=nombre_completo,
                    clues_institucion=segundo_hosp["clues"],
                    institucion_nombre=segundo_hosp["nombre"],
                    expediente_tipo="Interconsulta / Valoración Previa",
                    alergias_criticas=alergias_txt,
                    tipo_sangre=tipo_sangre,
                    diagnosticos_clave=f"{patologia['cie10']} {patologia['enfermedad']}",
                    medicacion_activa=patologia["medicacion"],
                    contacto_emergencia=f"Familiar ({p_obj.contacto_emergencia_tel})",
                    consentimiento_estado="Otorgado",
                    updated_at=now - timedelta(days=random.randint(15, 180))
                ))

        print(f"[*] Guardando en base local (SQLite local.db)...")
        # Inserción en bloques
        db_local.bulk_save_objects(nuevos_pacientes)
        db_local.bulk_save_objects(nuevas_alergias)
        db_local.bulk_save_objects(nuevos_antecedentes)
        db_local.bulk_save_objects(nuevos_eventos)
        db_local.bulk_save_objects(nuevas_consultas)
        db_local.commit()
        print(f"  -> {len(nuevos_pacientes)} pacientes guardados en base local.")

        print(f"[*] Guardando en índice federado de red (SQLite global.db)...")
        db_global.bulk_save_objects(nuevos_indices)
        db_global.commit()
        print(f"  -> {len(nuevos_indices)} registros indexados en la Red Interhospitalaria.")

        # Sembrar 25 referencias interhospitalarias adicionales
        print(f"[*] Generando referencias interhospitalarias activas...")
        nuevas_referencias = []
        for j in range(25):
            idx_sample = random.choice(nuevos_indices)
            hosp_destino = random.choice([h for h in HOSPITALES_RED if h["clues"] != idx_sample.clues_institucion])
            prio = random.choice(["Urgencia", "Prioritaria", "Ordinaria"])
            estado = random.choice(["En_Transito", "Aceptada", "Completada"])
            
            ref = InterHospitalReferral(
                id=f"REF-2026-{random.randint(1000, 9999)}",
                patient_curp=idx_sample.curp,
                patient_nombre=idx_sample.nombre,
                clues_origen=idx_sample.clues_institucion,
                hospital_origen_nombre=idx_sample.institucion_nombre,
                clues_destino=hosp_destino["clues"],
                hospital_destino_nombre=hosp_destino["nombre"],
                motivo_envio=f"Envío de paciente para valoración y manejo por la especialidad. {idx_sample.diagnosticos_clave}",
                diagnostico_cie10=idx_sample.diagnosticos_clave,
                prioridad=prio,
                estado=estado,
                medico_solicitante=random.choice(DOCTORES_FIRMA)["nombre"],
                cedula_solicitante=random.choice(DOCTORES_FIRMA)["cedula"],
                detalles_clinicos=f"Paciente con diagnóstico activo de {idx_sample.diagnosticos_clave}. Alergias: {idx_sample.alergias_criticas}. Medicación en curso: {idx_sample.medicacion_activa}.",
                folio_fhir=f"FHIR-YUC-2026-{random.randint(10000, 99999)}",
                created_at=now - timedelta(hours=random.randint(1, 48)),
                updated_at=now - timedelta(minutes=random.randint(5, 60))
            )
            nuevas_referencias.append(ref)

        db_global.bulk_save_objects(nuevas_referencias)
        db_global.commit()
        print(f"  -> {len(nuevas_referencias)} referencias activas creadas en la red.")

        total_local = db_local.query(Patient).count()
        total_global = db_global.query(PatientIndex).count()
        total_refs = db_global.query(InterHospitalReferral).count()

        print("=================================================================")
        print(f"[OK] CARGA MASIVA COMPLETADA CON EXITO:")
        print(f"   - Total Pacientes en Base Local: {total_local}")
        print(f"   - Total Registros en Red Federada: {total_global}")
        print(f"   - Total Referencias Interhospitalarias: {total_refs}")
        print(f"   - Hospitales Federados: {len(HOSPITALES_RED)}")
        print("=================================================================")

    finally:
        db_local.close()
        db_global.close()

if __name__ == "__main__":
    seed_masivo(650)
