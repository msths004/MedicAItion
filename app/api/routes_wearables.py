"""
routes_wearables.py — MedicAItion Sprint 2
===========================================
Telemetría biométrica real de Wearables y dispositivos médicos.

Fuentes soportadas:
  - "ble"    : lecturas en vivo vía Web Bluetooth (Heart Rate Service 0x180D)
  - "csv"    : importación de archivo CSV exportado por smartwatch
  - "json"   : importación de archivo JSON exportado
  - "manual" : captura manual en triaje

Endpoints:
  GET  /api/wearables/latest              — Última lectura por paciente/dispositivo
  GET  /api/wearables/readings            — Historial (filtros: curp, limit)
  POST /api/wearables/readings            — Registrar una lectura
  POST /api/wearables/import              — Importar lote CSV/JSON (texto)
"""

import csv
import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request

from app.api.routes_security import require_permission
from app.db.local_db import SessionLocal, VitalReading

router = APIRouter(prefix="/api/wearables", tags=["Wearables"])


def evaluate_vital_alert(hr=None, spo2=None, sbp=None, dbp=None, temp=None):
    """Umbrales clínicos para alerta biométrica. Devuelve (flag, mensaje)."""
    msgs = []
    if spo2 is not None and spo2 < 90:
        msgs.append(f"Desaturación grave SpO2 {spo2:.0f}%")
    elif spo2 is not None and spo2 <= 93:
        msgs.append(f"Desaturación moderada SpO2 {spo2:.0f}%")
    if hr is not None and (hr >= 130 or hr <= 40):
        msgs.append(f"FC crítica {hr:.0f} lpm")
    elif hr is not None and hr >= 110:
        msgs.append(f"Taquicardia sostenida {hr:.0f} lpm")
    elif hr is not None and hr < 50:
        msgs.append(f"Bradicardia {hr:.0f} lpm")
    if sbp is not None and (sbp >= 180 or (dbp is not None and dbp >= 120)):
        msgs.append(f"Crisis hipertensiva {sbp:.0f}/{dbp or 0:.0f} mmHg")
    elif sbp is not None and sbp < 90:
        msgs.append(f"Hipotensión {sbp:.0f}/{dbp or 0:.0f} mmHg")
    if temp is not None and temp >= 39.0:
        msgs.append(f"Fiebre alta {temp:.1f} °C")
    elif temp is not None and temp < 35.0:
        msgs.append(f"Hipotermia {temp:.1f} °C")
    return (len(msgs) > 0, " • ".join(msgs) if msgs else None)


def _num(val):
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", ".").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def reading_to_dict(r: VitalReading) -> dict:
    return {
        "id": r.id,
        "curp": r.patient_curp or "",
        "patientName": r.patient_name or "",
        "device": r.device_name,
        "source": r.source,
        "heart_rate": r.heart_rate,
        "spo2": r.spo2,
        "systolic_bp": r.systolic_bp,
        "diastolic_bp": r.diastolic_bp,
        "temperature": r.temperature,
        "steps": r.steps,
        "alert": bool(r.alert_flag),
        "alert_message": r.alert_message,
        "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
    }


def _store_reading(db, payload: dict) -> VitalReading:
    hr = _num(payload.get("heart_rate") or payload.get("hr") or payload.get("bpm"))
    spo2 = _num(payload.get("spo2") or payload.get("oxygen") or payload.get("sat"))
    sbp = _num(payload.get("systolic_bp") or payload.get("sys") or payload.get("systolic"))
    dbp = _num(payload.get("diastolic_bp") or payload.get("dia") or payload.get("diastolic"))
    temp = _num(payload.get("temperature") or payload.get("temp"))
    steps = _num(payload.get("steps") or payload.get("pasos"))

    if all(v is None for v in (hr, spo2, sbp, dbp, temp, steps)):
        raise ValueError("La lectura no contiene ningún valor biométrico reconocible")

    flag, msg = evaluate_vital_alert(hr, spo2, sbp, dbp, temp)

    recorded_at = datetime.utcnow()
    ts = payload.get("recorded_at") or payload.get("timestamp") or payload.get("fecha")
    if ts:
        try:
            recorded_at = datetime.fromisoformat(str(ts).replace("Z", ""))
        except ValueError:
            pass

    r = VitalReading(
        patient_curp=(payload.get("curp") or "").strip().upper() or None,
        patient_name=payload.get("patientName") or payload.get("patient_name"),
        device_name=payload.get("device") or payload.get("device_name") or "Sensor BLE",
        source=payload.get("source") or "wearable",
        heart_rate=hr,
        spo2=spo2,
        systolic_bp=sbp,
        diastolic_bp=dbp,
        temperature=temp,
        steps=steps,
        alert_flag=flag,
        alert_message=msg,
        recorded_at=recorded_at,
    )
    db.add(r)
    return r


