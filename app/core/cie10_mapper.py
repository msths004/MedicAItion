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
        print("[CIE10Mapper] Cargando modelo de embeddings: " + EMBEDDING_MODEL)
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
        print("[CIE10Mapper] Modelo de embeddings listo [OK]")
    return _embedder


def is_biologically_incompatible(code: str, sex: str, age: float) -> bool:
    """
    Verifica si un código CIE-10/CIE-9MC es biológicamente incompatible con el paciente.
    """
    if not code:
        return False
    
    code = code.strip().upper()
    
    # Restricciones por Sexo
    if sex == "M":
        # Obstetrico/Embarazo (Empieza con O, o Z32-Z39)
        if code.startswith("O"):
            return True
        if code.startswith("Z"):
            try:
                num = int(code[1:3])
                if 32 <= num <= 39:
                    return True
            except ValueError:
                pass
        # Ginecológico Femenino
        if code.startswith("C"):
            try:
                num = int(code[1:3])
                if 51 <= num <= 58:
                    return True
            except ValueError:
                pass
        if code.startswith("D"):
            try:
                num = int(code[1:3])
                if 25 <= num <= 28:
                    return True
            except ValueError:
                pass
        if code.startswith("Q"):
            try:
                num = int(code[1:3])
                if 50 <= num <= 52:
                    return True
            except ValueError:
                pass
        if code.startswith("N"):
            try:
                num = int(code[1:3])
                if 70 <= num <= 98:
                    return True
            except ValueError:
                pass

    elif sex == "F":
        # Andrológico/Cáncer de órganos masculinos
        if code.startswith("C"):
            try:
                num = int(code[1:3])
                if 60 <= num <= 63:
                    return True
            except ValueError:
                pass
        if code.startswith("D29"):
            return True
        if code.startswith("Q"):
            try:
                num = int(code[1:3])
                if 53 <= num <= 55:
                    return True
            except ValueError:
                pass
        if code.startswith("N"):
            try:
                num = int(code[1:3])
                if 40 <= num <= 51:
                    return True
            except ValueError:
                pass

    # Restricciones por Edad (Neonatología / Perinatal vs Adulto)
    # Códigos "P" son de afecciones originadas en el período perinatal (generalmente recién nacidos).
    # Z38 es el código para nacidos vivos.
    # Si la edad es >= 1 año, se consideran incompatibles.
    if age is not None and age >= 1.0:
        if code.startswith("P"):
            return True
        if code.startswith("Z38"):
            return True

    return False


def is_medicine_term(term: str, extracted_medicines: list) -> bool:
    """
    Verifica si un término clínico corresponde a un medicamento, para evitar
    mapearlo erróneamente a un código de diagnóstico o procedimiento.
    """
    term_lower = term.lower().strip()
    
    # 1. Comparar con los medicamentos extraídos por el LLM en esta consulta
    for med in extracted_medicines:
        med_name = ""
        if isinstance(med, dict):
            med_name = med.get("nombre", "")
        elif isinstance(med, str):
            med_name = med
        
        if med_name:
            med_name_lower = med_name.lower().strip()
            # Si hay coincidencia exacta o contenida en ambas direcciones
            if term_lower in med_name_lower or med_name_lower in term_lower:
                return True
                
    # 2. Diccionario de principios activos y términos comunes de medicamentos en español
    common_meds = {
        "paracetamol", "acetaminofén", "acetaminophen", "ibuprofeno", "aspirina", "naproxeno", "ketorolaco", "diclofenaco",
        "metamizol", "tramadol", "morfina", "omeprazol", "pantoprazol", "ranitidina", "metformina", "glibenclamida",
        "insulina", "losartán", "losartan", "captopril", "enalapril", "telmisartán", "telmisartan", "amlodipino",
        "nifedipino", "atorvastatina", "simvastatina", "pravastatina", "salbutamol", "ipratropio", "budesonida",
        "fluticasona", "montelukast", "amoxicilina", "ampicilina", "ceftriaxona", "cefexina", "ciprofloxacino",
        "levofloxacino", "claritromicina", "azitromicina", "clindamicina", "metronidazol", "fluconazol",
        "ketoconazol", "loratadina", "cetirizina", "clorfenamina", "dexametasona", "prednisona", "metilprednisolona",
        "hidrocortisona", "complejo b", "vitamina", "multivitamínico", "ácido fólico", "sulfato ferroso",
        "gabapentina", "pregabalina", "carbamazepina", "valproato", "clonazepam", "diazepam", "alprazolam",
        "sertralina", "fluoxetina", "escitalopram", "paroxetina", "haloperidol", "risperidona", "quetiapina",
        "metoclopramida", "ondansetrón", "ondansetron", "loperamida", "butilhioscina", "hioscina", "senósidos",
        "psyllium", "aluminio", "magnesio", "calcio", "potasio", "sodio", "cloruro", "solución", "jarabe",
        "tableta", "cápsula", "ampolleta", "suspensión", "crema", "pomada", "gel", "gotas", "inyección",
        "vacuna", "parche"
    }
    
    words = term_lower.split()
    for w in words:
        w_clean = "".join(c for c in w if c.isalnum())
        if w_clean in common_meds:
            return True
            
    return False


