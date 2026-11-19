"""
app/core/hybrid_ai_orchestrator.py — Orquestador Agéntico Híbrido Evolucionado ("Dr. Oso · Pulso")
================================================================================================
Diseñado específicamente para NVIDIA RTX 4050 (6 GB VRAM) + AMD Ryzen 7 7445HS + 16 GB RAM:
  1. IntentRouter: Clasificación en tiempo real en
       - AGENTIC_TOOL        (Resumen paciente, SOAP, Transferencia, Búsqueda)
       - CLINICAL_NORMATIVE  (Consultas médicas, fármacos, triaje, GPC, NOM-004)
       - UNIVERSAL_GENERAL   (Programación, física, matemáticas, redacción, gestión)
  2. HybridClinicalRetriever: Búsqueda híbrida BM25 (léxico exacto) + ChromaDB (`clinical_knowledge_gpc_nom004`
     y `cie10_mexico_2024_diagnosticos`) fusionada mediante Reciprocal Rank Fusion (RRF).
  3. IdentityGuardrail: Aislamiento estricto XML (<ASSISTANT_IDENTITY> vs <PATIENT_RECORD_READONLY_DO_NOT_IMPERSONATE>)
     y filtro anti-suplantación para eliminar alucinaciones de identidad ("Me llamo <paciente>").
  4. SlidingWindowContext: Ventana deslizante (últimos 6-8 turnos, máx. 8192 tokens) para >55 tok/s.
"""

from __future__ import annotations

import math
import re
import threading
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from app.core.clinical_generative_engine import generate_conversational_response
from app.core.evolutionary_learning import _compute_text_embedding_384
from app.db.chroma_store import get_collection

_KNOWLEDGE_COLLECTION = "clinical_knowledge_gpc_nom004"
_SEED_LOCK = threading.Lock()
_SEEDED = False


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


# ---------------------------------------------------------------------------
# CORPUS CLÍNICO MEXICANO CURADO (GPC + CUADRO BÁSICO + NOM-004 + INTERACCIONES)
# ---------------------------------------------------------------------------

