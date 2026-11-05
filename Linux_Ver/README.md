# MedicAItion — Versión Linux
## Sistema de Expediente Clínico Electrónico con IA
### Cruz Roja Mérida

---

## Requisitos del Sistema

### Hardware Mínimo
- **CPU:** 4 núcleos (8 recomendado)
- **RAM:** 8 GB mínimo (16 GB recomendado)
- **Disco:** 10 GB libres
- **GPU:** (Opcional) NVIDIA con 6+ GB VRAM para aceleración GPU

### Software Requerido
- **Linux:** Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux
- **Python:** 3.10 o superior
- **Navegador:** Firefox, Chrome, o cualquier navegador moderno

---

## Instalación Rápida

### 1. Instalar dependencias del sistema

**Ubuntu / Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv libsndfile1
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip libsndfile
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip libsndfile
```

### 2. (Opcional) Instalar drivers NVIDIA para GPU

**Ubuntu:**
```bash
sudo apt install nvidia-driver-535 nvidia-cuda-toolkit
```

**Fedora:**
```bash
sudo dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda
```

### 3. Ejecutar el instalador

```bash
chmod +x run.sh
./run.sh
```

El script `run.sh`:
1. Verifica que Python 3.10+ está instalado
2. Crea un entorno virtual autónomo en `.python_env/`
3. Instala todas las dependencias automáticamente
4. Detecta tu GPU (si existe)
5. Ejecuta el setup wizard para descargar el modelo de IA
6. Carga las bases de datos médicas (CIE-10)
7. Arranca el servidor web en `http://localhost:8000`

### 4. Uso posterior

Simplemente ejecuta:
```bash
./run.sh
```

O usa el acceso directo del Escritorio (si lo creaste durante la instalación).

---

## Estructura del Proyecto

```
MedicAItion/
├── run.sh                    # ← Punto de entrada (ejecuta esto)
├── run.py                    # Lanzador principal en Python
├── setup_wizard.py           # Wizard de configuración (primera vez)
├── config.json               # (generado por el wizard)
├── .env                      # Variables de entorno
├── requirements.txt          # Dependencias Python
├── app/
│   ├── main.py               # Servidor FastAPI
│   ├── api/                  # Endpoints REST
│   ├── core/                 # Pipeline de IA (Whisper + LLM + CIE-10)
│   ├── db/                   # Persistencia (SQLite + ChromaDB)
│   └── models/               # Esquemas Pydantic
├── frontend/                 # Interfaz web (HTML/CSS/JS)
├── templates/                # Plantillas Jinja2 (notas médicas NOM-004)
├── terminology_database/     # Bases de datos CIE-10
└── scripts/                  # Utilidades (ingesta de terminologías)
```

---

## Solución de Problemas

### "No se encontró Python 3.10+"
```bash
# Ubuntu: instalar desde deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv
```

### "GPU no detectada"
1. Verifica que `nvidia-smi` funciona:
   ```bash
   nvidia-smi
   ```
2. Si no funciona, instala los drivers:
   ```bash
   sudo ubuntu-drivers autoinstall  # Ubuntu
   ```

### "Error de libsndfile"
```bash
sudo apt install libsndfile1  # Ubuntu/Debian
sudo dnf install libsndfile    # Fedora
```

### "Error al compilar llama-cpp-python con CUDA"
Necesitas CUDA Toolkit:
```bash
# Ubuntu
sudo apt install nvidia-cuda-toolkit
# Verificar
nvcc --version
```

### "El modelo tarda mucho en cargar"
- En CPU es normal que tarde 30-60 segundos la primera vez
- En GPU debería tardar 10-15 segundos
- Las siguientes consultas serán mucho más rápidas

---

## Licencia

Desarrollado para Cruz Roja Mérida | MedicAItion v2.0-NOM004
