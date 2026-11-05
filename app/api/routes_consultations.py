"""
routes_consultations.py — MedicAItion v3.0
=================================================
Endpoints para gestión de Consultas (visitas médicas).

Las consultas son INMUTABLES una vez creadas (NOM-004-SSA3-2012).
Solo se puede agregar un addendum — nunca modificar la nota original.

Endpoints:
  POST   /api/consultations/                  — Crear nueva consulta (asociar nota+receta a evento)
  GET    /api/consultations/event/{evento_id} — Listar consultas de un evento (línea de tiempo)
  GET    /api/consultations/{id}              — Detalle completo de una consulta
  GET    /api/consultations/{id}/nota         — Nota médica (JSON NOM-004)
  GET    /api/consultations/{id}/receta       — Receta médica (JSON)
  PATCH  /api/consultations/{id}/addendum     — Agregar nota aclaratoria (addendum)
  GET    /api/consultations/search/semantic   — Búsqueda semántica Nivel 3
"""

from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from typing import Optional

from app.db.local_db import (
    create_consulta,
    get_consultas_by_evento,
    get_consulta_by_id,
    index_consulta_semantically,
    index_evento_semantically,
    get_patient_events,
    SessionLocal,
    Consulta,
)

router = APIRouter(prefix="/api/consultations", tags=["Consultations"])


# ── BÚSQUEDA SEMÁNTICA (Nivel 3) ─────────────────────────────────

@router.get("/search/semantic")
def search_consultations_semantic(q: str, evento_id: Optional[str] = None):
    """Búsqueda semántica de consultas dentro de un evento (Nivel 3)."""
    try:
        from app.core.cie10_mapper import _get_embedder
        from app.db.chroma_store import get_collection

        col = get_collection("consultations_semantic")
        if col.count() == 0:
            return []

        embedder = _get_embedder()
        query_embedding = embedder.encode([q]).tolist()

        where = {"event_id": evento_id} if evento_id else None
        results = col.query(
            query_embeddings=query_embedding,
            n_results=10,
            where=where,
        )

        out = []
        if results["metadatas"] and results["metadatas"][0]:
            for i, meta in enumerate(results["metadatas"][0]):
                distance = results["distances"][0][i]
                similitud = round(max(0.0, 1.0 - distance), 3)
                out.append({
                    "consulta_id": meta.get("consulta_id"),
                    "event_id": meta.get("event_id"),
                    "patient_curp": meta.get("patient_curp"),
                    "match_text": results["documents"][0][i],
                    "similitud": similitud,
                })
        return out
    except Exception as e:
        print(f"[SemanticSearch] Error consultas: {e}")
        return []


# ── CONSULTAS POR EVENTO ──────────────────────────────────────────

@router.get("/event/{evento_id}")
def list_consultas(evento_id: str):
    """Devuelve todas las consultas de un Evento Clínico, ordenadas cronológicamente."""
    return get_consultas_by_evento(evento_id)


# ── CREAR CONSULTA ────────────────────────────────────────────────

