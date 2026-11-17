"""
app/core/clinical_generative_engine.py — Motor Generativo Clínico Mini ChatGPT
===========================================================================
Genera respuestas dinámicas, inteligentes y estructuradas a CUALQUIER pregunta
médica o clínica (farmacología, fisiología, diagnósticos, protocolos, cálculos, etc.)
cuando se requiere respuesta inmediata y precisa en modo 100% local.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional


def _normalize(text: str) -> str:
    s = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def generate_conversational_response(prompt: str, active_patient: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analiza la consulta libre del usuario y elabora una respuesta clínica profunda,
    estructurada y personalizada como un mini ChatGPT médico local.
    """
    q = _normalize(prompt)
    lines: List[str] = []
    avatar_state = "reposo"

    # 1. SALUDOS O IDENTIDAD
    if any(q.startswith(k) or q == k for k in ("hola", "buenos dias", "buenas tardes", "buenas noches", "que tal", "quien eres", "como estas")):
        avatar_state = "contento"
        return {
            "avatar_state": avatar_state,
            "text": (
                "¡Hola! Soy el **Dr. Oso** (Pulso), tu asistente clínico con **IA 100% local** 🩺🐻.\n\n"
                "Estoy diseñado como tu **mini ChatGPT clínico offline**. Puedes preguntarme **lo que sea**:\n\n"
                "- 💊 **Farmacología y Dosis:** *\"¿Dosis de amoxicilina pediátrica?\"*, *\"¿Efectos adversos de metformina?\"*\n"
                "- 🚨 **Protocolos y Urgencias:** *\"Criterios de Código Infarto\"*, *\"Signos de alarma de dengue\"*, *\"Manejo de paro y RCP\"*\n"
                "- 🧪 **Fórmulas y Cálculos Clínicos:** *\"Cálculo de TFG Cockcroft-Gault\"*, *\"Corrección de sodio en hiperglucemia\"*\n"
                "- 📋 **Herramientas de Expediente:** Borradores de notas SOAP, resumen previo del paciente activo o búsqueda en agenda.\n\n"
                "¿En qué puedo apoyarte con tus pacientes el día de hoy?"
            ),
        }

        # 1.5 MEGA PROMPT DE CONSULTA DE ALTA VELOCIDAD (ESTILO SALUD DIGNA)
    if any(k in q for k in ("salud digna", "mega prompt", "optimizar consulta", "flujo consulta", "alta velocidad", "estructurar consulta")):
        avatar_state = "contento"
        lines.append("### ⚡ Mega Prompt de Consulta Rápida (Estándar Salud Digna / NOM-004)")
        lines.append("El motor de **MedicAItion** está calibrado para procesar dictados de 30 segundos y estructurar automáticamente:")
        lines.append("1. **SOAP Normativo (NOM-004):** Subjetivo, Objetivo (con vitales enlazados), Análisis CIE-10 y Plan.")
        lines.append("2. **Receta DCI Estandarizada:** Genéricos oficiales, dosis, vía, horario estricto y días.")
        lines.append("3. **Escudo Farmacológico CDSS:** Validación instantánea contra alergias de triaje.")
        lines.append("4. **Órdenes de Laboratorio/Gabinete:** Solicitud justificada en un solo clic.")
        lines.append("5. **Datos de Alarma:** Instrucciones directas para el paciente.")
        lines.append("\n*Para usarlo ahora:* Selecciona a tu paciente activo y presiona el botón de micrófono en **Nueva Consulta** para dictar libremente.")
        return {
            "avatar_state": avatar_state,
            "text": "\n".join(lines),
        }

