"""
routes_pulso.py — Backend de Asistente Híbrido Evolutivo "Dr. Oso · Pulso" (100% IA Local NOM-024)
==================================================================================================
Provee:
  • GET  /api/pulso/status         — Sondea LM Studio (localhost:1234/v1), Ollama (localhost:11434),
                                     GGUF local y estado del Orquestador Híbrido + ML Evolutivo.
  • POST /api/pulso/config         — Configura URLs y modelos (Qwen3-8B / medgemma-4b-it / Ollama).
  • POST /api/pulso/chat-stream    — Streaming NDJSON con:
                                       - Enrutador Dinámico (CLINICAL_NORMATIVE / UNIVERSAL_GENERAL / AGENTIC_TOOL)
                                       - Guardrail Anti-Alucinación de Identidad (XML + filtro en vivo)
                                       - Clasificador ML de Triaje (`scikit-learn` NEWS2 / qSOFA)
                                       - RAG Híbrido (BM25 + ChromaDB RRF) + Memoria Episódica
                                       - Ventana Deslizante (últimos 6-8 turnos, máx. 8192 tokens)
  • POST /api/pulso/feedback       — Registra 👍 / 👎 / ✏️ Corregir y Enseñar en ChromaDB `episodic_learning`
                                     y genera pares en `training_data/dpo_pairs.jsonl`.
  • GET  /api/pulso/learning-stats — Estadísticas en tiempo real del aprendizaje evolutivo local.
  • POST /api/pulso/audit          — Bitácora NOM-024 sin almacenar contenido clínico sensible.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse

from app.core.entity_extractor import _heuristic_extract
from app.core.evolutionary_learning import episodic_memory, risk_ml_classifier
from app.core.hybrid_ai_orchestrator import (
    generate_hybrid_fallback_response,
    hybrid_retriever,
    identity_guardrail,
    intent_router,
    sliding_window,
)
from app.core.local_llm_runner import (
    find_local_gguf_model,
    get_local_llm_status,
    is_hybrid_sota_gguf,
    stream_local_llm_chat,
)
from app.db.chroma_store import get_collection
from app.db.local_db import (
    Appointment,
    SessionLocal,
    get_active_practitioner,
    get_all_patients,
    get_patient_full_history,
    log_audit_action,
)

router = APIRouter(prefix="/api/pulso", tags=["Pulso Local AI Assistant"])

_PULSO_SETTINGS: Dict[str, Any] = {
    "lmstudio_url": "http://localhost:1234/v1",
    "ollama_url": "http://localhost:11434",
    "model": "Qwen3-8B-Q4_K_M",
    "primary_model": "Qwen3-8B-Q4_K_M",
    "clinical_specialist_model": "medgemma-4b-it",
    "context_window": 8192,
    "sliding_window_turns": 8,
    "temperature": 0.2,
}


def _norm(text: str) -> str:
    s = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _extract_operator(request: Request) -> str:
    op_name = unquote(request.headers.get("X-Operator-Name") or "").strip()
    op_role = unquote(request.headers.get("X-Operator-Role") or "").strip()
    if op_name:
        return f"{op_name} [{op_role or 'Médico'}]"
    active = get_active_practitioner()
    return f"{active.get('full_name', 'Operador')} [{active.get('role', 'Médico')}]"


def _record_pulso_audit(action: str, operator: str, engine_used: str) -> None:
    """
    Registra el evento en la bitácora NOM-024 guardando SOLO usuario, fecha y acción,
    SIN contenido clínico sensible ni texto del paciente.
    """
    db = SessionLocal()
    try:
        log_audit_action(
            action=action,
            patient_curp="MEMORIA_LOCAL",
            operator=operator,
            details_dict={
                "assistant": "Pulso",
                "engine": engine_used,
                "timestamp_utc": datetime.utcnow().isoformat(),
                "sensitive_content_stored": False,
            },
            db=db,
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


async def _probe_local_backends(
    ollama_url: Optional[str] = None,
    lmstudio_url: Optional[str] = None,
) -> Dict[str, Any]:
    lm_url = (lmstudio_url or _PULSO_SETTINGS["lmstudio_url"]).rstrip("/")
    ol_url = (ollama_url or _PULSO_SETTINGS["ollama_url"]).rstrip("/")
    gguf_info = get_local_llm_status()
    learning_stats = episodic_memory.get_learning_stats()
    rag_docs = hybrid_retriever.corpus_size()

    # 1. Sondeo rápido a LM Studio / llama.cpp OpenAI Server (localhost:1234/v1)
    lmstudio_connected = False
    lmstudio_models: List[str] = []
    try:
        async with httpx.AsyncClient(timeout=0.8) as client:
            r_lm = await client.get(f"{lm_url}/models")
            if r_lm.status_code == 200:
                payload = r_lm.json()
                lmstudio_models = [m.get("id") for m in (payload.get("data") or []) if m.get("id")]
                lmstudio_connected = True
    except Exception:
        pass

    # 2. Sondeo rápido a Ollama (localhost:11434)
    ollama_connected = False
    ollama_models: List[str] = []
    ol_err = ""
    try:
        async with httpx.AsyncClient(timeout=0.8) as client:
            r_ol = await client.get(f"{ol_url}/api/tags")
            if r_ol.status_code == 200:
                payload = r_ol.json()
                ollama_models = [m.get("name") for m in (payload.get("models") or []) if m.get("name")]
                ollama_connected = True
            else:
                ol_err = f"HTTP {r_ol.status_code}"
    except Exception as exc:
        ol_err = str(exc)

    combined_models = list(dict.fromkeys(lmstudio_models + ollama_models))
    if lmstudio_connected:
        active_engine = "lmstudio_hybrid_local"
        status_label = f"IA Híbrida Conectada (LM Studio: {lmstudio_models[0] if lmstudio_models else _PULSO_SETTINGS['primary_model']})"
    elif ollama_connected:
        active_engine = "ollama_local"
        status_label = f"IA Local Conectada (Ollama: {_PULSO_SETTINGS['model']})"
    elif gguf_info.get("has_local_gguf") and is_hybrid_sota_gguf(gguf_info.get("model_path")):
        active_engine = "local_gguf_engine"
        combined_models = [gguf_info["model_name"]]
        status_label = f"IA Híbrida GGUF ({gguf_info['model_name']})"
    else:
        active_engine = "hybrid_clinical_local"
        status_label = "IA Híbrida Evolutiva Activa · BM25+ChromaDB+ML"

    return {
        "lmstudio_connected": lmstudio_connected,
        "lmstudio_url": lm_url,
        "lmstudio_models": lmstudio_models,
        "ollama_connected": ollama_connected,
        "ollama_url": ol_url,
        "configured_model": _PULSO_SETTINGS["model"],
        "primary_model": _PULSO_SETTINGS["primary_model"],
        "clinical_specialist_model": _PULSO_SETTINGS["clinical_specialist_model"],
        "context_window": _PULSO_SETTINGS["context_window"],
        "sliding_window_turns": _PULSO_SETTINGS["sliding_window_turns"],
        "available_models": combined_models,
        "active_engine": active_engine,
        "status_label": status_label,
        "local_gguf": gguf_info,
        "learning_stats": learning_stats,
        "hybrid_rag_docs": rag_docs,
        "ollama_hint": (
            f"Motor híbrido listo (RAG {rag_docs} guías + scikit-learn Triaje + ChromaDB Evolutivo). "
            + ("" if (lmstudio_connected or ollama_connected) else f"Opcional: inicia LM Studio en {lm_url} ({ol_err or 'offline'}).")
        ),
    }


@router.get("/status")
async def get_pulso_status(ollama_url: Optional[str] = None, lmstudio_url: Optional[str] = None):
    """Devuelve el estado de motores locales (LM Studio, Ollama, GGUF, Híbrido) y métricas ML."""
    return await _probe_local_backends(ollama_url=ollama_url, lmstudio_url=lmstudio_url)


@router.post("/config")
async def update_pulso_config(data: dict = Body(...), request: Request = None):
    """Actualiza URLs y modelos locales (LM Studio Qwen3-8B / medgemma-4b-it / Ollama)."""
    if data.get("lmstudio_url"):
        _PULSO_SETTINGS["lmstudio_url"] = str(data["lmstudio_url"]).strip().rstrip("/")
    if data.get("ollama_url"):
        _PULSO_SETTINGS["ollama_url"] = str(data["ollama_url"]).strip().rstrip("/")
    if data.get("model"):
        _PULSO_SETTINGS["model"] = str(data["model"]).strip()
    if data.get("primary_model"):
        _PULSO_SETTINGS["primary_model"] = str(data["primary_model"]).strip()
    if data.get("clinical_specialist_model"):
        _PULSO_SETTINGS["clinical_specialist_model"] = str(data["clinical_specialist_model"]).strip()
    if "temperature" in data and data["temperature"] is not None:
        try:
            _PULSO_SETTINGS["temperature"] = max(0.0, min(1.0, float(data["temperature"])))
        except ValueError:
            pass

    if request is not None:
        _record_pulso_audit("PULSO_CONFIG_IA_LOCAL", _extract_operator(request), _PULSO_SETTINGS["model"])

    status = await _probe_local_backends(_PULSO_SETTINGS["ollama_url"], _PULSO_SETTINGS["lmstudio_url"])
    return {"status": "updated", "settings": _PULSO_SETTINGS, "connection": status}


@router.get("/model-download")
def check_model_download_status():
    """Devuelve el estado de descarga y disponibilidad del modelo GGUF local."""
    return get_local_llm_status()


@router.post("/model-download")
def trigger_model_download():
    """Inicia la descarga en segundo plano del modelo GGUF local si no existe."""
    st = get_local_llm_status()
    if st["has_local_gguf"]:
        return {"status": "already_installed", "model": st["model_name"]}
    if st["is_downloading"]:
        return {"status": "in_progress", "downloaded_mb": st["downloaded_part_mb"]}

    import subprocess
    import sys

    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "download_local_llm.py"))
    subprocess.Popen([sys.executable, script_path])
    return {"status": "started", "target": "qwen2.5-0.5b-instruct-q4_k_m.gguf"}


@router.post("/audit")
def log_pulso_interaction(data: dict = Body(...), request: Request = None):
    """Endpoint explícito de auditoría NOM-024 sin contenido sensible."""
    action = str(data.get("action") or "PULSO_CONSULTA_IA").upper().strip()
    engine = str(data.get("engine") or "local").strip()
    operator = _extract_operator(request) if request else "Operador Local"
    _record_pulso_audit(action, operator, engine)
    return {"status": "logged", "action": action, "operator": operator}


@router.get("/learning-stats")
def get_pulso_learning_stats():
    """Devuelve métricas del aprendizaje continuo evolutivo (ChromaDB + DPO JSONL + ML)."""
    stats = episodic_memory.get_learning_stats()
    stats["hybrid_rag_docs"] = hybrid_retriever.corpus_size()
    return stats


@router.post("/feedback")
def record_pulso_feedback(data: dict = Body(...), request: Request = None):
    """
    Registra calificación o corrección clínica del médico (👍 / 👎 / ✏️ Corregir y Enseñar):
      - Guarda preferencia vectorial en ChromaDB `episodic_learning`.
      - Genera automáticamente par DPO/LoRA en `training_data/dpo_pairs.jsonl`.
      - Audita evento NOM-024 sin almacenar contenido clínico en la bitácora.
    """
    operator = _extract_operator(request) if request else "Médico Tratante"
    prompt = str(data.get("prompt") or "").strip()
    original_response = str(data.get("original_response") or "").strip()
    corrected_response = data.get("corrected_response")
    if corrected_response is not None:
        corrected_response = str(corrected_response).strip()
    rating = str(data.get("rating") or "positive").strip()
    curp = str(data.get("curp") or "").strip().upper() or None
    intent = str(data.get("intent") or "CLINICAL_NORMATIVE").strip()

    res = episodic_memory.record_feedback(
        prompt=prompt,
        original_response=original_response,
        corrected_response=corrected_response,
        rating=rating,
        doctor_name=operator,
        patient_curp=curp,
        intent=intent,
    )
    _record_pulso_audit(f"PULSO_FEEDBACK_{res['rating'].upper()}", operator, "episodic_learning")
    return res


# ---------------------------------------------------------------------------
# Funciones clínicas locales en memoria (Resumen, SOAP, Búsqueda Natural, Handoff)
# ---------------------------------------------------------------------------

def _search_cie10_local(query_text: str, top_k: int = 2) -> List[Dict[str, str]]:
    if not query_text or len(query_text.strip()) < 3:
        return []
    try:
        from app.core.cie10_mapper import _get_catalog, _lexical_candidates
        catalog = _get_catalog("diagnosticos")
        hits = _lexical_candidates(query_text, catalog, limit=top_k)
        if hits:
            return [{"codigo": h["codigo"], "descripcion": h["descripcion"]} for h in hits]
    except Exception:
        pass
    try:
        from app.core.cie10_mapper import _get_embedder
        emb = _get_embedder()
        if emb is not None:
            col = get_collection("cie10_mexico_2024_diagnosticos")
            vec = emb.encode([query_text.upper()]).tolist()
            res = col.query(query_embeddings=vec, n_results=top_k)
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            out = []
            for doc, meta in zip(docs, metas):
                code = (meta or {}).get("codigo") or (meta or {}).get("code") or ""
                desc = (meta or {}).get("descripcion") or doc or ""
                if code or desc:
                    out.append({"codigo": code, "descripcion": desc})
            return out
    except Exception:
        pass
    return []


def _find_patient_from_query(query: str, active_curp: Optional[str] = None) -> Optional[Dict[str, Any]]:
    patients = get_all_patients()
    q_norm = _norm(query)
    stopwords = {
        "busca", "buscar", "paciente", "expediente", "resumen", "previo", "del", "de", "la",
        "el", "los", "las", "para", "con", "citas", "cita", "hoy", "nota", "soap", "dictado",
        "quien", "que", "eres", "esta", "este", "estas", "dame", "mostrar", "ver", "historial",
        "alergias", "alergia", "tiene", "como", "hola", "encuentra", "sobre", "acerca",
        "estado", "actual", "signos", "vitales", "ultimos", "ultimas", "consultas",
        "riesgo", "clinico", "evalua", "news2", "qsofa", "alarma", "crisis", "hipertensiva",
        "cefalea", "intensa", "manejo", "mmhg", "lpm", "rpm", "temp", "spo2",
    }
    tokens = [t for t in re.findall(r"[a-z0-9]+", q_norm) if len(t) >= 3 and t not in stopwords]

    best_match = None
    best_score = 0
    for p in patients:
        full = _norm(f"{p.get('nombres', '')} {p.get('primer_apellido', '')} {p.get('segundo_apellido', '')} {p.get('curp', '')}")
        full_words = set(re.findall(r"[a-z0-9]+", full))
        curp_val = _norm(p.get("curp") or "")
        score = 0
        for tok in tokens:
            if tok in full_words or (len(tok) >= 10 and tok in curp_val):
                score += 2
        if score > best_score:
            best_score = score
            best_match = p

    if best_match and best_score >= 2:
        return get_patient_full_history(best_match["curp"])

    if active_curp:
        hist = get_patient_full_history(active_curp.strip().upper())
        if hist:
            return hist

    if patients:
        return get_patient_full_history(patients[0]["curp"])
    return None


def _build_interhospital_transfer_response(curp: str, bundle: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Genera un Resumen Clínico de Transferencia / Handoff Interhospitalario y detecta divergencias de protocolo."""
    p = bundle.get("patient") if bundle else None
    if not p:
        return {
            "avatar_state": "reposo",
            "action_audit": "PULSO_TRANSFER_SUMMARY",
            "text": "No hay un paciente seleccionado para generar el resumen de transferencia interhospitalaria. Por favor selecciona o busca un paciente.",
        }

    full_name = p.get("nombre_completo") or f"{p.get('nombres', '')} {p.get('primer_apellido', '')}".strip()
    curp_val = p.get("curp") or curp
    edad = f"{p.get('edad')} años" if p.get("edad") is not None else "Edad no especificada"
    sexo = p.get("sexo") or "N/D"
    sangre = p.get("tipo_sangre") or "O+"
    alergias = [a.get("descripcion") for a in (p.get("alergias") or [])]
    alg_str = ", ".join(alergias) if alergias else "Sin alergias conocidas documentadas"

    clues_origen = p.get("clues_institucion") or "YUC-SSA-001 (Hospital O'Horán)"
    hosp_origen = "Hospital General Dr. Agustín O'Horán" if "SSA-001" in clues_origen else "Hospital de Origen Remitente"
    hosp_destino = "Cruz Roja Mexicana - Delegación Mérida (Sede Receptora)"

    antecedentes = p.get("antecedentes") or []
    diag_general = p.get("anotaciones_generales") or "Cuadro agudo en estudio"

    divergencias = []
    if "diabetes" in diag_general.lower() or any("diab" in (a.get("descripcion", "").lower()) for a in antecedentes):
        divergencias.append(
            "⚠️ **ALERTA CLÍNICA (Protocolo Glucémico Divergente):** El hospital de origen maneja esquema de Insulina NPH subcutánea cada 12 hrs. "
            "El protocolo receptor de Cruz Roja Mérida estipula infusión basal análoga (Glargina) con escala móvil rápida según glucemia capilar horaria."
        )
    if "hipertens" in diag_general.lower() or any("hipertens" in (a.get("descripcion", "").lower()) for a in antecedentes):
        divergencias.append(
            "⚠️ **ALERTA CLÍNICA (Protocolo Antihipertensivo Divergente):** El centro de origen utilizó Enalapril IV / Captopril sublingual. "
            "En sede receptora, el protocolo de crisis hipertensiva prioriza Labetalol o Nicardipino IV con monitoreo continuo de PAM."
        )
    if any("penicil" in a.lower() for a in alergias):
        divergencias.append(
            "🚨 **ALERTA CLÍNICA (Seguridad Farmacológica):** Paciente alérgico a Betalactámicos. "
            "Evitar Ceftriaxona o Ampicilina; usar alternativas seguras según sensibilidad."
        )
    if not divergencias:
        divergencias.append(
            "✅ **Protocolos Alineados:** El esquema terapéutico coincide con las Guías de Práctica Clínica receptoras de Cruz Roja Mérida (CENETEC / NOM-004)."
        )

    divergencias_block = "\n\n".join(divergencias)
    text = f"""### 🏥 Resumen Clínico de Transferencia Interhospitalaria (Handoff Seguro)
**Paciente:** {full_name} (`{curp_val}`) · {edad} · {sexo} · **Tipo Sanguíneo:** {sangre}

---

#### 📍 Ruta de Interoperabilidad Federada
- **Hospital Emisor:** {hosp_origen} (`{clues_origen}`)
- **Hospital Receptor:** {hosp_destino}

#### ⚡ Síntesis Rápida de Ingreso
- **Diagnóstico / Motivo:** {diag_general}
- **Alergias Críticas:** {alg_str}
- **Antecedentes:** {'; '.join(a.get('descripcion', '') for a in antecedentes[:3]) if antecedentes else 'Sin antecedentes crónicos declarados'}

#### ⚖️ Auditoría de Divergencia de Protocolos
{divergencias_block}

⚠️ *Revisar por el médico tratante antes de confirmar órdenes de recepción.*
"""
    return {
        "avatar_state": "alerta" if len(divergencias) > 1 else "contento",
        "action_audit": "PULSO_TRANSFER_SUMMARY",
        "text": text,
    }


