#!/bin/bash
# ══════════════════════════════════════════════
#  MedicAItion — Lanzador Linux
#  Cruz Roja Mérida
# ══════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "  ${BOLD}${CYAN}============================================${NC}"
echo -e "   MedicAItion || Cruz Roja Mérida (Linux)"
echo -e "  ${BOLD}${CYAN}============================================${NC}"
echo ""

ENV_DIR=".python_env"
MIN_PY_MAJOR=3
MIN_PY_MINOR=10

# ── Paso 1: Encontrar Python adecuado ────────────────────────────────────────
find_python() {
    # Intentar varias versiones en orden de preferencia
    for cmd in python3.11 python3.12 python3.10 python3; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" -ge "$MIN_PY_MAJOR" ] && [ "$minor" -ge "$MIN_PY_MINOR" ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_CMD=$(find_python) || {
    echo -e "  ${RED}❌ No se encontró Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ instalado.${NC}"
    echo ""
    echo "  Para instalar Python en tu distribución:"
    echo ""
    echo "  Ubuntu/Debian:"
    echo "    sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo ""
    echo "  Fedora:"
    echo "    sudo dnf install python3 python3-pip"
    echo ""
    echo "  Arch Linux:"
    echo "    sudo pacman -S python python-pip"
    echo ""
    exit 1
}

PY_VERSION=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo -e "  ${GREEN}✅${NC} Python encontrado: ${CYAN}${PYTHON_CMD}${NC} (${PY_VERSION})"

# ── Paso 2: Verificar dependencias del sistema ───────────────────────────────
check_system_deps() {
    local missing=()

    # python3-venv es necesario para crear el entorno virtual
    if ! "$PYTHON_CMD" -c "import venv" &>/dev/null; then
        missing+=("python3-venv")
    fi

    # libsndfile es necesaria para soundfile (procesamiento de audio)
    if ! ldconfig -p 2>/dev/null | grep -q libsndfile; then
        if ! dpkg -l libsndfile1 &>/dev/null 2>&1 && ! rpm -q libsndfile &>/dev/null 2>&1; then
            missing+=("libsndfile1 (Ubuntu/Debian) o libsndfile (Fedora/Arch)")
        fi
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "  ${YELLOW}⚠️  Dependencias del sistema faltantes:${NC}"
        for dep in "${missing[@]}"; do
            echo -e "    - ${dep}"
        done
        echo ""
        echo "  Instala las dependencias faltantes:"
        echo "    Ubuntu/Debian: sudo apt install python3-venv libsndfile1"
        echo "    Fedora:        sudo dnf install libsndfile"
        echo "    Arch:          sudo pacman -S libsndfile"
        echo ""
        read -p "  ¿Continuar de todos modos? [s/N]: " cont
        if [[ ! "$cont" =~ ^[sS]$ ]]; then
            exit 1
        fi
    fi
}

check_system_deps

# ── Paso 3: Crear entorno virtual si no existe ───────────────────────────────
if [ ! -f "${ENV_DIR}/bin/python" ]; then
    echo ""
    echo -e "  ${CYAN}[!]${NC} Creando entorno virtual autónomo..."
    echo "      Esto solo se hará la primera vez."
    echo ""

    "$PYTHON_CMD" -m venv "$ENV_DIR"
    echo -e "  ${GREEN}✅${NC} Entorno virtual creado en ${CYAN}${ENV_DIR}/${NC}"

    # Actualizar pip
    "${ENV_DIR}/bin/python" -m pip install --upgrade pip --quiet
    echo -e "  ${GREEN}✅${NC} pip actualizado"
else
    echo -e "  ${GREEN}✅${NC} Entorno virtual existente encontrado"
fi

# ── Paso 4: Activar entorno e inyectar rutas CUDA ────────────────────────────
VENV_PYTHON="${ENV_DIR}/bin/python"

# Inyectar librerías CUDA portátiles al LD_LIBRARY_PATH (si existen)
CUDA_RT="${ENV_DIR}/lib/python3.*/site-packages/nvidia/cuda_runtime/lib"
CUDA_BLAS="${ENV_DIR}/lib/python3.*/site-packages/nvidia/cublas/lib"

# Expandir globs
for path in $CUDA_RT; do
    if [ -d "$path" ]; then
        export LD_LIBRARY_PATH="${path}:${LD_LIBRARY_PATH:-}"
    fi
done

for path in $CUDA_BLAS; do
    if [ -d "$path" ]; then
        export LD_LIBRARY_PATH="${path}:${LD_LIBRARY_PATH:-}"
    fi
done

# También buscar CUDA del sistema
if [ -d "/usr/local/cuda/lib64" ]; then
    export LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}"
fi

# ── Paso 5: Lanzar la aplicación ─────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}Iniciando MedicAItion...${NC}"
echo ""

"$VENV_PYTHON" run.py

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo -e "  ${RED}[ERROR] Ocurrió un error. Revisa los mensajes anteriores.${NC}"
    echo "  Presiona ENTER para cerrar..."
    read -r
fi
