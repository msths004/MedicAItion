"""
Script de ingesta universal: escanea terminology_database y carga los datos en ChromaDB.
Ejecutar una sola vez antes de arrancar la app:
    python scripts/ingest_terminologies.py
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sentence_transformers import SentenceTransformer
from app.db.chroma_store import get_collection

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
TERM_DIR = "terminology_database"

EXPECTED_FILES = {
    "diagnosticos": "diagnosticos.json",       # CIE-10 — diagnósticos médicos
    "procedimientos": "procedimientos.json",   # CIE-9MC — procedimientos quirúrgicos/terapéuticos
    # "cif": "cif.json",                       # CIF — uso futuro (ver future_update/USO_FUTURO_CLUES_CIF.md)
    # "insumos" eliminado: los medicamentos no se codifican con CIE-10
}


def build_document(entry: dict) -> str:
    """Construye el texto a vectorizar combinando descripción y sinónimos."""
    parts = [entry.get("descripcion", "")]
    parts += entry.get("sinonimos", [])
    return " | ".join(p for p in parts if p)


def ingest_collection(manifest_id: str, col_type: str, filepath: str, model: SentenceTransformer):
    collection_name = f"{manifest_id}_{col_type}"
    print(f"\n📂 Ingresando colección: {collection_name}")

    with open(filepath, "r", encoding="utf-8") as f:
        entries = json.load(f)

    col = get_collection(collection_name)

    # Limpiar colección existente
    existing = col.get()
    if existing["ids"]:
        col.delete(ids=existing["ids"])
        print(f"   🗑  {len(existing['ids'])} entradas anteriores eliminadas")

    documents = [build_document(e) for e in entries]
    ids = [f"{collection_name}_{i}" for i in range(len(entries))]
    metadatas = [
        {"codigo": e.get("codigo", ""), "descripcion": e.get("descripcion", "")}
        for e in entries
    ]

    embeddings = model.encode(documents, show_progress_bar=True).tolist()

    # ChromaDB tiene un límite de tamaño de lote (usualmente 5461)
    BATCH_SIZE = 5000
    for i in range(0, len(entries), BATCH_SIZE):
        end = min(i + BATCH_SIZE, len(entries))
        col.add(
            documents=documents[i:end],
            embeddings=embeddings[i:end],
            metadatas=metadatas[i:end],
            ids=ids[i:end]
        )
    print(f"   ✅ {len(entries)} entradas ingresadas en '{collection_name}'")


def get_manifests() -> list:
    """Escanea la carpeta de terminologías y devuelve los manifiestos encontrados."""
    manifests = []
    if not os.path.exists(TERM_DIR):
        return manifests

    for folder_name in os.listdir(TERM_DIR):
        folder_path = os.path.join(TERM_DIR, folder_name)
        if os.path.isdir(folder_path):
            info_path = os.path.join(folder_path, "info.json")
            if os.path.exists(info_path):
                with open(info_path, "r", encoding="utf-8") as f:
                    try:
                        manifest = json.load(f)
                        manifest["_folder_path"] = folder_path
                        manifests.append(manifest)
                    except Exception as e:
                        print(f"   ⚠️  Error leyendo {info_path}: {e}")
    return manifests


def main():
    print("🚀 Iniciando ingesta inteligente de Bases Médicas en ChromaDB...")
    
    # 1. Bucle interactivo para verificar manifiestos
    while True:
        manifests = get_manifests()
        if manifests:
            print(f"   Encontradas {len(manifests)} bases de datos:")
            for m in manifests:
                print(f"    - {m.get('display_name', m.get('id', 'Desconocido'))}")
            break
            
        print(f"\n   ⚠️  No se encontró ninguna base de datos médica en '{TERM_DIR}'.")
        print("   Asegúrate de que haya al menos una carpeta con su archivo 'info.json'.")
        
        if os.path.exists(TERM_DIR):
            contents = os.listdir(TERM_DIR)
            print(f"   Actualmente, dentro de '{TERM_DIR}' solo hay: {contents}")
        else:
            print(f"   La carpeta '{TERM_DIR}' ni siquiera existe.")
            
        opcion = input("\n   ¿Qué deseas hacer? [1] Reintentar buscar  [2] Salir: ").strip()
        if opcion == '2':
            print("Saliendo...")
            sys.exit(1)
        print("Reintentando búsqueda...\n")

    # 2. Descargar modelo de embeddings con reintentos
    print(f"\n   Modelo de embeddings: {EMBEDDING_MODEL}")
    while True:
        try:
            model = SentenceTransformer(EMBEDDING_MODEL)
            break
        except Exception as e:
            print(f"\n   ❌ Error de conexión al descargar el modelo de búsqueda: {e}")
            print("   Esto es común si tu internet sufre micro-cortes.")
            opcion = input("   ¿Qué deseas hacer? [1] Reintentar  [2] Salir: ").strip()
            if opcion == '2':
                print("Saliendo...")
                sys.exit(1)
            print("Reintentando...\n")

    # 3. Ingestar cada base de datos encontrada
    for m in manifests:
        manifest_id = m.get("id")
        folder_path = m.get("_folder_path")
        
        print(f"\n{'='*50}\nProcesando Base: {m.get('display_name')}\n{'='*50}")
        
        # Iterar sobre los archivos esperados
        for col_type, filename in EXPECTED_FILES.items():
            filepath = os.path.join(folder_path, filename)
            if not os.path.exists(filepath):
                print(f"   ⚠️  Aviso: El archivo opcional {filename} no existe en esta base.")
                continue
            
            ingest_collection(manifest_id, col_type, filepath, model)

    print("\n✅ Ingesta completa. Todas las bases médicas están listas en ChromaDB.")


if __name__ == "__main__":
    main()
