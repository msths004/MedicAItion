import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.local_db import get_all_patients
from app.db.chroma_store import get_collection
from app.core.cie10_mapper import _get_embedder

col = get_collection("patients_semantic")
embedder = _get_embedder()

for p in get_all_patients():
    curp = p.get("curp")
    nombre = p.get("nombre_completo") or f"{p.get('nombres', '')} {p.get('primer_apellido', '')} {p.get('segundo_apellido', '')}".strip()
    doc_text = (
        f"Paciente: {nombre}. "
        f"CURP: {curp}. "
        f"Folio: {p.get('folio_hospital') or ''}. "
        f"Ocupación: {p.get('ocupacion') or ''}. "
        f"Ubicación: {p.get('ubicacion_casa') or ''}. "
        f"Lugar de Nacimiento: {p.get('lugar_nacimiento') or ''}. "
        f"Anotaciones y Antecedentes: {p.get('anotaciones_generales') or ''}."
    )
    embedding = embedder.encode([doc_text]).tolist()
    col.upsert(
        ids=[curp],
        embeddings=embedding,
        documents=[doc_text],
        metadatas=[{
            "patient_curp": curp,
            "nombre_paciente": nombre,
        }]
    )
    print(f"Indizado correctamente: {nombre} ({curp})")

print(f"Total pacientes indizados en ChromaDB: {col.count()}")
