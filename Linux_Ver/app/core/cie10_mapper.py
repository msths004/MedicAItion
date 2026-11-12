import os
import json
import re
import unicodedata
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
_CATALOG_CACHE: Dict[str, Dict[str, Any]] = {}
_STOPWORDS = {
    "de", "del", "la", "las", "el", "los", "en", "con", "sin", "por", "para",
    "y", "o", "a", "al", "un", "una", "no", "su", "muy", "intenso", "intensa",
    "leve", "moderado", "moderada", "agudo", "aguda", "cronico", "cronica",
    "reciente", "actual", "general", "posible", "probable", "sospecha",
}

# Equivalencias verificadas contra el catálogo oficial México 2024 para evitar falsos 0% o errores de mayúsculas/minúsculas
_ALIAS_DIAGNOSTICOS = [
    (["dengue", "alarma"], "A971", 0.96),
    (["dengue"], "A970", 0.93),
    (["diabetes", "tipo 2"], "E119", 0.95),
    (["diabetes mellitus"], "E119", 0.93),
    (["dm2"], "E119", 0.92),
    (["hipertension"], "I10X", 0.94),
    (["hta"], "I10X", 0.90),
    (["presion alta"], "I10X", 0.88),
    (["fiebre"], "R509", 0.93),
    (["febricula"], "R509", 0.86),
    (["tos"], "R05X", 0.93),
    (["cefalea"], "R51X", 0.94),
    (["dolor", "cabeza"], "R51X", 0.92),
    (["dolor", "abdominal"], "R104", 0.92),
    (["dolor", "precordial"], "R072", 0.93),
    (["dolor", "pecho"], "R074", 0.92),
    (["dolor", "toracico"], "R074", 0.91),
    (["dolor", "retroocular"], "H571", 0.91),
    (["dolor", "ocular"], "H571", 0.92),
    (["disnea"], "R060", 0.93),
    (["falta de aire"], "R060", 0.90),
    (["diaforesis"], "R619", 0.86),
    (["odinofagia"], "R070", 0.89),
    (["dolor", "garganta"], "R070", 0.89),
    (["rinorrea"], "J00X", 0.88),
    (["vomito"], "R11X", 0.91),
    (["vomitos"], "R11X", 0.91),
    (["nausea"], "R11X", 0.91),
    (["nauseas"], "R11X", 0.91),
    (["mareo"], "R42X", 0.91),
    (["mareos"], "R42X", 0.91),
]

_ALIAS_PROCEDIMIENTOS = [
    (["hidratacion"], "00C2", 0.90),
    (["fluidoterapia"], "00C2", 0.95),
    (["suero"], "00C2", 0.86),
]


def _norm_text(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", str(s or ""))
    no_acc = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9\s]", " ", no_acc.lower()).strip()


def _content_tokens(s: str) -> set:
    return {t for t in _norm_text(s).split() if len(t) >= 2 and t not in _STOPWORDS}


def _get_catalog(collection_suffix: str) -> Dict[str, Any]:
    if collection_suffix in _CATALOG_CACHE:
        return _CATALOG_CACHE[collection_suffix]

    path = os.path.join("terminology_database", ACTIVE_TERM, f"{collection_suffix}.json")
    by_code: Dict[str, Dict[str, str]] = {}
    entries: List[Dict[str, Any]] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for row in raw:
                cod = str(row.get("codigo") or "").strip()
                desc = str(row.get("descripcion") or "").strip()
                if not cod or not desc:
                    continue
                norm_desc = _norm_text(desc)
                item = {
                    "codigo": cod,
                    "descripcion": desc,
                    "norm_desc": norm_desc,
                    "tokens": _content_tokens(desc),
                }
                by_code[cod] = item
                entries.append(item)
        except Exception as e:
            print(f"[CIE10Mapper] Error cargando catálogo {path}: {e}")

    _CATALOG_CACHE[collection_suffix] = {"by_code": by_code, "entries": entries}
    return _CATALOG_CACHE[collection_suffix]


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


