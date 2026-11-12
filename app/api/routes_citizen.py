"""
routes_citizen.py — MedicAItion v5.5 (Sprint 3)
====================================================
Ecosistema Ciudadano y Pasaporte Médico QR (ICE):
  • GET  /ice/{curp}                   — Tarjeta / Pasaporte Médico de Emergencia QR (HTML móvil <2s)
  • GET  /api/ice/{curp}               — Payload JSON del Pasaporte ICE (datos vitales de rescate)
  • GET  /api/ice/{curp}/qr            — Código QR en SVG apuntando a /ice/{curp}
  •GET   /mi-salud/{curp}              — Portal Diario del Paciente "Mi Salud Hoy" (HTML móvil interactivo)
  • GET  /api/patient-portal/{curp}    — Plan de alta amigable, horario de medicinas y bitácora diaria
  • POST /api/patient-portal/{curp}/logs — Registro diario de presión, glucosa, temperatura y síntomas
"""

from __future__ import annotations
import html
import re
from typing import Any, Dict, List
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from app.core.qr_svg import generate_qr_svg
from app.db.local_db import (
    add_patient_daily_log,
    check_patient_exists,
    get_latest_consent,
    get_patient_daily_logs,
    get_patient_full_history,
    get_patient_upcoming_appointments,
)

router = APIRouter(tags=["Citizen Portal & ICE"])


def _build_ice_payload(curp: str) -> Dict[str, Any]:
    bundle = get_patient_full_history(curp.upper())
    if not bundle:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    p = bundle["patient"]
    eventos = bundle["eventos"]

    # Extraer medicamentos de las últimas recetas (máx 6 únicos)
    meds_seen = set()
    current_meds: List[Dict[str, str]] = []
    for ev in eventos:
        for con in reversed(ev.get("consultas") or []):
            rec = con.get("receta") or {}
            for m in rec.get("medicamentos") or []:
                if isinstance(m, dict) and m.get("nombre"):
                    key = m["nombre"].strip().lower()
                    if key not in meds_seen:
                        meds_seen.add(key)
                        current_meds.append({
                            "nombre": m.get("nombre", ""),
                            "dosis": m.get("dosis", ""),
                            "periodicidad": m.get("periodicidad", ""),
                        })
            if len(current_meds) >= 6:
                break

    return {
        "curp": p.get("curp"),
        "nombre_completo": p.get("nombre_completo") or p.get("curp"),
        "edad": p.get("edad"),
        "sexo": p.get("sexo"),
        "tipo_sangre": p.get("tipo_sangre") or "No especificado",
        "folio_hospital": p.get("folio_hospital"),
        "alergias": [
            {"descripcion": a.get("descripcion"), "severidad": a.get("severidad") or "Confirmada"}
            for a in (p.get("alergias") or [])
        ],
        "condiciones_cronicas": [
            {"tipo": ant.get("tipo") or "Antecedente", "descripcion": ant.get("descripcion")}
            for ant in (p.get("antecedentes") or [])
        ],
        "medicamentos_actuales": current_meds,
        "contacto_emergencia": {
            "nombre": p.get("contacto_emergencia_nombre") or "No registrado",
            "telefono": p.get("contacto_emergencia_tel") or p.get("celular") or "",
        },
        "institucion_origen": p.get("clues_institucion") or "YUC-CR-001 (Cruz Roja Mérida)",
    }


def _infer_med_slots(med: Dict[str, Any]) -> List[str]:
    p = (med.get("periodicidad") or "").lower()
    slots: List[str] = []
    if any(k in p for k in ("6 h", "6h", "4 veces")):
        return ["Mañana (07:00)", "Mediodía (13:00)", "Tarde (19:00)", "Madrugada (01:00)"]
    if any(k in p for k in ("8 h", "8h", "3 veces")):
        return ["Mañana (08:00)", "Tarde (16:00)", "Noche (24:00)"]
    if any(k in p for k in ("12 h", "12h", "2 veces", "cada 12")):
        return ["Mañana (08:00)", "Noche (20:00)"]
    if "mañana" in p or "desayuno" in p or "ayuno" in p:
        slots.append("Mañana (08:00)")
    if "noche" in p or "acostar" in p or "cena" in p:
        slots.append("Noche (21:00)")
    if "24 h" in p or "cada día" in p or "1 vez" in p:
        if not slots:
            slots.append("Mañana (08:00)")
    if not slots:
        slots.append("Según indicación médica")
    return slots


