"""
MedicAItion — Setup Wizard
Ejecutar una sola vez antes de usar la app:
    python setup_wizard.py
"""

import sys
import os
import json
import subprocess
import importlib

# ── Colores en terminal ──────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def c(text, color): return f"{color}{text}{RESET}"
def header(text):   print(f"\n{BOLD}{CYAN}{'='*55}{RESET}\n  {BOLD}{text}{RESET}\n{BOLD}{CYAN}{'='*55}{RESET}")
def ok(text):       print(f"  {c('[OK]', GREEN)} {text}")
def warn(text):     print(f"  {c('[!]', YELLOW)} {text}")
def err(text):      print(f"  {c('[ERROR]', RED)} {text}")
def info(text):     print(f"  {c('[INFO]', BLUE)} {text}")
def ask(text):      return input(f"\n  {c('>>>', CYAN)} {text}: ").strip()


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
    #    Funciona en Python embebido/portable (.python_env\python.exe)
    #    y en venvs (.python_env\Scripts\python.exe)
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    possible_site_packages = [
        os.path.join(exe_dir, "Lib", "site-packages"),                       # Python embebido
        os.path.join(os.path.dirname(exe_dir), "Lib", "site-packages"),      # venv (Scripts\python.exe → Lib\site-packages)
    ]

    # ── Estrategia 2: site.getsitepackages() ──
    #    Funciona en instalaciones normales de Python
    try:
        import site
        possible_site_packages.extend(site.getsitepackages())
        possible_site_packages.append(site.getusersitepackages())
    except Exception:
        pass

    # ── Estrategia 3: sys.path ──
    #    Respaldo general
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
                    # Verificar que realmente contiene DLLs
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


# ── Modelos disponibles ──────────────────────────────────────────────────────
MODELS = [
    {
        "id": 1,
        "name": "Med42-8B",
        "quant": "Q4_K_M",
        "size_gb": 4.9,
        "device": "gpu",
        "repo": "QuantFactory/Llama3-Med42-8B-GGUF",
        "filename": "Llama3-Med42-8B.Q4_K_M.gguf",
        "desc": "Mejor calidad médica — Requiere GPU RTX 4050/4060+",
        "min_vram_gb": 6,
    },
    {
        "id": 2,
        "name": "Med42-8B",
        "quant": "Q2_K",
        "size_gb": 3.0,
        "device": "cpu",
        "repo": "QuantFactory/Llama3-Med42-8B-GGUF",
        "filename": "Llama3-Med42-8B.Q2_K.gguf",
        "desc": "Versión ligera — CPU o GPU con poca VRAM",
        "min_vram_gb": 0,
    },
    {
        "id": 3,
        "name": "OpenBioLLM-8B",
        "quant": "Q4_K_M",
        "size_gb": 5.0,
        "device": "gpu",
        "repo": "bartowski/OpenBioLLM-Llama3-8B-GGUF",
        "filename": "OpenBioLLM-Llama3-8B-Q4_K_M.gguf",
        "desc": "Excelente en extracción de entidades — Requiere GPU",
        "min_vram_gb": 6,
    },
    {
        "id": 4,
        "name": "OpenBioLLM-8B",
        "quant": "Q2_K",
        "size_gb": 3.0,
        "device": "cpu",
        "repo": "bartowski/OpenBioLLM-Llama3-8B-GGUF",
        "filename": "OpenBioLLM-Llama3-8B-Q2_K.gguf",
        "desc": "Versión ligera — CPU o GPU con poca VRAM",
        "min_vram_gb": 0,
    },
]