def _lookup_alias(collection_suffix: str, term: str, catalog: Dict[str, Any], sex: str, age: float):
    norm_t = _norm_text(term)
    by_code = catalog.get("by_code", {})
    alias_table = _ALIAS_DIAGNOSTICOS if collection_suffix == "diagnosticos" else _ALIAS_PROCEDIMIENTOS
    for required_parts, code, score in alias_table:
        if all(re.search(rf"\b{re.escape(part)}\b", norm_t) for part in required_parts) and code in by_code:
            if not is_biologically_incompatible(code, sex, age):
                entry = by_code[code]
                return {
                    "termino_original": term,
                    "codigo": entry["codigo"],
                    "descripcion": entry["descripcion"],
                    "similitud": score,
                }
    return None


def _lexical_candidates(term: str, catalog: Dict[str, Any], limit: int = 8) -> List[Dict[str, Any]]:
    q_tokens = _content_tokens(term)
    if not q_tokens:
        return []
    scored = []
    for item in catalog.get("entries", []):
        if not item["tokens"]:
            continue
        inter = len(q_tokens & item["tokens"])
        if inter == 0:
            continue
        coverage = inter / len(q_tokens)
        precision = inter / len(item["tokens"])
        score = round(min(0.95, 0.45 + 0.35 * coverage + 0.15 * precision), 3)
        if score >= 0.50:
            scored.append({
                "codigo": item["codigo"],
                "descripcion": item["descripcion"],
                "similitud": score,
            })
    scored.sort(key=lambda c: c["similitud"], reverse=True)
    return scored[:limit]


def _search_term(
    collection_suffix: str,
    term: str,
    context: str = "",
    sex: str = "Otro",
    age: float = None,
    mode: str = "auto",
    api_key: str = None
) -> Dict[str, Any]:
    """Busca un término usando matching clínico híbrido (catálogo oficial + ChromaDB) y validación por LLM."""
    collection_name = f"{ACTIVE_TERM}_{collection_suffix}"
    catalog = _get_catalog(collection_suffix)
    q_tokens = _content_tokens(term)

    # 1. Coincidencia clínica directa verificada contra el catálogo oficial
    alias_hit = _lookup_alias(collection_suffix, term, catalog, sex, age)
    if alias_hit:
        return alias_hit

    try:
        candidates_map: Dict[str, Dict[str, Any]] = {}

        # 2. Búsqueda vectorial en ChromaDB (consulta en MAYÚSCULAS para alinear con el catálogo oficial)
        col = get_collection(collection_name)
        if col.count() > 0:
            embedder = _get_embedder()
            query_embedding = embedder.encode([term.upper()]).tolist()
            results = col.query(query_embeddings=query_embedding, n_results=16)
            if results.get("documents") and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    meta = results["metadatas"][0][i]
                    cod = str(meta.get("codigo") or "").strip()
                    desc = str(meta.get("descripcion") or term).strip()
                    distance = results["distances"][0][i]
                    vec_sim = max(0.0, 1.0 - distance)

                    desc_tokens = _content_tokens(desc)
                    lex_cov = (len(q_tokens & desc_tokens) / len(q_tokens)) if q_tokens else 0.0
                    combined = round(min(0.98, vec_sim * (0.78 + 0.22 * lex_cov) + 0.12 * lex_cov), 3)
                    if combined >= 0.42 and cod:
                        prev = candidates_map.get(cod)
                        if not prev or combined > prev["similitud"]:
                            candidates_map[cod] = {
                                "codigo": cod,
                                "descripcion": desc,
                                "similitud": combined,
                            }

        # 3. Enriquecer con búsqueda léxica directa del catálogo oficial JSON (respaldo offline)
        for lc in _lexical_candidates(term, catalog, limit=6):
            cod = lc["codigo"]
            if cod not in candidates_map or lc["similitud"] > candidates_map[cod]["similitud"]:
                candidates_map[cod] = lc

        candidates = sorted(candidates_map.values(), key=lambda c: c["similitud"], reverse=True)[:5]

        if not candidates:
            return {
                "termino_original": term,
                "codigo": None,
                "descripcion": "Sin correspondencia adecuada en el catálogo clínico",
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

        # Si no hay contexto, usar el mejor candidato compatible
        if not context.strip():
            best = compatible_candidates[0]
        else:
            from app.core.entity_extractor import validate_cie10_candidates
            best_idx = validate_cie10_candidates(term, context, compatible_candidates, mode=mode, api_key=api_key)
            if 0 <= best_idx < len(compatible_candidates):
                best = compatible_candidates[best_idx]
            else:
                best = compatible_candidates[0]

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

