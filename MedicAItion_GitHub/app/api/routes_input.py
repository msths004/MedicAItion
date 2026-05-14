from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
import tempfile
import shutil
import os

from app.core.noise_suppressor import suppress_noise
from app.core.transcriber import transcribe
from app.core.entity_extractor import extract_entities
from app.core.cie10_mapper import map_to_cie10
from app.core.record_builder import build_record
from app.core.template_renderer import render_nota_medica
from app.db.local_db import save_patient, get_patient_by_curp
from app.db.global_db import index_patient

router = APIRouter(prefix="/api/input", tags=["Input"])


def _run_pipeline(text: str, curp: str, clues: str) -> dict:
    entities = extract_entities(text)
    cie10_codes = map_to_cie10(entities)
    record = build_record(curp, clues, text, entities, cie10_codes)

    # Guardar el registro SIN la nota HTML (se genera al vuelo cuando se pide)
    save_patient(record)
    index_patient(curp, clues, entities.get("demograficos", {}).get("nombre"))

    # Generar la nota HTML para la respuesta al frontend (no se persiste)
    try:
        record["nota_medica_html"] = render_nota_medica(record)
    except Exception as e:
        print(f"[Pipeline] Error al renderizar nota médica: {e}")
        record["nota_medica_html"] = None

    return record


@router.post("/audio")
async def process_audio(
    audio: UploadFile = File(...),
    curp: str = Form(...),
    clues: str = Form(...),
):
    suffix = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
    tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    clean_audio = None
    try:
        shutil.copyfileobj(audio.file, tmp_input)
        tmp_input.close()

        clean_audio = suppress_noise(tmp_input.name)
        text = transcribe(clean_audio)

        record = _run_pipeline(text, curp, clues)
        return JSONResponse(content=record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Limpiar TODOS los archivos temporales
        for path in [tmp_input.name, clean_audio]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass


@router.post("/text")
async def process_text(
    text: str = Form(...),
    curp: str = Form(...),
    clues: str = Form(...),
):
    try:
        record = _run_pipeline(text, curp, clues)
        return JSONResponse(content=record)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nota-medica/{curp}", response_class=HTMLResponse)
async def get_nota_medica(curp: str):
    """
    Devuelve la Nota Médica renderizada en HTML para un paciente existente.
    Siempre se genera al vuelo desde los datos guardados para evitar
    duplicar ~12KB de HTML por cada nota en la base de datos.
    """
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

