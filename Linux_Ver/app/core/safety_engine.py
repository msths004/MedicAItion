"""
safety_engine.py — MedicAItion Guardián Clínico Salva-Vidas (CDSS)
==================================================================
Motor determinista de soporte a la decisión clínica (sin latencia ni
alucinaciones) que opera 100% offline sobre entidades extraídas, signos
vitales, alergias, antecedentes y texto original de la consulta.

Capacidades principales:
  1. Triaje clínico automatizado (ESI / NEWS2 / qSOFA) y Banderas Rojas
     (Código Infarto, Código Cerebro, Código Sepsis, Código Dengue Alarma).
  2. Escudo Farmacológico: cruce alergia-fármaco (DB + dictado),
     interacciones fármaco-fármaco (DDI), contraindicaciones clínicas y
     límites de dosis por peso/edad.
  3. Evidencia Vinculada (Linked Evidence): vincula cada entidad o código
     CIE-10 con el fragmento literal del dictado original.
  4. Signos de Alarma en Casa redactados para el paciente en la receta.
"""

from __future__ import annotations
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────
# NORMALIZACIÓN Y CATÁLOGOS CLÍNICOS
# ─────────────────────────────────────────────────────────────────

def _norm(text: Optional[str]) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


DRUG_FAMILIES: Dict[str, List[str]] = {
    "betalactamico_penicilina": [
        "penicilina", "amoxicilina", "ampicilina", "dicloxacilina",
        "piperacilina", "bencilpenicilina", "benzatinica", "clavulanico",
        "amoxicilina con acido clavulanico", "augmentin",
    ],
    "cefalosporina": [
        "cefalexina", "ceftriaxona", "cefotaxima", "cefuroxima", "cefixima",
    ],
    "aine": [
        "ibuprofeno", "ketorolaco", "naproxeno", "diclofenaco", "meloxicam",
        "piroxicam", "indometacina", "celecoxib", "etoricoxib", "nimesulida",
        "acido acetilsalicilico", "aspirina", "aas",
    ],
    "pirazolona": [
        "metamizol", "dipirona", "neo-melubrina",
    ],
    "sulfa": [
        "sulfametoxazol", "trimetoprima", "cotrimoxazol", "bactrim", "sulfadiazina",
    ],
    "fluoroquinolona": [
        "ciprofloxacino", "levofloxacino", "moxifloxacino", "ofloxacino",
    ],
    "macrolido": [
        "azitromicina", "claritromicina", "eritromicina",
    ],
    "anticoagulante": [
        "warfarina", "acenocumarol", "rivaroxaban", "apixaban", "dabigatran",
        "enoxaparina", "heparina",
    ],
    "antiagregante": [
        "clopidogrel", "ticagrelor", "prasugrel", "aspirina", "acido acetilsalicilico",
    ],
    "nitrato": [
        "isosorbida", "dinitrato de isosorbida", "mononitrato de isosorbida",
        "nitroglicerina",
    ],
    "pde5": [
        "sildenafil", "tadalafil", "vardenafil",
    ],
    "ieca_ara2": [
        "losartan", "telmisartan", "valsartan", "irbesartan", "candesartan",
        "enalapril", "captopril", "lisinopril", "ramipril",
    ],
    "ahorrador_k": [
        "espironolactona", "eplerenona", "amilorida",
    ],
    "sulfonilurea": [
        "glibenclamida", "glimepirida", "glipizida",
    ],
    "biguanida": [
        "metformina",
    ],
    "paracetamol": [
        "paracetamol", "acetaminofen", "tempra", "tylenol",
    ],
    "opioide": [
        "tramadol", "morfina", "buprenorfina", "oxicodona", "fentanilo", "codeina",
    ],
}

# Reacción cruzada directa o precaución entre grupos de alergia y fármacos
ALLERGY_CROSS_REACTIVITY: Dict[str, List[Tuple[str, str, str]]] = {
    # familia_alergia -> [(familia_prescrita, severidad, motivo)]
    "betalactamico_penicilina": [
        ("betalactamico_penicilina", "CRITICA", "Alergia directa a penicilinas / betalactámicos (riesgo de anafilaxia)."),
        ("cefalosporina", "ALTA", "Riesgo de reactividad cruzada con cefalosporinas (~2-5%). Evaluar alternativa no betalactámica."),
    ],
    "cefalosporina": [
        ("cefalosporina", "CRITICA", "Alergia documentada a cefalosporinas."),
        ("betalactamico_penicilina", "ALTA", "Posible reactividad cruzada con penicilinas."),
    ],
    "aine": [
        ("aine", "CRITICA", "Alergia/hipersensibilidad a AINEs (riesgo de broncoespasmo, angioedema o anafilaxia)."),
        ("pirazolona", "ALTA", "Precaución cruzada: las pirazolonas (metamizol) pueden desencadenar reacción en pacientes sensibles a AINEs."),
    ],
    "pirazolona": [
        ("pirazolona", "CRITICA", "Alergia documentada a metamizol / pirazolonas (riesgo de choque anafiláctico / agranulocitosis)."),
        ("aine", "ALTA", "Posible sensibilidad cruzada con otros AINEs."),
    ],
    "sulfa": [
        ("sulfa", "CRITICA", "Alergia documentada a sulfonamidas (riesgo de síndrome de Stevens-Johnson / anafilaxia)."),
    ],
    "fluoroquinolona": [
        ("fluoroquinolona", "CRITICA", "Alergia documentada a fluoroquinolonas."),
    ],
    "macrolido": [
        ("macrolido", "CRITICA", "Alergia documentada a macrólidos."),
    ],
    "paracetamol": [
        ("paracetamol", "CRITICA", "Alergia/intolerancia documentada a paracetamol."),
    ],
}


