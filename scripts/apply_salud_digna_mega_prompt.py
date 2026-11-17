# -*- coding: utf-8 -*-
"""
scripts/apply_salud_digna_mega_prompt.py
========================================
Integrates the high-efficiency Salud Digna / NOM-004 Mega Prompt into:
- app/core/entity_extractor.py (and Linux_Ver)
- app/api/routes_input.py (and Linux_Ver)
- app/core/clinical_generative_engine.py (and Linux_Ver)
"""

import os
import re

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

NEW_SYSTEM_PROMPT = '''SYSTEM_PROMPT = """Eres el Asistente Clínico Inteligente de Alta Eficiencia de MedicAItion, optimizado bajo el estándar de flujo continuo de alta velocidad de Salud Digna y la normativa mexicana NOM-004-SSA3-2012 y NOM-024-SSA3-2012.

Tu objetivo es procesar el dictado/narrativa del médico, cruzarlo con el expediente activo del paciente y generar instantáneamente una nota SOAP impecable, receta médica estructurada, códigos CIE-10 precisos, órdenes de estudios y escudo de seguridad CDSS sin requerir clics adicionales.

Analiza el texto médico y realiza las siguientes tareas:
1. Extrae las entidades clínicas presentes (síntomas, diagnósticos, signos vitales, tratamientos, medicamentos).
2. Redacta las secciones narrativas de una Nota Médica de Evolución conforme a la NOM-004-SSA3-2012 (Subjetivo, Objetivo, Análisis, Plan).
3. Genera una Receta Médica digitalizada clara para el paciente con denominación genérica oficial (DCI), dosis, vía, frecuencia exacta y duración.
4. Identifica estudios de laboratorio o gabinete sugeridos y signos de alarma.
5. Valida el escudo de seguridad farmacológica (CDSS) cotejando contra las alergias y contraindicaciones del paciente.

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta, sin texto adicional:
{
  "demograficos": {
    "nombre": null,
    "edad": null,
    "sexo": null,
    "curp": null
  },
  "texto_redactado": "Resumen formal y redactado de la consulta en lenguaje médico profesional de alta calidad, libre de titubeos, muletillas o repeticiones del dictado.",
  "sintomas_referidos": [],
  "diagnosticos_tentativos": [],
  "signos_vitales": [],
  "tratamientos": [],
  "medicamentos": [
    {
      "nombre": "Nombre genérico del fármaco (DCI)",
      "presentacion": "Tabletas / Suspensión / Solución inyectable / etc.",
      "dosis": "cantidad y unidad (ej: 500 mg, 1 tableta)",
      "via": "Oral / Intramuscular / Intravenosa / Tópica / Inhalada",
      "periodicidad": "cada X horas con horario exacto",
      "duracion": "duración en días (ej: por 7 días, dosis única)"
    }
  ],
  "nota_clinica": {
    "motivo_consulta": "Razón principal por la que acude el paciente, en lenguaje médico formal",
    "evolucion_padecimiento": "Semiología completa del padecimiento actual (inicio, cronología, intensidad, factores agravantes/atenuantes)",
    "exploracion_fisica": "Hallazgos de la exploración física cefalocaudal y signos vitales consolidados",
    "diagnostico_integral": "Juicio clínico con código CIE-10 oficial de la Secretaría de Salud de México",
    "pronostico": "Pronóstico para la vida y para la función (bueno, reservado o grave)",
    "plan_tratamiento": "Plan terapéutico integral: farmacológico, higiénico-dietético, estudios solicitados y revaloración"
  },
  "diagnostico_diferencial": [
    {
      "condicion": "Nombre de la entidad clínica diferencial",
      "nivel": "Principal | Alternativo | Descartar (Grave)",
      "justificacion": "Por qué se considera según el cuadro clínico",
      "accion_descarte": "Estudio paraclínico o maniobra para confirmar/descartar"
    }
  ],
  "estudios_solicitados": [
    {
      "estudio": "Nombre del estudio (ej. Biometría Hemática Completa, Glucosa en ayuno)",
      "justificacion": "Motivo clínico del estudio",
      "tipo": "Laboratorio | Gabinete | Imagenología"
    }
  ],
  "alertas_seguridad": [
    {
      "nivel": "CRÍTICA | ADVERTENCIA | INFORMATIVA",
      "mensaje": "Alerta de alergia o validación farmacológica segura contra antecedentes del paciente"
    }
  ],
  "datos_alarma": [
    "Dificultad respiratoria o estridor",
    "Fiebre persistente que no cede",
    "Dolor torácico opresivo"
  ],
  "revaloracion_dias": 7,
  "receta_paciente": "Instrucciones de cuidado y administración redactadas de forma clara y amigable en segunda persona para el paciente."
}

Reglas ESTRICTAS:
- Traduce cualquier expresión coloquial ("calentura", "cuerpo cortado") a lenguaje clínico formal ("fiebre cuantificada", "mialgias y artralgias").
- Si el contexto del paciente incluye ALERGIAS (ej. Penicilinas, AINEs), NUNCA prescribas medicamentos de esa familia; emite una alerta en 'alertas_seguridad' y sugiere una opción terapéutica segura.
- Responde solo con el JSON, sin explicaciones ni rodeos."""'''