def _search_term(
    collection_suffix: str,
    term: str,
    context: str = "",
    sex: str = "Otro",
    age: float = None,
    mode: str = "auto",
    api_key: str = None
) -> Dict[str, Any]:
    """Busca un término en ChromaDB, obtiene candidatos compatibles y los valida con el LLM en su contexto clínico."""
    collection_name = f"{ACTIVE_TERM}_{collection_suffix}"
    try:
        col = get_collection(collection_name)
        if col.count() == 0:
            return {"termino_original": term, "codigo": None, "descripcion": term, "similitud": 0.0}

        embedder = _get_embedder()
        query_embedding = embedder.encode([term]).tolist()

        # Consultar los 4 candidatos más cercanos
        results = col.query(query_embeddings=query_embedding, n_results=4)
        if not results["documents"] or not results["documents"][0]:
            return {"termino_original": term, "codigo": None, "descripcion": term, "similitud": 0.0}

        candidates = []
        for i in range(len(results["documents"][0])):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            similitud = round(max(0.0, 1.0 - distance), 3)
            # Enforce similarity threshold of 0.45
            if similitud >= 0.45:
                candidates.append({
                    "codigo": meta.get("codigo"),
                    "descripcion": meta.get("descripcion", term),
                    "similitud": similitud
                })

        if not candidates:
            return {
                "termino_original": term,
                "codigo": None,
                "descripcion": "Sin correspondencia adecuada en el contexto clínico (similitud baja)",
                "similitud": 0.0
            }

        # Filtrar candidatos por incompatibilidad biológica
        compatible_candidates = [
            c for c in candidates if not is_biologically_incompatible(c["codigo"], sex, age)
        ]

        if not compatible_candidates:
            return {
                "termino_original": term,
                "codigo": None,
                "descripcion": "Sin correspondencia adecuada (incompatibilidad biológica)",
                "similitud": 0.0
            }

        # Si no hay contexto, usar el primero compatible directamente
        if not context.strip():
            best = compatible_candidates[0]
        else:
            from app.core.entity_extractor import validate_cie10_candidates
            best_idx = validate_cie10_candidates(term, context, compatible_candidates, mode=mode, api_key=api_key)
            if 0 <= best_idx < len(compatible_candidates):
                best = compatible_candidates[best_idx]
            else:
                # El LLM determinó que ninguno aplica en este contexto
                return {
                    "termino_original": term,
                    "codigo": None,
                    "descripcion": "Sin correspondencia adecuada en el contexto clínico",
                    "similitud": 0.0
                }

        return {
            "termino_original": term,
            "codigo": best["codigo"],
            "descripcion": best["descripcion"],
            "similitud": best["similitud"],
        }
    except Exception as e:
        print(f"[CIE10Mapper] Error buscando '{term}' en '{collection_name}': {e}")
        return {"termino_original": term, "codigo": None, "descripcion": term, "similitud": 0.0}


def _extract_search_term(term) -> str:
    """Extrae el texto de búsqueda de un término que puede ser string o dict."""
    if isinstance(term, dict):
        return term.get("nombre", "")
    return str(term) if term else ""


def map_to_cie10(
    entidades: dict,
    patient_sex: str = "Otro",
    patient_age: float = None,
    mode: str = "auto",
    api_key: str = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Mapea cada entidad clínica extraída a su código CIE-10/CIE-9MC equivalente
    usando búsqueda semántica y validación por LLM.
    """
    # Construir el contexto clínico enriquecido para la validación del LLM
    motivo = entidades.get("nota_clinica", {}).get("motivo_consulta", "") or ""
    diag_int = entidades.get("nota_clinica", {}).get("diagnostico_integral", "") or ""
    
    context_parts = []
    if patient_sex and patient_sex != "Otro":
        context_parts.append(f"Sexo Paciente: {patient_sex}")
    if patient_age is not None:
        context_parts.append(f"Edad Paciente: {patient_age} años")
    if motivo:
        context_parts.append(f"Motivo consulta: {motivo}")
    if diag_int and "Pendiente de diagnóstico" not in diag_int:
        context_parts.append(f"Diagnóstico: {diag_int}")
        
    context = " | ".join(context_parts)

    result = {}
    for category, collection_name in CATEGORY_COLLECTION_MAP.items():
        terms = entidades.get(category, [])
        search_terms = [_extract_search_term(t) for t in terms]
        result[category] = []
        for t in search_terms:
            if not t:
                continue
            # Exclude medication terms from being mapped to CIE-10/CIE-9MC
            if is_medicine_term(t, entidades.get("medicamentos", [])):
                print(f"[CIE10Mapper] Excluyendo término por ser medicamento: {t}")
                result[category].append({
                    "termino_original": t,
                    "codigo": None,
                    "descripcion": "Excluido (es un medicamento)",
                    "similitud": 0.0
                })
                continue
            
            mapped = _search_term(
                collection_name, 
                t, 
                context=context, 
                sex=patient_sex, 
                age=patient_age, 
                mode=mode, 
                api_key=api_key
            )
            result[category].append(mapped)
            
    return result