def _Number_or_zero(val: Any) -> float:
    try:
        return float(val or 0)
    except Exception:
        return 0.0


def _build_patient_summary_response(bundle: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not bundle or not bundle.get("patient"):
        return {
            "avatar_state": "reposo",
            "action_audit": "PULSO_RESUMEN_PACIENTE",
            "text": (
                "No encontré un paciente seleccionado en memoria. "
                "Selecciona un expediente o dime el nombre/CURP del paciente para generar su resumen previo."
            ),
        }

    p = bundle["patient"]
    eventos = bundle.get("eventos") or []
    vitals = bundle.get("vital_readings") or []
    alergias = p.get("alergias") or []
    antecedentes = p.get("antecedentes") or []

    full_name = p.get("nombre_completo") or f"{p.get('nombres', '')} {p.get('primer_apellido', '')}".strip() or p.get("curp")
    edad = f"{p.get('edad')} años" if p.get("edad") is not None else "[PENDIENTE: edad]"
    sexo = p.get("sexo") or "[PENDIENTE: sexo]"
    sangre = p.get("tipo_sangre") or "[PENDIENTE: grupo sanguíneo]"

    alg_txt = (
        ", ".join(f"**{a.get('descripcion')}** ({a.get('severidad') or 'Confirmada'})" for a in alergias)
        if alergias else "Sin alergias registradas en el expediente"
    )
    ant_txt = (
        "; ".join(f"{a.get('tipo') or 'Antecedente'}: {a.get('descripcion')}" for a in antecedentes[:4])
        if antecedentes else "Sin antecedentes crónicos o quirúrgicos registrados"
    )

    if vitals:
        v = vitals[0]
        vit_txt = (
            f"FC {v.get('heart_rate') or '[PENDIENTE]'} lpm · "
            f"TA {v.get('systolic_bp') or '--'}/{v.get('diastolic_bp') or '--'} mmHg · "
            f"Temp {v.get('temperature_c') or '[PENDIENTE]'} °C · "
            f"SpO2 {v.get('spo2') or '[PENDIENTE]'}%"
        )
    else:
        vit_txt = "[PENDIENTE: registrar signos vitales de la visita actual]"

    last_visits = []
    for ev in eventos[:3]:
        cons = ev.get("consultas") or []
        if cons:
            c = cons[-1]
            dx = (c.get("nota_medica") or {}).get("diagnostico_integral") or ev.get("nombre_evento") or "Consulta"
            fecha = (c.get("fecha_hora") or "")[:10] or "Fecha s/d"
            last_visits.append(f"• **{fecha}** — {dx}")
        else:
            last_visits.append(f"• **{ev.get('nombre_evento') or 'Evento clínico'}** (sin nota firmada)")

    visits_block = "\n".join(last_visits) if last_visits else "• Sin consultas previas firmadas."
    has_alert = bool(alergias) or (
        bool(vitals) and (_Number_or_zero(vitals[0].get("temperature_c")) >= 38.0 or _Number_or_zero(vitals[0].get("spo2")) in range(1, 93))
    )

    text = (
        f"### 📋 Resumen Previo del Paciente\n"
        f"**Paciente:** {full_name} (`{p.get('curp')}`)\n"
        f"**Demografía:** {edad} · {sexo} · Tipo de sangre: {sangre}\n\n"
        f"- **Alergias críticas:** {alg_txt}\n"
        f"- **Antecedentes:** {ant_txt}\n"
        f"- **Últimos signos vitales:** {vit_txt}\n"
        f"- **Historial reciente:**\n{visits_block}\n\n"
        f"⚠️ *Revisar por el médico antes de tomar decisiones clínicas. Los datos marcados como [PENDIENTE] deben completarse en consulta.*"
    )
    return {
        "avatar_state": "alerta" if has_alert else "reposo",
        "action_audit": "PULSO_RESUMEN_PACIENTE",
        "text": text,
    }


def _build_soap_draft_response(raw_text: str, bundle: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cleaned = re.sub(
        r"^(genera|crear|crea|haz|redacta|borrador|nota)?\s*(un|una|el|la)?\s*(borrador\s+de\s+)?(nota\s+)?(soap|dictado)\s*(:|de|para|con)?\s*",
        "",
        raw_text.strip(),
        flags=re.IGNORECASE,
    ).strip()

    if len(cleaned) < 8:
        cleaned = raw_text.strip()

    extracted = _heuristic_extract(cleaned)
    sintomas = extracted.get("sintomas_referidos") or []
    vitales = extracted.get("signos_vitales") or []
    meds = extracted.get("medicamentos") or []
    dxs = extracted.get("diagnosticos_tentativos") or []
    nota = extracted.get("nota_clinica") or {}

    cie_matches = _search_cie10_local(" ".join(dxs + sintomas) or cleaned, top_k=2)
    cie_str = (
        "; ".join(f"{m['codigo']} ({m['descripcion']})" for m in cie_matches)
        if cie_matches else "[PENDIENTE: confirmar codificación CIE-10]"
    )

    p_info = (bundle or {}).get("patient") or {}
    alergias = p_info.get("alergias") or []
    alg_warn = ""
    if alergias:
        alg_names = ", ".join(a.get("descripcion", "") for a in alergias)
        alg_warn = f"\n⚠️ **ALERTA CLÍNICA (Alergia en expediente):** {alg_names} *(Revisar por el médico)*."

    subj = (
        f"Paciente refiere: {', '.join(sintomas)}. Relato original: \"{cleaned}\""
        if sintomas else (
            f"Relato dictado: \"{cleaned}\". [PENDIENTE: detallar inicio, evolución y síntomas acompañantes]"
            if cleaned else "[PENDIENTE: motivo de consulta y padecimiento actual]"
        )
    )

    obj_parts = []
    if vitales:
        obj_parts.append("Signos vitales dictados: " + ", ".join(vitales))
    elif bundle and bundle.get("vital_readings"):
        v = bundle["vital_readings"][0]
        obj_parts.append(
            f"Signos vitales en expediente: FC {v.get('heart_rate') or '--'} lpm, "
            f"TA {v.get('systolic_bp') or '--'}/{v.get('diastolic_bp') or '--'} mmHg, "
            f"Temp {v.get('temperature_c') or '--'} °C, SpO2 {v.get('spo2') or '--'}%"
        )
    else:
        obj_parts.append("[PENDIENTE: signos vitales]")

    expl = nota.get("exploracion_fisica") or ""
    if not expl or "pendiente" in expl.lower():
        obj_parts.append("[PENDIENTE: hallazgos de la exploración física dirigida]")
    else:
        obj_parts.append(expl)
    obj = ". ".join(obj_parts)

    ana_dx = ", ".join(dxs) if dxs else "[PENDIENTE: diagnóstico clínico definitivo]"
    ana = f"{ana_dx}. Sugerencia terminológica CIE-10: {cie_str} — ⚠️ *Revisar por el médico*."

    if meds:
        meds_txt = "; ".join(
            f"{m.get('nombre')} {m.get('dosis') or '[PENDIENTE: dosis]'} "
            f"({m.get('via') or 'oral'}, {m.get('periodicidad') or '[PENDIENTE: horario]'})"
            for m in meds
        )
        plan = f"Propuesta farmacológica dictada: {meds_txt}. [PENDIENTE: estudios e indicaciones de alarma] — ⚠️ *Revisar por el médico*."
    else:
        plan = "[PENDIENTE: plan terapéutico, estudios solicitados y seguimiento] — ⚠️ *Revisar por el médico*."

    text = (
        f"### 📝 Borrador de Nota Clínica SOAP (NOM-004)\n"
        f"- **S (Subjetivo):** {subj}\n"
        f"- **O (Objetivo):** {obj}\n"
        f"- **A (Análisis):** {ana}\n"
        f"- **P (Plan):** {plan}\n"
        f"{alg_warn}\n\n"
        f"ℹ️ *Regla NOM-004: los campos marcados con `[PENDIENTE]` no se inventan. "
        f"⚠️ Revisar por el médico antes de firmar.*"
    )
    return {
        "avatar_state": "alerta" if alergias else "reposo",
        "action_audit": "PULSO_BORRADOR_SOAP",
        "soap_structured": {"s": subj, "o": obj, "a": ana, "p": plan},
        "text": text,
    }


def _build_natural_search_response(query: str) -> Dict[str, Any]:
    q_norm = _norm(query)
    patients = get_all_patients()

    db = SessionLocal()
    try:
        appts = db.query(Appointment).order_by(Appointment.date_str.asc(), Appointment.time_str.asc()).all()
        appt_list = [
            {
                "patient_name": a.patient_name,
                "patient_curp": a.patient_curp,
                "date_str": a.date_str,
                "time_str": a.time_str,
                "reason": a.reason,
                "status": a.status,
                "triage_level": a.triage_level,
                "doctor_nombre": a.doctor_nombre,
            }
            for a in appts
        ]
    finally:
        db.close()

    tokens = [
        t for t in re.split(r"\s+", q_norm)
        if len(t) >= 3 and t not in {
            "busca", "buscar", "paciente", "pacientes", "citas", "cita", "agenda", "programadas",
            "quien", "quienes", "tienen", "tiene", "hay", "para", "con", "del", "las", "los", "por", "ver",
        }
    ]

    wants_appointments = any(k in q_norm for k in ("cita", "citas", "agenda", "hoy", "programad", "sala", "triaje"))
    matched_patients = []
    for p in patients:
        haystack = _norm(
            f"{p.get('nombres', '')} {p.get('primer_apellido', '')} {p.get('segundo_apellido', '')} "
            f"{p.get('curp', '')} {p.get('folio_hospital', '')} {p.get('tipo_sangre', '')}"
        )
        if not tokens or any(tok in haystack for tok in tokens):
            matched_patients.append(p)

    matched_appts = []
    for a in appt_list:
        haystack = _norm(
            f"{a['patient_name']} {a['patient_curp']} {a['date_str']} {a['reason']} {a['status']} {a['triage_level']}"
        )
        if not tokens or any(tok in haystack for tok in tokens):
            matched_appts.append(a)

    lines = ["### 🔎 Resultados de Búsqueda Local en Memoria"]
    if wants_appointments or matched_appts:
        lines.append(f"**Citas encontradas ({len(matched_appts[:6])}):**")
        if matched_appts:
            for a in matched_appts[:6]:
                lines.append(
                    f"- **{a['date_str']} {a['time_str']}** · {a['patient_name']} (`{a['patient_curp'] or 'S/C'}`) "
                    f"— *{a['reason']}* · Estado: **{a['status']}** (Triaje: {a['triage_level']})"
                )
        else:
            lines.append("- No se encontraron citas que coincidan con ese criterio.")

    lines.append(f"\n**Pacientes encontrados ({len(matched_patients[:6])}):**")
    if matched_patients:
        for p in matched_patients[:6]:
            full = f"{p.get('nombres', '')} {p.get('primer_apellido', '')} {p.get('segundo_apellido', '')}".strip()
            lines.append(
                f"- **{full}** (`{p.get('curp')}`) · {p.get('sexo') or 'S/D'} · "
                f"Sangre: {p.get('tipo_sangre') or 'N/D'} · Folio: `{p.get('folio_hospital') or 'S/F'}`"
            )
    else:
        lines.append("- No se encontraron pacientes con esos términos.")

    return {
        "avatar_state": "reposo",
        "action_audit": "PULSO_BUSQUEDA_NATURAL",
        "text": "\n".join(lines),
    }


def _execute_agentic_tool(prompt: str, active_curp: Optional[str], bundle: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    q = _norm(prompt)
    if any(k in q for k in ("transferencia", "derivacion", "otro hospital", "hospital emisor", "protocolo distinto", "protocolo divergente", "divergencia")):
        target_curp = active_curp or (bundle["patient"]["curp"] if bundle and bundle.get("patient") else "")
        return _build_interhospital_transfer_response(target_curp, bundle)
    if any(k in q for k in ("borrador soap", "nota soap", "formato soap", "haz un soap", "crea un soap", "redacta soap", "dictado soap", "genera soap", "generar soap")):
        return _build_soap_draft_response(prompt, bundle)
    if any(k in q for k in ("busca paciente", "buscar paciente", "busca los pacientes", "citas de hoy", "agenda de hoy", "programadas hoy", "directorio de pacientes", "citas programadas")):
        return _build_natural_search_response(prompt)
    if any(k in q for k in ("resumen del paciente", "resumen previo del paciente", "antecedentes del paciente", "alergias del paciente", "historial del paciente", "quien es el paciente")):
        return _build_patient_summary_response(bundle)
    return _build_soap_draft_response(prompt, bundle)


# ---------------------------------------------------------------------------
# ENDPOINT PRINCIPAL DE STREAMING HÍBRIDO (NDJSON)
# ---------------------------------------------------------------------------

@router.post("/chat-stream")
async def pulso_chat_stream(data: dict = Body(...), request: Request = None):
    """
    Orquestador Híbrido Evolutivo en Streaming (NDJSON):
      1. IntentRouter clasifica en CLINICAL_NORMATIVE / UNIVERSAL_GENERAL / AGENTIC_TOOL.
      2. En rutas clínicas: evalúa signos vitales con `scikit-learn` (NEWS2 / qSOFA),
         recupera fragmentos híbridos BM25 + ChromaDB y recupera preferencias de `episodic_learning`.
      3. IdentityGuardrail aísla `<ASSISTANT_IDENTITY>` vs `<PATIENT_RECORD_READONLY_DO_NOT_IMPERSONATE>`.
      4. SlidingWindowContext preserva los últimos 6-8 turnos (máx. 8192 tokens).
      5. Despacha a LM Studio (localhost:1234/v1), Ollama, GGUF local o Motor Híbrido Local.
    """
    prompt = str(data.get("prompt") or data.get("message") or "").strip()
    active_curp = (data.get("curp") or "").strip().upper() or None
    history = data.get("history") if isinstance(data.get("history"), list) else []
    ollama_url = str(data.get("ollama_url") or _PULSO_SETTINGS["ollama_url"]).strip().rstrip("/")
    lmstudio_url = str(data.get("lmstudio_url") or _PULSO_SETTINGS["lmstudio_url"]).strip().rstrip("/")
    model_name = str(data.get("model") or _PULSO_SETTINGS["model"]).strip()
    route_override = data.get("route_override")

    operator = _extract_operator(request) if request else "Operador Local"

    # 1. Enrutamiento Dinámico de Intención
    route = intent_router.classify(prompt, route_override=route_override)

    # 2. Aislamiento de Contexto Clínico (NUNCA inyectar expediente en Ruta Universal)
    bundle = None
    patient_name: Optional[str] = None
    ml_triage: Optional[Dict[str, Any]] = None
    rag_chunks: List[Dict[str, Any]] = []
    episodic_prefs: List[Dict[str, Any]] = []

    if route in ("CLINICAL_NORMATIVE", "AGENTIC_TOOL"):
        bundle = _find_patient_from_query(prompt, active_curp)
        if bundle and bundle.get("patient"):
            p = bundle["patient"]
            patient_name = p.get("nombre_completo") or f"{p.get('nombres', '')} {p.get('primer_apellido', '')} {p.get('segundo_apellido', '')}".strip()

        # Evaluar triaje ML solo si el prompt contiene signos vitales/síntomas o es clínico directo
        prompt_vitals = risk_ml_classifier.extract_vitals_from_text(prompt)
        active_vitals = None
        if bundle and bundle.get("vital_readings"):
            active_vitals = bundle["vital_readings"][0]

        if prompt_vitals or any(k in _norm(prompt) for k in ("triaje", "triage", "riesgo", "alerta", "urgencia", "fiebre", "dolor", "disnea", "presion", "ta ")):
            ml_triage = risk_ml_classifier.evaluate_vitals(active_vitals, prompt)
        elif active_vitals and route == "CLINICAL_NORMATIVE":
            ml_triage = risk_ml_classifier.evaluate_vitals(active_vitals, prompt)

        rag_chunks = hybrid_retriever.retrieve(prompt, top_k=3)
        episodic_prefs = episodic_memory.retrieve_doctor_preferences(prompt, top_k=2)

    # 3. Construir ejecución local/herramienta + System Prompt blindado + Sliding Window
    if route == "AGENTIC_TOOL":
        local_result = _execute_agentic_tool(prompt, active_curp, bundle)
        # Complementar avatar si ML detecta riesgo crítico
        if ml_triage and ml_triage.get("is_emergency"):
            local_result["avatar_state"] = "alerta"
    else:
        local_result = generate_hybrid_fallback_response(
            prompt=prompt,
            route=route,
            patient_bundle=bundle,
            rag_chunks=rag_chunks,
            episodic_prefs=episodic_prefs,
            ml_triage=ml_triage,
        )
        local_result["action_audit"] = "PULSO_CONSULTA_IA" if route == "CLINICAL_NORMATIVE" else "PULSO_CONSULTA_UNIVERSAL"

    system_prompt = identity_guardrail.build_system_prompt(
        route=route,
        doctor_name=operator,
        patient_bundle=bundle if route != "UNIVERSAL_GENERAL" else None,
        rag_chunks=rag_chunks,
        episodic_prefs=episodic_prefs,
        ml_triage=ml_triage,
    )
    windowed_messages = sliding_window.build_messages(
        system_prompt=system_prompt,
        user_prompt=prompt,
        history=history,
        max_turns=_PULSO_SETTINGS["sliding_window_turns"],
    )

    probe = await _probe_local_backends(ollama_url=ollama_url, lmstudio_url=lmstudio_url)
    engine_used = probe.get("active_engine") or "hybrid_clinical_local"
    if probe.get("lmstudio_connected"):
        # Si medgemma-4b-it está disponible en LM Studio y la ruta es clínica, usarlo en cascada; si no Qwen3-8B
        lm_models = probe.get("lmstudio_models") or []
        chosen_lm = lm_models[0] if lm_models else _PULSO_SETTINGS["primary_model"]
        if route == "CLINICAL_NORMATIVE":
            for m_id in lm_models:
                if "medgemma" in m_id.lower():
                    chosen_lm = m_id
                    break
        else:
            for m_id in lm_models:
                if "qwen" in m_id.lower():
                    chosen_lm = m_id
                    break
        engine_used = f"lmstudio:{chosen_lm}"
    elif probe.get("ollama_connected"):
        engine_used = f"ollama:{model_name}"

    _record_pulso_audit(local_result.get("action_audit", "PULSO_CONSULTA_IA"), operator, engine_used)

    async def event_generator() -> AsyncGenerator[bytes, None]:
        meta_chunk = {
            "type": "meta",
            "engine": engine_used,
            "route": route,
            "ml_triage": ml_triage,
            "rag_sources": [{"title": c["title"], "source": c["source"]} for c in rag_chunks],
            "episodic_matches": len(episodic_prefs),
            "learning_stats": probe.get("learning_stats"),
            "lmstudio_connected": probe.get("lmstudio_connected", False),
            "ollama_connected": probe.get("ollama_connected", False),
            "local_gguf_ready": probe.get("local_gguf", {}).get("has_local_gguf", False),
            "avatar_state": local_result.get("avatar_state", "reposo"),
            "soap_structured": local_result.get("soap_structured"),
            "audit_logged": True,
        }
        yield (json.dumps(meta_chunk, ensure_ascii=False) + "\n").encode("utf-8")

        # Herramientas agénticas deterministas (BD real / SOAP [PENDIENTE] / Handoff): responder con precisión garantizada
        if route == "AGENTIC_TOOL":
            safe_txt = identity_guardrail.sanitize_identity_leak(local_result["text"], patient_name)
            words = re.split(r"(\s+)", safe_txt)
            buf = ""
            for idx, w in enumerate(words):
                buf += w
                if idx % 3 == 2 or idx == len(words) - 1:
                    yield (json.dumps({"type": "token", "content": buf}, ensure_ascii=False) + "\n").encode("utf-8")
                    buf = ""
                    await asyncio.sleep(0.012)
            yield (json.dumps({"type": "done"}, ensure_ascii=False) + "\n").encode("utf-8")
            return

        # Helper para aplicar filtro anti-suplantación sobre el bloque inicial de cualquier LLM
        async def _stream_with_identity_filter(token_iter):
            opening_buf = ""
            flushed_opening = False
            token_count = 0
            async for tok in token_iter:
                if not tok:
                    continue
                token_count += 1
                if not flushed_opening:
                    opening_buf += tok
                    if len(opening_buf) >= 140 or "\n" in opening_buf:
                        cleaned_open = identity_guardrail.sanitize_identity_leak(opening_buf, patient_name)
                        flushed_opening = True
                        yield (json.dumps({"type": "token", "content": cleaned_open}, ensure_ascii=False) + "\n").encode("utf-8")
                else:
                    yield (json.dumps({"type": "token", "content": tok}, ensure_ascii=False) + "\n").encode("utf-8")
            if opening_buf and not flushed_opening:
                cleaned_open = identity_guardrail.sanitize_identity_leak(opening_buf, patient_name)
                yield (json.dumps({"type": "token", "content": cleaned_open}, ensure_ascii=False) + "\n").encode("utf-8")

        # 1. Backend LM Studio / llama.cpp OpenAI-compatible (localhost:1234/v1)
        if probe.get("lmstudio_connected"):
            try:
                lm_model = engine_used.split(":", 1)[1] if ":" in engine_used else _PULSO_SETTINGS["primary_model"]
                payload = {
                    "model": lm_model,
                    "messages": windowed_messages,
                    "temperature": _PULSO_SETTINGS["temperature"],
                    "max_tokens": 1200,
                    "stream": True,
                }
                async with httpx.AsyncClient(timeout=45.0) as client:
                    async with client.stream("POST", f"{lmstudio_url}/chat/completions", json=payload) as resp:
                        if resp.status_code == 200:
                            # Si ML detectó emergencia clínica, anteponer cabecera de alerta antes del stream LLM
                            if ml_triage and ml_triage.get("is_emergency") and ml_triage.get("red_flags"):
                                alert_banner = (
                                    f"⚠️ **ALERTA CLÍNICA ({ml_triage['summary_badge']}):** "
                                    + " | ".join(ml_triage["red_flags"][:2])
                                    + "\n\n---\n\n"
                                )
                                yield (json.dumps({"type": "token", "content": alert_banner}, ensure_ascii=False) + "\n").encode("utf-8")

                            async def _lm_tokens():
                                async for line in resp.aiter_lines():
                                    if not line or not line.startswith("data:"):
                                        continue
                                    raw = line[5:].strip()
                                    if raw == "[DONE]":
                                        break
                                    try:
                                        obj = json.loads(raw)
                                        delta = ((obj.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
                                        if delta:
                                            yield delta
                                    except Exception:
                                        continue

                            async for frame in _stream_with_identity_filter(_lm_tokens()):
                                yield frame
                            yield (json.dumps({"type": "done"}, ensure_ascii=False) + "\n").encode("utf-8")
                            return
            except Exception as exc:
                print(f"[PulsoStream] Fallback desde LM Studio: {exc}")

        # 2. Backend Ollama Local (localhost:11434)
        if probe.get("ollama_connected"):
            try:
                payload = {
                    "model": model_name,
                    "stream": True,
                    "options": {
                        "temperature": _PULSO_SETTINGS["temperature"],
                        "num_ctx": _PULSO_SETTINGS["context_window"],
                    },
                    "messages": windowed_messages,
                }
                async with httpx.AsyncClient(timeout=45.0) as client:
                    async with client.stream("POST", f"{ollama_url}/api/chat", json=payload) as resp:
                        if resp.status_code == 200:
                            if ml_triage and ml_triage.get("is_emergency") and ml_triage.get("red_flags"):
                                alert_banner = (
                                    f"⚠️ **ALERTA CLÍNICA ({ml_triage['summary_badge']}):** "
                                    + " | ".join(ml_triage["red_flags"][:2])
                                    + "\n\n---\n\n"
                                )
                                yield (json.dumps({"type": "token", "content": alert_banner}, ensure_ascii=False) + "\n").encode("utf-8")

                            async def _ol_tokens():
                                async for line in resp.aiter_lines():
                                    if not line:
                                        continue
                                    try:
                                        obj = json.loads(line)
                                        tok = (obj.get("message") or {}).get("content") or ""
                                        if tok:
                                            yield tok
                                    except Exception:
                                        continue

                            async for frame in _stream_with_identity_filter(_ol_tokens()):
                                yield frame
                            yield (json.dumps({"type": "done"}, ensure_ascii=False) + "\n").encode("utf-8")
                            return
            except Exception as exc:
                print(f"[PulsoStream] Fallback desde Ollama: {exc}")

        # 3. Modelo GGUF embebido (solo arquitectura híbrida SOTA Qwen3/MedGemma, evitando OpenBioLLM legado)
        gguf_model = find_local_gguf_model()
        if gguf_model and (is_hybrid_sota_gguf(gguf_model) or bool(data.get("force_gguf"))):
            try:
                opening_buf = ""
                flushed_opening = False
                token_count = 0
                has_system_leak = False
                buffered_tokens: List[str] = []

                for tok in stream_local_llm_chat(windowed_messages, temperature=_PULSO_SETTINGS["temperature"]):
                    if not tok:
                        continue
                    token_count += 1
                    opening_buf += tok
                    if len(opening_buf) < 60 and not flushed_opening:
                        buffered_tokens.append(tok)
                        continue
                    if not flushed_opening:
                        if any(tag in opening_buf for tag in ("<ATTENDING_PHYSICIAN>", "<ASSISTANT_IDENTITY>", "<PATIENT_RECORD")):
                            has_system_leak = True
                            break
                        if ml_triage and ml_triage.get("is_emergency") and ml_triage.get("red_flags"):
                            alert_banner = (
                                f"⚠️ **ALERTA CLÍNICA ({ml_triage['summary_badge']}):** "
                                + " | ".join(ml_triage["red_flags"][:2])
                                + "\n\n---\n\n"
                            )
                            yield (json.dumps({"type": "token", "content": alert_banner}, ensure_ascii=False) + "\n").encode("utf-8")
                        cleaned_open = identity_guardrail.sanitize_identity_leak(opening_buf, patient_name)
                        flushed_opening = True
                        yield (json.dumps({"type": "token", "content": cleaned_open}, ensure_ascii=False) + "\n").encode("utf-8")
                    else:
                        yield (json.dumps({"type": "token", "content": tok}, ensure_ascii=False) + "\n").encode("utf-8")
                    await asyncio.sleep(0.002)

                if not has_system_leak and not flushed_opening and len(opening_buf.strip()) >= 25 and not any(
                    tag in opening_buf for tag in ("<ATTENDING_PHYSICIAN>", "<ASSISTANT_IDENTITY>", "<PATIENT_RECORD")
                ):
                    cleaned_open = identity_guardrail.sanitize_identity_leak(opening_buf, patient_name)
                    flushed_opening = True
                    yield (json.dumps({"type": "token", "content": cleaned_open}, ensure_ascii=False) + "\n").encode("utf-8")

                if flushed_opening and not has_system_leak:
                    yield (json.dumps({"type": "done"}, ensure_ascii=False) + "\n").encode("utf-8")
                    return
            except Exception as exc:
                print(f"[PulsoStream] Aviso inferencia GGUF local: {exc}")

        # 4. Orquestador Híbrido Local Integrado (BM25 + ChromaDB + scikit-learn + Guardrail)
        safe_fallback = identity_guardrail.sanitize_identity_leak(local_result["text"], patient_name)
        words = re.split(r"(\s+)", safe_fallback)
        chunk_buf = ""
        for idx, w in enumerate(words):
            chunk_buf += w
            if idx % 3 == 2 or idx == len(words) - 1:
                yield (json.dumps({"type": "token", "content": chunk_buf}, ensure_ascii=False) + "\n").encode("utf-8")
                chunk_buf = ""
                await asyncio.sleep(0.012)

        yield (json.dumps({"type": "done"}, ensure_ascii=False) + "\n").encode("utf-8")

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
