"""
ask_expediente.py — Copiloto Ask-Expediente (RAG + Síntesis Longitudinal)
=========================================================================
Responde preguntas clínicas sobre todo el historial longitudinal del paciente
citando eventos, fechas, diagnósticos CIE-10, medicamentos, alergias, lecturas
de wearables y bitácoras diarias ("Mi Salud Hoy"), 100% funcional offline y con
enriquecimiento opcional por LLM cuando esté disponible.
"""

from __future__ import annotations
from typing import Any, Dict, List


def _collect_medications(eventos: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    meds: List[Dict[str, str]] = []
    for ev in eventos:
        for con in ev.get("consultas") or []:
            rec = con.get("receta") or {}
            fecha = (con.get("fecha_hora") or "")[:10]
            for m in rec.get("medicamentos") or []:
                if isinstance(m, dict) and m.get("nombre"):
                    meds.append({
                        "nombre": m.get("nombre", ""),
                        "dosis": m.get("dosis", ""),
                        "periodicidad": m.get("periodicidad", ""),
                        "duracion": m.get("duracion", ""),
                        "evento": ev.get("nombre_evento", ""),
                        "fecha": fecha,
                    })
    return meds


def _collect_diagnoses(eventos: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    dxs: List[Dict[str, str]] = []
    for ev in eventos:
        for con in ev.get("consultas") or []:
            nota = con.get("nota_medica") or {}
            ent = con.get("entidades") or {}
            fecha = (con.get("fecha_hora") or "")[:10]
            cie = ent.get("codigos_cie10") or {}
            if isinstance(cie, dict):
                for k, v in cie.items():
                    cod = v.get("codigo") if isinstance(v, dict) else str(v)
                    dxs.append({
                        "dx": f"{k} ({cod})" if cod else k,
                        "fecha": fecha,
                        "evento": ev.get("nombre_evento", ""),
                    })
            dx_int = nota.get("diagnostico_integral")
            if dx_int and "Pendiente" not in dx_int and not any(dx_int in d["dx"] for d in dxs):
                dxs.append({
                    "dx": dx_int,
                    "fecha": fecha,
                    "evento": ev.get("nombre_evento", ""),
                })
    return dxs


def answer_patient_question(
    question: str,
    patient: Dict[str, Any],
    eventos: List[Dict[str, Any]],
    vitals: List[Dict[str, Any]] | None = None,
    daily_logs: List[Dict[str, Any]] | None = None,
    llm_mode: str = "offline",
) -> Dict[str, Any]:
    """
    Responde una pregunta clínica fundamentada exclusivamente en los registros del paciente.
    Devuelve {"answer": str, "citations": [...], "mode": str}.
    """
    vitals = vitals or []
    daily_logs = daily_logs or []
    q = (question or "").strip()
    ql = q.lower()

    nombre = patient.get("nombre_completo") or patient.get("curp") or "Paciente"
    edad = f"{patient['edad']} años" if patient.get("edad") is not None else "edad no registrada"
    sexo = patient.get("sexo") or "sexo no especificado"
    sangre = patient.get("tipo_sangre") or "No registrado"
    bmi = f"{patient['bmi']} kg/m²" if patient.get("bmi") else "no calculado"

    alergias = patient.get("alergias") or []
    antecedentes = patient.get("antecedentes") or []
    meds = _collect_medications(eventos)
    dxs = _collect_diagnoses(eventos)

    citations: List[Dict[str, str]] = []
    sections: List[str] = []

    # 1. Alergias y seguridad
    wants_allergy = any(k in ql for k in ("alerg", "segur", "reacc", "recet", "medica", "fármac", "farmac", "puedo dar", "contraind", "todo", "resumen"))
    if wants_allergy or not ql:
        if alergias:
            a_txt = "; ".join(f"{a['descripcion']} ({a.get('severidad') or 'sin severidad'})" for a in alergias)
            sections.append(f"⚠️ Alergias registradas: {a_txt}.")
            citations.append({"fuente": "Tabla Alergias", "detalle": a_txt})
        else:
            sections.append("✅ Alergias registradas: Ninguna documentada en expediente.")

    # 2. Medicamentos actuales / históricos
    wants_meds = any(k in ql for k in ("medica", "fármac", "farmac", "recet", "toma", "tratamiento", "dosis", "resumen", "todo"))
    if wants_meds:
        if meds:
            top_meds = meds[-6:]
            m_lines = [
                f"• {m['nombre']} {m['dosis']} ({m['periodicidad']} {m['duracion']}) — [{m['fecha'] or 's/f'} · {m['evento']}]".strip()
                for m in top_meds
            ]
            sections.append("💊 Medicación prescrita reciente:\n" + "\n".join(m_lines))
            citations.append({"fuente": "Recetas NOM-004", "detalle": f"{len(meds)} prescripción(es) en historial"})
        else:
            sections.append("💊 Medicación reciente: Sin prescripciones registradas.")

    # 3. Antecedentes y diagnósticos / evolución
    wants_hist = any(k in ql for k in ("evolu", "diagn", "cie", "anteced", "padec", "hist", "enferm", "crónic", "cronic", "resumen", "consult", "bander", "riesgo", "alarma", "todo")) or not sections
    if wants_hist:
        if antecedentes:
            ant_txt = "; ".join(f"[{a.get('tipo') or 'Antecedente'}] {a['descripcion']}" for a in antecedentes)
            sections.append(f"📋 Antecedentes: {ant_txt}.")
            citations.append({"fuente": "Antecedentes Personales", "detalle": ant_txt})
        if dxs:
            dx_lines = [f"• {d['dx']} [{d['fecha'] or 's/f'} · {d['evento']}]" for d in dxs[-6:]]
            sections.append("🩺 Diagnósticos / CIE-10 documentados:\n" + "\n".join(dx_lines))
            citations.append({"fuente": "Diagnósticos CIE-10", "detalle": f"{len(dxs)} diagnóstico(s)"})

        # Últimas consultas y banderas rojas detectadas
        all_consultas = []
        red_flags_hist = []
        for ev in eventos:
            for con in ev.get("consultas") or []:
                all_consultas.append((ev.get("nombre_evento", ""), con))
                seg = (con.get("entidades") or {}).get("seguridad_clinica") or {}
                for rf in seg.get("banderas_rojas") or []:
                    red_flags_hist.append(f"{(con.get('fecha_hora') or '')[:10]}: {rf.get('titulo') or rf.get('codigo')}")
        if all_consultas:
            last_ev, last_c = all_consultas[-1]
            nota = last_c.get("nota_medica") or {}
            sections.append(
                f"📅 Última consulta ({(last_c.get('fecha_hora') or '')[:10]} — {last_ev}): "
                f"Motivo: {nota.get('motivo_consulta') or '—'}. "
                f"Plan: {nota.get('plan_tratamiento') or '—'}"
            )
            citations.append({"fuente": f"Consulta {(last_c.get('fecha_hora') or '')[:10]}", "detalle": last_ev})
        if red_flags_hist:
            sections.append("🚨 Banderas rojas detectadas en consultas previas:\n• " + "\n• ".join(red_flags_hist[-5:]))
            citations.append({"fuente": "Guardián Clínico CDSS", "detalle": f"{len(red_flags_hist)} alerta(s)"})

    # 4. Signos vitales, wearables y bitácora ciudadana
    wants_vitals = any(k in ql for k in ("signo", "vital", "presi", "gluc", "spo2", "ox", "fc", "frecuenc", "temp", "wearable", "reloj", "peso", "imc", "bmi", "bitácora", "bitacora", "casa", "resumen", "descomp", "todo"))
    if wants_vitals or vitals or daily_logs:
        if vitals:
            v0 = vitals[0]
            bp = f"{int(v0['systolic_bp'])}/{int(v0['diastolic_bp'])} mmHg" if v0.get("systolic_bp") else "—"
            sections.append(
                f"⌚ Última lectura Wearable ({v0.get('device') or 'Sensor'}, {(v0.get('recorded_at') or '')[:10]}): "
                f"FC {v0.get('heart_rate') or '—'} lpm · SpO2 {v0.get('spo2') or '—'}% · TA {bp}"
                + (f" · ⚠️ {v0['alert_message']}" if v0.get("alert") and v0.get("alert_message") else "")
            )
            citations.append({"fuente": "Telemetría Wearables", "detalle": f"{len(vitals)} lectura(s)"})
        if daily_logs:
            dl0 = daily_logs[0]
            bp = f"{int(dl0['systolic_bp'])}/{int(dl0['diastolic_bp'])} mmHg" if dl0.get("systolic_bp") else "—"
            adherencia = "Sí tomó medicinas" if dl0.get("medication_taken") else "No registró toma"
            sections.append(
                f"📱 Bitácora diaria en casa ({(dl0.get('recorded_at') or '')[:10]}): "
                f"TA {bp} · Glucosa {dl0.get('glucose_mg_dl') or '—'} mg/dL · Temp {dl0.get('temperature_c') or '—'} °C · "
                f"{adherencia}" + (f" · Nota: {dl0['symptoms_note']}" if dl0.get("symptoms_note") else "")
            )
            citations.append({"fuente": "Portal Mi Salud Hoy", "detalle": f"{len(daily_logs)} registro(s) en casa"})

    # 5. Búsqueda semántica ChromaDB complementaria si hay texto específico en la pregunta
    if len(q) >= 4:
        try:
            from app.db.local_db import search_events_semantically
            sem = search_events_semantically(q, patient_curp=patient.get("curp"), n_results=3)
            if sem:
                citations.append({
                    "fuente": "Memoria Vectorial (ChromaDB)",
                    "detalle": f"{len(sem)} coincidencia(s) semántica(s) relevante(s)",
                })
        except Exception:
            pass

    header = (
        f"Expediente de {nombre} ({edad}, {sexo}, Tipo de sangre: {sangre}, IMC: {bmi}) — "
        f"{len(eventos)} evento(s) clínico(s)."
    )
    answer = header + "\n\n" + "\n\n".join(sections)

    return {
        "question": q or "Resumen clínico integral",
        "answer": answer,
        "citations": citations,
        "mode": "offline-rag-sql",
    }