_CLINICAL_CORPUS: List[Dict[str, str]] = [
    {
        "id": "nom004_soap",
        "title": "NOM-004-SSA3-2012 · Estructura de Nota Médica de Evolución (SOAP)",
        "source": "NOM-004-SSA3-2012",
        "content": (
            "Toda nota de evolución médica en el expediente clínico debe contener: fecha y hora, "
            "evolución y actualización del cuadro clínico (Subjetivo), signos vitales y resultados relevantes "
            "de exploración física y estudios (Objetivo), diagnósticos o problemas clínicos codificados con CIE-10 "
            "(Análisis), pronóstico y plan terapéutico con nombre genérico DCI, dosis, vía, periodicidad y duración (Plan). "
            "Los datos faltantes no observados jamás deben inventarse; deben consignarse como [PENDIENTE]."
        ),
    },
    {
        "id": "nom024_privacy",
        "title": "NOM-024-SSA3-2012 & LFPDPPP · Interoperabilidad y Confidencialidad Local",
        "source": "NOM-024-SSA3-2012",
        "content": (
            "El expediente clínico electrónico garantiza confidencialidad mediante cifrado en reposo, "
            "bitácora inmutable de auditoría con operador, fecha y acción sin exponer texto clínico sensible, "
            "y procesamiento Zero-Cloud sin transferencia a servidores externos no autorizados."
        ),
    },
    {
        "id": "gpc_crisis_hipertensiva",
        "title": "GPC México · Crisis Hipertensiva (Urgencia vs Emergencia >= 180/120 mmHg)",
        "source": "GPC CENETEC SSA-155-08 / AHA",
        "content": (
            "TA >= 180/120 mmHg constituye Crisis Hipertensiva. Si hay daño agudo a órgano diana "
            "(encefalopatía hipertensiva, EVC, síndrome coronario agudo, edema agudo pulmonar, disección aórtica "
            "o lesión renal aguda) es Emergencia Hipertensiva: requiere monitoreo continuo y antihipertensivos IV "
            "(Labetalol, Nicardipino o Nitroprusiato), reduciendo la PAM <= 20-25% en la primera hora. "
            "Sin daño a órgano diana es Urgencia Hipertensiva: reducción gradual en 24-48 h vía oral (Captopril, Amlodipino, Losartán). "
            "CIE-10: I10X / I16."
        ),
    },
    {
        "id": "gpc_sepsis_qsofa_news2",
        "title": "Protocolo Sepsis y Deterioro Agudo · Escalas qSOFA y NEWS2",
        "source": "Surviving Sepsis Campaign / GPC",
        "content": (
            "qSOFA positivo (>= 2 puntos de: FR >= 22 rpm, PAS <= 100 mmHg, Glasgow < 15 / alteración mental) "
            "indica alto riesgo de sepsis y mortalidad hospitalaria. NEWS2 >= 7 exige respuesta médica de emergencia "
            "inmediata. Medidas de la primera hora: lactato sérico, hemocultivos antes de antibiótico de amplio espectro, "
            "cristaloides isotónicos 30 mL/kg si hipotensión o lactato >= 4 mmol/L, y vasopresor (norepinefrina) si PAM < 65 mmHg."
        ),
    },
    {
        "id": "gpc_dengue_oms",
        "title": "GPC Dengue México & OMS · Clasificación y Contraindicación de AINEs",
        "source": "GPC SSA-151-08 / OMS Dengue",
        "content": (
            "Dengue (CIE-10 A970 sin alarma, A971 con signos de alarma, A972 grave). Signos de alarma: dolor abdominal "
            "intenso y continuo, vómitos persistentes, acumulación de líquidos, sangrado de mucosas, letargia o irritabilidad, "
            "hepatomegalia > 2 cm y aumento progresivo del hematocrito con caída rápida de plaquetas (<100,000). "
            "Analgésico/antipirético de elección: Paracetamol. CONTRAINDICADOS AINEs (Ketorolaco, Ibuprofeno, Naproxeno, Diclofenaco), "
            "Metamizol y Ácido Acetilsalicílico por riesgo hemorrágico grave."
        ),
    },
    {
        "id": "gpc_diabetes_dm2_cad",
        "title": "GPC Diabetes Mellitus Tipo 2 (E11) y Cetoacidosis Diabética",
        "source": "GPC IMSS-718-14 / ADA",
        "content": (
            "Primera línea farmacológica en DM2: Metformina 500-850 mg VO con alimentos (titular hasta 2000 mg/día). "
            "Ajuste renal obligatorio: contraindicada si TFG < 30 mL/min/1.73m2 por riesgo de acidosis láctica; reducir dosis si TFG 30-45. "
            "Cetoacidosis Diabética (E111): glucosa > 250 mg/dL, pH < 7.30, HCO3 < 18 mEq/L, cetonemia/cetonuria. "
            "Tratamiento: Solución Salina 0.9%, corrección de potasio (no iniciar insulina si K+ < 3.3 mEq/L) e insulina regular IV."
        ),
    },
    {
        "id": "gpc_codigo_infarto",
        "title": "Código Infarto IMSS/SSA · Síndrome Coronario Agudo (IAMCEST I21)",
        "source": "GPC Código Infarto / AHA",
        "content": (
            "Ante dolor precordial opresivo o sospecha de SCA: ECG de 12 derivaciones en < 10 minutos. "
            "Antiagregación dual: Aspirina 150-300 mg VO masticada + Clopidogrel 300-600 mg VO (300 mg si >75 años). "
            "Nitroglicerina SL 0.4 mg c/5 min máx 3 dosis solo si PAS >= 90 mmHg y descartado infarto de VD o uso reciente de inhibidores PDE-5. "
            "Reperfusión: Angioplastia primaria < 90 min o fibrinólisis < 30 min."
        ),
    },
    {
        "id": "cuadro_basico_interacciones",
        "title": "Cuadro Básico de Medicamentos & Interacciones Farmacológicas Críticas",
        "source": "Compendio Nacional de Insumos para la Salud / CDSS",
        "content": (
            "Interacciones críticas a vigilar: 1) Alergia a Penicilina: evitar Amoxicilina, Ampicilina y valorar riesgo cruzado con Cefalosporinas "
            "(usar Macrólidos o Quinolonas si indicado). 2) IECA/ARA-II (Enalapril, Captopril, Losartán) + AINEs (Ketorolaco, Ibuprofeno) + Diurético = 'Triple Whammy' con riesgo de lesión renal aguda. "
            "3) Metformina + medio de contraste yodado con TFG reducida = acidosis láctica. 4) Amoxicilina pediátrica: 50-90 mg/kg/día dividida c/8-12h. "
            "Paracetamol pediátrico: 10-15 mg/kg/dosis c/6h (máx 60 mg/kg/día)."
        ),
    },
    {
        "id": "gpc_asma_epoc",
        "title": "GPC Asma Bronquial (J45) y EPOC (J44) · Rescate y Exacerbaciones",
        "source": "GINA / GOLD / GPC CENETEC",
        "content": (
            "Crisis asmática o exacerbación de EPOC: evaluar SpO2 (meta 93-95% en asma; 88-92% en EPOC hipercapnico), "
            "broncodilatador de acción corta (Salbutamol 4-10 inhalaciones cada 20 min la primera hora + Bromuro de Ipratropio en crisis moderada-grave), "
            "y corticoesteroide sistémico temprano (Prednisona 40-50 mg VO o Hidrocortisona/Metilprednisolona IV)."
        ),
    },
]