def _identify_drug_families(drug_name: str) -> List[str]:
    norm_name = _norm(drug_name)
    found = []
    for fam, terms in DRUG_FAMILIES.items():
        for t in terms:
            if re.search(r"\b" + re.escape(t) + r"\b", norm_name) or t in norm_name:
                if fam not in found:
                    found.append(fam)
                break
    return found


def _extract_inline_allergies(text: str) -> List[str]:
    """Detecta alergias mencionadas libremente dentro del dictado o nota."""
    if not text:
        return []
    norm_t = _norm(text)
    found: List[str] = []
    patterns = [
        r"(?:alergico|alergica|alergia(?:\s+conocida)?|hipersensible)\s+(?:a\s+(?:la|el|los|las)?\s*)([^.,;\n]+)",
        r"(?:no\s+puede\s+tomar|reaccion\s+(?:adversa|alergica)\s+a)\s+(?:la|el|los|las)?\s*([^.,;\n]+)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, norm_t):
            chunk = m.group(1).strip()
            # Cortar antes de conectores clínicos si la frase continúa
            chunk = re.split(r"\b(?:refiere|presenta|desde|hace|niega|con|y\s+se\s+le|por\s+lo\s+que)\b", chunk)[0].strip()
            for part in re.split(r"[,/]|\by\b", chunk):
                p = part.strip()
                if 3 <= len(p) <= 45 and p not in found:
                    found.append(p)
    return found


# ─────────────────────────────────────────────────────────────────
# PARSER DE SIGNOS VITALES & CALCULADORAS
# ─────────────────────────────────────────────────────────────────

def _parse_vitals(signos_vitales: List[str], texto: str) -> Dict[str, Any]:
    joined = " | ".join(str(v) for v in (signos_vitales or [])) + " | " + (texto or "")
    norm_j = _norm(joined)
    parsed: Dict[str, Any] = {}

    ta = re.search(r"(?:ta|tension arterial|presion(?:\s+arterial)?)\s*(?:de|:|=)?\s*(\d{2,3})\s*[/\-]\s*(\d{2,3})", norm_j)
    if not ta:
        # También detectar formato suelto tipo 160/100 mmHg
        ta = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\s*(?:mm\s*hg|mmhg)\b", norm_j)
    if ta:
        parsed["tas"] = int(ta.group(1))
        parsed["tad"] = int(ta.group(2))

    fc = re.search(r"(?:fc|frecuencia cardiaca|pulso)\s*(?:de|:|=)?\s*(\d{2,3})\b", norm_j)
    if not fc:
        fc = re.search(r"\b(\d{2,3})\s*(?:lpm|latidos por minuto)\b", norm_j)
    if fc:
        parsed["fc"] = int(fc.group(1))

    fr = re.search(r"(?:fr|frecuencia respiratoria)\s*(?:de|:|=)?\s*(\d{1,2})\b", norm_j)
    if not fr:
        fr = re.search(r"\b(\d{1,2})\s*(?:rpm|respiraciones por minuto)\b", norm_j)
    if fr:
        parsed["fr"] = int(fr.group(1))

    temp = re.search(r"(?:temp(?:eratura)?)\s*(?:de|:|=)?\s*(\d{2}(?:[.,]\d)?)", norm_j)
    if not temp:
        temp = re.search(r"\b(\d{2}(?:[.,]\d)?)\s*(?:°c|grados)\b", norm_j)
    if temp:
        parsed["temp"] = float(temp.group(1).replace(",", "."))

    spo2 = re.search(r"(?:spo2|sato2|saturacion(?:\s+de\s+oxigeno)?|oxigenacion)\s*(?:de|:|=)?\s*(\d{2,3})\s*%?", norm_j)
    if spo2:
        val = int(spo2.group(1))
        if 40 <= val <= 100:
            parsed["spo2"] = val

    glu = re.search(r"(?:glucosa|glucemia|dextrostix)(?:\s+capilar)?\s*(?:de|:|=)?\s*(\d{2,4})\b", norm_j)
    if glu:
        parsed["glucosa"] = int(glu.group(1))

    return parsed


def _compute_bmi(patient_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not patient_data:
        return None
    peso = patient_data.get("peso_kg")
    altura = patient_data.get("altura_cm")
    try:
        if peso and altura and float(altura) > 0:
            m = float(altura) / 100.0
            imc = round(float(peso) / (m * m), 1)
            cat = (
                "Bajo peso" if imc < 18.5 else
                "Normal" if imc < 25 else
                "Sobrepeso" if imc < 30 else
                "Obesidad grado I" if imc < 35 else
                "Obesidad grado II" if imc < 40 else
                "Obesidad grado III"
            )
            return {"valor": imc, "categoria": cat, "peso_kg": float(peso), "altura_cm": float(altura)}
    except (TypeError, ValueError):
        pass
    return None


def _compute_news2(vitals: Dict[str, Any], mental_altered: bool) -> int:
    score = 0
    fr = vitals.get("fr")
    if fr is not None:
        if fr <= 8 or fr >= 25:
            score += 3
        elif 21 <= fr <= 24:
            score += 2
        elif 9 <= fr <= 11:
            score += 1

    spo2 = vitals.get("spo2")
    if spo2 is not None:
        if spo2 <= 91:
            score += 3
        elif 92 <= spo2 <= 93:
            score += 2
        elif 94 <= spo2 <= 95:
            score += 1

    tas = vitals.get("tas")
    if tas is not None:
        if tas <= 90 or tas >= 220:
            score += 3
        elif 91 <= tas <= 100:
            score += 2
        elif 101 <= tas <= 110:
            score += 1

    fc = vitals.get("fc")
    if fc is not None:
        if fc <= 40 or fc >= 131:
            score += 3
        elif 111 <= fc <= 130:
            score += 2
        elif (41 <= fc <= 50) or (91 <= fc <= 110):
            score += 1

    temp = vitals.get("temp")
    if temp is not None:
        if temp <= 35.0:
            score += 3
        elif temp >= 39.1:
            score += 2
        elif (35.1 <= temp <= 36.0) or (38.1 <= temp <= 39.0):
            score += 1

    if mental_altered:
        score += 3

    return score


# ─────────────────────────────────────────────────────────────────
# TRIAJE Y BANDERAS ROJAS (CÓDIGOS DE EMERGENCIA)
# ─────────────────────────────────────────────────────────────────

def _evaluate_triage_and_red_flags(
    vitals: Dict[str, Any],
    sintomas: List[str],
    diags: List[str],
    texto: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], int]:
    norm_all = _norm(" ".join(sintomas + diags) + " " + (texto or ""))

    mental_altered = bool(re.search(
        r"\b(inconsciente|letargia|estupor|somnolencia|confusion|confuso|desorientado|coma|glasgow\s*<\s*15|perdida del estado de alerta)\b",
        norm_all,
    ))
    news2 = _compute_news2(vitals, mental_altered)

    # qSOFA (0..3)
    qsofa = 0
    if vitals.get("fr") is not None and vitals["fr"] >= 22:
        qsofa += 1
    if vitals.get("tas") is not None and vitals["tas"] <= 100:
        qsofa += 1
    if mental_altered:
        qsofa += 1

    red_flags: List[Dict[str, Any]] = []
    reasons: List[str] = []
    severity_rank = 4  # 1=ROJO, 2=NARANJA, 3=AMARILLO, 4=VERDE

    def _elevate(rank: int, reason: str):
        nonlocal severity_rank
        if rank < severity_rank:
            severity_rank = rank
        if reason not in reasons:
            reasons.append(reason)

    # 1. Signos vitales críticos
    spo2 = vitals.get("spo2")
    if spo2 is not None:
        if spo2 < 90:
            _elevate(1, f"Hipoxemia severa (SpO2 {spo2}% < 90%)")
            red_flags.append({
                "codigo": "INSUFICIENCIA RESPIRATORIA",
                "severidad": "CRITICA",
                "titulo": f"Desaturación grave de oxígeno (SpO2 {spo2}%)",
                "accion_inmediata": "Oxigenoterapia suplementaria inmediata, valorar vía aérea, gasometría arterial y monitoreo continuo.",
            })
        elif spo2 <= 93:
            _elevate(2, f"Desaturación moderada (SpO2 {spo2}%)")

    tas = vitals.get("tas")
    tad = vitals.get("tad")
    if tas is not None:
        if tas < 90:
            _elevate(1, f"Hipotensión / probable estado de choque (TA {tas}/{tad or '?'} mmHg)")
        elif tas >= 180 or (tad is not None and tad >= 120):
            _elevate(2, f"Crisis hipertensiva (TA {tas}/{tad or '?'} mmHg)")
            red_flags.append({
                "codigo": "CRISIS HIPERTENSIVA",
                "severidad": "ALTA",
                "titulo": f"Presión arterial en rango de crisis ({tas}/{tad or '?'} mmHg)",
                "accion_inmediata": "Descartar daño a órgano blanco (cefalea intensa, dolor torácico, déficit focal, disnea) y ECG.",
            })

    fc = vitals.get("fc")
    if fc is not None:
        if fc >= 130 or fc <= 40:
            _elevate(1, f"Frecuencia cardíaca crítica ({fc} lpm)")
        elif fc >= 110:
            _elevate(2, f"Taquicardia significativa ({fc} lpm)")

    glu = vitals.get("glucosa")
    if glu is not None:
        if glu < 60:
            _elevate(1, f"Hipoglucemia crítica ({glu} mg/dL)")
            red_flags.append({
                "codigo": "HIPOGLUCEMIA SEVERA",
                "severidad": "CRITICA",
                "titulo": f"Glucemia crítica baja ({glu} mg/dL)",
                "accion_inmediata": "Administrar solución glucosada al 50% IV (o glucosa oral si alerta y tolera vía oral) y revalorar en 15 min.",
            })
        elif glu >= 300:
            _elevate(2, f"Hiperglucemia severa ({glu} mg/dL)")
            red_flags.append({
                "codigo": "DESCOMPENSACION METABOLICA",
                "severidad": "ALTA",
                "titulo": f"Hiperglucemia severa ({glu} mg/dL)",
                "accion_inmediata": "Descartar cetoacidosis diabética / estado hiperosmolar (cetonas, gasometría, electrolitos e hidratación).",
            })

    # 2. Código Infarto (IAM / SCA)
    has_chest_pain = bool(re.search(r"dolor\s+(?:en\s+(?:el\s+)?pecho|toracico|precordial|opresivo)", norm_all))
    has_acs_companion = bool(re.search(r"irradia|brazo\s+izquierdo|mandibula|diaforesis|sudoracion\s+fria|falta\s+de\s+aire|disnea|opresion", norm_all))
    if has_chest_pain and (has_acs_companion or (tas is not None and tas < 100) or (fc is not None and fc > 100)):
        _elevate(1, "Sospecha de Síndrome Coronario Agudo (Código Infarto)")
        red_flags.append({
            "codigo": "CODIGO INFARTO",
            "severidad": "CRITICA",
            "titulo": "Sospecha de Síndrome Coronario Agudo / IAM",
            "accion_inmediata": "Electrocardiograma de 12 derivaciones en <10 minutos, acceso venoso, troponinas y monitorización continua.",
        })
    elif has_chest_pain:
        _elevate(2, "Dolor torácico agudo por descartar causa coronaria")

    # 3. Código Cerebro (EVC / FAST)
    if re.search(r"asimetria\s+facial|desviacion\s+de\s+comisura|disartria|dificultad\s+para\s+hablar|hemiparesia|debilidad\s+subita|paralisis\s+de\s+(?:brazo|pierna|mitad)", norm_all):
        _elevate(1, "Déficit neurológico agudo (Código Cerebro / FAST)")
        red_flags.append({
            "codigo": "CODIGO CEREBRO (EVC)",
            "severidad": "CRITICA",
            "titulo": "Déficit neurológico focal súbito",
            "accion_inmediata": "Registrar hora exacta de inicio (ventana <4.5h), glucometría capilar inmediata y TAC de cráneo urgente.",
        })

    # 4. Código Dengue con Signos de Alarma (Yucatán / México)
    has_fever_or_dengue = bool(re.search(r"dengue|fiebre|febril|38\.\d|39\.\d|40\.\d|retroocular|artralgias|mialgias", norm_all))
    dengue_alarm_signs = re.findall(
        r"(dolor\s+abdominal\s+intenso|dolor\s+abdominal\s+continuo|vomito\s+persistente|vomitos\s+persistentes|sangrado\s+de\s+encias|epistaxis|gingivorragia|petequias|lipotimia|plaquetopenia|plaquetas\s+bajas|derrame\s+pleural|ascitis)",
        norm_all,
    )
    if has_fever_or_dengue and (dengue_alarm_signs or "dengue grave" in norm_all):
        _elevate(2, f"Dengue / síndrome febril con signos de alarma ({', '.join(set(dengue_alarm_signs)) or 'criterio clínico'})")
        red_flags.append({
            "codigo": "DENGUE CON SIGNOS DE ALARMA",
            "severidad": "CRITICA" if (tas and tas < 90) or "sangrado" in norm_all else "ALTA",
            "titulo": "Sospecha de Dengue con Signos de Alarma",
            "accion_inmediata": "Hidratación parenteral inmediata (Solución Hartmann/Salina), biometría hemática urgente (hematocrito y plaquetas). EVITAR ESTRICTAMENTE AINEs y Aspirina.",
        })

    # 5. Código Sepsis (qSOFA >= 2 o NEWS2 >= 7)
    if qsofa >= 2 or (has_fever_or_dengue and news2 >= 6):
        _elevate(1, f"Riesgo alto de Sepsis (qSOFA {qsofa}/3, NEWS2 {news2})")
        red_flags.append({
            "codigo": "CODIGO SEPSIS",
            "severidad": "CRITICA",
            "titulo": f"Criterios de alerta por probable Sepsis (qSOFA {qsofa}/3)",
            "accion_inmediata": "Paquete 1ra hora: lactato sérico, hemocultivos, antibiótico empírico temprano y cargas de cristaloides si hipotensión.",
        })

    if news2 >= 7 and severity_rank > 1:
        _elevate(1, f"Escala NEWS2 de alto riesgo ({news2} puntos)")
    elif news2 >= 5 and severity_rank > 2:
        _elevate(2, f"Escala NEWS2 de riesgo intermedio-alto ({news2} puntos)")
    elif sintomas and severity_rank > 3:
        _elevate(3, "Valoración médica prioritaria según sintomatología aguda")

    triage_map = {
        1: ("ROJO", 1, "Resucitación / Riesgo Vital Inmediato", "Inmediato (0 min)"),
        2: ("NARANJA", 2, "Emergencia / Alta Prioridad", "≤ 10 minutos"),
        3: ("AMARILLO", 3, "Urgencia Calificada", "≤ 30 minutos"),
        4: ("VERDE", 4, "Urgencia Menor / Consulta Externa", "≤ 60 minutos"),
    }
    nivel, esi, etiqueta, espera = triage_map[severity_rank]

    triaje = {
        "nivel": nivel,
        "codigo_esi": esi,
        "etiqueta": etiqueta,
        "tiempo_espera_max": espera,
        "puntaje_news2": news2,
        "puntaje_qsofa": qsofa,
        "criterios_activados": reasons or ["Signos y síntomas sin criterios inmediatos de alarma vital."],
    }
    return triaje, red_flags, qsofa


# ─────────────────────────────────────────────────────────────────
# ESCUDO FARMACOLÓGICO (ALERGIAS, INTERACCIONES, DOSIS)
# ─────────────────────────────────────────────────────────────────

def _extract_mg_value(dose_str: Optional[str]) -> Optional[float]:
    if not dose_str:
        return None
    norm_d = _norm(dose_str)
    g = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|gr|gramos)\b", norm_d)
    if g:
        return float(g.group(1)) * 1000.0
    mg = re.search(r"(\d+(?:\.\d+)?)\s*(?:mg|miligramos)\b", norm_d)
    if mg:
        return float(mg.group(1))
    return None