def update_entity_extractor(base_dir):
    p = os.path.join(base_dir, "app", "core", "entity_extractor.py")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    # Reemplazar SYSTEM_PROMPT
    pattern = r'SYSTEM_PROMPT = """.*?"""'
    content = re.sub(pattern, NEW_SYSTEM_PROMPT.strip(), content, flags=re.DOTALL)

    # Actualizar extract_entities para aceptar patient_context
    old_fn_def = "def extract_entities(text: str, mode: str = \"auto\", api_key: str = None) -> dict:"
    new_fn_def = "def extract_entities(text: str, mode: str = \"auto\", api_key: str = None, patient_context: dict = None) -> dict:"
    if old_fn_def in content:
        content = content.replace(old_fn_def, new_fn_def)

    # Inyectar contexto del paciente al armar los mensajes del LLM
    old_prompt_call = '{"role": "user",   "content": f"Extrae las entidades médicas y redacta la nota clínica del siguiente texto:\\n\\n{text}"}'
    new_prompt_call = """{"role": "user",   "content": _build_user_prompt_with_context(text, patient_context)}"""
    
    helper_code = '''
def _build_user_prompt_with_context(text: str, patient_context: dict = None) -> str:
    if not patient_context:
        return f"Extrae las entidades médicas y redacta la nota clínica del siguiente texto:\\n\\n{text}"
    
    allergies = patient_context.get("alergias") or []
    if isinstance(allergies, list):
        al_str = ", ".join(a.get("descripcion", str(a)) for a in allergies) or "Sin alergias conocidas"
    else:
        al_str = str(allergies)
        
    antecedentes = patient_context.get("antecedentes") or []
    if isinstance(antecedentes, list):
        ant_str = ", ".join(a.get("descripcion", str(a)) for a in antecedentes) or "Sin antecedentes patológicos relevantes"
    else:
        ant_str = str(antecedentes)

    ctx_block = (
        f"[CONTEXTO PRECARGADO DEL PACIENTE (TRIAGE / SALUD DIGNA)]\\n"
        f"- Nombre: {patient_context.get('nombre_completo') or patient_context.get('nombre') or 'No especificado'}\\n"
        f"- CURP: {patient_context.get('curp') or 'N/A'} | Edad: {patient_context.get('edad')} años | Sexo: {patient_context.get('sexo')}\\n"
        f"- Tipo de Sangre: {patient_context.get('tipo_sangre') or 'O+'}\\n"
        f"- ALERGIAS CRÍTICAS REPORTADAS: {al_str}\\n"
        f"- ANTECEDENTES RELEVANTES: {ant_str}\\n"
        f"- ANOTACIONES: {patient_context.get('anotaciones_generales') or 'Ninguna'}\\n"
    )
    return f"{ctx_block}\\n[DICTADO O NARRATIVA MÉDICA A PROCESAR]:\\n{text}"
'''
    if "_build_user_prompt_with_context" not in content:
        # Añadir la función auxiliar antes de extract_entities
        content = content.replace("def extract_entities(", helper_code + "\ndef extract_entities(")

    # Reemplazar las llamadas de prompt en extract_entities
    content = content.replace(
        '{"role": "user", "content": f"Extrae las entidades médicas y redacta la nota clínica del siguiente texto:\\n\\n{text}"}',
        '{"role": "user", "content": _build_user_prompt_with_context(text, patient_context)}'
    )
    content = content.replace(
        '{"role": "user",   "content": f"Extrae las entidades médicas y redacta la nota clínica del siguiente texto:\\n\\n{text}"}',
        '{"role": "user", "content": _build_user_prompt_with_context(text, patient_context)}'
    )

    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated entity_extractor.py with Salud Digna Mega Prompt in: {p}")

