"""
MedicAItion — Setup Wizard (Linux)
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
def header(text):   print(f"\n{BOLD}{CYAN}{'─'*55}{RESET}\n  {BOLD}{text}{RESET}\n{BOLD}{CYAN}{'─'*55}{RESET}")
def ok(text):       print(f"  {c('✅', GREEN)} {text}")
def warn(text):     print(f"  {c('⚠️ ', YELLOW)} {text}")
def err(text):      print(f"  {c('❌', RED)} {text}")
def info(text):     print(f"  {c('ℹ️ ', BLUE)} {text}")
def ask(text):      return input(f"\n  {c('▶', CYAN)} {text}: ").strip()


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
        "desc": "Mejor calidad médica — Requiere GPU NVIDIA con 6GB+ VRAM",
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

    # RAM del sistema (Linux: /proc/meminfo)
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_kb = int(line.split()[1])
                    hw["ram_gb"] = round(mem_kb / (1024 * 1024), 1)
                    ok(f"RAM del sistema: {hw['ram_gb']} GB")
                    break
    except Exception:
        try:
            import psutil
            hw["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 1)
            ok(f"RAM del sistema: {hw['ram_gb']} GB")
        except ImportError:
            warn("No se pudo medir la RAM")

    # Detectar GPU NVIDIA usando nvidia-smi o lspci
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            text=True, stderr=subprocess.DEVNULL
        )
        for line in output.strip().split("\n"):
            parts = line.split(",")
            if len(parts) >= 2:
                hw["has_gpu"] = True
                hw["gpu_name"] = parts[0].strip()
                hw["vram_gb"] = round(int(parts[1].strip()) / 1024, 1)
                break
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback: buscar con lspci
        try:
            output = subprocess.check_output(["lspci"], text=True, stderr=subprocess.DEVNULL)
            for line in output.split("\n"):
                if "NVIDIA" in line.upper() and ("VGA" in line or "3D" in line):
                    hw["has_gpu"] = True
                    hw["gpu_name"] = line.split(":")[-1].strip()
                    warn("GPU NVIDIA detectada via lspci, pero nvidia-smi no disponible")
                    warn("Instala los drivers NVIDIA para verificar VRAM")
                    hw["vram_gb"] = 8.0  # Asumido
                    break
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    if hw["has_gpu"]:
        ok(f"GPU detectada: {hw['gpu_name']}")
        if hw["vram_gb"] > 0:
            ok(f"VRAM detectada: {hw['vram_gb']} GB")
    else:
        warn("No se detectó GPU NVIDIA.")
        info("Si tienes una GPU NVIDIA, asegúrate de tener los drivers instalados:")
        info("  Ubuntu: sudo apt install nvidia-driver-535")
        info("  Fedora: sudo dnf install akmod-nvidia")

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
        info("Instalando versión con soporte CUDA...")
        info("Esto puede tardar varios minutos (se compila desde código fuente)")
        info("Requiere: CUDA Toolkit y gcc instalados en el sistema")

        # Verificar que CUDA toolkit esté disponible
        nvcc_found = False
        try:
            subprocess.check_output(["nvcc", "--version"], stderr=subprocess.DEVNULL, text=True)
            nvcc_found = True
            ok("CUDA Toolkit (nvcc) detectado")
        except (FileNotFoundError, subprocess.CalledProcessError):
            warn("nvcc no encontrado. Intentando instalar con pip precompilado...")

        env = os.environ.copy()

        if nvcc_found:
            # Compilar desde source con CUDA
            env["CMAKE_ARGS"] = "-DGGML_CUDA=on"
            env["FORCE_CMAKE"] = "1"
            cmd = [sys.executable, "-m", "pip", "install", "llama-cpp-python",
                   "--force-reinstall", "--no-cache-dir"]
        else:
            # Intentar wheel precompilado de CUDA 12.1 para Linux
            url = (
                "https://github.com/abetlen/llama-cpp-python/releases/download/"
                "v0.2.63-cu121/"
                "llama_cpp_python-0.2.63-cp311-cp311-linux_x86_64.whl"
            )
            cmd = [sys.executable, "-m", "pip", "install", url,
                   "--force-reinstall", "--no-cache-dir"]
            info("Intentando con wheel precompilado para CUDA 12.1...")

        result = subprocess.run(cmd, env=env)

        if result.returncode != 0:
            warn("La versión GPU falló. Instalando versión CPU como fallback...")
            cmd_cpu = [sys.executable, "-m", "pip", "install", "llama-cpp-python",
                       "--force-reinstall", "--no-cache-dir"]
            result = subprocess.run(cmd_cpu)
            if result.returncode != 0:
                err("Error al instalar llama-cpp-python")
                sys.exit(1)
            warn("Se instaló la versión CPU. La GPU no se usará para el LLM.")
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
        from llama_cpp import Llama  # noqa
        ok("llama-cpp-python instalado y verificado correctamente")
    except ImportError:
        err("llama-cpp-python se instaló pero no se puede importar")
        err("Reinicia el wizard o instálalo manualmente")
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
    print(f"  {c('[2]', CYAN)} Elegir ruta preferida (ej. /opt/MedicAItion)")
    print()

    while True:
        opt = ask("¿Dónde quieres instalar la app? (Escribe el número 1 o 2)")
        if opt == "1":
            chosen = default_path
        elif opt == "2":
            chosen = ask("Pega o escribe la ruta preferida (ej. /opt/MedicAItion)")
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
            err("Elige otra ruta o ejecútalo con sudo")
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
            return [f for f in files if f in [".git", "__pycache__", "models", "data", ".python_env", "env", "artifacts"]]
            
        # En subcarpetas de librerías, solo ignoramos basura
        return [f for f in files if f == "__pycache__"]
        
    try:
        shutil.copytree(current_dir, dest_path, dirs_exist_ok=True, ignore=ignore_files)
        os.makedirs(os.path.join(dest_path, "data"), exist_ok=True)
        ok("Archivos copiados exitosamente")

        # Dar permisos de ejecución al script de arranque
        run_sh = os.path.join(dest_path, "run.sh")
        if os.path.exists(run_sh):
            os.chmod(run_sh, 0o755)
            ok("Permisos de ejecución asignados a run.sh")

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
    info("La descarga se puede retomar si se interrumpe")
    print()

    try:
        from huggingface_hub import hf_hub_download
        hf_hub_download(
            repo_id=model["repo"],
            filename=model["filename"],
            local_dir=install_path,
            local_dir_use_symlinks=False,
        )
        ok(f"Modelo descargado en: {dest_path}")
        return dest_path
    except Exception as e:
        err(f"Error al descargar: {e}")
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


# ── PASO 8: Crear acceso directo (.desktop) ─────────────────────────────────
def create_desktop_shortcut(install_path: str):
    header("PASO 8 — Creando acceso directo")
    try:
        # Buscar escritorio (soporta XDG y paths comunes)
        desktop = None
        try:
            result = subprocess.check_output(
                ["xdg-user-dir", "DESKTOP"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if os.path.isdir(result):
                desktop = result
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        if not desktop:
            for candidate in ["Desktop", "Escritorio"]:
                path = os.path.join(os.path.expanduser("~"), candidate)
                if os.path.isdir(path):
                    desktop = path
                    break

        if not desktop:
            warn("No se encontró la carpeta del Escritorio")
            warn(f"Para iniciar la app manualmente: cd {install_path} && ./run.sh")
            return

        run_sh_path = os.path.join(install_path, "run.sh")
        desktop_file = os.path.join(desktop, "MedicAItion.desktop")

        content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=MedicAItion
Comment=Sistema de Expediente Clínico Electrónico con IA — Cruz Roja Mérida
Exec=bash "{run_sh_path}"
Path={install_path}
Terminal=true
Categories=Office;MedicalSoftware;
StartupNotify=true
"""
        with open(desktop_file, "w") as f:
            f.write(content)

        os.chmod(desktop_file, 0o755)
        ok(f"Acceso directo creado en: {desktop_file}")
        info("Nota: En algunos escritorios (GNOME), haz clic derecho → 'Permitir ejecución'")

    except Exception as e:
        warn(f"No se pudo crear el acceso directo: {e}")
        warn(f"Para iniciar la app: cd {install_path} && ./run.sh")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{CYAN}")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║     MedicAItion — Setup Wizard (Linux)       ║")
    print("  ║     Cruz Roja Mérida                         ║")
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
        print(f"  {c('  ./run.sh', YELLOW)}\n")


if __name__ == "__main__":
    main()
