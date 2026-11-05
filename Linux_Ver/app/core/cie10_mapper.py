import os
from dotenv import load_dotenv
from app.db.chroma_store import get_collection
from typing import List, Dict, Any

load_dotenv()
ACTIVE_TERM = os.getenv("ACTIVE_TERMINOLOGY", "cie10_mexico_2024")

# Mismo modelo usado en ingest_terminologies.py para crear los embeddings
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Mapeo: llave del JSON del LLM → colección en ChromaDB
CATEGORY_COLLECTION_MAP = {
    "sintomas_referidos":       "diagnosticos",    # CIE-10 códigos R (síntomas/signos)
    "diagnosticos_tentativos":  "diagnosticos",    # CIE-10 (A00-Z99)
    "tratamientos":             "procedimientos",  # CIE-9MC
    # medicamentos → NO se codifican con CIE-10 (se reportan con posología en la nota)
    # signos_vitales → NO se codifican (son valores numéricos: PA, FC, T°, etc.)
}

_embedder = None


def _get_embedder():
    """Carga el modelo de embeddings una sola vez (el mismo usado en la ingesta)."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        print(f"[CIE10Mapper] Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
        print("[CIE10Mapper] Modelo de embeddings listo ✅")
    return _embedder


def _search_term(collection_suffix: str, term: str, n_results: int = 3) -> Dict[str, Any]:
    """Busca un término clínico en ChromaDB usando el mismo modelo de embeddings de la ingesta."""
    collection_name = f"{ACTIVE_TERM}_{collection_suffix}"
    try:
        col = get_collection(collection_name)
        if col.count() == 0:
            return {"termino_original": term, "codigo": None, "descripcion": term, "similitud": 0.0}

        # Generar el embedding con el MISMO modelo usado en la ingesta
        embedder = _get_embedder()
        query_embedding = embedder.encode([term]).tolist()

        results = col.query(query_embeddings=query_embedding, n_results=n_results)
        if not results["documents"] or not results["documents"][0]:
            return {"termino_original": term, "codigo": None, "descripcion": term, "similitud": 0.0}

        # Tomar el mejor resultado
        meta = results["metadatas"][0][0]
        distance = results["distances"][0][0]
        similitud = round(max(0.0, 1.0 - distance), 3)

        return {
            "termino_original": term,
            "codigo": meta.get("codigo"),
            "descripcion": meta.get("descripcion", term),
            "similitud": similitud,
        }
    except Exception as e:
        print(f"[CIE10Mapper] Error buscando '{term}' en '{collection_name}': {e}")
        return {"termino_original": term, "codigo": None, "descripcion": term, "similitud": 0.0}


def _extract_search_term(term) -> str:
    """Extrae el texto de búsqueda de un término que puede ser string o dict."""
    if isinstance(term, dict):
        return term.get("nombre", "")
    return str(term) if term else ""


def map_to_cie10(entidades: dict) -> Dict[str, List[Dict[str, Any]]]:
    """
    Mapea cada entidad clínica extraída a su código CIE-10 equivalente
    usando búsqueda semántica en ChromaDB con el mismo modelo de embeddings
    utilizado durante la ingesta de la terminología.
    """
    result = {}
    for category, collection_name in CATEGORY_COLLECTION_MAP.items():
        terms = entidades.get(category, [])
        search_terms = [_extract_search_term(t) for t in terms]
        result[category] = [
            _search_term(collection_name, t) for t in search_terms if t
        ]
    return result
