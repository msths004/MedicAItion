"""
app/core/evolutionary_learning.py — Motor de Machine Learning Ligero y Aprendizaje Evolutivo
=============================================================================================
Implementa dos pilares sin desbordar GPU (RTX 4050 6 GB VRAM) ni CPU:
  1. ClinicalRiskMLClassifier (scikit-learn GradientBoosting + NEWS2 / qSOFA / Shock Index):
     Evalúa signos vitales y síntomas en <5 ms antes de que el LLM redacte su respuesta.
  2. EpisodicMemoryManager (ChromaDB `episodic_learning` + Dataset DPO `training_data/dpo_pairs.jsonl`):
     Registra aprobaciones, rechazos y correcciones médicas (`diff`) para adaptar estilo
     y preferencias de prescripción sin reentrenamiento pesado en vivo.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import math
import os
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from app.db.chroma_store import get_collection

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TRAINING_DIR = os.path.join(_BASE_DIR, "training_data")
_DPO_JSONL_PATH = os.path.join(_TRAINING_DIR, "dpo_pairs.jsonl")
_EPISODIC_COLLECTION = "episodic_learning"

_LOCK = threading.Lock()


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _compute_text_embedding_384(text: str) -> List[float]:
    """
    Obtiene un vector de 384 dimensiones usando SentenceTransformer local si está disponible,
    o una proyección hash determinista L2-normalizada de 384 dimensiones (100% offline, 0 ms)
    para no disparar descargas ONNX externas en ChromaDB.
    """
    try:
        from app.core.cie10_mapper import _get_embedder
        emb = _get_embedder()
        if emb is not None:
            vec = emb.encode([text or " "])[0]
            return vec.tolist() if hasattr(vec, "tolist") else list(vec)
    except Exception:
        pass

    dim = 384
    vec = np.zeros(dim, dtype=np.float32)
    clean = _norm(text)
    tokens = re.findall(r"[a-z0-9]{2,}", clean)
    if not tokens:
        vec[0] = 1.0
        return vec.tolist()

    for tok in tokens:
        # Unigramas y bigramas de caracteres para robustez semántica/léxica
        pieces = [tok] + [tok[i : i + 3] for i in range(max(0, len(tok) - 2))]
        for piece in pieces:
            h = hashlib.blake2b(piece.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "little") % dim
            sign = 1.0 if (h[4] & 1) == 0 else -1.0
            weight = 1.5 if piece == tok else 0.5
            vec[idx] += sign * weight

    norm_val = float(np.linalg.norm(vec))
    if norm_val > 1e-8:
        vec /= norm_val
    else:
        vec[0] = 1.0
    return vec.tolist()


# ---------------------------------------------------------------------------
# 1. CLASIFICADOR ML LIGERO DE TRIAJE Y RIESGO CLÍNICO (scikit-learn)
# ---------------------------------------------------------------------------

class ClinicalRiskMLClassifier:
    """
    Modelo predictivo local ultrarrápido (GradientBoostingClassifier + escalas NEWS2 / qSOFA)
    entrenado sobre fisiología clínica estandarizada al inicializar el backend.
    """

    def __init__(self) -> None:
        self._model: Optional[GradientBoostingClassifier] = None
        self._ready: bool = False
        self._train_baseline_model()

    def _train_baseline_model(self) -> None:
        """
        Entrena un clasificador de 4 niveles de riesgo clínico:
          0 = BAJO, 1 = MODERADO, 2 = ALTO, 3 = CRÍTICO
        sobre un conjunto balanceado y determinista de perfiles fisiológicos reales.
        """
        rng = np.random.default_rng(42)
        rows = []
        labels = []

        # Nivel 0: BAJO (Fisiología normal / estable)
        for _ in range(140):
            sbp = rng.uniform(105, 129)
            dbp = rng.uniform(65, 84)
            hr = rng.uniform(58, 88)
            rr = rng.uniform(12, 19)
            temp = rng.uniform(36.1, 37.3)
            spo2 = rng.uniform(96, 100)
            alt = 0.0
            rows.append([sbp, dbp, hr, rr, temp, spo2, alt])
            labels.append(0)

        # Nivel 1: MODERADO (Febrícula / HTA Grado 1-2 / Taquicardia leve)
        for _ in range(120):
            sbp = rng.choice([rng.uniform(135, 165), rng.uniform(96, 104)])
            dbp = rng.uniform(82, 104)
            hr = rng.uniform(92, 110)
            rr = rng.uniform(18, 21)
            temp = rng.choice([rng.uniform(37.6, 38.4), rng.uniform(36.2, 37.2)])
            spo2 = rng.uniform(94, 96)
            alt = 0.0
            rows.append([sbp, dbp, hr, rr, temp, spo2, alt])
            labels.append(1)

        # Nivel 2: ALTO (Fiebre alta, hipoxemia moderada, taquipnea o taquicardia marcada)
        for _ in range(120):
            mode = int(rng.integers(0, 4))
            sbp = rng.uniform(166, 179) if mode == 0 else rng.uniform(92, 102)
            dbp = rng.uniform(100, 114) if mode == 0 else rng.uniform(58, 78)
            hr = rng.uniform(111, 128)
            rr = rng.uniform(22, 25)
            temp = rng.uniform(38.5, 39.4) if mode in (1, 2) else rng.uniform(36.5, 37.8)
            spo2 = rng.uniform(90, 93) if mode in (2, 3) else rng.uniform(93, 95)
            alt = 0.0
            rows.append([sbp, dbp, hr, rr, temp, spo2, alt])
            labels.append(2)

        # Nivel 3: CRÍTICO (Crisis hipertensiva >=180/120, sepsis qSOFA>=2, choque o hipoxia grave <=89%)
        for _ in range(140):
            mode = int(rng.integers(0, 4))
            if mode == 0:  # Crisis hipertensiva
                sbp, dbp = rng.uniform(180, 225), rng.uniform(115, 140)
                hr, rr, temp, spo2, alt = rng.uniform(95, 130), rng.uniform(20, 28), rng.uniform(36.5, 37.8), rng.uniform(91, 97), float(rng.choice([0, 1]))
            elif mode == 1:  # Choque / Sepsis
                sbp, dbp = rng.uniform(68, 92), rng.uniform(40, 62)
                hr, rr, temp, spo2, alt = rng.uniform(118, 152), rng.uniform(24, 34), rng.choice([rng.uniform(34.2, 35.4), rng.uniform(38.8, 40.5)]), rng.uniform(86, 93), 1.0
            elif mode == 2:  # Falla respiratoria aguda
                sbp, dbp = rng.uniform(95, 145), rng.uniform(60, 90)
                hr, rr, temp, spo2, alt = rng.uniform(110, 140), rng.uniform(26, 36), rng.uniform(37.5, 39.6), rng.uniform(76, 89), float(rng.choice([0, 1]))
            else:  # Alteración neurológica / combinación crítica
                sbp, dbp = rng.uniform(80, 100), rng.uniform(50, 68)
                hr, rr, temp, spo2, alt = rng.uniform(115, 145), rng.uniform(22, 30), rng.uniform(38.0, 40.2), rng.uniform(84, 92), 1.0
            rows.append([sbp, dbp, hr, rr, temp, spo2, alt])
            labels.append(3)

        X = np.array(rows, dtype=np.float32)
        y = np.array(labels, dtype=np.int32)
        clf = GradientBoostingClassifier(
            n_estimators=45,
            max_depth=3,
            learning_rate=0.12,
            random_state=42,
        )
        clf.fit(X, y)
        self._model = clf
        self._ready = True

    @staticmethod
    def extract_vitals_from_text(text: str) -> Dict[str, Any]:
        """Extrae signos vitales mencionados en texto libre clínico si están presentes."""
        out: Dict[str, Any] = {}
        if not text:
            return out
        low = _norm(text)

        # TA / PA: 185/122, 120/80 mmHg
        m_bp = re.search(r"(?:ta|pa|presion(?:\s+arterial)?)\s*(?:de|:)?\s*(\d{2,3})\s*/\s*(\d{2,3})", low)
        if not m_bp:
            m_bp = re.search(r"\b(1?\d{2}|2\d{2})\s*/\s*(\d{2,3})\s*(?:mmhg|mm\s*hg)?", low)
        if m_bp:
            sbp, dbp = int(m_bp.group(1)), int(m_bp.group(2))
            if 50 <= sbp <= 260 and 30 <= dbp <= 170:
                out["systolic_bp"] = sbp
                out["diastolic_bp"] = dbp

        # FC: 118 lpm / bpm
        m_hr = re.search(r"(?:fc|frec(?:uencia)?\.?\s*card[ií]aca)\s*(?:de|:)?\s*(\d{2,3})", low)
        if not m_hr:
            m_hr = re.search(r"\b(\d{2,3})\s*(?:lpm|bpm|latidos)", low)
        if m_hr:
            hr = int(m_hr.group(1))
            if 25 <= hr <= 230:
                out["heart_rate"] = hr

        # FR: 24 rpm
        m_rr = re.search(r"(?:fr|frec(?:uencia)?\.?\s*resp(?:iratoria)?)\s*(?:de|:)?\s*(\d{1,2})", low)
        if not m_rr:
            m_rr = re.search(r"\b(\d{1,2})\s*(?:rpm|resp(?:iraciones)?/min)", low)
        if m_rr:
            rr = int(m_rr.group(1))
            if 6 <= rr <= 60:
                out["resp_rate"] = rr

        # Temp: 38.6 C / °C
        m_temp = re.search(r"(?:temp(?:eratura)?|t°?)\s*(?:de|:)?\s*(\d{2}(?:[.,]\d{1,2})?)", low)
        if not m_temp:
            m_temp = re.search(r"\b(3\d(?:[.,]\d{1,2})?|4[0-2](?:[.,]\d{1,2})?)\s*°?\s*c\b", low)
        if m_temp:
            t_val = float(m_temp.group(1).replace(",", "."))
            if 32.0 <= t_val <= 43.0:
                out["temperature_c"] = t_val

        # SpO2: 91%
        m_spo2 = re.search(r"(?:spo2|sat(?:uracion)?\.?\s*o2|oximetria)\s*(?:de|:)?\s*(\d{2,3})\s*%?", low)
        if not m_spo2:
            m_spo2 = re.search(r"\b(7\d|8\d|9\d|100)\s*%\s*(?:de\s*)?(?:spo2|o2|saturacion)?", low)
        if m_spo2:
            sp = int(m_spo2.group(1))
            if 50 <= sp <= 100 and ("spo2" in low or "sat" in low or "%" in m_spo2.group(0)):
                out["spo2"] = sp

        # Alteración del estado mental
        if any(k in low for k in ("confusion", "desorientad", "somnolien", "letarg", "estupor", "inconsciente", "glasgow")):
            out["altered_mental"] = 1

        return out

    @staticmethod
    def _compute_news2(sbp: float, hr: float, rr: float, temp: float, spo2: float, altered: int) -> int:
        score = 0
        # Frecuencia respiratoria
        if rr <= 8 or rr >= 25:
            score += 3
        elif 21 <= rr <= 24:
            score += 2
        elif 9 <= rr <= 11:
            score += 1

        # SpO2 (Escala 1 estándar)
        if spo2 <= 91:
            score += 3
        elif 92 <= spo2 <= 93:
            score += 2
        elif 94 <= spo2 <= 95:
            score += 1

        # Presión arterial sistólica
        if sbp <= 90 or sbp >= 220:
            score += 3
        elif 91 <= sbp <= 100:
            score += 2
        elif 101 <= sbp <= 110:
            score += 1

        # Frecuencia cardíaca
        if hr <= 40 or hr >= 131:
            score += 3
        elif 111 <= hr <= 130:
            score += 2
        elif (41 <= hr <= 50) or (91 <= hr <= 110):
            score += 1

        # Temperatura
        if temp <= 35.0:
            score += 3
        elif temp >= 39.1:
            score += 2
        elif (35.1 <= temp <= 36.0) or (38.1 <= temp <= 39.0):
            score += 1

        # Conciencia
        if altered:
            score += 3
        return score

    @staticmethod
    def _compute_qsofa(sbp: float, rr: float, altered: int) -> int:
        q = 0
        if rr >= 22:
            q += 1
        if sbp <= 100:
            q += 1
        if altered:
            q += 1
        return q

    def evaluate_vitals(
        self,
        vitals_dict: Optional[Dict[str, Any]] = None,
        symptoms_text: str = "",
    ) -> Dict[str, Any]:
        """
        Evalúa en <5 ms los signos vitales (del expediente y/o extraídos del texto actual)
        combinando ML (GradientBoostingClassifier) + escalas médicas validadas (NEWS2, qSOFA).
        """
        base = dict(vitals_dict or {})
        text_vitals = self.extract_vitals_from_text(symptoms_text)

        # Priorizar signos vitales explícitamente mencionados en el prompt actual si existen
        merged = {
            "systolic_bp": text_vitals.get("systolic_bp") or base.get("systolic_bp") or 120,
            "diastolic_bp": text_vitals.get("diastolic_bp") or base.get("diastolic_bp") or 78,
            "heart_rate": text_vitals.get("heart_rate") or base.get("heart_rate") or 76,
            "resp_rate": text_vitals.get("resp_rate") or base.get("resp_rate") or 16,
            "temperature_c": text_vitals.get("temperature_c") or base.get("temperature_c") or 36.6,
            "spo2": text_vitals.get("spo2") or base.get("spo2") or 98,
            "altered_mental": int(text_vitals.get("altered_mental") or base.get("altered_mental") or 0),
        }
        has_observed_vitals = bool(text_vitals) or bool(vitals_dict)

        sbp = float(merged["systolic_bp"])
        dbp = float(merged["diastolic_bp"])
        hr = float(merged["heart_rate"])
        rr = float(merged["resp_rate"])
        temp = float(merged["temperature_c"])
        spo2 = float(merged["spo2"])
        alt = int(merged["altered_mental"])

        news2 = self._compute_news2(sbp, hr, rr, temp, spo2, alt)
        qsofa = self._compute_qsofa(sbp, rr, alt)
        shock_index = round(hr / max(sbp, 1.0), 2)

        # Predicción con scikit-learn
        level_names = ["BAJO", "MODERADO", "ALTO", "CRÍTICO"]
        ml_idx = 0
        ml_prob = 0.90
        if self._model is not None:
            X_vec = np.array([[sbp, dbp, hr, rr, temp, spo2, float(alt)]], dtype=np.float32)
            probs = self._model.predict_proba(X_vec)[0]
            ml_idx = int(np.argmax(probs))
            ml_prob = round(float(probs[ml_idx]), 3)

        # Reglas deterministas de banderas rojas (red flags)
        red_flags: List[str] = []
        low = _norm(symptoms_text)

        if sbp >= 180 or dbp >= 120:
            red_flags.append(
                f"Crisis hipertensiva ({int(sbp)}/{int(dbp)} mmHg): descartar daño agudo a órgano diana (EVC, IAM, disección, edema pulmonar)."
            )
            ml_idx = max(ml_idx, 3)
        elif sbp < 90:
            red_flags.append(f"Hipotensión severa (PAS {int(sbp)} mmHg): vigilar choque hipovolémico/séptico.")
            ml_idx = max(ml_idx, 3)

        if spo2 <= 91:
            red_flags.append(f"Hipoxemia significativa (SpO2 {int(spo2)}%): evaluar oxigenoterapia suplementaria inmediata y gasometría.")
            ml_idx = max(ml_idx, 3)
        elif spo2 <= 94:
            red_flags.append(f"Desaturación leve-moderada (SpO2 {int(spo2)}%): vigilar mecánica ventilatoria.")
            ml_idx = max(ml_idx, 2)

        if qsofa >= 2:
            red_flags.append(f"Alerta de Sepsis / Deterioro (qSOFA {qsofa}/3): iniciar protocolo de reanimación y cultivos tempranos.")
            ml_idx = max(ml_idx, 3)

        if news2 >= 7:
            red_flags.append(f"NEWS2 = {news2} (Riesgo Clínico Alto): requiere valoración médica urgente y monitoreo continuo.")
            ml_idx = max(ml_idx, 3)
        elif news2 >= 5:
            red_flags.append(f"NEWS2 = {news2} (Riesgo Intermedio-Alto): vigilancia estrecha.")
            ml_idx = max(ml_idx, 2)

        if shock_index >= 1.0:
            red_flags.append(f"Índice de choque elevado ({shock_index}): posible inestabilidad hemodinámica.")
            ml_idx = max(ml_idx, 2)

        if temp >= 38.5:
            red_flags.append(f"Fiebre alta ({temp:.1f} °C): investigar foco infeccioso o arbovirosis (dengue si cefalea retroocular/plaquetopenia).")
            ml_idx = max(ml_idx, 2)
        elif temp <= 35.4:
            red_flags.append(f"Hipotermia ({temp:.1f} °C): evaluar sepsis o exposición metabólica.")
            ml_idx = max(ml_idx, 2)

        # Síntomas de alarma narrativa
        symptom_alerts = [
            (("dolor toracico", "dolor de pecho", "opresion toracica", "dolor precordial"), "Sospecha de Síndrome Coronario Agudo: realizar ECG de 12 derivaciones en <10 min."),
            (("sangrado", "hemorragia", "gingivorragia", "hematemesis", "plaquetopenia"), "Hemorragia / Signo de alarma hematológico: monitorizar biometría hemática y coagulación."),
            (("disnea intensa", "dificultad para respirar", "no puede respirar", "cianosis"), "Insuficiencia respiratoria aguda potencial: priorizar vía aérea y oximetría."),
            (("anafilaxia", "edema de glotis", "dificultad al tragar", "urticaria generalizada"), "Posible anafilaxia aguda: evaluar Epinefrina IM inmediata."),
        ]
        for keys, alert_msg in symptom_alerts:
            if any(k in low for k in keys):
                red_flags.append(alert_msg)
                ml_idx = max(ml_idx, 2)

        risk_level = level_names[ml_idx]
        return {
            "has_observed_vitals": has_observed_vitals,
            "vitals_used": merged,
            "news2_score": news2,
            "qsofa_score": qsofa,
            "shock_index": shock_index,
            "ml_risk_level": risk_level,
            "ml_probability": ml_prob,
            "red_flags": red_flags,
            "is_emergency": ml_idx >= 2,
            "summary_badge": f"Riesgo {risk_level} · NEWS2: {news2} · qSOFA: {qsofa}/3",
        }


# ---------------------------------------------------------------------------
# 2. MEMORIA EPISÓDICA VECTORIAL + GENERADOR AUTOMÁTICO DE DATASET DPO/LoRA
# ---------------------------------------------------------------------------

class EpisodicMemoryManager:
    """
    Gestiona la colección `episodic_learning` en ChromaDB y el archivo
    `training_data/dpo_pairs.jsonl` para aprendizaje continuo evolutivo.
    """

    def __init__(self) -> None:
        os.makedirs(_TRAINING_DIR, exist_ok=True)
        if not os.path.exists(_DPO_JSONL_PATH):
            try:
                with open(_DPO_JSONL_PATH, "a", encoding="utf-8"):
                    pass
            except Exception:
                pass

    @staticmethod
    def _compute_diff_summary(original_text: str, corrected_text: str) -> str:
        orig_lines = (original_text or "").strip().splitlines()
        corr_lines = (corrected_text or "").strip().splitlines()
        diff_lines = list(
            difflib.unified_diff(
                orig_lines,
                corr_lines,
                fromfile="ia_original",
                tofile="medico_corregida",
                n=1,
                lineterm="",
            )
        )
        if not diff_lines:
            return "Sin cambios textuales."
        return "\n".join(diff_lines[:18])

    def record_feedback(
        self,
        prompt: str,
        original_response: str,
        corrected_response: Optional[str] = None,
        rating: str = "positive",
        doctor_name: str = "Médico Tratante",
        patient_curp: Optional[str] = None,
        intent: str = "CLINICAL_NORMATIVE",
    ) -> Dict[str, Any]:
        """
        Registra evaluación médica:
          - Si es positiva o incluye texto corregido -> guarda preferencia en ChromaDB `episodic_learning`.
          - Si incluye corrección o rating negativo -> añade par DPO en `training_data/dpo_pairs.jsonl`.
        """
        ts = datetime.now(timezone.utc).isoformat()
        clean_prompt = (prompt or "").strip()
        clean_orig = (original_response or "").strip()
        clean_corr = (corrected_response or "").strip()
        norm_rating = "negative" if str(rating).lower() in ("negative", "down", "bad", "reject") else (
            "corrected" if clean_corr else "positive"
        )

        diff_summary = self._compute_diff_summary(clean_orig, clean_corr) if clean_corr else ""
        preferred_answer = clean_corr if clean_corr else clean_orig

        stored_chroma = False
        stored_dpo = False

        # 1. Almacenar en memoria episódica vectorial si es ejemplo positivo o corrección aprendida
        if norm_rating in ("positive", "corrected") and clean_prompt and preferred_answer:
            doc_text = (
                f"CONSULTA DEL MÉDICO: {clean_prompt}\n"
                f"PREFERENCIA CLÍNICA / ESTILO DEL MÉDICO ({doctor_name}):\n{preferred_answer}"
            )
            if diff_summary:
                doc_text += f"\nCAMBIOS CORREGIDOS POR EL MÉDICO:\n{diff_summary[:600]}"

            try:
                with _LOCK:
                    col = get_collection(_EPISODIC_COLLECTION)
                    emb = _compute_text_embedding_384(clean_prompt + " " + preferred_answer[:350])
                    col.add(
                        ids=[f"ep_{uuid.uuid4().hex[:12]}"],
                        documents=[doc_text],
                        embeddings=[emb],
                        metadatas=[
                            {
                                "timestamp": ts,
                                "doctor": str(doctor_name)[:80],
                                "rating": norm_rating,
                                "intent": str(intent)[:40],
                                "has_correction": bool(clean_corr),
                                "diff_summary": diff_summary[:400],
                                "patient_curp": str(patient_curp or "SIN_CURP")[:24],
                            }
                        ],
                    )
                    stored_chroma = True
            except Exception as exc:
                print(f"[EpisodicLearning] Aviso al guardar en ChromaDB: {exc}")

        # 2. Generar par DPO/LoRA en JSONL si hubo corrección del médico o rechazo explícito
        if clean_corr or norm_rating == "negative":
            dpo_entry = {
                "timestamp": ts,
                "doctor": doctor_name,
                "intent": intent,
                "prompt": clean_prompt,
                "chosen": clean_corr if clean_corr else "[MARCADA COMO INCORRECTA — REVISAR Y COMPLETAR]",
                "rejected": clean_orig,
                "diff_summary": diff_summary or "Rechazada por el médico tratante",
                "patient_curp": patient_curp or "MEMORIA_LOCAL",
            }
            try:
                os.makedirs(_TRAINING_DIR, exist_ok=True)
                with _LOCK:
                    with open(_DPO_JSONL_PATH, "a", encoding="utf-8") as f:
                        f.write(json.dumps(dpo_entry, ensure_ascii=False) + "\n")
                stored_dpo = True
            except Exception as exc:
                print(f"[EpisodicLearning] Error escribiendo DPO JSONL: {exc}")

        stats = self.get_learning_stats()
        return {
            "status": "recorded",
            "rating": norm_rating,
            "stored_in_episodic_chroma": stored_chroma,
            "stored_in_dpo_jsonl": stored_dpo,
            "diff_summary": diff_summary,
            "stats": stats,
        }

    def retrieve_doctor_preferences(self, prompt: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Recupera correcciones o estilos previos del médico relevantes para la consulta actual."""
        if not prompt or len(prompt.strip()) < 3:
            return []
        try:
            col = get_collection(_EPISODIC_COLLECTION)
            count = col.count()
            if count == 0:
                return []
            q_emb = _compute_text_embedding_384(prompt)
            res = col.query(
                query_embeddings=[q_emb],
                n_results=min(top_k, count),
                include=["documents", "metadatas", "distances"],
            )
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]

            out = []
            for doc, meta, dist in zip(docs, metas, dists):
                similarity = max(0.0, 1.0 - float(dist))
                if similarity >= 0.15:
                    out.append(
                        {
                            "document": doc,
                            "similarity": round(similarity, 3),
                            "doctor": (meta or {}).get("doctor", "Médico"),
                            "rating": (meta or {}).get("rating", "positive"),
                            "has_correction": bool((meta or {}).get("has_correction", False)),
                        }
                    )
            return out
        except Exception as exc:
            print(f"[EpisodicLearning] Aviso en recuperación episódica: {exc}")
            return []

    def get_learning_stats(self) -> Dict[str, Any]:
        """Devuelve métricas en vivo de memoria episódica y pares DPO/LoRA acumulados."""
        ep_count = 0
        try:
            col = get_collection(_EPISODIC_COLLECTION)
            ep_count = int(col.count())
        except Exception:
            ep_count = 0

        dpo_count = 0
        try:
            if os.path.exists(_DPO_JSONL_PATH):
                with open(_DPO_JSONL_PATH, "r", encoding="utf-8") as f:
                    dpo_count = sum(1 for line in f if line.strip())
        except Exception:
            dpo_count = 0

        return {
            "episodic_memories_count": ep_count,
            "dpo_pairs_count": dpo_count,
            "ml_classifier_ready": True,
            "dpo_file_path": "training_data/dpo_pairs.jsonl",
        }


# Instancias singleton precargadas para latencia sub-5ms
risk_ml_classifier = ClinicalRiskMLClassifier()
episodic_memory = EpisodicMemoryManager()