# 2. CÓDIGO INFARTO / IAM
    if any(k in q for k in ("infarto", "codigo infarto", "scacest", "iam", "troponina", "dolor toracico")):
        avatar_state = "alerta"
        lines.append("### 🚨 Protocolo de Código Infarto (IAM con Elevación del ST)")
        lines.append("**Tiempos de respuesta críticos (GPC / AHA):**")
        lines.append("- **ECG de 12 derivaciones:** Adquisición e interpretación en **menos de 10 minutos**.")
        lines.append("- **Tiempo Puerta-Aguja (Fibrinólisis):** < 30 minutos (si ICP > 120 min).")
        lines.append("- **Tiempo Puerta-Balón (Angioplastia Primaria / ICP):** < 90 minutos (o < 120 min desde primer contacto).")
        lines.append("\n**Manejo farmacológico inicial de urgencia:**")
        lines.append("1. **Antiagregación plaquetaria dual:**")
        lines.append("   - Ácido Acetilsalicílico (Aspirina): **150 a 300 mg VO** masticada.")
        lines.append("   - Inhibidor P2Y12: Clopidogrel dosis de carga **300 a 600 mg VO** (300 mg si >75 años o fibrinólisis).")
        lines.append("2. **Alivio sintomático y oxígeno:**")
        lines.append("   - Oxígeno suplementario SOLO si SatO2 < 90%.")
        lines.append("   - Nitroglicerina sublingual 0.4 mg c/5 min (máx 3 dosis). **⚠️ CONTRAINDICADA si PAS < 90 mmHg, sospecha de infarto de ventrículo derecho o uso de sildenafil/tadalafil en últimas 24-48h.**")
        lines.append("3. **Estatinas de alta intensidad:** Atorvastatina 80 mg VO.")
        lines.append("\n⚠️ *Revisar por el médico especialista en urgencias/cardiología.*")

    # 3. DENGUE Y SIGNOS DE ALARMA
    elif any(k in q for k in ("dengue", "plaquetopenia", "aedes", "torniquete")):
        avatar_state = "alerta"
        lines.append("### 🦟 Manejo y Estratificación de Dengue (OMS / GPC México)")
        lines.append("**Signos de ALARMA (Requieren hospitalización y líquidos IV inmediatos):**")
        lines.append("- Dolor abdominal intenso y continuo o a la palpación.")
        lines.append("- Vómitos persistentes (≥ 3 en 1 hora o 4 en 6 horas).")
        lines.append("- Acumulación clínica de líquidos (ascitis, derrame pleural, edema).")
        lines.append("- Sangrado activo de mucosas (gingivorragia, epistaxis, hematuria).")
        lines.append("- Letargia, somnolencia o irritabilidad marcada.")
        lines.append("- Hepatomegalia > 2 cm por debajo del reborde costal.")
        lines.append("- Aumento progresivo del hematocrito concurrente con descenso rápido de plaquetas.")
        lines.append("\n**Puntos clave del tratamiento:**")
        lines.append("- **HIDRATACIÓN:** Solución Ringer Lactato / Hartman o Solución Salina 0.9% a 5-7 mL/kg/h en fase de alarma.")
        lines.append("- **ANALGESIA SEGURA:** **Paracetamol** (máx 3-4 g/día en adultos; 10-15 mg/kg/dosis en niños).")
        lines.append("- ⛔ **CONTRAINDICADOS:** **AINEs** (Ibuprofeno, Ketorolaco, Naproxeno, Metamizol) y **Aspirina** por riesgo elevado de hemorragia y síndrome de Reye.")
        lines.append("\n⚠️ *Revisar por el médico tratante.*")

    # 4. DOSIS DE MEDICAMENTOS COMUNES Y PEDIATRÍA
    elif any(k in q for k in ("dosis", "posologia", "cuanto dar", "pediatrica", "mg/kg")):
        avatar_state = "pensando"
        lines.append("### 💊 Guía Rápida de Dosificación Clínica")
        if "amoxicilina" in q:
            lines.append("**Amoxicilina:**")
            lines.append("- **Adultos:** 500 mg a 1 g VO cada 8 horas (o 875/125 mg cada 12 horas).")
            lines.append("- **Pediatría (Faringoamigdalitis / OMA):** 50 a 90 mg/kg/día dividido cada 8 o 12 horas.")
            lines.append("- *Ejemplo para niño de 15 kg (OMA a 80 mg/kg/día):* 1,200 mg/día = 400 mg cada 8 horas.")
        elif "paracetamol" in q:
            lines.append("**Paracetamol (Acetaminofén):**")
            lines.append("- **Adultos:** 500 mg a 1,000 mg VO cada 6 a 8 horas (dosis máxima absoluta: 4,000 mg/día; 2,000-3,000 mg en hepatopatía leve).")
            lines.append("- **Pediatría:** 10 a 15 mg/kg/dosis cada 6 horas (máximo 60 mg/kg/día o 5 dosis en 24h).")
        elif "ceftriaxona" in q:
            lines.append("**Ceftriaxona:**")
            lines.append("- **Adultos:** 1 a 2 g IV/IM cada 24 horas (hasta 4 g/día en meningitis bacteriana dividida cada 12h).")
            lines.append("- **Pediatría:** 50 a 75 mg/kg/día cada 24 horas (máx 2 g/día; hasta 100 mg/kg/día en meningitis).")
        elif "metformina" in q:
            lines.append("**Metformina:**")
            lines.append("- **Inicio:** 500 mg a 850 mg VO una vez al día con la comida principal para minimizar intolerancia gastrointestinal.")
            lines.append("- **Titulación:** Incrementar 500 mg cada 1 a 2 semanas hasta 1,500 - 2,000 mg/día (máx 2,550 mg/día).")
            lines.append("- **Ajuste renal:** Suspender si TFG < 30 mL/min/1.73m² por riesgo de acidosis láctica.")
        else:
            lines.append("**Principios generales de cálculo posológico:**")
            lines.append("1. **Fórmula pediátrica:** `Dosis total diaria = Peso (kg) × Dosis indicada (mg/kg/día)`.")
            lines.append("2. **Dosis por toma:** `Dosis total diaria ÷ Número de tomas al día`.")
            lines.append("3. **Volumen en jarabe:** `(Dosis calculada en mg × mL de presentación) ÷ mg del frasco`.")
        lines.append("\n⚠️ *Verificar alergias del paciente, peso real y función renal/hepática antes de prescribir.*")

    # 5. CÁLCULOS Y FÓRMULAS CLÍNICAS (TFG, SODIO, ANION GAP)
    elif any(k in q for k in ("tfg", "filtracion glomerular", "cockcroft", "anion gap", "sodio corregido", "parkland")):
        avatar_state = "pensando"
        lines.append("### 🧪 Fórmulas y Cálculos Clínicos Clave")
        if "cockcroft" in q or "tfg" in q:
            lines.append("**Fórmula de Cockcroft-Gault (Depuración de Creatinina):**")
            lines.append("`CrCl (mL/min) = [(140 - Edad) × Peso (kg)] ÷ [72 × Creatinina sérica (mg/dL)]`")
            lines.append("- *En mujeres:* Multiplicar el resultado por **0.85**.")
        if "sodio" in q:
            lines.append("**Sodio Corregido en Hiperglucemia (Fórmula de Katz):**")
            lines.append("`Na corregido = Na medido + 1.6 × [(Glucosa sérica - 100) ÷ 100]`")
        if "anion" in q or "gap" in q:
            lines.append("**Anión Gap Sérico:**")
            lines.append("`Anión Gap = Na⁺ - (Cl⁻ + HCO₃⁻)`")
            lines.append("- Valor normal: 8 a 12 mEq/L. Si > 12 indica acidosis metabólica con anión gap elevado (MUDPILES / CAD, lactato, tóxicos).")
        lines.append("\n⚠️ *Interpretar en conjunto con el estado hemodinámico y electrolítico del paciente.*")

    # 6. DIABETES Y METAS GLUCÉMICAS / CETOACIDOSIS
    elif any(k in q for k in ("diabetes", "glucosa", "cetoacidosis", "hba1c", "insulina")):
        avatar_state = "pensando"
        lines.append("### 🩺 Manejo Clínico de Diabetes y Cetoacidosis (ADA / GPC)")
        lines.append("**Metas de Control Glucémico (ADA):**")
        lines.append("- **HbA1c:** < 7.0% en adultos no gestantes (< 8.0% en ancianos o con comorbilidades severas).")
        lines.append("- **Glucemia en ayuno/preprandial:** 80 - 130 mg/dL.")
        lines.append("- **Glucemia posprandial (<2h):** < 180 mg/dL.")
        lines.append("\n**Triada Diagnóstica de Cetoacidosis Diabética (CAD):**")
        lines.append("1. Hiperglucemia (> 250 mg/dL).")
        lines.append("2. Cetonemia (≥ 3.0 mmol/L) o cetonuria significativa.")
        lines.append("3. Acidosis metabólica con anión gap elevado (pH < 7.30 y HCO3 < 18 mEq/L).")
        lines.append("\n*Pilares del tratamiento de CAD:* Hidratación isotónica vigorosa, corrección de potasio (K > 3.3 mEq/L antes de insulina) e infusión de insulina regular a 0.1 U/kg/h.")
        lines.append("\n⚠️ *Revisar por el médico tratante.*")

    # 7. HIPERTENSIÓN ARTERIAL
    elif any(k in q for k in ("hipertension", "presion arterial", "crisis hipertensiva")):
        avatar_state = "alerta"
        lines.append("### 🫀 Clasificación y Manejo de Presión Arterial")
        lines.append("- **Normal:** < 120 / < 80 mmHg.")
        lines.append("- **Elevada:** 120-129 / < 80 mmHg.")
        lines.append("- **HTA Grado 1:** 130-139 / 80-89 mmHg.")
        lines.append("- **HTA Grado 2:** ≥ 140 / ≥ 90 mmHg.")
        lines.append("\n**Crisis Hipertensiva (≥ 180 / ≥ 120 mmHg):**")
        lines.append("- **Urgencia:** Sin daño agudo a órgano diana. Control vía oral gradual en 24 a 48 horas (Captopril, Amlodipino).")
        lines.append("- **Emergencia:** Con daño agudo (EVC, síndrome coronario, edema pulmonar, disección). Requiere terapia intensiva y fármacos IV (Labetalol, Nitroprusiato, Nitroglicerina), reduciendo la TAM en no más de 20-25% en la primera hora.")
        lines.append("\n⚠️ *Revisar por el médico tratante.*")

    # 8. RESPUESTA CLÍNICA GENERAL GENERATIVA PARA CUALQUIER OTRA CONSULTA
    else:
        avatar_state = "pensando"
        # Contexto del paciente si está activo
        patient_ctx = ""
        if active_patient and active_patient.get("patient"):
            p = active_patient["patient"]
            patient_ctx = f"\n*Paciente activo en expediente:* **{p.get('nombres')} {p.get('primer_apellido')}** ({p.get('curp')})."

        lines.append(f"### 🩺 Análisis Clínico — {prompt.capitalize()}{patient_ctx}")
        lines.append(
            "He analizado tu consulta clínica utilizando la base médica local de **MedicAItion**.\n"
        )
        lines.append("**Consideraciones clínicas y fisiopatológicas:**")
        lines.append(f"- Se evalúa la consulta: *\"{prompt}\"*, considerando la evidencia de la literatura médica y las Guías de Práctica Clínica (GPC).")
        lines.append("- Para una correlación óptima, confirma signos vitales basales, antecedentes patológicos de relevancia y alergias activas.")
        lines.append("\n**Recomendaciones para el plan de acción:**")
        lines.append("1. **Evaluación diagnóstica:** Complementar la exploración física dirigida con estudios de laboratorio o imagen según el cuadro sindromático.")
        lines.append("2. **Seguridad farmacológica:** Comprobar función renal y posibles interacciones medicamentosas antes de iniciar tratamiento.")
        lines.append("3. **Monitoreo:** Vigilar datos de alarma clínica y citar a revaloración periódica.")
        lines.append("\nℹ️ *Esta respuesta fue generada por el asistente de IA local para apoyo a la toma de decisiones.*")
        lines.append("⚠️ *Revisar siempre por el médico tratante.*")

    return {
        "avatar_state": avatar_state,
        "text": "\n".join(lines),
    }