def _extract_doses_per_day(freq_str: Optional[str]) -> Optional[float]:
    if not freq_str:
        return None
    norm_f = _norm(freq_str)
    m = re.search(r"cada\s+(\d{1,2})\s*(?:h|hs|hrs|horas)\b", norm_f)
    if m:
        hours = float(m.group(1))
        if hours > 0:
            return 24.0 / hours
    if "una vez al dia" in norm_f or "cada 24" in norm_f:
        return 1.0
    if "dos veces al dia" in norm_f:
        return 2.0
    if "tres veces al dia" in norm_f:
        return 3.0
    return None


def _evaluate_medications_safety(
    meds: List[Any],
    patient_data: Optional[Dict[str, Any]],
    texto: str,
    sintomas: List[str],
    diags: List[str],
    red_flags: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    if not meds:
        return alerts

    norm_all = _norm(" ".join(sintomas + diags) + " " + (texto or ""))
    antecedentes_text = _norm(" ".join(
        f"{a.get('tipo', '')} {a.get('descripcion', '')}"
        for a in (patient_data.get("antecedentes", []) if patient_data else [])
        if isinstance(a, dict)
    ))
    clinical_context = f"{norm_all} {antecedentes_text}"

    # 1. Reunir alergias desde BD + texto del dictado
    allergy_sources: List[Tuple[str, str]] = []
    if patient_data and isinstance(patient_data.get("alergias"), list):
        for al in patient_data["alergias"]:
            if isinstance(al, dict):
                subst = al.get("sustancia") or al.get("descripcion")
                if subst:
                    allergy_sources.append((subst, f"Expediente ({al.get('severidad', 'Registrada')})"))
            elif isinstance(al, str):
                allergy_sources.append((al, "Expediente"))

    for inline_al in _extract_inline_allergies(texto):
        allergy_sources.append((inline_al, "Mencionada en dictado"))

    # Mapear familias alergénicas del paciente
    patient_allergy_families: Dict[str, Tuple[str, str]] = {}
    for subst, src in allergy_sources:
        fams = _identify_drug_families(subst)
        for f in fams:
            patient_allergy_families[f] = (subst, src)

    # Identificar medicamentos prescritos y sus familias
    med_entries: List[Dict[str, Any]] = []
    for m in meds:
        if isinstance(m, dict):
            name = str(m.get("nombre") or "").strip()
            med_entries.append({
                "nombre": name,
                "dosis": m.get("dosis"),
                "via": m.get("via"),
                "periodicidad": m.get("periodicidad"),
                "duracion": m.get("duracion"),
                "familias": _identify_drug_families(name),
            })
        elif isinstance(m, str) and m.strip():
            med_entries.append({
                "nombre": m.strip(),
                "dosis": None,
                "via": None,
                "periodicidad": None,
                "duracion": None,
                "familias": _identify_drug_families(m),
            })

    # 2. Cruce Alergia vs Medicamento (texto directo + reactividad cruzada)
    for me in med_entries:
        norm_med = _norm(me["nombre"])
        matched_crit = False
        for subst, src in allergy_sources:
            norm_sub = _norm(subst)
            if norm_sub and (norm_sub in norm_med or norm_med in norm_sub):
                alerts.append({
                    "tipo": "ALERGIA_DIRECTA",
                    "severidad": "CRITICA",
                    "medicamento": me["nombre"],
                    "titulo": f"Contraindicación por alergia a {subst}",
                    "detalle": f"El paciente tiene alergia registrada a '{subst}' ({src}). No administrar {me['nombre']}.",
                    "recomendacion": "Suspender prescripción y seleccionar alternativa terapéutica de distinta familia farmacológica.",
                })
                matched_crit = True
                break

        if not matched_crit:
            for p_fam, (subst, src) in patient_allergy_families.items():
                for target_fam, sev, reason in ALLERGY_CROSS_REACTIVITY.get(p_fam, []):
                    if target_fam in me["familias"]:
                        alerts.append({
                            "tipo": "ALERGIA_CRUZADA",
                            "severidad": sev,
                            "medicamento": me["nombre"],
                            "titulo": f"Riesgo de reacción cruzada con alergia a {subst}",
                            "detalle": f"{reason} (Fuente: {src}).",
                            "recomendacion": "Evitar medicamento y sustituir por opción segura sin reactividad cruzada.",
                        })
                        break

    # 3. Contraindicación Fármaco vs Condición Clínica (Dengue, Renal, Úlcera, Edad)
    is_dengue_or_bleeding = any(rf["codigo"].startswith("DENGUE") for rf in red_flags) or bool(
        re.search(r"\b(dengue|hemorragia|sangrado|ulcera gastrica|melena|hematemesis)\b", clinical_context)
    )
    has_renal_disease = bool(re.search(r"\b(insuficiencia renal|enfermedad renal|erc|nefropatia|dialisis)\b", clinical_context))

    edad = None
    if patient_data and patient_data.get("edad") is not None:
        try:
            edad = float(re.findall(r"\d+", str(patient_data["edad"]))[0])
        except Exception:
            edad = None

    peso_kg = None
    if patient_data and patient_data.get("peso_kg") is not None:
        try:
            peso_kg = float(patient_data["peso_kg"])
        except Exception:
            peso_kg = None

    for me in med_entries:
        fams = me["familias"]
        if is_dengue_or_bleeding and ("aine" in fams or "anticoagulante" in fams):
            alerts.append({
                "tipo": "CONTRAINDICACION_CLINICA",
                "severidad": "CRITICA",
                "medicamento": me["nombre"],
                "titulo": f"Contraindicado en sospecha de Dengue / riesgo hemorrágico",
                "detalle": f"{me['nombre']} pertenece a AINEs/anticoagulantes e incrementa gravemente el riesgo de hemorragia y choque en dengue o sangrado activo.",
                "recomendacion": "Sustituir manejo sintomático de fiebre/dolor por Paracetamol en dosis seguras e hidratación.",
            })

        if has_renal_disease and "aine" in fams:
            alerts.append({
                "tipo": "CONTRAINDICACION_RENAL",
                "severidad": "ALTA",
                "medicamento": me["nombre"],
                "titulo": "Riesgo nefrotóxico en enfermedad renal",
                "detalle": f"Uso de AINE ({me['nombre']}) con antecedente/sospecha de compromiso renal.",
                "recomendacion": "Evitar AINEs o valorar alternativa no nefrotóxica.",
            })

        if has_renal_disease and "biguanida" in fams:
            alerts.append({
                "tipo": "CONTRAINDICACION_RENAL",
                "severidad": "ALTA",
                "medicamento": me["nombre"],
                "titulo": "Precaución con Metformina en falla renal",
                "detalle": "Verificar TFG (CKD-EPI); contraindicada si TFG < 30 mL/min por riesgo de acidosis láctica.",
                "recomendacion": "Confirmar creatinina/TFG antes de continuar dosis plena.",
            })

        if edad is not None and edad < 18 and ("aspirina" in _norm(me["nombre"]) or "acetilsalicilico" in _norm(me["nombre"])) and "fiebre" in clinical_context:
            alerts.append({
                "tipo": "RIESGO_PEDIATRICO",
                "severidad": "CRITICA",
                "medicamento": me["nombre"],
                "titulo": "Riesgo de Síndrome de Reye en menor de 18 años",
                "detalle": "El ácido acetilsalicílico está contraindicado en cuadros febriles virales pediátricos.",
                "recomendacion": "Suspender aspirina y usar paracetamol calculado por peso.",
            })

        if edad is not None and edad >= 65 and "sulfonilurea" in fams:
            alerts.append({
                "tipo": "RIESGO_GERIATRICO",
                "severidad": "MODERADA",
                "medicamento": me["nombre"],
                "titulo": "Alto riesgo de hipoglucemia prolongada en adulto mayor",
                "detalle": f"{me['nombre']} (sulfonilurea de vida media larga) en paciente de {int(edad)} años.",
                "recomendacion": "Vigilar glucemia capilar o considerar opciones con menor riesgo hipoglucémico.",
            })

        # 4. Guardrails de Dosis (Paracetamol y Ketorolaco)
        mg = _extract_mg_value(me["dosis"])
        per_day = _extract_doses_per_day(me["periodicidad"])
        if mg and per_day and "paracetamol" in fams:
            daily_mg = mg * per_day
            if daily_mg > 4000:
                alerts.append({
                    "tipo": "SOBREDOSIS",
                    "severidad": "CRITICA",
                    "medicamento": me["nombre"],
                    "titulo": f"Dosis diaria hepatotóxica de Paracetamol ({int(daily_mg)} mg/día)",
                    "detalle": "Supera el límite máximo recomendado de 4,000 mg/día en adultos.",
                    "recomendacion": "Reducir dosis o espaciar periodicidad (máx 4g/24h en adultos sin hepatopatía).",
                })
            elif peso_kg and edad is not None and edad < 15:
                max_ped_day = 75.0 * peso_kg
                if daily_mg > max_ped_day:
                    alerts.append({
                        "tipo": "SOBREDOSIS_PEDIATRICA",
                        "severidad": "CRITICA",
                        "medicamento": me["nombre"],
                        "titulo": f"Exceso de dosis pediátrica por peso ({peso_kg} kg)",
                        "detalle": f"Prescrito {int(daily_mg)} mg/día vs máximo 75 mg/kg/día ({int(max_ped_day)} mg/día).",
                        "recomendacion": f"Ajustar a 10–15 mg/kg/dosis ({round(15*peso_kg)} mg máx por toma).",
                    })

        if "ketorolaco" in _norm(me["nombre"]) and me["duracion"]:
            dur_m = re.search(r"(\d+)\s*d[ií]as?", _norm(me["duracion"]))
            if dur_m and int(dur_m.group(1)) > 5:
                alerts.append({
                    "tipo": "DURACION_EXCEDIDA",
                    "severidad": "ALTA",
                    "medicamento": me["nombre"],
                    "titulo": f"Ketorolaco prescrito por más de 5 días ({dur_m.group(1)} días)",
                    "detalle": "El uso de ketorolaco >5 días eleva significativamente el riesgo de hemorragia digestiva y falla renal aguda.",
                    "recomendacion": "Limitar ketorolaco a máximo 5 días y cambiar a analgésico de menor riesgo.",
                })

    # 5. Interacciones Fármaco–Fármaco (DDI) y Duplicidad
    all_fams = set()
    aines_list = []
    for me in med_entries:
        all_fams.update(me["familias"])
        if "aine" in me["familias"]:
            aines_list.append(me["nombre"])

    if len(aines_list) >= 2:
        alerts.append({
            "tipo": "DUPLICIDAD_TERAPEUTICA",
            "severidad": "ALTA",
            "medicamento": " + ".join(aines_list),
            "titulo": "Duplicidad terapéutica de AINEs",
            "detalle": f"Se prescribieron simultáneamente múltiples AINEs ({', '.join(aines_list)}), sumando toxicidad gástrica y renal sin mayor analgesia.",
            "recomendacion": "Conservar un solo AINE y combinar con analgésico de distinto mecanismo si es necesario.",
        })

    if "anticoagulante" in all_fams and "aine" in all_fams:
        alerts.append({
            "tipo": "INTERACCION_DDI",
            "severidad": "CRITICA",
            "medicamento": "Anticoagulante + AINE",
            "titulo": "Interacción mayor: riesgo grave de hemorragia",
            "detalle": "La combinación de anticoagulante con AINE multiplica el riesgo de sangrado digestivo e intracraneal.",
            "recomendacion": "Evitar AINEs; usar Paracetamol o gastroprotección solo bajo estricta valoración.",
        })

    if "nitrato" in all_fams and "pde5" in all_fams:
        alerts.append({
            "tipo": "INTERACCION_DDI",
            "severidad": "CRITICA",
            "medicamento": "Nitrato + Inhibidor PDE5",
            "titulo": "Interacción letal: hipotensión refractaria",
            "detalle": "Combinar nitratos con sildenafil/tadalafil provoca vasodilatación severa e hipotensión potencialmente mortal.",
            "recomendacion": "Contraindicación absoluta. Suspender uno de los dos inmediatamente.",
        })

    if "ieca_ara2" in all_fams and "ahorrador_k" in all_fams:
        alerts.append({
            "tipo": "INTERACCION_DDI",
            "severidad": "MODERADA",
            "medicamento": "IECA/ARA-II + Espironolactona",
            "titulo": "Riesgo de hiperkalemia",
            "detalle": "La asociación eleva potasio sérico, especialmente en enfermedad renal o adultos mayores.",
            "recomendacion": "Monitorizar electrolitos séricos (K+) y creatinina.",
        })

    return alerts


# ─────────────────────────────────────────────────────────────────
# EVIDENCIA VINCULADA Y SIGNOS DE ALARMA EN CASA
# ─────────────────────────────────────────────────────────────────

def extract_linked_evidence(
    texto_original: str,
    entities: Dict[str, Any],
    codigos_cie10: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """
    Vincula cada entidad clínica o código CIE-10 con la oración literal del
    dictado original para que el médico audite la fuente al instante.
    """
    if not texto_original or not texto_original.strip():
        return []

    sentences = [s.strip() for s in re.split(r"(?<=[.!?\n;])\s+|\n+", texto_original.strip()) if s.strip()]
    if not sentences:
        sentences = [texto_original.strip()]

    evidence: List[Dict[str, str]] = []
    seen_keys = set()

    def _find_quote(query: str) -> str:
        nq = _norm(query)
        words = [w for w in re.findall(r"[a-z0-9]{4,}", nq)]
        best_sent = ""
        best_hits = 0
        for sent in sentences:
            ns = _norm(sent)
            if nq and nq in ns:
                return sent
            hits = sum(1 for w in words if w in ns)
            if hits > best_hits:
                best_hits = hits
                best_sent = sent
        return best_sent if best_hits > 0 else sentences[0]

    for sint in entities.get("sintomas_referidos", [])[:6]:
        key = ("Síntoma", str(sint))
        if key not in seen_keys:
            seen_keys.add(key)
            evidence.append({
                "categoria": "Síntoma",
                "entidad": str(sint),
                "cita_textual": _find_quote(str(sint)),
            })

    for diag in entities.get("diagnosticos_tentativos", [])[:5]:
        key = ("Diagnóstico", str(diag))
        if key not in seen_keys:
            seen_keys.add(key)
            evidence.append({
                "categoria": "Diagnóstico",
                "entidad": str(diag),
                "cita_textual": _find_quote(str(diag)),
            })

    for sv in entities.get("signos_vitales", [])[:6]:
        key = ("Signo Vital", str(sv))
        if key not in seen_keys:
            seen_keys.add(key)
            evidence.append({
                "categoria": "Signo Vital",
                "entidad": str(sv),
                "cita_textual": _find_quote(str(sv)),
            })

    for med in entities.get("medicamentos", [])[:6]:
        name = med.get("nombre", "") if isinstance(med, dict) else str(med)
        if not name:
            continue
        key = ("Medicamento", name)
        if key not in seen_keys:
            seen_keys.add(key)
            evidence.append({
                "categoria": "Medicamento",
                "entidad": name,
                "cita_textual": _find_quote(name),
            })

    return evidence


def _build_home_warning_signs(
    red_flags: List[Dict[str, Any]],
    sintomas: List[str],
    diags: List[str],
    texto: str,
) -> List[str]:
    """
    Instrucciones claras para el paciente en casa ("Cuándo acudir a Urgencias").
    """
    norm_all = _norm(" ".join(sintomas + diags) + " " + (texto or ""))
    warnings: List[str] = []

    if "dengue" in norm_all or "fiebre" in norm_all:
        warnings.append("Dolor abdominal intenso y continuo, vómito que no cede o incapacidad para tomar líquidos.")
        warnings.append("Sangrado de encías, nariz, puntos rojos en piel (petequias), mareo al levantarse o somnolencia extrema.")

    if re.search(r"pecho|presion|hipertension|cardiac|infarto", norm_all):
        warnings.append("Dolor o presión en el pecho que dura >5 minutos o se corre al brazo, cuello, espalda o mandíbula.")

    if re.search(r"tos|disnea|aire|pulmon|asma|respirator", norm_all):
        warnings.append("Falta de aire en reposo, hundimiento de costillas, coloración azulada en labios/uñas o fiebre persistente >3 días.")

    if re.search(r"diabetes|glucosa|azucar", norm_all):
        warnings.append("Sudoración fría, temblor, confusión (posible bajón de azúcar <70 mg/dL) o respiración agitada con aliento afrutado.")

    if not warnings:
        warnings.append("Fiebre alta >38.5 °C que no cede, dificultad para respirar, desmayo, confusión o empeoramiento rápido de los síntomas.")
        warnings.append("Reacción alérgica a medicamentos (ronchas, hinchazón de labios/párpados o cierre de garganta).")

    return warnings


# ─────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def evaluate_clinical_safety(
    entities: Dict[str, Any],
    patient_data: Optional[Dict[str, Any]] = None,
    texto_original: str = "",
) -> Dict[str, Any]:
    """
    Evalúa integralmente la seguridad clínica de una consulta o borrador.
    """
    sintomas = [str(s) for s in (entities.get("sintomas_referidos") or [])]
    diags = [str(d) for d in (entities.get("diagnosticos_tentativos") or [])]
    signos = [str(v) for v in (entities.get("signos_vitales") or [])]
    meds = entities.get("medicamentos") or []

    parsed_vitals = _parse_vitals(signos, texto_original)
    bmi = _compute_bmi(patient_data)
    triaje, red_flags, qsofa = _evaluate_triage_and_red_flags(parsed_vitals, sintomas, diags, texto_original)
    med_alerts = _evaluate_medications_safety(meds, patient_data, texto_original, sintomas, diags, red_flags)
    home_warnings = _build_home_warning_signs(red_flags, sintomas, diags, texto_original)

    has_critical_med_block = any(a.get("severidad") == "CRITICA" for a in med_alerts)
    total_alerts = len(red_flags) + len(med_alerts)

    return {
        "triaje": triaje,
        "banderas_rojas": red_flags,
        "alertas_medicamentos": med_alerts,
        "signos_alarma_casa": home_warnings,
        "calculos_clinicos": {
            "signos_vitales_parseados": parsed_vitals,
            "imc": bmi,
            "qsofa": qsofa,
            "news2": triaje["puntaje_news2"],
        },
        "bloqueo_seguridad": has_critical_med_block,
        "total_alertas": total_alerts,
    }
