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

# ── Rutas Base ───────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "terminology_database", "cie10_mexico_2024")


def find_file_by_substring(directory: str, substring: str) -> str:
    """Busca el primer archivo en el directorio que contenga el substring."""
    if not os.path.exists(directory):
        return None
    for f in os.listdir(directory):
        if substring.lower() in f.lower() and f.endswith(".xlsx") and not f.startswith("~"):
            return os.path.join(directory, f)
    return None


# ── Conversor de Diagnósticos CIE-10 ────────────────────────────────────────
def convert_diagnosticos(xlsx_dir: str):
    path = find_file_by_substring(xlsx_dir, "diagnostico")
    if not path:
        print(f"  [!] No se encontró ningún archivo con 'diagnostico' en su nombre en: {xlsx_dir}")
        return False

    print(f"\n📂 Procesando {os.path.basename(path)}...")
    wb = openpyxl.load_workbook(path, read_only=True)

    # Buscar la hoja de datos (la primera que no sea "Descripción")
    ws = None
    for name in wb.sheetnames:
        if "descripci" not in name.lower():
            ws = wb[name]
            break

    if ws is None:
        print("  [ERROR] No se encontró hoja de datos")
        wb.close()
        return False

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
    col_chapter = headers.get("CAPITULO")

    if col_key is None or col_name is None:
        print(f"  [ERROR] Columnas requeridas no encontradas. Disponibles: {list(headers.keys())}")
        wb.close()
        return False

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

        if n_chars < 4:
            skipped_categories += 1
            continue

        entry = {
            "codigo": codigo,
            "descripcion": nombre,
        }

        if col_chapter is not None and row_list[col_chapter]:
            entry["capitulo"] = str(row_list[col_chapter]).strip()

        entries.append(entry)

    wb.close()

    # Guardar JSON
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "diagnosticos.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)

    print(f"  [OK] {len(entries)} diagnósticos extraídos (de {total} filas)")
    print(f"     {skipped_categories} categorías padre (3 chars) omitidas")
    print(f"     Guardado en: {out_path}")
    print(f"     Tamaño: {os.path.getsize(out_path) / 1024:.0f} KB")
    return True


# ── Conversor de Procedimientos CIE-9MC ──────────────────────────────────────
def convert_procedimientos(xlsx_dir: str):
    path = find_file_by_substring(xlsx_dir, "procedimiento")
    if not path:
        print(f"  [!] No se encontró ningún archivo con 'procedimiento' en su nombre en: {xlsx_dir}")
        return False

    print(f"\n📂 Procesando {os.path.basename(path)}...")
    wb = openpyxl.load_workbook(path, read_only=True)

    # Buscar la hoja de datos (la primera que no sea MetaDatos)
    ws = None
    for name in wb.sheetnames:
        if "meta" not in name.lower():
            ws = wb[name]
            break

    if ws is None:
        print("  [ERROR] No se encontró hoja de datos")
        wb.close()
        return False

    headers = {}
    for row in ws.iter_rows(min_row=1, max_row=1, values_only=False):
        for cell in row:
            if cell.value:
                headers[str(cell.value).strip().upper()] = cell.column - 1

    col_key = headers.get("CATALOG_KEY")
    col_name = headers.get("PRO_NOMBRE")

    if col_key is None or col_name is None:
        print(f"  [ERROR] Columnas requeridas no encontradas. Disponibles: {list(headers.keys())}")
        wb.close()
        return False

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

        if len(codigo) <= 2:
            skipped_chapters += 1
            continue

        entry = {
            "codigo": codigo,
            "descripcion": nombre,
        }

        entries.append(entry)

    wb.close()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "procedimientos.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)

    print(f"  [OK] {len(entries)} procedimientos extraídos (de {total} filas)")
    print(f"     {skipped_chapters} capítulos padre omitidos")
    print(f"     Guardado en: {out_path}")
    print(f"     Tamaño: {os.path.getsize(out_path) / 1024:.0f} KB")
    return True


# ── Modulo Principal ─────────────────────────────────────────────────────────
def run_conversion(xlsx_dir: str) -> bool:
    print("=" * 55)
    print("  Conversor de archivos oficiales CIE-10/CIE-9MC → JSON")
    print("  MedicAItion — Cruz Roja Mérida")
    print("=" * 55)

    if not os.path.exists(xlsx_dir):
        print(f"\n  [ERROR] Carpeta no encontrada: {xlsx_dir}")
        return False

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Crear info.json para el catálogo
    info_path = os.path.join(OUTPUT_DIR, "info.json")
    if not os.path.exists(info_path):
        info_data = {
            "id": "cie10_mexico",
            "display_name": "CIE-10 México (Edición Automática)",
            "version": "2024",
            "publisher": "DGIS"
        }
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info_data, f, ensure_ascii=False, indent=2)

    diag_ok = convert_diagnosticos(xlsx_dir)
    proc_ok = convert_procedimientos(xlsx_dir)

    print("\n" + "=" * 55)
    if diag_ok or proc_ok:
        print("  [OK] Conversión completada con éxito.")
        return True
    else:
        print("  [ERROR] No se pudo convertir ninguno de los catálogos.")
        return False


if __name__ == "__main__":
    # Si se corre directo, usa una ruta por defecto o argumentos
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "Archivos_CIE10")
    run_conversion(target_dir)