def update_routes_input(base_dir):
    p = os.path.join(base_dir, "app", "api", "routes_input.py")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    # Pasar patient_data a extract_entities
    old_call = "entities = extract_entities(text, mode=llm_mode, api_key=api_key)"
    new_call = "entities = extract_entities(text, mode=llm_mode, api_key=api_key, patient_context=patient_data)"
    if old_call in content:
        content = content.replace(old_call, new_call)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated routes_input.py to pass patient_context in: {p}")

def update_clinical_generative_engine(base_dir):
    p = os.path.join(base_dir, "app", "core", "clinical_generative_engine.py")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    # Añadir sección de Salud Digna / Mega Prompt
    target_check = '# 2. CÓDIGO INFARTO / IAM'
    mega_prompt_block = '''    # 1.5 MEGA PROMPT DE CONSULTA DE ALTA VELOCIDAD (ESTILO SALUD DIGNA)
    if any(k in q for k in ("salud digna", "mega prompt", "optimizar consulta", "flujo consulta", "alta velocidad", "estructurar consulta")):
        avatar_state = "contento"
        lines.append("### ⚡ Mega Prompt de Consulta Rápida (Estándar Salud Digna / NOM-004)")
        lines.append("El motor de **MedicAItion** está calibrado para procesar dictados de 30 segundos y estructurar automáticamente:")
        lines.append("1. **SOAP Normativo (NOM-004):** Subjetivo, Objetivo (con vitales enlazados), Análisis CIE-10 y Plan.")
        lines.append("2. **Receta DCI Estandarizada:** Genéricos oficiales, dosis, vía, horario estricto y días.")
        lines.append("3. **Escudo Farmacológico CDSS:** Validación instantánea contra alergias de triaje.")
        lines.append("4. **Órdenes de Laboratorio/Gabinete:** Solicitud justificada en un solo clic.")
        lines.append("5. **Datos de Alarma:** Instrucciones directas para el paciente.")
        lines.append("\\n*Para usarlo ahora:* Selecciona a tu paciente activo y presiona el botón de micrófono en **Nueva Consulta** para dictar libremente.")
        return {
            "avatar_state": avatar_state,
            "text": "\\n".join(lines),
        }

'''
    if "MEGA PROMPT DE CONSULTA DE ALTA VELOCIDAD" not in content and target_check in content:
        content = content.replace(target_check, mega_prompt_block + target_check)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated clinical_generative_engine.py in: {p}")

for root in ROOTS:
    update_entity_extractor(root)
    update_routes_input(root)
    update_clinical_generative_engine(root)

print("Salud Digna Mega Prompt integration completed successfully.")