# ── PASO 1: Detectar hardware ────────────────────────────────────────────────
def detect_hardware() -> dict:
    header("PASO 1 — Detectando hardware")

    hw = {"has_gpu": False, "vram_gb": 0, "ram_gb": 0, "gpu_name": None}

    # RAM del sistema
    try:
        import psutil
        hw["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)
        ok(f"RAM del sistema: {hw['ram_gb']} GB")
    except ImportError:
        warn("No se pudo medir la RAM (psutil no instalado)")

    # Detectar GPU NVIDIA usando comandos de Windows
    try:
        output = subprocess.check_output("wmic path win32_VideoController get name", shell=True, text=True)
        for line in output.split("\n"):
            if "NVIDIA" in line.upper():
                hw["has_gpu"] = True
                hw["gpu_name"] = line.strip()
                break
    except Exception:
        pass

    if hw["has_gpu"]:
        ok(f"GPU detectada: {hw['gpu_name']}")
        try:
            import torch
            if torch.cuda.is_available():
                hw["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
                ok(f"VRAM detectada: {hw['vram_gb']} GB")
            else:
                warn("PyTorch local no tiene CUDA, asumiendo 8GB VRAM para la RTX")
                hw["vram_gb"] = 8.0
        except ImportError:
            hw["vram_gb"] = 8.0
    else:
        warn("No se detectó GPU NVIDIA automáticamente.")

    return hw


# ── PASO 2: Elegir versión de llama-cpp-python ───────────────────────────────
def choose_llama_version(hw: dict) -> str:
    header("PASO 2 — Versión de llama-cpp-python")

    if not hw["has_gpu"]:
        warn("Al parecer no tienes una GPU NVIDIA.")
        print()
        print(f"  {c('[1]', CYAN)} Forzar instalación GPU (elige esto si SABES que tienes NVIDIA)")
        print(f"  {c('[2]', CYAN)} CPU  — instala la versión sin CUDA (más lenta)")
        print()
        while True:
            choice = ask("¿Qué versión quieres instalar? [2]") or "2"
            if choice == "1":
                ok("Forzando versión GPU (CUDA)")
                return "gpu"
            elif choice == "2":
                ok("Usarás la versión CPU")
                return "cpu"
            else:
                err("Opción inválida, elige 1 o 2")

    # Hay GPU → dejar elegir
    print(f"\n  GPU detectada: {c(hw['gpu_name'], GREEN)}")
    print()
    print(f"  {c('[1]', CYAN)} GPU  (recomendado) — usa tu tarjeta para máxima velocidad")
    print(f"  {c('[2]', CYAN)} CPU  — instala la versión sin CUDA (más lenta)")
    print()

    while True:
        choice = ask("¿Qué versión de llama-cpp-python quieres instalar? (Escribe el número 1 o 2)")
        if choice == "1":
            ok("Usarás la versión GPU (CUDA)")
            return "gpu"
        elif choice == "2":
            warn("Usarás la versión CPU aunque tienes GPU disponible")
            return "cpu"
        else:
            err("Opción inválida, por favor escribe el número 1 o 2")


# ── PASO 3: Instalar llama-cpp-python ────────────────────────────────────────
def install_llama_cpp(version: str):
    header("PASO 3 — Instalando llama-cpp-python")

    if version == "gpu":
        info("Instalando versión con soporte CUDA (RTX 4050/4060)...")
        info("También se descargarán las librerías CUDA de NVIDIA (puede tardar varios minutos)")
        # Wheel pre-compilado exacto para CUDA 12.1 (Garantizado para Python 3.11)
        url = "https://github.com/abetlen/llama-cpp-python/releases/download/v0.2.63-cu121/llama_cpp_python-0.2.63-cp311-cp311-win_amd64.whl"
        cmd = [sys.executable, "-m", "pip", "install", url, "nvidia-cuda-runtime-cu12", "nvidia-cublas-cu12", "--force-reinstall", "--no-cache-dir"]
    else:
        info("Instalando versión CPU estándar...")
        cmd = [sys.executable, "-m", "pip", "install", "llama-cpp-python"]

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        err("Error al instalar llama-cpp-python")
        err("Intenta instalarlo manualmente y vuelve a correr el wizard")
        sys.exit(1)

    # Verificar importación
    try:
        importlib.invalidate_caches()
        setup_cuda_dll_path()
        from llama_cpp import Llama  # noqa
        ok("llama-cpp-python instalado y verificado correctamente")
    except Exception as e:
        err("llama-cpp-python se instaló pero no se puede importar")
        if sys.platform == "win32":
            warn("En Windows, esto suele deberse a que falta 'Microsoft Visual C++ Redistributable'.")
            warn("Descárgalo gratis e instálalo desde: https://aka.ms/vs/17/release/vc_redist.x64.exe")
            warn("Una vez instalado, reinicia tu computadora e intenta correr el wizard nuevamente.")
        err(f"Detalle del error: {e}")
        sys.exit(1)


# ── PASO 4: Elegir modelo ────────────────────────────────────────────────────
def choose_model(hw: dict, llama_version: str) -> dict:
    header("PASO 4 — Elige el modelo de IA médica")

    # Filtrar modelos según versión de llama elegida
    if llama_version == "gpu":
        available = MODELS  # todos disponibles
        info("Mostrando todos los modelos (tienes versión GPU instalada)")
    else:
        available = [m for m in MODELS if m["device"] == "cpu"]
        info("Mostrando solo modelos CPU (versión GPU no instalada)")

    print()
    print(f"  {'#':<4} {'Modelo':<20} {'Quant':<10} {'Tamaño':<10} {'Descripción'}")
    print(f"  {'─'*4} {'─'*20} {'─'*10} {'─'*10} {'─'*35}")

    for m in available:
        rec = c(" ← RECOMENDADO", GREEN) if (
            llama_version == "gpu" and m["device"] == "gpu"
            and hw.get("vram_gb", 0) >= m["min_vram_gb"]
            and m["id"] == 1
        ) else ""
        id_str = f"[{m['id']}]"
        print(f"  {c(id_str, CYAN):<12} {m['name']:<20} {m['quant']:<10} "
              f"{str(m['size_gb'])+' GB':<10} {m['desc']}{rec}")

    valid_ids = [str(m["id"]) for m in available]
    default = valid_ids[0]

    while True:
        choice = ask("¿Qué modelo quieres descargar? (Escribe el número)")
        if choice in valid_ids:
            selected = next(m for m in available if str(m["id"]) == choice)
            ok(f"Seleccionado: {selected['name']} {selected['quant']} ({selected['size_gb']} GB)")
            return selected
        else:
            err(f"Opción inválida. Escribe uno de estos números: {', '.join(valid_ids)}")


# ── PASO 5: Elegir ruta de instalación ──────────────────────────────────────
def choose_install_path(model: dict) -> tuple[str, bool]:
    header("PASO 5 — Ruta de instalación de la aplicación")

    default_path = os.path.abspath(os.path.join(os.path.expanduser("~"), "MedicAItion"))
    print(f"  {c('[1]', CYAN)} Instalar en la ruta sugerida: {c(default_path, GREEN)}")
    print(f"  {c('[2]', CYAN)} Elegir ruta preferida (ej. C:\\Aplicaciones\\MedicAItion)")
    print()

    while True:
        opt = ask("¿Dónde quieres instalar la app? (Escribe el número 1 o 2)")
        if opt == "1":
            chosen = default_path
        elif opt == "2":
            chosen = ask("Pega o escribe la ruta preferida (ej. C:\\MisAplicaciones)")
            if not chosen:
                continue
            # Asegurar que siempre se cree dentro de una carpeta "MedicAItion"
            chosen = os.path.abspath(chosen.strip())
            if not os.path.basename(chosen).lower() == "medicaition":
                chosen = os.path.join(chosen, "MedicAItion")
        else:
            err("Opción inválida, por favor escribe el número 1 o 2")
            continue

        chosen = os.path.abspath(chosen.strip())

        try:
            os.makedirs(chosen, exist_ok=True)
            import shutil
            free_gb = shutil.disk_usage(chosen).free / (1024**3)
            if free_gb < model["size_gb"] + 0.5:
                warn(f"Espacio libre en '{chosen}': {free_gb:.1f} GB")
                warn(f"Se necesitan al menos {model['size_gb'] + 0.5:.1f} GB")
                retry = ask("¿Quieres elegir otra ruta? [S/n]") or "S"
                if retry.upper() == "S":
                    continue

            ok(f"Ruta seleccionada: {chosen}")
            break
        except PermissionError:
            err(f"Sin permisos de escritura en '{chosen}'")
            err("Elige otra ruta o ejecútalo como administrador")
        except Exception as e:
            err(f"Ruta inválida: {e}")
            
    create_shortcut = ask("¿Quieres crear un acceso directo en tu Escritorio? [S/n]") or "S"
    return chosen, create_shortcut.upper() != "N"


def copy_app_files(dest_path: str):
    current_dir = os.path.abspath(os.getcwd())
    dest_path = os.path.abspath(dest_path)
    
    if current_dir == dest_path:
        return
        
    header("PASO 5.5 — Instalando archivos de la aplicación")
    info(f"Copiando archivos de {current_dir}")
    info(f"Hacia {dest_path} ...")
    
    import shutil
    def ignore_files(directory, files):
        relative_path = os.path.relpath(directory, current_dir)
        
        # En la raíz, ignoramos estas carpetas pesadas/basura
        if relative_path == ".":
            return [f for f in files if f in [".git", "__pycache__", "models", "data", ".venv", "env", "artifacts"]]
            
        # En subcarpetas de librerías, solo ignoramos basura
        return [f for f in files if f == "__pycache__"]
        
    try:
        shutil.copytree(current_dir, dest_path, dirs_exist_ok=True, ignore=ignore_files)
        os.makedirs(os.path.join(dest_path, "data"), exist_ok=True)
        ok("Archivos copiados exitosamente")
        os.chdir(dest_path)
        ok("Directorio de trabajo cambiado a la nueva ruta")
    except Exception as e:
        err(f"Error al copiar archivos: {e}")
        sys.exit(1)


# ── PASO 6: Descargar modelo ─────────────────────────────────────────────────
def download_model(model: dict, install_path: str) -> str:
    header("PASO 6 — Descargando modelo desde HuggingFace")

    os.makedirs(install_path, exist_ok=True)
    dest_path = os.path.join(install_path, model["filename"])

    if os.path.exists(dest_path):
        size_gb = os.path.getsize(dest_path) / (1024**3)
        ok(f"El modelo ya existe en: {dest_path} ({size_gb:.1f} GB)")
        reuse = ask("¿Usar el existente? [S/n]") or "S"
        if reuse.upper() != "N":
            return dest_path

    info(f"Descargando {model['filename']} (~{model['size_gb']} GB)")
    info(f"Destino: {dest_path}")
    info("Esto puede tardar varios minutos según tu conexión...")
    info("Si se interrumpe, al volver a ejecutar se reanudará automáticamente")
    print()

    # URL directa de descarga de HuggingFace (funciona sin autenticación para repos públicos)
    url = f"https://huggingface.co/{model['repo']}/resolve/main/{model['filename']}"
    part_path = dest_path + ".part"  # Archivo temporal para descargas parciales

    max_retries = 5
    chunk_size = 1024 * 1024  # 1 MB por chunk

    for attempt in range(1, max_retries + 1):
        try:
            # ── Determinar cuánto ya se descargó (para reanudación) ──
            downloaded = 0
            if os.path.exists(part_path):
                downloaded = os.path.getsize(part_path)

            # ── Construir request con Range header si hay descarga parcial ──
            import urllib.request
            import urllib.error
            req = urllib.request.Request(url, headers={"User-Agent": "MedicAItion-Installer/1.0"})
            if downloaded > 0:
                req.add_header("Range", f"bytes={downloaded}-")
                info(f"Reanudando descarga desde {downloaded / (1024**3):.2f} GB...")

            response = urllib.request.urlopen(req, timeout=30)

            # ── Obtener tamaño total ──
            content_range = response.headers.get("Content-Range")
            content_length = response.headers.get("Content-Length")

            if content_range:
                # Respuesta 206 Partial: "bytes 12345-99999/100000"
                total_size = int(content_range.split("/")[-1])
            elif content_length:
                total_size = int(content_length) + downloaded
            else:
                total_size = int(model["size_gb"] * 1024**3)  # Estimación

            # ── Descargar con progreso ──
            import time
            start_time = time.time()

            mode = "ab" if downloaded > 0 else "wb"
            with open(part_path, mode) as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    # ── Mostrar barra de progreso ──
                    elapsed = time.time() - start_time
                    speed = (downloaded - (os.path.getsize(part_path) - len(chunk) if elapsed < 0.1 else 0)) / max(elapsed, 0.01)
                    pct = (downloaded / total_size * 100) if total_size > 0 else 0
                    speed_mb = speed / (1024**2)
                    remaining = (total_size - downloaded) / max(speed, 1)
                    eta_min = int(remaining // 60)
                    eta_sec = int(remaining % 60)

                    bar_len = 30
                    filled = int(bar_len * downloaded / max(total_size, 1))
                    bar = "█" * filled + "░" * (bar_len - filled)

                    print(f"\r  [{bar}] {pct:5.1f}%  "
                          f"{downloaded/(1024**3):.2f}/{total_size/(1024**3):.2f} GB  "
                          f"{speed_mb:.1f} MB/s  "
                          f"ETA {eta_min}m{eta_sec:02d}s   ", end="", flush=True)

            print()  # Nueva línea después de la barra de progreso

            # ── Verificar descarga completa ──
            final_size = os.path.getsize(part_path)
            if total_size > 0 and final_size < total_size * 0.95:
                warn(f"Archivo incompleto ({final_size/(1024**3):.2f} GB de {total_size/(1024**3):.2f} GB)")
                warn("Se reintentará la descarga...")
                continue

            # ── Renombrar .part → archivo final ──
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(part_path, dest_path)

            ok(f"Modelo descargado en: {dest_path}")
            return dest_path

        except KeyboardInterrupt:
            print()
            warn("Descarga interrumpida por el usuario")
            warn(f"Progreso guardado en: {part_path}")
            warn("Al volver a ejecutar el wizard, la descarga se reanudará automáticamente")
            sys.exit(0)

        except Exception as e:
            print()
            if attempt < max_retries:
                wait_time = attempt * 5  # 5s, 10s, 15s, 20s...
                warn(f"Error de conexión (intento {attempt}/{max_retries}): {e}")
                warn(f"Reintentando en {wait_time} segundos con conexión nueva...")
                import time
                time.sleep(wait_time)
            else:
                err(f"Error al descargar tras {max_retries} intentos: {e}")
                if os.path.exists(part_path):
                    partial_gb = os.path.getsize(part_path) / (1024**3)
                    warn(f"Progreso parcial guardado: {partial_gb:.2f} GB en {part_path}")
                    warn("Al volver a ejecutar el wizard, la descarga se reanudará desde ahí")
                err("Verifica tu conexión a internet e intenta de nuevo")
                sys.exit(1)


# ── PASO 7: Guardar config y verificar ──────────────────────────────────────
def save_config_and_verify(model: dict, model_path: str, llama_version: str, hw: dict):
    header("PASO 7 — Guardando configuración y verificando")

    n_gpu_layers = -1 if llama_version == "gpu" else 0

    config = {
        "model_path": model_path,
        "model_name": f"{model['name']} {model['quant']}",
        "n_gpu_layers": n_gpu_layers,
        "device": llama_version,
        "n_ctx": 4096,
        "hardware": {
            "gpu": hw.get("gpu_name"),
            "vram_gb": hw.get("vram_gb"),
            "ram_gb": hw.get("ram_gb"),
        },
    }

    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    ok("Configuración guardada en config.json")

    # Test de carga del modelo
    info("Verificando que el modelo carga correctamente (puede tardar ~30 seg)...")
    try:
        setup_cuda_dll_path()
        from llama_cpp import Llama
        llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=512,
            verbose=False,
        )
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": "Responde solo: OK"}],
            max_tokens=10,
        )
        reply = response["choices"][0]["message"]["content"].strip()
        ok(f"Modelo verificado — respuesta de prueba: '{reply}'")
        del llm
    except Exception as e:
        warn(f"No se pudo verificar el modelo: {e}")
        warn("Esto puede ser normal. La app intentará cargarlo al arrancar.")


# ── PASO 8: Crear acceso directo ─────────────────────────────────────────────
def create_desktop_shortcut(install_path: str):
    header("PASO 8 — Creando acceso directo")
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        path = os.path.join(desktop, "MedicAItion.lnk")
        target = os.path.join(install_path, "run.bat")
        
        vbs_script = f"""
        Set oWS = WScript.CreateObject("WScript.Shell")
        sLinkFile = "{path}"
        Set oLink = oWS.CreateShortcut(sLinkFile)
        oLink.TargetPath = "{target}"
        oLink.WorkingDirectory = "{install_path}"
        oLink.Save
        """
        vbs_path = os.path.join(install_path, "create_shortcut.vbs")
        with open(vbs_path, "w") as f:
            f.write(vbs_script)
            
        subprocess.run(["cscript.exe", "//Nologo", vbs_path], capture_output=True)
        if os.path.exists(vbs_path):
            os.unlink(vbs_path)
        ok(f"Acceso directo creado en el Escritorio")
    except Exception as e:
        warn(f"No se pudo crear el acceso directo: {e}")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{CYAN}")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║        MedicAItion — Setup Wizard            ║")
    print("  ║        Cruz Roja Mérida                      ║")
    print("  ╚══════════════════════════════════════════════╝")
    print(RESET)
    print("  Este wizard configura MedicAItion por primera vez.")
    print("  Solo necesitas correrlo una vez.")

    # Verificar huggingface_hub disponible
    try:
        import huggingface_hub  # noqa
    except ImportError:
        print("\n  Instalando dependencia previa: huggingface_hub...")
        subprocess.run([sys.executable, "-m", "pip", "install", "huggingface_hub"],
                       capture_output=True)

    hw            = detect_hardware()
    llama_version = choose_llama_version(hw)
    install_llama_cpp(llama_version)
    model         = choose_model(hw, llama_version)
    install_path, make_shortcut = choose_install_path(model)
    
    copy_app_files(install_path)
    
    model_path    = download_model(model, os.path.join(install_path, "models"))
    save_config_and_verify(model, model_path, llama_version, hw)
    
    if make_shortcut:
        create_desktop_shortcut(install_path)

    header("✅ CONFIGURACIÓN COMPLETA")
    print(f"\n  Modelo:    {c(model['name'] + ' ' + model['quant'], GREEN)}")
    print(f"  Ruta:      {c(install_path, CYAN)}")
    print(f"  Ejecución: {c(llama_version.upper(), CYAN)}")
    
    if os.path.abspath(os.getcwd()) != os.path.abspath(os.path.dirname(__file__)):
        print(f"\n  {c('⚠️ ATENCIÓN: La aplicación fue movida a la nueva ruta.', YELLOW)}")
        print(f"  Cierra esta ventana y abre la app desde tu Escritorio o la nueva ruta.")
    else:
        print(f"\n  Para arrancar la app:\n")
        print(f"  {c('  uvicorn app.main:app --reload', YELLOW)}\n")


if __name__ == "__main__":
    main()