@router.post("/", status_code=201)
async def create_consulta_endpoint(
    data: dict = Body(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Crea una nueva Consulta asociada a un Evento Clínico.
    La indexación semántica en ChromaDB se realiza en background
    para no bloquear la respuesta al frontend.

    Body esperado:
    {
      "evento_id": "uuid-del-evento",
      "doctor_nombre": "Dr. García",
      "fecha_hora": "2026-05-22T10:45:00",   (opcional, default: ahora)
      "resumen_doctor": "Texto libre...",     (opcional)
      "nota_medica": { ... },                 (estructura NOM-004)
      "receta": { "medicamentos": [...], "instrucciones": "..." },
      "entidades": { "codigos_cie10": {...}, "sintomas": [...] },
      "texto_original": "Transcripción cruda..."
    }
    """
    try:
        consulta = create_consulta(data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear consulta: {str(e)}")

    # Indexación asíncrona en ChromaDB (Nivel 3: consulta + Nivel 2: evento padre)
    if background_tasks:
        consulta_text = _build_consulta_text(consulta)
        background_tasks.add_task(
            index_consulta_semantically,
            consulta["id"],
            consulta["evento_id"],
            consulta["patient_curp"],
            consulta_text,
        )
        # Re-indexar el evento padre en Nivel 2
        background_tasks.add_task(
            _reindex_evento,
            consulta["evento_id"],
            consulta["patient_curp"],
        )

    return consulta


# ── DETALLE DE CONSULTA ───────────────────────────────────────────

@router.get("/{consulta_id}")
def get_consulta(consulta_id: str):
    """Detalle completo de una consulta (nota médica, receta, entidades, metadata)."""
    consulta = get_consulta_by_id(consulta_id)
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return consulta


@router.get("/{consulta_id}/nota")
def get_nota_medica(consulta_id: str):
    """Devuelve únicamente la nota médica (estructura NOM-004) de la consulta."""
    consulta = get_consulta_by_id(consulta_id)
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return {
        "consulta_id": consulta_id,
        "doctor_nombre": consulta.get("doctor_nombre"),
        "fecha_hora": consulta.get("fecha_hora"),
        "nota_medica": consulta.get("nota_medica", {}),
        "texto_original": consulta.get("texto_original", ""),
    }


@router.get("/{consulta_id}/receta")
def get_receta(consulta_id: str):
    """Devuelve únicamente la receta médica de la consulta."""
    consulta = get_consulta_by_id(consulta_id)
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return {
        "consulta_id": consulta_id,
        "doctor_nombre": consulta.get("doctor_nombre"),
        "fecha_hora": consulta.get("fecha_hora"),
        "receta": consulta.get("receta", {}),
    }


# ── ADDENDUM (NOM-004: no modifica la nota original) ─────────────

@router.patch("/{consulta_id}/addendum")
def add_addendum(consulta_id: str, data: dict = Body(...)):
    """
    Agrega una nota aclaratoria (addendum) a una consulta.
    NUNCA modifica la nota médica o receta original (NOM-004).
    """
    texto = data.get("texto", "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El addendum no puede estar vacío")

    db = SessionLocal()
    try:
        consulta = db.query(Consulta).filter(Consulta.id == consulta_id).first()
        if not consulta:
            raise HTTPException(status_code=404, detail="Consulta no encontrada")

        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        nuevo_addendum = f"[{timestamp}] {texto}"

        if consulta.notas_addendum:
            consulta.notas_addendum = consulta.notas_addendum + "\n\n" + nuevo_addendum
        else:
            consulta.notas_addendum = nuevo_addendum

        db.commit()
        return {"status": "success", "addendum": consulta.notas_addendum}
    finally:
        db.close()


# ── HELPERS INTERNOS ──────────────────────────────────────────────

def _build_consulta_text(consulta: dict) -> str:
    """Construye el texto de indexación para ChromaDB a partir de una consulta."""
    nota = consulta.get("nota_medica", {})
    receta = consulta.get("receta", {})
    entidades = consulta.get("entidades", {})

    meds = receta.get("medicamentos", [])
    meds_text = ", ".join(
        m.get("nombre", "") for m in meds if isinstance(m, dict)
    ) if meds else ""

    parts = filter(None, [
        f"Doctor: {consulta.get('doctor_nombre', '')}",
        f"Resumen: {consulta.get('resumen_doctor', '')}",
        f"Motivo: {nota.get('motivo_consulta', '')}",
        f"Diagnóstico: {nota.get('diagnostico_integral', '')}",
        f"Plan: {nota.get('plan_tratamiento', '')}",
        f"Medicamentos: {meds_text}",
        f"Texto original: {consulta.get('texto_original', '')[:500]}",
    ])
    return " | ".join(parts)


def _reindex_evento(evento_id: str, patient_curp: str):
    """Re-indexa el evento padre en ChromaDB Nivel 2 al agregar una nueva consulta."""
    try:
        db = SessionLocal()
        try:
            from app.db.local_db import EventoClinico, Consulta, _consulta_to_dict
            evento = db.query(EventoClinico).filter(EventoClinico.id == evento_id).first()
            if not evento:
                return

            consultas_texts = []
            for c in evento.consultas:
                c_dict = _consulta_to_dict(c)
                nota = c_dict.get("nota_medica", {})
                consultas_texts.append(nota.get("motivo_consulta", ""))
                consultas_texts.append(nota.get("diagnostico_integral", ""))

            consultas_combined = " | ".join(filter(None, consultas_texts))
            index_evento_semantically(evento_id, patient_curp, evento.nombre_evento, consultas_combined)
        finally:
            db.close()
    except Exception as e:
        print(f"[ReindexEvento] Error: {e}")