def _build_red_flags(patient: Dict[str, Any], eventos: List[Dict[str, Any]]) -> List[str]:
    flags = [
        "Dificultad para respirar, sensación de falta de aire o labios morados",
        "Dolor opresivo en el pecho que irradia a brazo, mandíbula o espalda",
        "Confusión súbita, debilidad de un lado del cuerpo, dificultad para hablar o desmayo",
    ]
    text_blob = " ".join(
        (a.get("descripcion") or "") for a in (patient.get("antecedentes") or [])
    ).lower()
    for ev in eventos[:3]:
        text_blob += " " + (ev.get("nombre_evento") or "").lower()
        for con in (ev.get("consultas") or [])[-2:]:
            nota = con.get("nota_medica") or {}
            text_blob += " " + (nota.get("diagnostico_integral") or "").lower()

    if any(k in text_blob for k in ("dengue", "febril", "plaquet")):
        flags.insert(0, "Dengue — Ir a Urgencias de inmediato ante: dolor abdominal intenso, vómito persistente o sangrado en encías/nariz")
    if any(k in text_blob for k in ("diabet", "gluc", "dm2")):
        flags.insert(0, "Glucosa < 70 mg/dL (sudoración fría/temblor) o ≥ 250 mg/dL con malestar/vómito")
    if any(k in text_blob for k in ("hipert", "hta", "presi")):
        flags.insert(0, "Presión arterial ≥ 160/100 mmHg acompañada de dolor de cabeza intenso, mareo o visión borrosa")
    return flags[:5]


def _build_portal_payload(curp: str) -> Dict[str, Any]:
    bundle = get_patient_full_history(curp.upper())
    if not bundle:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    p = bundle["patient"]
    eventos = bundle["eventos"]
    vitals = bundle["vital_readings"]
    daily_logs = bundle["patient_daily_logs"]

    latest_consult = None
    for ev in eventos:
        cons = ev.get("consultas") or []
        if cons:
            latest_consult = cons[-1]
            break

    meds = []
    horario: Dict[str, List[Dict[str, str]]] = {
        "Mañana": [],
        "Mediodía / Tarde": [],
        "Noche": [],
        "Según indicación": [],
    }
    receta_texto = ""
    if latest_consult:
        rec = latest_consult.get("receta") or {}
        receta_texto = rec.get("instrucciones") or ""
        for m in rec.get("medicamentos") or []:
            if not isinstance(m, dict) or not m.get("nombre"):
                continue
            slots = _infer_med_slots(m)
            med_entry = {
                "nombre": m.get("nombre", ""),
                "dosis": m.get("dosis", ""),
                "via": m.get("via", "Oral"),
                "periodicidad": m.get("periodicidad", ""),
                "duracion": m.get("duracion", ""),
                "horarios": slots,
            }
            meds.append(med_entry)
            for s in slots:
                if "Mañana" in s:
                    horario["Mañana"].append(med_entry)
                elif "Mediodía" in s or "Tarde" in s:
                    horario["Mediodía / Tarde"].append(med_entry)
                elif "Noche" in s or "Madrugada" in s:
                    horario["Noche"].append(med_entry)
                else:
                    horario["Según indicación"].append(med_entry)

    last_diag = "Control y prevención general"
    if latest_consult:
        last_diag = (latest_consult.get("nota_medica") or {}).get("diagnostico_integral") or last_diag

    return {
        "curp": p.get("curp"),
        "nombre_completo": p.get("nombre_completo") or p.get("curp"),
        "edad": p.get("edad"),
        "tipo_sangre": p.get("tipo_sangre") or "No especificado",
        "ultimo_diagnostico": last_diag,
        "ultima_consulta_fecha": (latest_consult or {}).get("fecha_hora"),
        "doctor_nombre": (latest_consult or {}).get("doctor_nombre") or "Equipo Médico Cruz Roja",
        "receta_amigable": receta_texto or "Sigue tus horarios indicados y registra tus signos diariamente.",
        "medicamentos": meds,
        "horario_visual": horario,
        "banderas_rojas": _build_red_flags(p, eventos),
        "daily_logs": daily_logs,
        "latest_wearable": vitals[0] if vitals else None,
        "citas_proximas": get_patient_upcoming_appointments(curp.upper()),
        "consentimiento": get_latest_consent(curp.upper()),
    }


