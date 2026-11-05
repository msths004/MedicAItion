# ⚕️ MedicAItion - AI-Powered Medical Consultation & Clinical Record Management

> **Plataforma médica asistida por Inteligencia Artificial para la gestión, transcripción y estructuración de consultas clínicas bajo normativa oficial (NOM-004-SSA3 y CIE-10).**

---

## 📌 Descripción General

**MedicAItion** es una solución clínica diseñada bajo la filosofía *Local-First* y *Zero-Install*. Permite a médicos y personal de salud capturar consultas mediante audio en tiempo real o dictado de texto, procesar la información mediante modelos de IA (ASR con Whisper, extracción de entidades clínicas con LLM y búsqueda semántica con ChromaDB), y generar notas médicas estandarizadas con codificación CIE-10 de forma autónoma y privada.

---

## 📂 Estructura del Repositorio y Carpetas

A continuación se detallan las carpetas principales del proyecto con enlaces directos:

| Carpeta / Recurso | Descripción |
| :--- | :--- |
| 📁 [**`app/`**](./app) | **Núcleo del Backend (FastAPI)**: Rutas de la API (`app/api`), motores centrales de IA (`app/core`), bases de datos SQLite (`app/db`) y esquemas clínicos (`app/models`). |
| 📁 [**`Archivos_CIE10/`**](./Archivos_CIE10) | **Catálogos CIE-10**: Tablas, códigos y descripciones oficiales de la Clasificación Internacional de Enfermedades. |
| 📁 [**`data/`**](./data) | **Almacenamiento Local**: Bases de datos SQLite locales (`medicaition_local.db`) y base vectorial de ChromaDB (`chroma/`). |
| 📁 [**`deps/`**](./deps) | **Dependencias Nativas**: Librerías de tiempo de ejecución (C/C++ runtime, DLLs de compatibilidad) para entornos Windows. |
| 📁 [**`frontend/`**](./frontend) | **Interfaz de Usuario Web**: Pantallas de consulta clínica, visualizadores de expedientes, captura de audio y componentes interactivos. |
| 📁 [**`future_update/`**](./future_update) | **Actualizaciones Futuras**: Módulos experimentales, extensiones de telemedicina y hojas de ruta técnicas. |
| 📁 [**`Linux_Ver/`**](./Linux_Ver) | **Soporte Linux**: Scripts de configuración, arranque y dependencias para entornos basados en UNIX/Linux. |
| 📁 [**`scripts/`**](./scripts) | **Herramientas y Scripts**: Utilidades de mantenimiento, vectorización e ingesta de terminologías médicas (`ingest_terminologies.py`). |
| 📁 [**`templates/`**](./templates) | **Plantillas HTML / Jinja2**: Formatos estandarizados para la generación dinámica de la Nota Médica Oficial (NOM-004-SSA3). |
| 📁 [**`terminology_database/`**](./terminology_database) | **Repertorio Terminológico**: Repositorios modulares de conocimiento médico (`cie10_mexico_2024`, etc.) con manifiestos `info.json`. |
| 📁 [**`.kilo/`**](./.kilo) | **Configuración de Agentes**: Metadatos de asistencia y flujos de trabajo inteligentes. |

---

## 📑 Documentación Técnica Incluida

- 📄 [**`EXPLICACION_APP.md`**](./EXPLICACION_APP.md) — Explicación profunda de la arquitectura, instalador, CUDA dinámico y repertorios.
- 📄 [**`ESTADO_ACTUAL_APP.md`**](./ESTADO_ACTUAL_APP.md) — Registro de versiones, estado funcional y diagnósticos de ejecución.
- 📄 [**`GUIA_ACTUALIZACION.md`**](./GUIA_ACTUALIZACION.md) — Guía paso a paso para el mantenimiento e incorporación de nuevas funcionalidades.
- 📄 [**`implementation_plan.md`**](./implementation_plan.md) — Plan de arquitectura e ingeniería del sistema.
- 📄 [**`Respuesta.md`**](./Respuesta.md) — Documentación de resolución de incidencias y análisis funcional.

---

## ⚡ Flujo del Pipeline de Inteligencia Artificial

```
                      [ Consulta Médica ]
                      (Audio WAV o Texto)
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │       1. Supresión de Ruido           │
            │      (app.core.noise_suppressor)      │
            └───────────────────┬───────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │        2. Transcripción ASR           │
            │       (Whisper / app.core)            │
            └───────────────────┬───────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │     3. Extracción de Entidades NER    │
            │   (Síntomas, Signos Vitales, Meds)    │
            └───────────────────┬───────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │     4. Mapeo CIE-10 Semántico         │
            │  (ChromaDB + terminology_database)    │
            └───────────────────┬───────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │    5. Armado de Expediente Clínico    │
            │     (CURP + CLUES + Diagnósticos)     │
            └───────────────────┬───────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────┐
            │    6. Renderizado de Nota Médica      │
            │  (Generada al vuelo en HTML NOM-004)  │
            └───────────────────────────────────────┘
```

---

## 🚀 Puesta en Marcha Rápida

### 1. Configuración de Variables de Entorno
Copia la plantilla de variables de entorno y ajusta tus preferencias:
```bash
cp .env.example .env
```

### 2. Instalación Asistida (Zero-Install)
Para una instalación automática que detecte aceleración GPU (CUDA) y cree el entorno sin interferir con el sistema global:
```bash
python setup_wizard.py
```

### 3. Ejecución Directa
- **En Windows:** Haz doble clic en [`run.bat`](./run.bat) o ejecuta:
  ```cmd
  python run.py
  ```
- **En Linux:**
  ```bash
  chmod +x run.sh
  ./run.sh
  ```

---

## 📦 Dependencias y Requisitos del Sistema

- **Python**: 3.10 o superior (definido en [`requirements.txt`](./requirements.txt)).
- **Hardware recomendado**: GPU NVIDIA (>= 6GB VRAM) para aceleración local, o procesador multicore con >= 16GB RAM para modo CPU.
- **Modelos**: Med42-8B / Whisper (medium/small) / SentenceTransformers.
