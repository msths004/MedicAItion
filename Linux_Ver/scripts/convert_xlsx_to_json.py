"""
Conversor de archivos oficiales Excel (CIE-10 / CIE-9MC) a JSON
para su ingesta en ChromaDB.

Uso:
    python scripts/convert_xlsx_to_json.py

Lee los archivos .xlsx de Archivos_CIE10/ y genera los .json
en terminology_database/cie10_mexico_2024/
"""

import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

try:
    import openpyxl
except ImportError:
    print("Instalando openpyxl...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl", "--quiet"])
    import openpyxl

# ── Rutas ────────────────────────────────────────────────────────────────────
XLSX_DIR = os.path.join(os.path.dirname(__file__), "..", "Archivos_CIE10")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "terminology_database", "cie10_mexico_2024")

DIAGNOSTICOS_FILE = "DIAGNOSTICOS_20240416.xlsx"
PROCEDIMIENTOS_FILE = "PROCEDIMIENTO_202402.xlsx"


# ── Conversor de Diagnósticos CIE-10 ────────────────────────────────────────
def convert_diagnosticos():
    path = os.path.join(XLSX_DIR, DIAGNOSTICOS_FILE)
    if not os.path.exists(path):
        print(f"  ❌ No encontrado: {path}")
        return

    print(f"\n📂 Procesando {DIAGNOSTICOS_FILE}...")
    wb = openpyxl.load_workbook(path, read_only=True)

    # Buscar la hoja de datos (la primera que no sea "Descripción")
    ws = None
    for name in wb.sheetnames:
        if "descripci" not in name.lower():
            ws = wb[name]
            break

    if ws is None:
        print("  ❌ No se encontró hoja de datos")
        wb.close()
        return

    # Leer headers para encontrar las columnas correctas
    headers = {}
    for row in ws.iter_rows(min_row=1, max_row=1, values_only=False):
        for cell in row:
            if cell.value:
                headers[str(cell.value).strip().upper()] = cell.column - 1

    # Columnas necesarias
    col_key = headers.get("CATALOG_KEY")
    col_name = headers.get("NOMBRE")
    col_chars = headers.get("NO. CARACTERES")
    col_chapter_key = headers.get("CLAVE_CAPITULO")
    col_chapter = headers.get("CAPITULO")

    if col_key is None or col_name is None:
        print(f"  ❌ Columnas requeridas no encontradas. Disponibles: {list(headers.keys())}")
        wb.close()
        return

    entries = []
    skipped_categories = 0
    total = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        total += 1
        row_list = list(row)

        codigo = str(row_list[col_key]).strip() if row_list[col_key] else ""
        nombre = str(row_list[col_name]).strip() if row_list[col_name] else ""
        n_chars = int(row_list[col_chars]) if col_chars is not None and row_list[col_chars] else 0

        if not codigo or not nombre:
            continue

        # Solo incluir subcategorías (4+ caracteres) — son los códigos válidos
        # para reportar en expedientes clínicos.
        # Los de 3 caracteres son categorías padre (ej. "A00" = "CÓLERA") y no se
        # usan directamente en la codificación de diagnósticos.
        if n_chars < 4:
            skipped_categories += 1
            continue

        entry = {
            "codigo": codigo,
            "descripcion": nombre,
        }

        # Agregar capítulo si está disponible
        if col_chapter is not None and row_list[col_chapter]:
            entry["capitulo"] = str(row_list[col_chapter]).strip()

        entries.append(entry)

    wb.close()

    # Guardar JSON
    out_path = os.path.join(OUTPUT_DIR, "diagnosticos.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)

    print(f"  ✅ {len(entries)} diagnósticos extraídos (de {total} filas)")
    print(f"     {skipped_categories} categorías padre (3 chars) omitidas")
    print(f"     Guardado en: {out_path}")
    print(f"     Tamaño: {os.path.getsize(out_path) / 1024:.0f} KB")


# ── Conversor de Procedimientos CIE-9MC ──────────────────────────────────────
def convert_procedimientos():
    path = os.path.join(XLSX_DIR, PROCEDIMIENTOS_FILE)
    if not os.path.exists(path):
        print(f"  ❌ No encontrado: {path}")
        return

    print(f"\n📂 Procesando {PROCEDIMIENTOS_FILE}...")
    wb = openpyxl.load_workbook(path, read_only=True)

    # Buscar la hoja de datos (la primera que no sea MetaDatos)
    ws = None
    for name in wb.sheetnames:
        if "meta" not in name.lower():
            ws = wb[name]
            break

    if ws is None:
        print("  ❌ No se encontró hoja de datos")
        wb.close()
        return

    # Leer headers
    headers = {}
    for row in ws.iter_rows(min_row=1, max_row=1, values_only=False):
        for cell in row:
            if cell.value:
                headers[str(cell.value).strip().upper()] = cell.column - 1

    col_key = headers.get("CATALOG_KEY")
    col_name = headers.get("PRO_NOMBRE")
    col_chapter = headers.get("CAPITULO")

    if col_key is None or col_name is None:
        print(f"  ❌ Columnas requeridas no encontradas. Disponibles: {list(headers.keys())}")
        wb.close()
        return

    entries = []
    skipped_chapters = 0
    total = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        total += 1
        row_list = list(row)

        codigo = str(row_list[col_key]).strip() if row_list[col_key] else ""
        nombre = str(row_list[col_name]).strip() if row_list[col_name] else ""

        if not codigo or not nombre:
            continue

        # Omitir códigos que son solo capítulos (2 chars, ej. "00", "01")
        if len(codigo) <= 2:
            skipped_chapters += 1
            continue

        entry = {
            "codigo": codigo,
            "descripcion": nombre,
        }

        entries.append(entry)

    wb.close()

    # Guardar JSON
    out_path = os.path.join(OUTPUT_DIR, "procedimientos.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)

    print(f"  ✅ {len(entries)} procedimientos extraídos (de {total} filas)")
    print(f"     {skipped_chapters} capítulos padre omitidos")
    print(f"     Guardado en: {out_path}")
    print(f"     Tamaño: {os.path.getsize(out_path) / 1024:.0f} KB")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("═" * 55)
    print("  Conversor de archivos oficiales CIE-10 → JSON")
    print("  MedicAItion — Cruz Roja Mérida")
    print("═" * 55)

    if not os.path.exists(XLSX_DIR):
        print(f"\n  ❌ Carpeta no encontrada: {XLSX_DIR}")
        print("  Coloca los archivos Excel oficiales en esa carpeta.")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    convert_diagnosticos()
    convert_procedimientos()

    # Eliminar insumos.json si existe (los medicamentos no se codifican con CIE-10)
    insumos_path = os.path.join(OUTPUT_DIR, "insumos.json")
    if os.path.exists(insumos_path):
        os.remove(insumos_path)
        print(f"\n  🗑️  Eliminado: insumos.json (los medicamentos no usan código CIE-10)")

    print("\n" + "═" * 55)
    print("  ✅ Conversión completa")
    print("  Ahora ejecuta la ingesta: python scripts/ingest_terminologies.py")
    print("═" * 55)


if __name__ == "__main__":
    main()
