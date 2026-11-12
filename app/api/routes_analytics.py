"""
routes_analytics.py — MedicAItion Sprint 2
===========================================
Vigilancia epidemiológica y métricas operativas calculadas en tiempo real
desde las consultas reales (CIE-10), la agenda y la telemetría.

Endpoints:
  GET /api/analytics/epidemiology   — Grupos sindromáticos por semana (CIE-10 + texto)
  GET /api/analytics/tasks          — Tareas y alertas pendientes del médico (accionables)
  GET /api/analytics/summary        — KPIs operativos para Reportes y Estadísticas
"""

import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter

from app.core.crypto_vault import decrypt_text
from app.db.local_db import SessionLocal, Consulta, Patient, Appointment, VitalReading, Alergia

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# Grupos de vigilancia: (clave, etiqueta, prefijos CIE-10, palabras clave)
SURVEILLANCE_GROUPS = [
    ("dengue", "Dengue / Arbovirosis", ("A90", "A91", "A92", "A97"), ("dengue", "chikungunya", "zika", "arbovirosis")),
    ("respiratoria", "Infección Respiratoria Aguda", ("J00", "J01", "J02", "J03", "J04", "J05", "J06", "J09", "J10", "J11", "J12", "J18", "J20", "J21", "J22", "U07"), ("respiratoria", "faringitis", "amigdalitis", "neumonia", "bronquitis", "influenza", "covid", "resfriado")),
    ("eda", "Enfermedad Diarreica Aguda", ("A00", "A01", "A02", "A03", "A04", "A05", "A06", "A08", "A09"), ("diarrea", "gastroenteritis", "diarreica")),
    ("diabetes", "Diabetes descompensada", ("E10", "E11", "E12", "E13", "E14"), ("diabetes", "hiperglucemia", "cetoacidosis")),
    ("hipertension", "Hipertensión / Crisis", ("I10", "I11", "I12", "I13", "I15", "I16"), ("hipertension", "crisis hipertensiva")),
    ("cardio", "Síndrome Coronario / Cardiovascular", ("I20", "I21", "I22", "I24", "I63", "I64"), ("infarto", "coronario", "angina", "evc", "ictus")),
]


def _norm(text) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _safe_json(raw):
    if not raw:
        return {}
    try:
        plain = decrypt_text(raw)
        val = json.loads(plain)
        return val if isinstance(val, dict) else {}
    except (TypeError, ValueError):
        return {}


def classify_consulta(entidades: dict, nota: dict, texto: str) -> set:
    """Devuelve el conjunto de grupos de vigilancia a los que pertenece una consulta."""
    groups = set()
    codes = []
    for items in (entidades.get("codigos_cie10") or {}).values():
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and it.get("codigo"):
                    codes.append(str(it["codigo"]).upper())

    blob = _norm(" ".join([
        " ".join(str(d) for d in entidades.get("diagnosticos_tentativos") or []),
        str(nota.get("diagnostico_integral") or ""),
    ]))

    for key, _label, prefixes, keywords in SURVEILLANCE_GROUPS:
        if any(c.startswith(prefixes) for c in codes) or any(k in blob for k in keywords):
            groups.add(key)
    return groups