@router.get("/latest")
def latest_readings():
    """Última lectura registrada por cada paciente/dispositivo."""
    db = SessionLocal()
    try:
        rows = db.query(VitalReading).order_by(VitalReading.recorded_at.desc()).limit(500).all()
        seen = set()
        out = []
        for r in rows:
            key = (r.patient_curp or "", r.device_name)
            if key in seen:
                continue
            seen.add(key)
            out.append(reading_to_dict(r))
        return out
    finally:
        db.close()


@router.get("/readings")
def list_readings(curp: Optional[str] = None, limit: int = 60):
    db = SessionLocal()
    try:
        q = db.query(VitalReading)
        if curp:
            q = q.filter(VitalReading.patient_curp == curp.upper())
        rows = q.order_by(VitalReading.recorded_at.desc()).limit(max(1, min(limit, 500))).all()
        return [reading_to_dict(r) for r in reversed(rows)]
    finally:
        db.close()


@router.post("/readings", status_code=201)
def create_reading(request: Request, data: dict = Body(...)):
    require_permission(request, "record_vitals")
    db = SessionLocal()
    try:
        r = _store_reading(db, data)
        db.commit()
        db.refresh(r)
        return reading_to_dict(r)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        db.close()


@router.post("/import", status_code=201)
def import_readings(request: Request, data: dict = Body(...)):
    """
    Importa un lote de lecturas desde contenido de archivo.
    Body: { "format": "csv" | "json", "content": "...", "curp": "...", "patientName": "...", "device": "..." }
    CSV con encabezados (cualquiera de): timestamp, heart_rate|hr|bpm, spo2, systolic|sys, diastolic|dia, temperature|temp, steps
    """
    require_permission(request, "record_vitals")
    fmt = (data.get("format") or "csv").lower()
    content = data.get("content") or ""
    if not content.strip():
        raise HTTPException(status_code=422, detail="Archivo vacío")

    base = {
        "curp": data.get("curp"),
        "patientName": data.get("patientName"),
        "device": data.get("device") or "Importación de archivo",
        "source": fmt,
    }

    rows = []
    try:
        if fmt == "json":
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed = parsed.get("readings") or parsed.get("data") or [parsed]
            rows = [r for r in parsed if isinstance(r, dict)]
        else:
            reader = csv.DictReader(io.StringIO(content.strip()))
            rows = [{(k or "").strip().lower(): v for k, v in r.items()} for r in reader]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo: {e}")

    db = SessionLocal()
    imported, skipped, alerts = 0, 0, []
    try:
        for row in rows:
            payload = {**base, **{k: v for k, v in row.items() if v not in (None, "")}}
            payload["source"] = fmt
            try:
                r = _store_reading(db, payload)
                imported += 1
                if r.alert_flag:
                    alerts.append(r.alert_message)
            except ValueError:
                skipped += 1
        db.commit()
    finally:
        db.close()

    if imported == 0:
        raise HTTPException(status_code=422, detail="No se encontró ninguna lectura biométrica válida en el archivo")
    return {"imported": imported, "skipped": skipped, "alerts": alerts[:10], "total_alerts": len(alerts)}
