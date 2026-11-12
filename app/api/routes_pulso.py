"""
routes_pulso.py — Backend de Asistente Clínico "Pulso" (100% IA Local + Privacidad NOM-024)
===========================================================================================
Provee:
  • GET  /api/pulso/status       — Verifica conexión con servidor local Ollama (http://localhost:11434)
                                   y lista modelos instalados + estado del Motor Clínico Local integrado.
  • POST /api/pulso/config       — Guarda URL/modelo preferido de Ollama local.
  • POST /api/pulso/chat-stream  — Respuesta en streaming (NDJSON) para:
                                     1) Resumen previo del paciente
                                     2) Borrador de nota SOAP a partir de dictado (con [PENDIENTE])
                                     3) Búsqueda de pacientes y citas en lenguaje natural
                                     4) Consulta clínica asistida (con aviso "Revisar por el médico")
                                   Usa Ollama local si está conectado o el Motor Clínico Local integrado.
  • POST /api/pulso/audit        — Registra en la bitácora NOM-024 cada acción de Pulso
                                   (usuario, fecha, acción) SIN almacenar contenido clínico sensible.
"""

from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse

from app.core.entity_extractor import _heuristic_extract
from app.db.chroma_store import get_collection
from app.db.local_db import (
    Appointment,
    SessionLocal,
    get_active_practitioner,
    get_all_patients,
    get_patient_by_curp,
    get_patient_events,
    get_patient_full_history,
    log_audit_action,
)

router = APIRouter(prefix="/api/pulso", tags=["Pulso Local AI Assistant"])

_PULSO_SETTINGS: Dict[str, Any] = {
    "ollama_url": "http://localhost:11434",
    "model": "qwen2.5:7b-instruct",
    "temperature": 0.2,
}

PULSO_SYSTEM_PROMPT = """Eres "Pulso", el asistente clínico de IA 100% LOCAL integrado en MedicAItion (Cruz Roja Mérida / Yucatán).
REGLAS CLÍNICAS Y DE SEGURIDAD OBLIGATORIAS:
1. NUNCA inventes datos clínicos, signos vitales, antecedentes ni hallazgos de exploración física.
2. Todo dato clínico que falte o no haya sido dictado DEBE marcarse literalmente como [PENDIENTE] (ej. [PENDIENTE: exploración física], [PENDIENTE: signos vitales]).
3. Toda sugerencia diagnóstica, código CIE-10 o propuesta de tratamiento DEBE incluir el aviso explícito: "⚠️ Revisar por el médico".
4. Responde en español médico claro, estructurado y conciso.
5. Si el usuario pide un borrador SOAP, estructura siempre en:
   - S (Subjetivo)
   - O (Objetivo)
   - A (Análisis / Impresión diagnóstica — Revisar por el médico)
   - P (Plan y tratamiento — Revisar por el médico)
"""


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


async def _probe_ollama(base_url: Optional[str] = None) -> Dict[str, Any]:
    url = (base_url or _PULSO_SETTINGS["ollama_url"]).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=1.8) as client:
            res = await client.get(f"{url}/api/tags")
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in (data.get("models") or []) if m.get("name")]
                return {
                    "ollama_connected": True,
                    "ollama_url": url,
                    "configured_model": _PULSO_SETTINGS["model"],
                    "available_models": models,
                    "active_engine": "ollama_local",
                    "status_label": "IA local conectada (Ollama)",
                }
    except Exception as exc:
        err_msg = str(exc)
    else:
        err_msg = f"HTTP {res.status_code}"

    return {
        "ollama_connected": False,
        "ollama_url": url,
        "configured_model": _PULSO_SETTINGS["model"],
        "available_models": [],
        "active_engine": "embedded_clinical_local",
        "status_label": "Ollama desconectado · Motor Clínico Local Activo",
        "ollama_hint": (
            f"No se detectó servidor Ollama en {url} ({err_msg}). "
            "Pulso opera con el Motor Clínico Local integrado (ChromaDB CIE-10 + Extractor SOAP Offline)."
        ),
    }


@router.get("/status")
async def get_pulso_status(ollama_url: Optional[str] = None):
    """Devuelve el estado de conexión con Ollama local y el motor clínico integrado."""
    return await _probe_ollama(ollama_url)


@router.post("/config")
async def update_pulso_config(data: dict = Body(...), request: Request = None):
    """Actualiza URL y modelo local de Ollama en Configuración."""
    if data.get("ollama_url"):
        _PULSO_SETTINGS["ollama_url"] = str(data["ollama_url"]).strip().rstrip("/")
    if data.get("model"):
        _PULSO_SETTINGS["model"] = str(data["model"]).strip()
    if "temperature" in data and data["temperature"] is not None:
        try:
            _PULSO_SETTINGS["temperature"] = max(0.0, min(1.0, float(data["temperature"])))
        except ValueError:
            pass

    if request is not None:
        _record_pulso_audit("PULSO_CONFIG_IA_LOCAL", _extract_operator(request), _PULSO_SETTINGS["model"])

    status = await _probe_ollama(_PULSO_SETTINGS["ollama_url"])
    return {"status": "updated", "settings": _PULSO_SETTINGS, "connection": status}