@router.get("/epidemiology")
def epidemiology(weeks: int = 8):
    weeks = max(2, min(weeks, 26))
    now = datetime.utcnow()
    start = now - timedelta(weeks=weeks)
    this_week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    db = SessionLocal()
    try:
        consultas = db.query(Consulta).filter(Consulta.fecha_hora >= start).all()
        total = len(consultas)
        group_counts = Counter()
        this_week = Counter()
        prev_week = Counter()
        weekly = {}  # week_index -> Counter
        this_week_total = 0

        for c in consultas:
            ent = _safe_json(c.entidades_json)
            nota = _safe_json(c.nota_medica_json)
            groups = classify_consulta(ent, nota, decrypt_text(c.texto_original or "") or "")
            fh = c.fecha_hora or now
            wk = max(0, min(weeks - 1, int((now - fh).days // 7)))
            weekly.setdefault(wk, Counter())
            if fh >= this_week_start:
                this_week_total += 1
            for g in groups:
                group_counts[g] += 1
                weekly[wk][g] += 1
                if fh >= this_week_start:
                    this_week[g] += 1
                elif fh >= prev_week_start:
                    prev_week[g] += 1

        groups_out = []
        for key, label, _p, _k in SURVEILLANCE_GROUPS:
            cur, prev = this_week[key], prev_week[key]
            if prev > 0:
                change = round(((cur - prev) / prev) * 100, 1)
            else:
                change = 100.0 if cur > 0 else 0.0
            share = round((group_counts[key] / total) * 100, 1) if total else 0.0
            series = [weekly.get(w, Counter())[key] for w in range(weeks - 1, -1, -1)]
            level = "ALTA" if (cur >= 3 and change >= 25) or share >= 30 else "MEDIA" if cur >= 1 else "BAJA"
            groups_out.append({
                "key": key,
                "label": label,
                "total": group_counts[key],
                "this_week": cur,
                "prev_week": prev,
                "change_pct": change,
                "share_pct": share,
                "series": series,
                "alert_level": level,
            })

        groups_out.sort(key=lambda g: (g["this_week"], g["total"]), reverse=True)
        top = groups_out[0] if groups_out and groups_out[0]["total"] > 0 else None
        return {
            "generated_at": now.isoformat(),
            "window_weeks": weeks,
            "total_consultas": total,
            "consultas_semana": this_week_total,
            "top_alert": top,
            "groups": groups_out,
            "fuente": "Consultas registradas en MedicAItion (CIE-10 + diagnóstico integral)",
        }
    finally:
        db.close()


@router.get("/tasks")
def pending_tasks():
    """Lista priorizada de tareas accionables para el médico."""
    today = datetime.now().strftime("%Y-%m-%d")
    since = datetime.utcnow() - timedelta(hours=24)
    db = SessionLocal()
    tasks = []
    try:
        # 1. Pacientes críticos en sala hoy
        crit = db.query(Appointment).filter(
            Appointment.date_str == today,
            Appointment.status.in_(["En Sala / Triaje", "Programada"]),
            Appointment.triage_level.in_(["ROJO", "NARANJA"]),
        ).all()
        for a in crit:
            tasks.append({
                "priority": "CRITICA",
                "type": "triaje",
                "title": f"Atender prioridad {a.triage_level}: {a.patient_name}",
                "detail": f"{a.time_str} • {a.reason}",
                "action": {"kind": "start_appt", "id": a.id, "curp": a.patient_curp or "", "name": a.patient_name},
            })

        # 2. Alertas biométricas de wearables (últimas 24h)
        vitals = db.query(VitalReading).filter(
            VitalReading.alert_flag == True,  # noqa: E712
            VitalReading.recorded_at >= since,
        ).order_by(VitalReading.recorded_at.desc()).limit(5).all()
        for v in vitals:
            tasks.append({
                "priority": "ALTA",
                "type": "wearable",
                "title": f"Alerta biométrica: {v.patient_name or v.patient_curp or v.device_name}",
                "detail": v.alert_message or "Valor fuera de rango",
                "action": {"kind": "open_profile", "curp": v.patient_curp or ""},
            })

        # 3. Consultas firmadas con override de seguridad farmacológica (revisión)
        recent = db.query(Consulta).filter(Consulta.fecha_hora >= datetime.utcnow() - timedelta(days=7)).all()
        overrides = 0
        for c in recent:
            ent = _safe_json(c.entidades_json)
            if ent.get("justificacion_seguridad"):
                overrides += 1
        if overrides:
            tasks.append({
                "priority": "ALTA",
                "type": "seguridad",
                "title": f"{overrides} receta(s) con alerta crítica autorizada por justificación",
                "detail": "Revisar evolución y tolerancia de los pacientes en los últimos 7 días",
                "action": {"kind": "goto", "tab": "expedientes"},
            })

        # 4. Pacientes en sala esperando
        waiting = db.query(Appointment).filter(
            Appointment.date_str == today,
            Appointment.status == "En Sala / Triaje",
        ).count()
        if waiting:
            tasks.append({
                "priority": "MEDIA",
                "type": "sala",
                "title": f"{waiting} paciente(s) esperando en sala",
                "detail": "Abrir la cola de atención del día",
                "action": {"kind": "goto", "tab": "agenda"},
            })

        # 5. Pacientes con datos incompletos (peso/talla necesarios para dosis seguras)
        incomplete = db.query(Patient).filter((Patient.peso_kg == None) | (Patient.altura_cm == None)).count()  # noqa: E711
        if incomplete:
            tasks.append({
                "priority": "BAJA",
                "type": "expediente",
                "title": f"{incomplete} expediente(s) sin peso/talla",
                "detail": "Necesarios para cálculo de IMC y dosis por kg",
                "action": {"kind": "goto", "tab": "expedientes"},
            })

        order = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2, "BAJA": 3}
        tasks.sort(key=lambda t: order.get(t["priority"], 9))
        return {"total": len(tasks), "tasks": tasks}
    finally:
        db.close()


@router.get("/summary")
def summary():
    now = datetime.utcnow()
    today = datetime.now().strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        total_patients = db.query(Patient).count()
        total_consultas = db.query(Consulta).count()
        consultas_30d = db.query(Consulta).filter(Consulta.fecha_hora >= now - timedelta(days=30)).count()
        today_appts = db.query(Appointment).filter(Appointment.date_str == today).all()
        noshow = db.query(Appointment).filter(Appointment.status == "No asistió").count()
        total_appts = db.query(Appointment).count()
        alertas_vitales = db.query(VitalReading).filter(VitalReading.alert_flag == True).count()  # noqa: E712
        alergias = db.query(Alergia).count()

        triage_counts = Counter(a.triage_level for a in today_appts)
        status_counts = Counter(a.status for a in today_appts)

        dx_counter = Counter()
        for c in db.query(Consulta).filter(Consulta.fecha_hora >= now - timedelta(days=90)).all():
            ent = _safe_json(c.entidades_json)
            for items in (ent.get("codigos_cie10") or {}).values():
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict) and it.get("codigo"):
                            dx_counter[f"{it['codigo']} — {it.get('descripcion') or it.get('termino_original') or ''}".strip(" —")] += 1

        return {
            "pacientes": total_patients,
            "consultas_total": total_consultas,
            "consultas_30d": consultas_30d,
            "citas_hoy": len(today_appts),
            "atendidas_hoy": status_counts.get("Atendida", 0),
            "tasa_inasistencia_pct": round((noshow / total_appts) * 100, 1) if total_appts else 0.0,
            "alertas_biometricas": alertas_vitales,
            "alergias_registradas": alergias,
            "triaje_hoy": {k: triage_counts.get(k, 0) for k in ("ROJO", "NARANJA", "AMARILLO", "VERDE")},
            "estado_hoy": dict(status_counts),
            "top_diagnosticos": [{"label": k, "count": v} for k, v in dx_counter.most_common(8)],
        }
    finally:
        db.close()