@router.get("/api/ice/{curp}")
def get_ice_json(curp: str):
    """Devuelve el Pasaporte Médico de Emergencia (ICE) en JSON (respetando revocación/permiso LFPDPPP)."""
    consent = get_latest_consent(curp.upper())
    if consent and (consent.get("revoked") or not consent.get("accepted_ice_qr_emergency")):
        raise HTTPException(
            status_code=403,
            detail="Pasaporte ICE restringido por decisión de privacidad / Derechos ARCO del titular (LFPDPPP).",
        )
    return _build_ice_payload(curp)


@router.get("/api/ice/{curp}/qr")
def get_ice_qr(curp: str, request: Request):
    """Genera el código QR en SVG offline apuntando al Pasaporte ICE /ice/{curp}."""
    if not check_patient_exists(curp.upper()):
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    ice_url = str(request.base_url).rstrip("/") + f"/ice/{curp.upper()}"
    svg = generate_qr_svg(ice_url, size_px=150)
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/ice/{curp}", response_class=HTMLResponse)
def get_ice_passport_html(curp: str, request: Request):
    """Vista pública móvil ultra-rápida del Pasaporte Médico de Emergencia QR (ICE)."""
    consent = get_latest_consent(curp.upper())
    if consent and (consent.get("revoked") or not consent.get("accepted_ice_qr_emergency")):
        return HTMLResponse(
            status_code=403,
            content="""<!doctype html><html lang="es"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
            <title>Pasaporte ICE Restringido — MedicAItion</title>
            <style>body{font-family:system-ui,sans-serif;background:#0f172a;color:#f8fafc;padding:24px;display:flex;justify-content:center;align-items:center;min-height:90vh;}
            .box{max-width:460px;background:#1e293b;border:1px solid #ef4444;border-radius:18px;padding:22px;text-align:center;}
            h1{font-size:18px;margin:0 0 8px;color:#fca5a5;}p{font-size:13.5px;color:#cbd5e1;line-height:1.5;}</style></head>
            <body><div class="box"><h1>🔒 Pasaporte ICE Restringido por Privacidad</h1>
            <p>El titular ejerció su derecho de privacidad / oposición ARCO conforme a la LFPDPPP (México / Yucatán). Para atención médica urgente, consulte directamente en ventanilla clínica autorizada.</p></div></body></html>""",
        )
    data = _build_ice_payload(curp)
    ice_url = str(request.base_url).rstrip("/") + f"/ice/{data['curp']}"
    qr_svg = generate_qr_svg(ice_url, size_px=112)

    allergies_html = "".join(
        f"<div class='chip-danger'>⚠️ {html.escape(str(a['descripcion']))} "
        f"<small>({html.escape(str(a['severidad']))})</small></div>"
        for a in data["alergias"]
    ) or "<div class='chip-safe'>✅ Sin alergias críticas registradas</div>"

    conds_html = "".join(
        f"<li><strong>{html.escape(str(c['tipo']))}:</strong> {html.escape(str(c['descripcion']))}</li>"
        for c in data["condiciones_cronicas"]
    ) or "<li>Sin enfermedades crónicas documentadas</li>"

    meds_html = "".join(
        f"<li><strong>{html.escape(str(m['nombre']))}</strong> {html.escape(str(m['dosis']))} "
        f"<span class='muted'>({html.escape(str(m['periodicidad']))})</span></li>"
        for m in data["medicamentos_actuales"]
    ) or "<li>Sin medicación crónica registrada</li>"

    tel = data["contacto_emergencia"]["telefono"]
    tel_clean = re.sub(r"[^0-9+]", "", tel or "")
    tel_btn = (
        f"<a class='call-btn' href='tel:{html.escape(tel_clean)}'>📞 Llamar ahora: {html.escape(tel)}</a>"
        if tel_clean else "<span class='muted'>Sin teléfono de emergencia registrado</span>"
    )

    page = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Pasaporte ICE — {html.escape(data['nombre_completo'])}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; background: #0f172a; color: #0f172a; padding: 16px; }}
    .ice-card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 22px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.45); }}
    .ice-header {{ background: linear-gradient(135deg, #dc2626, #991b1b); color: #fff; padding: 18px 20px; display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
    .ice-kicker {{ font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.92; }}
    .ice-name {{ font-size: 22px; font-weight: 800; margin: 4px 0 2px; line-height: 1.15; }}
    .ice-meta {{ font-size: 13px; opacity: 0.9; }}
    .blood-pill {{ background: #fff; color: #b91c1c; font-weight: 900; font-size: 22px; padding: 10px 14px; border-radius: 14px; text-align: center; min-width: 72px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
    .blood-pill small {{ display: block; font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; color: #475569; }}
    .section {{ padding: 14px 20px; border-bottom: 1px solid #e2e8f0; }}
    .section:last-child {{ border-bottom: none; }}
    h2 {{ margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.07em; color: #475569; }}
    .chip-danger {{ background: #fef2f2; border: 1.5px solid #ef4444; color: #991b1b; padding: 8px 12px; border-radius: 12px; font-weight: 700; margin-bottom: 6px; font-size: 14px; }}
    .chip-safe {{ background: #f0fdf4; border: 1px solid #86efac; color: #166534; padding: 8px 12px; border-radius: 12px; font-weight: 700; font-size: 13px; }}
    ul {{ margin: 0; padding-left: 18px; line-height: 1.55; font-size: 14px; }}
    .muted {{ color: #64748b; font-size: 13px; }}
    .call-btn {{ display: inline-block; margin-top: 8px; background: #16a34a; color: #fff; text-decoration: none; font-weight: 800; padding: 10px 16px; border-radius: 999px; font-size: 14px; }}
    .qr-footer {{ display: flex; justify-content: space-between; align-items: center; gap: 14px; background: #f8fafc; padding: 14px 20px; }}
    .actions-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
    .btn-lite {{ background: #e2e8f0; color: #0f172a; border: none; padding: 7px 12px; border-radius: 999px; font-weight: 700; font-size: 12px; text-decoration: none; cursor: pointer; }}
    @media print {{ body {{ background: #fff; padding: 0; }} .actions-row {{ display: none; }} }}
  </style>
</head>
<body>
  <div class="ice-card">
    <div class="ice-header">
      <div>
        <div class="ice-kicker">✚ Pasaporte Médico de Emergencia (ICE) &bull; Cruz Roja Mérida</div>
        <div class="ice-name">{html.escape(data['nombre_completo'])}</div>
        <div class="ice-meta">{html.escape(str(data['edad'] if data['edad'] is not None else '—'))} años &bull; {html.escape(str(data['sexo'] or '—'))} &bull; CURP: {html.escape(data['curp'])}</div>
      </div>
      <div class="blood-pill"><small>Sangre</small>{html.escape(data['tipo_sangre'])}</div>
    </div>

    <div class="section">
      <h2>Alergias Críticas</h2>
      {allergies_html}
    </div>

    <div class="section">
      <h2>Condiciones y Antecedentes Médicos</h2>
      <ul>{conds_html}</ul>
    </div>

    <div class="section">
      <h2>Medicación Habitual / Última Receta</h2>
      <ul>{meds_html}</ul>
    </div>

    <div class="section">
      <h2>Contacto de Emergencia</h2>
      <div><strong>{html.escape(data['contacto_emergencia']['nombre'])}</strong></div>
      {tel_btn}
    </div>

    <div class="qr-footer">
      <div>
        <div style="font-weight:800;font-size:13px;">Solo datos vitales de rescate</div>
        <div class="muted">Notas privadas ocultas por privacidad (NOM-004 / LFPDPPP).</div>
        <div class="actions-row">
          <button class="btn-lite" onclick="window.print()">🖨️ Imprimir Tarjeta</button>
          <a class="btn-lite" href="/mi-salud/{html.escape(data['curp'])}">📱 Ir a Mi Salud Hoy</a>
        </div>
      </div>
      <div style="flex-shrink:0;">{qr_svg}</div>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=page)


@router.get("/api/patient-portal/{curp}")
def get_patient_portal_json(curp: str):
    """Devuelve el Plan Diario amigable y bitácora del paciente para web o móvil."""
    return _build_portal_payload(curp)


@router.post("/api/patient-portal/{curp}/logs", status_code=201)
def create_patient_daily_log(curp: str, data: dict = Body(...)):
    """Registra una medición diaria en la bitácora 'Mi Salud Hoy' y evalúa signos de alarma."""
    if not check_patient_exists(curp.upper()):
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return add_patient_daily_log(curp.upper(), data)


@router.get("/mi-salud/{curp}", response_class=HTMLResponse)
def get_mi_salud_html(curp: str):
    """Portal móvil diario 'Mi Salud Hoy' para el paciente y su familia."""
    data = _build_portal_payload(curp)
    slots_html = ""
    for slot_name, items in data["horario_visual"].items():
        if not items:
            continue
        lis = "".join(
            f"<li><strong>{html.escape(m['nombre'])}</strong> — {html.escape(m['dosis'])} ({html.escape(m['duracion'] or 'según indicación')})</li>"
            for m in items
        )
        slots_html += f"<div class='slot-card'><div class='slot-title'>{html.escape(slot_name)}</div><ul>{lis}</ul></div>"
    if not slots_html:
        slots_html = "<div class='slot-card'><div class='slot-title'>Tratamiento actual</div><p class='muted'>Sin medicamentos activos en última consulta.</p></div>"

    flags_html = "".join(f"<li>{html.escape(f)}</li>" for f in data["banderas_rojas"])
    logs_html = "".join(
        f"<div class='log-item {'log-alert' if l['alert_flag'] else ''}'>"
        f"<strong>{html.escape((l['recorded_at'] or '')[:16].replace('T',' '))}</strong> — "
        f"TA: {l['systolic_bp'] or '--'}/{l['diastolic_bp'] or '--'} mmHg · Glucosa: {l['glucose_mg_dl'] or '--'} mg/dL · "
        f"Temp: {l['temperature_c'] or '--'} °C · Medicinas: {'✅' if l['medication_taken'] else '❌'}"
        f"{'<br><small>⚠ ' + html.escape(l['alert_message']) + '</small>' if l['alert_flag'] and l.get('alert_message') else ''}"
        f"</div>"
        for l in data["daily_logs"][:8]
    ) or "<p class='muted'>Aún no hay registros diarios. Captura el primero abajo.</p>"

    page = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Mi Salud Hoy — {html.escape(data['nombre_completo'])}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; background: #f1f5f9; color: #0f172a; padding: 16px; }}
    .wrap {{ max-width: 640px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }}
    .hero {{ background: linear-gradient(135deg, #111c2d, #1e3a5f); color: #fff; border-radius: 20px; padding: 20px; }}
    .hero h1 {{ margin: 4px 0; font-size: 21px; }}
    .hero p {{ margin: 0; opacity: 0.85; font-size: 13px; }}
    .card {{ background: #fff; border-radius: 18px; padding: 16px 18px; box-shadow: 0 6px 20px rgba(15,23,42,0.06); }}
    .card h2 {{ margin: 0 0 10px; font-size: 15px; }}
    .slot-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px 12px; margin-bottom: 8px; }}
    .slot-title {{ font-weight: 800; font-size: 13px; color: #0284c7; margin-bottom: 4px; }}
    .red-box {{ background: #fef2f2; border: 1.5px solid #fca5a5; border-radius: 16px; padding: 14px 16px; }}
    .red-box h2 {{ color: #b91c1c; margin: 0 0 8px; font-size: 15px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }}
    label {{ font-size: 12px; font-weight: 600; display: flex; flex-direction: column; gap: 4px; }}
    input, select {{ padding: 8px 10px; border-radius: 10px; border: 1px solid #cbd5e1; font-size: 14px; }}
    button {{ background: #ee2a42; color: #fff; border: none; border-radius: 12px; padding: 11px 16px; font-weight: 800; cursor: pointer; margin-top: 10px; width: 100%; }}
    .log-item {{ padding: 8px 10px; border-radius: 10px; background: #f8fafc; border: 1px solid #e2e8f0; margin-bottom: 6px; font-size: 12.5px; }}
    .log-alert {{ background: #fef2f2; border-color: #ef4444; color: #991b1b; }}
    .muted {{ color: #64748b; font-size: 13px; }}
    .top-link {{ color: #93c5fd; font-size: 12px; font-weight: 700; text-decoration: none; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:11px;font-weight:800;letter-spacing:0.06em;">MI SALUD HOY &bull; PORTAL DEL PACIENTE</span>
        <a class="top-link" href="/ice/{html.escape(data['curp'])}">🪪 Ver Pasaporte ICE ›</a>
      </div>
      <h1>Hola, {html.escape(data['nombre_completo'])}</h1>
      <p>Diagnóstico reciente: {html.escape(str(data['ultimo_diagnostico']))}</p>
    </div>

    <div class="card">
      <h2>💊 Tu horario visual de medicamentos</h2>
      {slots_html}
      <p class="muted">{html.escape(data['receta_amigable'])}</p>
    </div>

    <div class="red-box">
      <h2>🚨 Cuándo acudir a Urgencias de inmediato</h2>
      <ul style="margin:0;padding-left:18px;font-size:13.5px;line-height:1.5;">{flags_html}</ul>
    </div>

    <div class="card">
      <h2>📝 Registrar mi chequeo de hoy</h2>
      <form id="log-form" onsubmit="event.preventDefault(); saveLog();">
        <div class="grid">
          <label>Presión sistólica (alta)<input type="number" id="bp-s" placeholder="120" /></label>
          <label>Presión diastólica (baja)<input type="number" id="bp-d" placeholder="80" /></label>
          <label>Glucosa capilar (mg/dL)<input type="number" id="gluc" placeholder="105" /></label>
          <label>Temperatura (°C)<input type="number" step="0.1" id="temp" placeholder="36.5" /></label>
          <label>¿Tomaste tus medicinas?
            <select id="med-ok"><option value="true">Sí, al día</option><option value="false">No / Olvidé una toma</option></select>
          </label>
          <label>¿Cómo te sientes hoy?
            <select id="mood"><option value="Bien">Bien</option><option value="Molestia leve">Molestia leve</option><option value="Síntomas importantes">Síntomas importantes</option></select>
          </label>
        </div>
        <label style="margin-top:8px;">Síntomas o comentarios<input type="text" id="note" placeholder="Ej: dolor de cabeza leve en la tarde" /></label>
        <button type="submit">Guardar chequeo de hoy</button>
      </form>
      <div id="msg" style="margin-top:8px;font-size:13px;font-weight:700;"></div>
    </div>

    <div class="card">
      <h2>📊 Tus últimos chequeos</h2>
      <div id="logs-list">{logs_html}</div>
    </div>
  </div>
  <script>
    async function saveLog() {{
      const payload = {{
        systolic_bp: parseFloat(document.getElementById('bp-s').value) || null,
        diastolic_bp: parseFloat(document.getElementById('bp-d').value) || null,
        glucose_mg_dl: parseFloat(document.getElementById('gluc').value) || null,
        temperature_c: parseFloat(document.getElementById('temp').value) || null,
        medication_taken: document.getElementById('med-ok').value === 'true',
        mood_or_pain: document.getElementById('mood').value,
        symptoms_note: document.getElementById('note').value.trim() || null
      }};
      const res = await fetch('/api/patient-portal/{html.escape(data['curp'])}/logs', {{
        method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(payload)
      }});
      const out = await res.json();
      const msg = document.getElementById('msg');
      if (!res.ok) {{ msg.textContent = 'Error al guardar'; return; }}
      msg.style.color = out.alert_flag ? '#dc2626' : '#16a34a';
      msg.textContent = out.alert_flag ? '⚠️ ' + out.alert_message : '✅ Chequeo guardado correctamente.';
      setTimeout(() => location.reload(), 900);
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=page)