@router.post("/audit")
def log_pulso_interaction(data: dict = Body(...), request: Request = None):
    """Endpoint explícito de auditoría NOM-024 sin contenido sensible."""
    action = str(data.get("action") or "PULSO_CONSULTA_IA").upper().strip()
    engine = str(data.get("engine") or "local").strip()
    operator = _extract_operator(request) if request else "Operador Local"
    _record_pulso_audit(action, operator, engine)
    return {"status": "logged", "action": action, "operator": operator}


# ---------------------------------------------------------------------------
# Funciones clínicas locales en memoria (Resumen, SOAP, Búsqueda Natural)
# ---------------------------------------------------------------------------

def _search_cie10_local(query_text: str, top_k: int = 2) -> List[Dict[str, str]]:
    if not query_text or len(query_text.strip()) < 3:
        return []
    try:
        col = get_collection("cie10_mexico_2024_diagnosticos")
        res = col.query(query_texts=[query_text], n_results=top_k)
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
        return []


def _find_patient_from_query(query: str, active_curp: Optional[str] = None) -> Optional[Dict[str, Any]]:
    patients = get_all_patients()
    q_norm = _norm(query)
    stopwords = {
        "busca", "buscar", "paciente", "expediente", "resumen", "previo", "del", "de", "la",
        "el", "los", "las", "para", "con", "citas", "cita", "hoy", "nota", "soap", "dictado",
        "quien", "es", "dame", "mostrar", "ver", "historial", "alergias", "tiene", "como",
    }
    tokens = [t for t in re.split(r"\s+", q_norm) if len(t) >= 3 and t not in stopwords]

    # 1. Buscar coincidencia explícita en el texto de la pregunta
    best_match = None
    best_score = 0
    for p in patients:
        full = _norm(f"{p.get('nombres', '')} {p.get('primer_apellido', '')} {p.get('segundo_apellido', '')} {p.get('curp', '')}")
        score = sum(2 if tok in full else 0 for tok in tokens)
        if score > best_score:
            best_score = score
            best_match = p

    if best_match and best_score >= 2:
        return get_patient_full_history(best_match["curp"])

    # 2. Si no se nombró a otro, usar el paciente activo en pantalla
    if active_curp:
        hist = get_patient_full_history(active_curp.strip().upper())
        if hist:
            return hist

    if patients:
        return get_patient_full_history(patients[0]["curp"])
    return None


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
    has_alert = bool(alergias) or any(
        (vitals and (Number_or_zero(vitals[0].get("temperature_c")) >= 38.0 or Number_or_zero(vitals[0].get("spo2")) in range(1, 93)))
        for _ in [0]
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


def Number_or_zero(val: Any) -> float:
    try:
        return float(val or 0)
    except Exception:
        return 0.0


def _build_soap_draft_response(raw_text: str, bundle: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    # Limpiar prefijos de comando ("haz un soap de:", "dictado:", etc.)
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
        alg_warn = f"\n🚨 **Alerta de alergia registrada en expediente:** {alg_names} *(Revisar por el médico)*."

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
        f"### 📝 Borrador de Nota Clínica SOAP\n"
        f"- **S (Subjetivo):** {subj}\n"
        f"- **O (Objetivo):** {obj}\n"
        f"- **A (Análisis):** {ana}\n"
        f"- **P (Plan):** {plan}\n"
        f"{alg_warn}\n\n"
        f"ℹ️ *Regla de seguridad: los campos marcados con `[PENDIENTE]` no se inventan. "
        f"⚠️ Revisar por el médico antes de incorporar o firmar en el expediente NOM-004.*"
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


def _classify_and_execute_local(prompt: str, active_curp: Optional[str] = None) -> Dict[str, Any]:
    q = _norm(prompt)
    bundle = _find_patient_from_query(prompt, active_curp)

    if any(k in q for k in ("soap", "dictado", "redacta", "nota clinica", "borrador", "subjetivo", "motivo:")):
        return _build_soap_draft_response(prompt, bundle)

    if any(k in q for k in ("busca", "buscar", "citas", "cita", "agenda", "directorio", "quienes", "lista de pacientes")):
        return _build_natural_search_response(prompt)

    if any(k in q for k in ("resumen", "antecedentes", "alergias", "historial", "signos", "vitales", "paciente actual", "quien es")):
        return _build_patient_summary_response(bundle)

    # Si parece un relato clínico con síntomas/fármacos, estructurar como SOAP seguro
    if any(k in q for k in ("fiebre", "dolor", "cefalea", "tos", "mg", "cada ", "presion", "glucosa", "paciente de")):
        return _build_soap_draft_response(prompt, bundle)

    # Respuesta general asistida combinando resumen del paciente activo + guía
    summary = _build_patient_summary_response(bundle)
    return {
        "avatar_state": summary["avatar_state"],
        "action_audit": "PULSO_CONSULTA_IA",
        "text": (
            f"Soy **Pulso**, tu copiloto clínico de IA 100% local. Puedo ayudarte con:\n"
            f"1. **Resumen previo del paciente** (*\"Dame el resumen previo del paciente\"*)\n"
            f"2. **Borrador SOAP desde dictado** (*\"Borrador SOAP: paciente masculino refiere dolor...\"*)\n"
            f"3. **Búsqueda natural de pacientes y citas** (*\"Busca citas de hoy\"* o *\"Busca paciente Kevin\"*)\n\n"
            f"---\n{summary['text']}"
        ),
    }


@router.post("/chat-stream")
async def pulso_chat_stream(data: dict = Body(...), request: Request = None):
    """
    Endpoint de chat en streaming (NDJSON) para el asistente Pulso.
    - Si Ollama (`http://localhost:11434`) está disponible, transmite tokens reales desde Ollama
      enriquecidos con el contexto local en memoria (sin salir del equipo).
    - Si Ollama está desconectado, transmite en streaming desde el Motor Clínico Local integrado.
    - Registra la acción en la bitácora NOM-024 sin almacenar datos sensibles.
    """
    prompt = str(data.get("prompt") or data.get("message") or "").strip()
    active_curp = (data.get("curp") or "").strip().upper() or None
    ollama_url = str(data.get("ollama_url") or _PULSO_SETTINGS["ollama_url"]).strip().rstrip("/")
    model_name = str(data.get("model") or _PULSO_SETTINGS["model"]).strip()

    operator = _extract_operator(request) if request else "Operador Local"
    local_result = _classify_and_execute_local(prompt, active_curp)
    probe = await _probe_ollama(ollama_url)

    engine_used = f"ollama:{model_name}" if probe["ollama_connected"] else "embedded_clinical_local"
    _record_pulso_audit(local_result["action_audit"], operator, engine_used)

    async def event_generator() -> AsyncGenerator[bytes, None]:
        meta_chunk = {
            "type": "meta",
            "engine": engine_used,
            "ollama_connected": probe["ollama_connected"],
            "avatar_state": local_result.get("avatar_state", "reposo"),
            "soap_structured": local_result.get("soap_structured"),
            "audit_logged": True,
        }
        yield (json.dumps(meta_chunk, ensure_ascii=False) + "\n").encode("utf-8")

        if probe["ollama_connected"]:
            try:
                context_msg = (
                    f"CONTEXTO LOCAL EN MEMORIA (NO INVENTAR NADA FUERA DE ESTO):\n"
                    f"{local_result['text']}\n\n"
                    f"SOLICITUD DEL MÉDICO:\n{prompt}"
                )
                payload = {
                    "model": model_name,
                    "stream": True,
                    "options": {"temperature": _PULSO_SETTINGS["temperature"]},
                    "messages": [
                        {"role": "system", "content": PULSO_SYSTEM_PROMPT},
                        {"role": "user", "content": context_msg},
                    ],
                }
                async with httpx.AsyncClient(timeout=45.0) as client:
                    async with client.stream("POST", f"{ollama_url}/api/chat", json=payload) as resp:
                        if resp.status_code == 200:
                            async for line in resp.aiter_lines():
                                if not line:
                                    continue
                                try:
                                    obj = json.loads(line)
                                    token = (obj.get("message") or {}).get("content") or ""
                                    if token:
                                        yield (json.dumps({"type": "token", "content": token}, ensure_ascii=False) + "\n").encode("utf-8")
                                except Exception:
                                    continue
                            yield (json.dumps({"type": "done"}, ensure_ascii=False) + "\n").encode("utf-8")
                            return
            except Exception:
                pass

        # Streaming local token a token desde el motor clínico integrado
        words = re.split(r"(\s+)", local_result["text"])
        chunk_buf = ""
        for idx, w in enumerate(words):
            chunk_buf += w
            if idx % 4 == 3 or idx == len(words) - 1:
                yield (json.dumps({"type": "token", "content": chunk_buf}, ensure_ascii=False) + "\n").encode("utf-8")
                chunk_buf = ""
                await asyncio.sleep(0.012)

        yield (json.dumps({"type": "done"}, ensure_ascii=False) + "\n").encode("utf-8")

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
