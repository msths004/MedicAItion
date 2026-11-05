"""
MedicAItion — Lanzador principal (Linux)
Corre este archivo para iniciar la app:
    python run.py
O simplemente ejecuta: ./run.sh
"""

import sys
import os
import json
import subprocess

# ── Colores ──────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(t):   print(f"  \033[92m✅\033[0m {t}")
def warn(t): print(f"  \033[93m⚠️ \033[0m {t}")
def err(t):  print(f"  \033[91m❌\033[0m {t}")
def info(t): print(f"  \033[94mℹ️ \033[0m {t}")
def step(t): print(f"\n{BOLD}{CYAN}▶ {t}{RESET}")


# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd: list, **kwargs) -> int:
    return subprocess.run(cmd, **kwargs).returncode


def is_package_installed(package: str) -> bool:
    try:
        __import__(package)
        return True
    except ImportError:
        return False


# ── ETAPA 1: Instalar dependencias base ──────────────────────────────────────
BASE_PACKAGES = [
    ("fastapi",               "fastapi"),
    ("uvicorn",               "uvicorn"),
    ("dotenv",                "python-dotenv"),
    ("soundfile",             "soundfile"),
    ("noisereduce",           "noisereduce"),
    ("numpy",                 "numpy"),
    ("chromadb",              "chromadb"),
    ("sentence_transformers", "sentence-transformers"),
    ("sqlalchemy",            "sqlalchemy"),
    ("pydantic",              "pydantic"),
    ("multipart",             "python-multipart"),
    ("httpx",                 "httpx"),
    ("aiofiles",              "aiofiles"),
    ("psutil",                "psutil"),
    ("huggingface_hub",       "huggingface_hub"),
    ("torch",                 "torch"),
    ("faster_whisper",        "faster-whisper"),
    ("jinja2",                "jinja2"),
]


def install_base_requirements():
    step("ETAPA 1 — Verificando dependencias base")

    missing = []
    for import_name, pip_name in BASE_PACKAGES:
        if not is_package_installed(import_name):
            missing.append(pip_name)
        else:
            ok(f"{pip_name}")

    if not missing:
        ok("Todas las dependencias base están instaladas")
        return

    print(f"\n  Paquetes faltantes: {', '.join(missing)}")
    info("Instalando dependencias faltantes...")

    result = run([sys.executable, "-m", "pip", "install"] + missing)
    if result != 0:
        err("Error al instalar dependencias. Revisa tu conexión a internet.")
        sys.exit(1)

    ok("Dependencias instaladas correctamente")


# ── ETAPA 2: Verificar setup (wizard) ────────────────────────────────────────
def check_setup_done() -> bool:
    """Verifica si el wizard ya fue corrido (existe config.json válido)."""
    if not os.path.exists("config.json"):
        return False
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        model_path = config.get("model_path", "")
        if not os.path.exists(model_path):
            warn(f"El modelo configurado no existe en: {model_path}")
            return False
        return True
    except Exception:
        return False


def run_wizard() -> bool:
    """Retorna True si la app fue movida a otra ruta, False si se quedó aquí."""
    step("ETAPA 2 — Configuración inicial (primera vez)")
    info("Iniciando setup wizard...")
    print()
    result = run([sys.executable, "setup_wizard.py"])
    if result != 0:
        err("El wizard no completó correctamente.")
        sys.exit(1)
        
    # Si config.json no está aquí, significa que la app se mudó
    if not os.path.exists("config.json"):
        return True
    return False


# ── ETAPA 3: Verificar ChromaDB poblado ──────────────────────────────────────
def check_chroma_populated() -> bool:
    """Verifica si ChromaDB ya tiene datos. Si la carpeta chroma no existe, devuelve False."""
    try:
        import chromadb
        path = "data/chroma"
        if not os.path.exists(path):
            return False
        client = chromadb.PersistentClient(path=path)
        # Si tiene al menos una colección, asumimos que ya hubo ingesta previa
        return len(client.list_collections()) > 0
    except Exception:
        return False


def run_ingest():
    step("ETAPA 3 — Cargando Bases Médicas en ChromaDB")
    info("Vectorizando terminologías médicas (solo la primera vez)...")
    print()
    result = run([sys.executable, "scripts/ingest_terminologies.py"])
    if result != 0:
        err("Error al cargar las bases médicas. Revisa los archivos en terminology_database/")
        sys.exit(1)


# ── ETAPA 4: Arrancar la app ──────────────────────────────────────────────────
def start_app():
    step("ETAPA 4 — Iniciando MedicAItion")
    print()
    print(f"  {BOLD}App disponible en:{RESET} {CYAN}http://localhost:8000{RESET}")
    print(f"  {BOLD}API docs:{RESET}         {CYAN}http://localhost:8000/docs{RESET}")
    print(f"\n  Presiona {BOLD}Ctrl+C{RESET} para detener la app\n")

    # Abrir navegador automáticamente
    import threading, time, webbrowser
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8000")
    threading.Thread(target=open_browser, daemon=True).start()

    run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ])


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    # 0. Forzar CWD al directorio donde vive este script
    #    Evita errores de rutas relativas si se ejecuta desde otro lugar
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 1. Instalar dependencias base si faltan
    install_base_requirements()

    # Diferenciar estéticamente si es instalación vs uso normal
    if check_setup_done():
        print(f"\n{BOLD}{GREEN}")
        print("  ╔══════════════════════════════════════════════════╗")
        print("  ║   MedicAItion — Listo para usar (Linux)          ║")
        print("  ╚══════════════════════════════════════════════╝")
        print(RESET)
    else:
        print(f"\n{BOLD}{CYAN}")
        print("  ╔══════════════════════════════════════════════════╗")
        print("  ║   MedicAItion — Instalador Inicial (Linux)       ║")
        print("  ╚══════════════════════════════════════════════════╝")
        print(RESET)

    # 2. Wizard si es primera vez
    if not check_setup_done():
        warn("Primera ejecución detectada — iniciando configuración...")
        moved = run_wizard()
        if moved:
            print()
            ok("La aplicación ha sido instalada en su nueva ubicación.")
            info("Por favor, usa el acceso directo en tu Escritorio")
            info("O ve a la nueva carpeta y ejecuta ./run.sh desde ahí.")
            print()
            input(f"  {BOLD}{GREEN}¡La instalación fue un éxito! Presiona ENTER para cerrar...{RESET}")
            sys.exit(0)
    else:
        with open("config.json") as f:
            cfg = json.load(f)
        ok(f"Configuración encontrada: {cfg.get('model_name', 'Modelo')} "
           f"({cfg.get('device', '').upper()})")

    # 3. Ingestar Bases Médicas si ChromaDB está vacío
    if not check_chroma_populated():
        warn("Bases de datos médicas no encontradas — iniciando carga...")
        run_ingest()
    else:
        ok("Bases de datos médicas listas")

    # 4. Arrancar app
    start_app()


if __name__ == "__main__":
    main()
