from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from typing import Optional
import tempfile
import shutil
import uuid
import os

from app.core.noise_suppressor import suppress_noise
from app.core.transcriber import transcribe
from app.core.entity_extractor import extract_entities
from app.core.cie10_mapper import map_to_cie10
from app.core.record_builder import build_record
from app.core.template_renderer import render_nota_medica
from app.db.local_db import get_patient_by_curp

router = APIRouter(prefix="/api/input", tags=["Input"])

_last_consultation_records: dict = {}


def _run_pipeline(
    text: str,
    curp: str,
    clues: str,
    llm_mode: str = "auto",
    api_key: str = None,
    event_id: str = None
) -> dict:
    """
    Procesa el texto clínico y devuelve el borrador en memoria.
    NO guarda nada en la BD — el guardado ocurre cuando el médico
    presiona 'Crear Consulta' en el modal de Asociar, que llama a
    POST /api/consultations/ con el borrador como payload.
    """
    if not curp or not curp.strip():
        curp = f"URGENCIAS-{uuid.uuid4().hex[:8].upper()}"

    # Intentar obtener sexo y edad desde la DB
    patient_sex = "Otro"
    patient_age = None
    patient_data = None
    if curp and not curp.startswith("URGENCIAS"):
        patient_data = get_patient_by_curp(curp)
        if patient_data:
            patient_sex = patient_data.get("sexo", "Otro")
            patient_age = patient_data.get("edad", None)

    entities = extract_entities(text, mode=llm_mode, api_key=api_key)

    # Asegurar que demográficos exista como dict
    if "demograficos" not in entities or not isinstance(entities["demograficos"], dict):
        entities["demograficos"] = {}
    demo = entities["demograficos"]

    # Inyectar datos del paciente de la BD si están disponibles
    if patient_data:
        if not demo.get("nombre"):
            nombre_db = patient_data.get("nombre_completo")
            if not nombre_db:
                partes = [patient_data.get("nombres", ""), patient_data.get("primer_apellido", ""), patient_data.get("segundo_apellido", "")]
                nombre_db = " ".join(p for p in partes if p).strip()
            demo["nombre"] = nombre_db or None
        if not demo.get("curp"):
            demo["curp"] = patient_data.get("curp") or curp
        if not demo.get("sexo"):
            demo["sexo"] = patient_data.get("sexo")
        if not demo.get("edad"):
            demo["edad"] = patient_data.get("edad")

    if curp and not curp.startswith("URGENCIAS") and not demo.get("curp"):
        demo["curp"] = curp

    # Fallback a demográficos extraídos por el LLM si faltan datos en la DB
    if patient_sex == "Otro" and demo.get("sexo"):
        s = str(demo.get("sexo")).strip().upper()
        if s in ["M", "MASCULINO", "HOMBRE", "H"]:
            patient_sex = "M"
        elif s in ["F", "FEMENINO", "MUJER", "F"]:
            patient_sex = "F"
    if patient_age is None and demo.get("edad"):
        try:
            import re
            nums = re.findall(r'\d+', str(demo.get("edad")))
            if nums:
                patient_age = float(nums[0])
        except Exception:
            pass

    cie10_codes = map_to_cie10(
        entities,
        patient_sex=patient_sex,
        patient_age=patient_age,
        mode=llm_mode,
        api_key=api_key
    )
    record = build_record(curp, clues, text, entities, cie10_codes)

    # Inyectar el event_id en el borrador si ya existe, para que el modal lo use
    if event_id:
        record["event_id"] = event_id

    # Generar la nota HTML para previsualización (no se persiste en BD)
    try:
        record["nota_medica_html"] = render_nota_medica(record)
    except Exception as e:
        print(f"[Pipeline] Error al renderizar nota médica: {e}")
        record["nota_medica_html"] = None

    if curp:
        _last_consultation_records[curp] = record
        _last_consultation_records[curp.strip().upper()] = record
    _last_consultation_records["__latest__"] = record

    return record


@router.post("/audio")
async def process_audio(
    audio: UploadFile = File(...),
    curp: Optional[str] = Form(None),
    clues: str = Form(...),
    llm_mode: str = Form("auto"),
    api_key: Optional[str] = Form(None),
    event_id: Optional[str] = Form(None),
):
    suffix = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
    tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        shutil.copyfileobj(audio.file, tmp_input)
        tmp_input.close()

        clean_audio = suppress_noise(tmp_input.name)
        text = transcribe(clean_audio)

        record = _run_pipeline(text, curp, clues, llm_mode, api_key, event_id=event_id)
        return JSONResponse(content=record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_input and hasattr(tmp_input, 'name') and os.path.exists(tmp_input.name):
            try:
                os.unlink(tmp_input.name)
            except OSError:
                pass


@router.post("/text")
async def process_text(
    text: str = Form(...),
    curp: Optional[str] = Form(None),
    clues: str = Form(...),
    llm_mode: str = Form("auto"),
    api_key: Optional[str] = Form(None),
    event_id: Optional[str] = Form(None),
):
    try:
        record = _run_pipeline(text, curp, clues, llm_mode, api_key, event_id=event_id)
        return JSONResponse(content=record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nota-medica/{curp}", response_class=HTMLResponse)
async def get_nota_medica(curp: str):
    """
    Renderiza la nota médica de previsualización para el panel principal.
    Para notas persistidas específicas por consulta, usar:
    GET /api/consultations/{consulta_id}/nota
    """
    clean_curp = curp.strip().upper() if curp else ""
    rec = _last_consultation_records.get(curp) or _last_consultation_records.get(clean_curp)
    if not rec and "__latest__" in _last_consultation_records:
        rec = _last_consultation_records["__latest__"]

    if rec:
        if rec.get("nota_medica_html"):
            return HTMLResponse(content=rec["nota_medica_html"])
        try:
            return HTMLResponse(content=render_nota_medica(rec))
        except Exception as e:
            print(f"[get_nota_medica] Error renderizando borrador: {e}")

    patient_data = get_patient_by_curp(curp)
    if not patient_data:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    try:
        nota_html = render_nota_medica(patient_data)
        return HTMLResponse(content=nota_html)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar la nota médica: {str(e)}"
        )