class _BM25Index:
    """Índice léxico BM25Okapi ligero en Python puro para búsqueda exacta de fármacos y códigos."""

    def __init__(self, docs: List[Dict[str, str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.tokenized = [self._tokenize(f"{d['title']} {d['source']} {d['content']}") for d in docs]
        self.N = max(len(docs), 1)
        self.avgdl = sum(len(t) for t in self.tokenized) / self.N
        self.df: Dict[str, int] = {}
        for toks in self.tokenized:
            for w in set(toks):
                self.df[w] = self.df.get(w, 0) + 1
        self.idf: Dict[str, float] = {
            w: math.log(1.0 + (self.N - freq + 0.5) / (freq + 0.5))
            for w, freq in self.df.items()
        }

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[a-z0-9]{2,}", _norm(text))

    def search(self, query: str, top_k: int = 4) -> List[Tuple[int, float]]:
        q_toks = self._tokenize(query)
        if not q_toks:
            return []
        scores: List[Tuple[int, float]] = []
        for idx, doc_toks in enumerate(self.tokenized):
            dl = max(len(doc_toks), 1)
            tf_map: Dict[str, int] = {}
            for w in doc_toks:
                tf_map[w] = tf_map.get(w, 0) + 1
            s = 0.0
            for qw in q_toks:
                if qw not in tf_map:
                    continue
                idf = self.idf.get(qw, 0.0)
                tf = tf_map[qw]
                s += idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * (1.0 - self.b + self.b * dl / max(self.avgdl, 1.0)))
            if s > 0.0:
                scores.append((idx, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridClinicalRetriever:
    """
    Combina BM25 léxico exacto + Embeddings Densos en ChromaDB mediante
    Reciprocal Rank Fusion (RRF) sobre GPC, Cuadro Básico, NOM-004 y CIE-10.
    """

    def __init__(self) -> None:
        self._bm25 = _BM25Index(_CLINICAL_CORPUS)
        self._id_to_idx = {d["id"]: i for i, d in enumerate(_CLINICAL_CORPUS)}

    def ensure_seeded(self) -> int:
        global _SEEDED
        if _SEEDED:
            return len(_CLINICAL_CORPUS)
        with _SEED_LOCK:
            if _SEEDED:
                return len(_CLINICAL_CORPUS)
            try:
                col = get_collection(_KNOWLEDGE_COLLECTION)
                if col.count() < len(_CLINICAL_CORPUS):
                    ids = [d["id"] for d in _CLINICAL_CORPUS]
                    docs = [f"{d['title']}\n{d['content']}" for d in _CLINICAL_CORPUS]
                    embs = [_compute_text_embedding_384(doc) for doc in docs]
                    metas = [{"title": d["title"], "source": d["source"]} for d in _CLINICAL_CORPUS]
                    col.upsert(ids=ids, documents=docs, embeddings=embs, metadatas=metas)
                _SEEDED = True
            except Exception as exc:
                print(f"[HybridRAG] Aviso sembrando conocimiento clínico en ChromaDB: {exc}")
        return len(_CLINICAL_CORPUS)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        self.ensure_seeded()
        bm25_hits = self._bm25.search(query, top_k=max(top_k * 2, 5))

        dense_hits: List[Tuple[str, float]] = []
        try:
            col = get_collection(_KNOWLEDGE_COLLECTION)
            cnt = col.count()
            if cnt > 0:
                q_emb = _compute_text_embedding_384(query)
                res = col.query(
                    query_embeddings=[q_emb],
                    n_results=min(max(top_k * 2, 5), cnt),
                    include=["distances"],
                )
                ids = (res.get("ids") or [[]])[0]
                dists = (res.get("distances") or [[]])[0]
                for doc_id, dist in zip(ids, dists):
                    dense_hits.append((doc_id, max(0.0, 1.0 - float(dist))))
        except Exception as exc:
            print(f"[HybridRAG] Aviso consulta vectorial ChromaDB: {exc}")

        # Reciprocal Rank Fusion (RRF, k=60)
        rrf_scores: Dict[int, float] = {}
        for rank, (idx, _score) in enumerate(bm25_hits, start=1):
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (60.0 + rank)

        for rank, (doc_id, _sim) in enumerate(dense_hits, start=1):
            idx = self._id_to_idx.get(doc_id)
            if idx is not None:
                rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (60.0 + rank)

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results: List[Dict[str, Any]] = []
        for idx, rrf_score in ranked:
            entry = _CLINICAL_CORPUS[idx]
            results.append(
                {
                    "id": entry["id"],
                    "title": entry["title"],
                    "source": entry["source"],
                    "content": entry["content"],
                    "rrf_score": round(rrf_score, 4),
                }
            )
        return results

    def corpus_size(self) -> int:
        try:
            col = get_collection(_KNOWLEDGE_COLLECTION)
            return max(len(_CLINICAL_CORPUS), int(col.count()))
        except Exception:
            return len(_CLINICAL_CORPUS)


# ---------------------------------------------------------------------------
# ENRUTADOR DINÁMICO DE INTENCIÓN (CLINICAL vs AGENTIC_TOOL vs UNIVERSAL)
# ---------------------------------------------------------------------------

class IntentRouter:
    """
    Clasifica cada prompt en tiempo real en:
      - AGENTIC_TOOL: Transferencias, borrador SOAP explícito, búsqueda en BD/agenda, resumen de paciente.
      - CLINICAL_NORMATIVE: Medicina, fármacos, signos vitales, triaje, códigos CIE-10, NOM-004, GPC.
      - UNIVERSAL_GENERAL: Programación, matemáticas, física, redacción general, arquitectura/gestión no médica.
    """

    _UNIVERSAL_KEYWORDS = {
        "python", "javascript", "typescript", "html", "css", "sql", "fastapi", "react", "docker",
        "git", "bash", "linux", "regex", "algoritmo", "funcion", "fibonacci", "complejidad",
        "big o", "ordenamiento", "estructura de datos", "json", "codigo", "programacion",
        "depurar", "bug", "clase", "herencia", "asincrono", "async",
        "fisica", "cuantica", "termodinamica", "relatividad", "cinematica", "newton", "entropia",
        "matematica", "integral", "derivada", "ecuacion", "matriz", "algebra", "geometria", "calculo",
        "probabilidad", "estadistica", "trigonometria", "teorema", "logaritmo",
        "correo electronico", "carta formal", "ensayo", "traduce", "traducir", "resumen de texto",
        "plan de proyecto", "excel", "powerpoint", "cronograma", "historia universal", "filosofia",
        "clima", "capital de", "receta de cocina", "poema", "cuento",
    }

    _CLINICAL_KEYWORDS = {
        "paciente", "clinica", "clinico", "medico", "medica", "doctor", "sintoma", "sintomas",
        "diagnostico", "tratamiento", "medicamento", "farmaco", "receta", "posologia", "dosis",
        "mg/kg", "cie-10", "cie10", "soap", "nom-004", "nom004", "nom-024", "triaje", "triage",
        "alergia", "alergias", "signos vitales", "mmhg", "lpm", "rpm", "spo2", "saturacion",
        "temperatura", "fiebre", "febril", "hipertension", "hipotension", "crisis hipertensiva",
        "diabetes", "glucosa", "insulina", "metformina", "hba1c", "cetoacidosis", "dengue",
        "plaquetopenia", "sepsis", "qsofa", "news2", "infarto", "iam", "precordial", "toracico",
        "disnea", "asma", "epoc", "salbutamol", "amoxicilina", "paracetamol", "ketorolaco",
        "ibuprofeno", "losartan", "ceftriaxona", "tfg", "creatinina", "cockcroft", "anion gap",
        "sodio corregido", "expediente", "curp", "consulta", "urgencia", "emergencia",
        "cefalea", "dolor", "nausea", "vomito", "enfermedad", "patologia", "exploracion",
        "gpc", "cuadro basico", "interaccion", "salud digna",
    }

    @classmethod
    def classify(cls, prompt: str, route_override: Optional[str] = None) -> str:
        if route_override in ("AGENTIC_TOOL", "CLINICAL_NORMATIVE", "UNIVERSAL_GENERAL"):
            return route_override

        q = _norm(prompt)

        # 1. Ruta Agéntica de Herramientas del Sistema
        if any(
            k in q
            for k in (
                "transferencia",
                "derivacion",
                "otro hospital",
                "hospital emisor",
                "protocolo distinto",
                "protocolo divergente",
                "divergencia",
            )
        ):
            return "AGENTIC_TOOL"

        if any(
            k in q
            for k in (
                "borrador soap",
                "nota soap",
                "formato soap",
                "haz un soap",
                "crea un soap",
                "redacta soap",
                "dictado soap",
                "genera soap",
                "generar soap",
            )
        ):
            return "AGENTIC_TOOL"

        if any(
            k in q
            for k in (
                "busca paciente",
                "buscar paciente",
                "busca los pacientes",
                "citas de hoy",
                "agenda de hoy",
                "programadas hoy",
                "directorio de pacientes",
                "citas programadas",
            )
        ):
            return "AGENTIC_TOOL"

        if any(
            k in q
            for k in (
                "resumen del paciente",
                "resumen previo del paciente",
                "antecedentes del paciente",
                "alergias del paciente",
                "historial del paciente",
                "quien es el paciente",
            )
        ):
            return "AGENTIC_TOOL"

        if (q.startswith("paciente ") or q.startswith("caso ")) and any(
            k in q for k in ("acude a consulta", "refiere que", "ingresa con", "motivo de ingreso")
        ):
            return "AGENTIC_TOOL"

        # 2. Evaluar señales clínicas vs universales
        has_vitals_pattern = bool(
            re.search(r"\b\d{2,3}\s*/\s*\d{2,3}\b", q)
            or re.search(r"\b(?:ta|fc|fr|spo2|temp)\b", q)
            or re.search(r"\b\d+(?:\.\d+)?\s*(?:mmhg|lpm|rpm|mg|mcg|ml|kg|°c)\b", q)
        )
        clinical_score = sum(1 for k in cls._CLINICAL_KEYWORDS if k in q)
        if has_vitals_pattern:
            clinical_score += 2

        universal_score = sum(1 for k in cls._UNIVERSAL_KEYWORDS if k in q)

        if universal_score > 0 and clinical_score == 0:
            return "UNIVERSAL_GENERAL"

        if universal_score >= 2 and clinical_score <= 1:
            return "UNIVERSAL_GENERAL"

        if clinical_score > 0:
            return "CLINICAL_NORMATIVE"

        # Saludos simples o preguntas sobre identidad del asistente -> Ruta Clínica (para responder como Dr. Oso conociendo si pregunta por el paciente)
        if any(k in q for k in ("quien eres", "como se encuentra", "como esta el", "hola", "buenos dias", "buenas tardes", "buenas noches")):
            if "paciente" in q or "expediente" in q:
                return "CLINICAL_NORMATIVE"
            if any(q.startswith(g) or q == g for g in ("hola", "buenos dias", "buenas tardes", "buenas noches", "quien eres")):
                return "CLINICAL_NORMATIVE"

        # Por defecto: si no contiene términos clínicos, tratar en Ruta Universal inteligente
        return "UNIVERSAL_GENERAL"


# ---------------------------------------------------------------------------
# BLINDAJE ANTI-ALUCINACIÓN DE IDENTIDAD + SLIDING WINDOW
# ---------------------------------------------------------------------------

class IdentityGuardrail:
    """
    Asegura separación estricta entre la identidad del Asistente (Dr. Oso · Pulso),
    el Médico Tratante usuario y el Expediente del Paciente de solo lectura.
    """

    @staticmethod
    def build_system_prompt(
        route: str,
        doctor_name: str = "Médico Tratante",
        patient_bundle: Optional[Dict[str, Any]] = None,
        rag_chunks: Optional[List[Dict[str, Any]]] = None,
        episodic_prefs: Optional[List[Dict[str, Any]]] = None,
        ml_triage: Optional[Dict[str, Any]] = None,
    ) -> str:
        sections: List[str] = [
            "<ASSISTANT_IDENTITY>",
            "Eres Dr. Oso (Pulso), el Sistema de IA Híbrida Evolutiva integrado en MedicAItion (Cruz Roja Mérida).",
            "REGLA INQUEBRANTABLE DE IDENTIDAD: TÚ ERES EL ASISTENTE DE INTELIGENCIA ARTIFICIAL QUE APOYA AL MÉDICO.",
            "TÚ NO ERES EL PACIENTE. JAMÁS te presentes con el nombre de ningún paciente ni hables en primera persona asumiendo su edad, síntomas o expediente.",
            "Habla SIEMPRE sobre cualquier paciente en TERCERA PERSONA (ej. 'El paciente Kevin Morales presenta...').",
            "Responde siempre en el MISMO IDIOMA en que el usuario redactó su consulta.",
            "</ASSISTANT_IDENTITY>",
            "",
            f"<ATTENDING_PHYSICIAN>\nOperador autorizado en sesión: {doctor_name}\n</ATTENDING_PHYSICIAN>",
        ]

        if route == "UNIVERSAL_GENERAL":
            sections.extend([
                "",
                "<ROUTING_MODE>UNIVERSAL_GENERAL</ROUTING_MODE>",
                "El usuario realiza una consulta general o técnica (programación, ciencias, matemáticas, redacción o gestión).",
                "Responde con máxima profundidad, claridad, razonamiento paso a paso y estilo GPT-4o / Claude 3.5 Sonnet / Gemini.",
                "NO menciones datos clínicos ni expedientes de pacientes a menos que el usuario lo pida explícitamente.",
            ])
            return "\n".join(sections)

        # Ruta Clínica o Agéntica: inyectar contexto clínico blindado
        sections.extend([
            "",
            f"<ROUTING_MODE>{route}</ROUTING_MODE>",
            "Reglas clínicas obligatorias (NOM-004-SSA3-2012):",
            "1. NUNCA inventes signos vitales, antecedentes o hallazgos no documentados; marca lo faltante como [PENDIENTE].",
            "2. Ante riesgo moderado/alto/crítico o contraindicaciones, inicia la alerta con '⚠️ ALERTA CLÍNICA:'.",
            "3. Toda sugerencia diagnóstica, código CIE-10 o fármaco debe recordar: '⚠️ Revisar por el médico tratante'.",
        ])

        if patient_bundle and patient_bundle.get("patient"):
            p = patient_bundle["patient"]
            full_name = p.get("nombre_completo") or f"{p.get('nombres', '')} {p.get('primer_apellido', '')} {p.get('segundo_apellido', '')}".strip()
            alergias = ", ".join(a.get("descripcion", "") for a in (p.get("alergias") or [])) or "Ninguna conocida"
            antec = "; ".join(a.get("descripcion", "") for a in (p.get("antecedentes") or [])[:4]) or "Ninguno registrado"
            vitals = patient_bundle.get("vital_readings") or []
            vit_str = "Sin registro reciente"
            if vitals:
                v = vitals[0]
                vit_str = (
                    f"TA {v.get('systolic_bp') or '--'}/{v.get('diastolic_bp') or '--'} mmHg, "
                    f"FC {v.get('heart_rate') or '--'} lpm, Temp {v.get('temperature_c') or '--'} °C, SpO2 {v.get('spo2') or '--'}%"
                )
            sections.extend([
                "",
                "<PATIENT_RECORD_READONLY_DO_NOT_IMPERSONATE>",
                f"PACIENTE EN PANTALLA (TERCERA PERSONA — NO ERES TÚ): {full_name}",
                f"CURP: {p.get('curp')} | Edad: {p.get('edad', 'N/D')} años | Sexo: {p.get('sexo', 'N/D')} | Grupo Sanguíneo: {p.get('tipo_sangre', 'N/D')}",
                f"Alergias documentadas: {alergias}",
                f"Antecedentes: {antec}",
                f"Últimos signos vitales registrados: {vit_str}",
                "</PATIENT_RECORD_READONLY_DO_NOT_IMPERSONATE>",
            ])

        if ml_triage and (ml_triage.get("has_observed_vitals") or ml_triage.get("red_flags")):
            sections.extend([
                "",
                "<ML_TRIAGE_ASSESSMENT>",
                f"Nivel de riesgo ML: {ml_triage.get('ml_risk_level')} (confianza {ml_triage.get('ml_probability')})",
                f"NEWS2: {ml_triage.get('news2_score')} | qSOFA: {ml_triage.get('qsofa_score')}/3 | Índice de choque: {ml_triage.get('shock_index')}",
                "Banderas rojas detectadas: " + ("; ".join(ml_triage.get("red_flags") or []) or "Ninguna"),
                "</ML_TRIAGE_ASSESSMENT>",
            ])

        if rag_chunks:
            sections.append("")
            sections.append("<HYBRID_RAG_EVIDENCE>")
            for idx, ch in enumerate(rag_chunks, start=1):
                sections.append(f"[{idx}] {ch['title']} ({ch['source']}): {ch['content']}")
            sections.append("</HYBRID_RAG_EVIDENCE>")

        if episodic_prefs:
            sections.append("")
            sections.append("<EPISODIC_DOCTOR_PREFERENCES>")
            for pref in episodic_prefs:
                sections.append(pref.get("document", "")[:500])
            sections.append("</EPISODIC_DOCTOR_PREFERENCES>")

        return "\n".join(sections)

    @staticmethod
    def sanitize_identity_leak(text: str, patient_name: Optional[str] = None) -> str:
        """
        Corrige si el modelo llegara a emitir una alucinación de identidad en primera persona
        atribuyéndose el nombre del paciente activo (ej. "Hola, me llamo Kevin Enrique...").
        """
        if not text:
            return text
        if not patient_name:
            return text

        clean_name = " ".join(patient_name.split()).strip()
        if not clean_name:
            return text

        tokens = [t for t in re.split(r"\s+", clean_name) if len(t) >= 3]
        if not tokens:
            return text

        first_two = " ".join(tokens[:2]) if len(tokens) >= 2 else tokens[0]
        patterns = [
            rf"(?i)\b(?:hola,?\s*)?(?:yo\s+)?(?:soy|me\s+llamo|mi\s+nombre\s+es)\s+{re.escape(clean_name)}\b[.,!?:]*",
            rf"(?i)\b(?:hola,?\s*)?(?:yo\s+)?(?:soy|me\s+llamo|mi\s+nombre\s+es)\s+{re.escape(first_two)}\b[.,!?:]*",
            rf"(?i)\b(?:hola,?\s*)(?:yo\s+)?(?:soy|me\s+llamo|mi\s+nombre\s+es)\s+{re.escape(tokens[0])}\b[.,!?:]*",
        ]

        out = text
        replacement = f"Soy el **Dr. Oso (Pulso)**, asistente clínico de IA del médico. Respecto al paciente **{clean_name}**: "
        for pat in patterns:
            if re.search(pat, out):
                out = re.sub(pat, replacement, out, count=1)
                break
        return out


class SlidingWindowContext:
    """Conserva únicamente los últimos turnos válidos para mantener >55 tok/s dentro de 8192 tokens."""

    @staticmethod
    def build_messages(
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        max_turns: int = 8,
        max_history_chars: int = 5600,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if history:
            sliced = history[-max_turns:]
            kept: List[Dict[str, str]] = []
            char_budget = max_history_chars
            for item in reversed(sliced):
                role = str(item.get("role") or "").strip().lower()
                if role not in ("user", "assistant"):
                    continue
                content = str(item.get("content") or item.get("text") or "").strip()
                if not content:
                    continue
                if len(content) > 1200:
                    content = content[:1180] + "…"
                if char_budget - len(content) < 0 and kept:
                    break
                char_budget -= len(content)
                kept.append({"role": role, "content": content})
            kept.reverse()
            messages.extend(kept)

        messages.append({"role": "user", "content": user_prompt})
        return messages


# ---------------------------------------------------------------------------
# GENERADOR HÍBRIDO LOCAL DE RESPALDO (CUANDO NO HAY SERVIDOR LM STUDIO / OLLAMA)
# ---------------------------------------------------------------------------

def _generate_universal_response(prompt: str) -> str:
    q = _norm(prompt)

    # 1. Código Python / Fibonacci / Algoritmos
    if "fibonacci" in q:
        return (
            "### 💻 Serie de Fibonacci en Python y Análisis de Complejidad\n\n"
            "La forma más eficiente para producción en Python utiliza programación dinámica iterativa en espacio constante:\n\n"
            "```python\n"
            "def fibonacci(n: int) -> int:\n"
            "    if n < 0:\n"
            "        raise ValueError('n debe ser >= 0')\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n):\n"
            "        a, b = b, a + b\n"
            "    return a\n"
            "```\n\n"
            "**Complejidad Algorítmica:**\n"
            "- **Tiempo:** `O(n)` — realiza exactamente `n` iteraciones lineales.\n"
            "- **Espacio auxiliar:** `O(1)` — solo mantiene dos variables escalares (`a`, `b`), evitando desbordamiento de pila.\n"
            "- *(Nota: Una versión recursiva ingenua sería `O(2^n)` en tiempo y `O(n)` en pila; con exponenciación de matrices puede bajarse a `O(log n)`).* "
        )

    if any(k in q for k in ("python", "javascript", "sql", "html", "css", "algoritmo", "funcion", "codigo")):
        return (
            f"### 💻 Asistencia Técnica Universal — Dr. Oso (Modo Experto)\n\n"
            f"He enrutado tu consulta (**\"{prompt.strip()}\"**) al **Canal Universal** (aislado de datos de pacientes NOM-024).\n\n"
            "**Recomendación de ingeniería:**\n"
            "1. Define entradas/salidas tipadas y validación explícita de bordes (`ValueError` / guard clauses).\n"
            "2. Prioriza complejidad temporal `O(n)` u `O(n log n)` evitando bucles anidados innecesarios.\n"
            "3. Para ejecutar generación de código libre ilimitado en streaming con `Qwen3-8B` en tu RTX 4050, "
            "abre **LM Studio** en `http://localhost:1234/v1` con contexto `8192`.\n\n"
            "Si me indicas las entradas/salidas exactas de la función o consulta SQL que necesitas, te entrego el bloque completo paso a paso."
        )

    if any(k in q for k in ("fisica", "cuantica", "termodinamica", "derivada", "integral", "ecuacion", "matematica")):
        return (
            f"### 📐 Razonamiento Científico Universal — Dr. Oso\n\n"
            f"Consulta clasificada en **Ruta Universal**: *\"{prompt.strip()}\"*\n\n"
            "- **Planteamiento formal:** Identifica variables independientes, condiciones de frontera y unidades en el Sistema Internacional (SI).\n"
            "- **Verificación dimensional:** Comprueba homogeneidad dimensional en cada término antes de evaluar numéricamente.\n"
            "- Con **Qwen3-8B** activo en LM Studio (`localhost:1234/v1`), este canal desarrolla demostraciones simbólicas y derivaciones matemáticas completas a >55 tok/s."
        )

    return (
        f"### 🌐 Respuesta Universal — Dr. Oso (Pulso)\n\n"
        f"He procesado tu solicitud en la **Ruta Universal** (sin inyectar expedientes médicos): *\"{prompt.strip()}\"*.\n\n"
        "Puedo ayudarte con **arquitectura de software, Python/SQL/JS, redacción ejecutiva, análisis lógico y matemáticas**, "
        "o cambiar automáticamente a la **Ruta Clínica NOM-004** en cuanto menciones un paciente, síntoma, signo vital o medicamento.\n\n"
        "💡 *Tip de rendimiento RTX 4050:* Conecta `Qwen3-8B (Q4_K_M)` en LM Studio (`http://localhost:1234/v1`) para razonamiento generativo ilimitado en streaming."
    )


def generate_hybrid_fallback_response(
    prompt: str,
    route: str,
    patient_bundle: Optional[Dict[str, Any]],
    rag_chunks: List[Dict[str, Any]],
    episodic_prefs: List[Dict[str, Any]],
    ml_triage: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Orquesta la respuesta local determinista/generativa cuando no hay servidor LLM externo
    o complementa las herramientas agénticas garantizando cero alucinación de identidad.
    """
    if route == "UNIVERSAL_GENERAL":
        return {
            "avatar_state": "contento",
            "text": _generate_universal_response(prompt),
        }

    q = _norm(prompt)
    avatar_state = "pensando"
    blocks: List[str] = []

    # Caso especial de identidad + estado del paciente en tercera persona
    if any(k in q for k in ("quien eres", "como se encuentra", "como esta el paciente")) and patient_bundle and patient_bundle.get("patient"):
        p = patient_bundle["patient"]
        full_name = p.get("nombre_completo") or f"{p.get('nombres', '')} {p.get('primer_apellido', '')} {p.get('segundo_apellido', '')}".strip()
        edad = f"{p.get('edad')} años" if p.get("edad") is not None else "edad no especificada"
        sexo = p.get("sexo") or "N/D"
        alergias = ", ".join(a.get("descripcion", "") for a in (p.get("alergias") or [])) or "sin alergias conocidas"
        vitals = patient_bundle.get("vital_readings") or []
        vit_str = (
            f"TA {vitals[0].get('systolic_bp') or '--'}/{vitals[0].get('diastolic_bp') or '--'} mmHg, "
            f"FC {vitals[0].get('heart_rate') or '--'} lpm, Temp {vitals[0].get('temperature_c') or '--'} °C, "
            f"SpO2 {vitals[0].get('spo2') or '--'}%"
            if vitals
            else "[PENDIENTE: registro reciente de signos vitales]"
        )
        text = (
            f"Soy el **Dr. Oso (Pulso)**, tu asistente clínico de **IA Híbrida 100% local** integrado en MedicAItion 🩺🐻.\n\n"
            f"Respecto al paciente en expediente activo **{full_name}** (`{p.get('curp')}`, {edad}, sexo {sexo}):\n"
            f"- **Alergias documentadas:** {alergias}.\n"
            f"- **Últimos signos vitales registrados:** {vit_str}.\n"
            f"- **Estado del copiloto:** Memoria episódica activa y vigilancia NOM-004 habilitada.\n\n"
            "⚠️ *Revisar siempre por el médico tratante.*"
        )
        return {"avatar_state": "contento", "text": text}

    # 1. Bloque de Alertas Rojas del Clasificador ML (scikit-learn + NEWS2 + qSOFA)
    if ml_triage and (ml_triage.get("red_flags") or ml_triage.get("is_emergency")):
        avatar_state = "alerta"
        flags_md = "\n".join(f"- ⚠️ **ALERTA CLÍNICA:** {rf}" for rf in (ml_triage.get("red_flags") or []))
        v = ml_triage.get("vitals_used") or {}
        blocks.append(
            f"### 🚨 Evaluación Inmediata de Triaje ML (`scikit-learn` · {ml_triage.get('ml_risk_level')})\n"
            f"**Signos evaluados:** TA `{v.get('systolic_bp')}/{v.get('diastolic_bp')} mmHg` · FC `{v.get('heart_rate')} lpm` · "
            f"FR `{v.get('resp_rate')} rpm` · Temp `{v.get('temperature_c')} °C` · SpO2 `{v.get('spo2')}%`\n"
            f"**Escalas calculadas:** `NEWS2 = {ml_triage.get('news2_score')}` · `qSOFA = {ml_triage.get('qsofa_score')}/3` · `Índice de Choque = {ml_triage.get('shock_index')}`\n\n"
            f"{flags_md}"
        )

    # 2. Motor clínico generativo específico (Código Infarto, Dengue, Dosis, TFG, DM2, HTA, etc.)
    gen = generate_conversational_response(prompt, patient_bundle)
    gen_text = gen.get("text", "")
    # Evitar mensaje genérico redundante si ya tenemos alertas ML y evidencia RAG rica
    is_generic = "He analizado tu consulta clínica utilizando la base médica local" in gen_text
    if not (is_generic and blocks and rag_chunks):
        blocks.append(gen_text)
        if avatar_state != "alerta":
            avatar_state = gen.get("avatar_state", "pensando")

    # 3. Evidencia del RAG Híbrido (BM25 + ChromaDB RRF)
    if rag_chunks:
        rag_lines = ["### 📚 Evidencia Recuperada (RAG Híbrido BM25 + ChromaDB)"]
        for ch in rag_chunks[:2]:
            rag_lines.append(f"- **{ch['title']}** *({ch['source']})*: {ch['content']}")
        blocks.append("\n".join(rag_lines))

    # 4. Preferencias del médico recuperadas por Memoria Episódica
    if episodic_prefs:
        pref_lines = ["### 🧬 Preferencias Previas del Médico (`episodic_learning`)"]
        for ep in episodic_prefs[:1]:
            snippet = ep["document"].replace("\n", " ")[:240]
            pref_lines.append(f"- *Adaptación aprendida (similitud {ep['similarity']}):* {snippet}…")
        blocks.append("\n".join(pref_lines))

    final_text = "\n\n---\n\n".join(blocks)
    if "Revisar" not in final_text:
        final_text += "\n\n⚠️ *Revisar por el médico tratante.*"

    return {"avatar_state": avatar_state, "text": final_text}


# Instancias singleton
hybrid_retriever = HybridClinicalRetriever()
intent_router = IntentRouter()
identity_guardrail = IdentityGuardrail()
sliding_window = SlidingWindowContext()
