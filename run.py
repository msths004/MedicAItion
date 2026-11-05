"""
MedicAItion — Lanzador principal
Corre este archivo para iniciar la app:
    python run.py
O simplemente haz doble clic en run.bat
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

def c(text, color): return f"{color}{text}{RESET}"

def ok(t):   print(f"  \033[92m[OK]\033[0m {t}")
def warn(t): print(f"  \033[93m[!]\033[0m {t}")
def err(t):  print(f"  \033[91m[ERROR]\033[0m {t}")
def info(t): print(f"  \033[94m[INFO]\033[0m {t}")
def step(t): print(f"\n{BOLD}{CYAN}>>> {t}{RESET}")


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


def setup_cuda_dll_path():
    """
    Registra las rutas de las DLLs de NVIDIA (cublas64_12.dll, cudart64_12.dll, etc.)
    para que Windows pueda encontrarlas al cargar llama.dll.

    Usa MÚLTIPLES estrategias porque el entorno puede ser:
      - Python embebido/portable (.python_env descargado como .zip)
      - venv estándar
      - Instalación global de Python
    Y registra las rutas tanto en os.environ['PATH'] (método legacy, funciona siempre)
    como en os.add_dll_directory() (método moderno Python 3.8+).
    """
    if sys.platform != "win32":
        return

    nvidia_dll_dirs = set()

    # ── Estrategia 1: Ruta relativa al ejecutable de Python ──
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    possible_site_packages = [
        os.path.join(exe_dir, "Lib", "site-packages"),                       # Python embebido
        os.path.join(os.path.dirname(exe_dir), "Lib", "site-packages"),      # venv
    ]

    # ── Estrategia 2: site.getsitepackages() ──
    try:
        import site
        possible_site_packages.extend(site.getsitepackages())
        possible_site_packages.append(site.getusersitepackages())
    except Exception:
        pass

    # ── Estrategia 3: sys.path ──
    for p in sys.path:
        if "site-packages" in p:
            possible_site_packages.append(p)

    # ── Buscar carpetas nvidia/*/bin y nvidia/*/lib en cada site-packages ──
    seen = set()
    for sp in possible_site_packages:
        sp = os.path.abspath(sp) if sp else ""
        if not sp or sp in seen or not os.path.isdir(sp):
            continue
        seen.add(sp)

        nvidia_root = os.path.join(sp, "nvidia")
        if not os.path.isdir(nvidia_root):
            continue

        for pkg_name in os.listdir(nvidia_root):
            pkg_path = os.path.join(nvidia_root, pkg_name)
            if not os.path.isdir(pkg_path):
                continue
            for subdir in ("bin", "lib"):
                dll_dir = os.path.join(pkg_path, subdir)
                if os.path.isdir(dll_dir):
                    if any(f.lower().endswith(".dll") for f in os.listdir(dll_dir)):
                        nvidia_dll_dirs.add(dll_dir)

    if not nvidia_dll_dirs:
        return

    # ── Registrar en PATH (método legacy — funciona en TODOS los escenarios) ──
    current_path = os.environ.get("PATH", "")
    new_entries = [d for d in nvidia_dll_dirs if d not in current_path]
    if new_entries:
        os.environ["PATH"] = ";".join(new_entries) + ";" + current_path

    # ── Registrar con os.add_dll_directory (método moderno Python 3.8+) ──
    for d in nvidia_dll_dirs:
        try:
            os.add_dll_directory(d)
        except (OSError, AttributeError):
            pass


def check_vc_redist() -> bool:
    import ctypes
    import sys
    if sys.platform != "win32":
        return True
    try:
        ctypes.CDLL("msvcp140.dll")
        return True
    except OSError:
        return False


def check_gpu_and_driver() -> tuple[str | None, bool]:
    import subprocess
    import ctypes
    import sys
    
    gpu_name = None
    has_gpu = False
    has_driver = False
    
    try:
        if sys.platform == "win32":
            output = subprocess.check_output("wmic path win32_VideoController get name", shell=True, text=True)
            for line in output.split("\n"):
                if "NVIDIA" in line.upper():
                    has_gpu = True
                    gpu_name = line.strip()
                    break
        else:
            output = subprocess.check_output("lspci | grep -i nvidia", shell=True, text=True)
            if output:
                has_gpu = True
                gpu_name = "NVIDIA GPU"
    except Exception:
        pass
        
    if has_gpu:
        if sys.platform == "win32":
            try:
                ctypes.CDLL("nvcuda.dll")
                has_driver = True
            except OSError:
                pass
        else:
            try:
                ctypes.CDLL("libcuda.so")
                has_driver = True
            except OSError:
                pass
                
    return gpu_name if has_gpu else None, has_driver


def check_python_version() -> tuple[bool, str]:
    import sys
    version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    # Python 3.11 es la versión recomendada para el wheel de GPU precompilado
    is_ok = (sys.version_info.major == 3 and sys.version_info.minor == 11)
    return is_ok, version_str


def check_disk_space() -> tuple[bool, float]:
    import shutil
    try:
        total, used, free = shutil.disk_usage(".")
        free_gb = round(free / (1024**3), 1)
        # Se requieren al menos 6.0 GB para descargar y descomprimir el modelo de IA
        return free_gb >= 6.0, free_gb
    except Exception:
        return True, 0.0


def run_preflight_checks() -> tuple[dict, bool]:
    # Prerrequisitos que la app no puede resolver sola (externos del sistema)
    vc_ok = check_vc_redist()
    gpu_name, cuda_driver_ok = check_gpu_and_driver()
    python_ok, python_version = check_python_version()
    space_ok, free_gb = check_disk_space()
    
    checks = {
        "vc_redist": vc_ok,
        "gpu_name": gpu_name,
        "cuda_driver": cuda_driver_ok,
        "python_ok": python_ok,
        "python_version": python_version,
        "space_ok": space_ok,
        "free_gb": free_gb
    }
    
    # Bloqueos críticos que causarán fallos absolutos de la instalación
    # (Visual C++ faltante o no tener espacio suficiente en disco)
    critical_ok = vc_ok and space_ok
    return checks, critical_ok


def print_preflight_table(checks: dict):
    print(f"\n{BOLD}{CYAN}=== PRERREQUISITOS EXTERNOS DEL SISTEMA ==={RESET}")
    
    # 1. VC++ Redist
    if sys.platform == "win32":
        vc_str = c("Instalado", GREEN) if checks["vc_redist"] else c("FALTANTE (Se requiere Microsoft Visual C++ Redistributable)", RED)
        print(f"  [{c('✓', GREEN) if checks['vc_redist'] else c('X', RED)}] Microsoft Visual C++ Redistributable : {vc_str}")
        
    # 2. Versión de Python
    py_ok = checks["python_ok"]
    py_ver = checks["python_version"]
    if py_ok:
        print(f"  [{c('✓', GREEN)}] Versión de Python (Recom. 3.11)     : OK ({py_ver})")
    else:
        if checks["gpu_name"]:
            print(f"  [{c('!', YELLOW)}] Versión de Python (Recom. 3.11)     : ADVERTENCIA ({py_ver})")
            print(f"      {c('Nota: El precompilado de GPU requiere Python 3.11. Se usará CPU o requerirá compilación.', YELLOW)}")
        else:
            print(f"  [{c('✓', GREEN)}] Versión de Python (Recom. 3.11)     : OK ({py_ver})")
        
    # 3. GPU & Driver
    gpu_name = checks["gpu_name"]
    if gpu_name:
        driver_str = c("OK", GREEN) if checks["cuda_driver"] else c("FALTANTE (Instala los drivers de tu tarjeta NVIDIA)", RED)
        print(f"  [{c('✓', GREEN) if checks['cuda_driver'] else c('X', RED)}] Tarjeta Gráfica NVIDIA detectada     : {gpu_name} (Driver CUDA: {driver_str})")
    else:
        print(f"  [{c('✓', GREEN)}] Tarjeta Gráfica NVIDIA detectada     : No detectada (Se usará CPU por defecto)")
        
    # 4. Espacio en disco
    space_ok = checks["space_ok"]
    free_gb = checks["free_gb"]
    if space_ok:
        print(f"  [{c('✓', GREEN)}] Espacio libre en disco             : OK ({free_gb} GB libres, mín. 6 GB requeridos)")
    else:
        print(f"  [{c('X', RED)}] Espacio libre en disco             : INSUFICIENTE ({free_gb} GB libres, se requieren mín. 6 GB)")
        
    print(f"{BOLD}{CYAN}==========================================={RESET}\n")


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
    """Verifica si el wizard ya fue corrido (existe config.json válido) y si llama-cpp-python carga bien."""
    if not os.path.exists("config.json"):
        return False
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        model_path = config.get("model_path", "")
        if not os.path.exists(model_path):
            warn(f"El modelo configurado no existe en: {model_path}")
            return False
            
        # Verificar que el motor de IA pueda cargar sus DLLs y dependencias
        setup_cuda_dll_path()
        from llama_cpp import Llama  # noqa
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
    result = run([sys.executable, "scripts/ingest_terminologies.py", "--non-interactive"])
    if result != 0:
        err("Error al cargar las bases médicas. Revisa los archivos en terminology_database/")
        sys.exit(1)


# ── ETAPA 4: Arrancar la app ──────────────────────────────────────────────────
def start_app():
    step("ETAPA 4 — Iniciando MedicAItion")
    print()
    print(f"  {BOLD}Cargando el servidor...{RESET} (esto puede tardar unos segundos)")
    print(f"  Presiona {BOLD}Ctrl+C{RESET} para detener la app\n")

    # Abrir navegador solo cuando el backend esté completamente listo
    import threading, time, webbrowser, urllib.request
    def open_browser_when_ready():
        url = "http://localhost:8000"
        max_wait = 120  # esperar máximo 2 minutos
        waited = 0
        while waited < max_wait:
            try:
                urllib.request.urlopen(url, timeout=2)
                # El servidor respondió — abrir navegador
                print(f"\n  {BOLD}{GREEN}✓ Backend listo.{RESET}")
                print(f"  {BOLD}App disponible en:{RESET} {CYAN}{url}{RESET}")
                print(f"  {BOLD}API docs:{RESET}         {CYAN}{url}/docs{RESET}\n")
                webbrowser.open(url)
                return
            except Exception:
                time.sleep(1)
                waited += 1
        print(f"\n  {YELLOW}[!] El servidor tardó demasiado. Abre manualmente: {url}{RESET}")

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

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
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Si la app ya está totalmente configurada y funcionando, iniciar directo sin retrasos
    if check_setup_done():
        print(f"\n{BOLD}{GREEN}")
        print("  ==============================================")
        print("        MedicAItion — Iniciando Aplicación      ")
        print("  ==============================================")
        print(RESET)
        
        # Ingestar bases médicas si están vacías
        if not check_chroma_populated():
            info("ChromaDB no inicializado — creando índice de búsqueda para terminologías médicas...")
            run_ingest()
            
        start_app()
        return

    # Si no está configurado, ejecutar los chequeos de prerrequisitos del sistema
    checks, critical_ok = run_preflight_checks()

    print(f"\n{BOLD}{CYAN}")
    print("  ==============================================")
    print("        MedicAItion — Chequeo de Prerrequisitos ")
    print("  ==============================================")
    print(RESET)
    print_preflight_table(checks)

    if not critical_ok:
        err("Faltan prerrequisitos críticos del sistema para continuar.")
        if not checks["vc_redist"]:
            warn("--> Falta Microsoft Visual C++ Redistributable.")
            warn("    Descárgalo e instálalo desde: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        if not checks["space_ok"]:
            warn(f"--> Espacio en disco insuficiente ({checks['free_gb']} GB libres, necesitas mín. 6 GB).")
        warn("Por favor soluciona estos problemas y vuelve a ejecutar el instalador.")
        print()
        input(f"  {BOLD}Presiona ENTER para salir...{RESET}")
        sys.exit(1)

    # Advertencia no bloqueante de Python para GPU
    if checks["gpu_name"] and not checks["python_ok"]:
        warn("ATENCIÓN: Tu versión de Python no es 3.11.")
        warn("El precompilado con soporte para tu GPU RTX requiere exactamente Python 3.11.")
        warn("Si continúas, la instalación de GPU fallará o requerirá herramientas pesadas de compilación C++.")
        confirm_py = input(f"  {c('>>>', CYAN)} ¿Deseas continuar con la instalación de todas formas? [s/N]: ").strip()
        if confirm_py.upper() != "S":
            sys.exit(0)

    warn("Se iniciará el instalador automático de la aplicación.")
    confirm = input(f"\n  {c('>>>', CYAN)} ¿Deseas continuar? [S/n]: ").strip()
    if confirm.upper() == "N":
        print(f"\n  {c('[INFO]', GREEN)} Instalación cancelada. Saliendo.")
        sys.exit(0)

    # 1. Instalar dependencias de Python base
    install_base_requirements()

    # 2. Iniciar el Setup Wizard (llama-cpp, descarga del modelo, etc.)
    warn("Iniciando setup wizard...")
    moved = run_wizard()
    if moved:
        print()
        ok("La aplicación ha sido instalada en su nueva ubicación.")
        info("Por favor, usa el acceso directo en tu Escritorio")
        info("O ve a la nueva carpeta y ejecuta run.bat desde ahí.")
        print()
        input(f"  {BOLD}{GREEN}¡La instalación fue un éxito! Presiona ENTER para cerrar...{RESET}")
        sys.exit(0)

    # 3. Ingestar Bases Médicas si ChromaDB está vacío
    if not check_chroma_populated():
        info("ChromaDB no inicializado — creando índice de búsqueda para terminologías médicas...")
        run_ingest()
    else:
        ok("Bases de datos médicas listas y cargadas en ChromaDB")

    # 4. Arrancar app
    start_app()


if __name__ == "__main__":
    main()
