# ⚕️ MedicAItion — AI-Powered Medical Consultation & Clinical Record Management

<div align="center">

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Whisper ASR](https://img.shields.io/badge/Audio%20AI-Whisper-74aa9c?style=for-the-badge&logo=openai&logoColor=white)](https://github.com/openai/whisper)
[![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-fc60a8?style=for-the-badge)](https://www.trychroma.com/)
[![Norma Oficial](https://img.shields.io/badge/Norma-NOM--004--SSA3-emerald?style=for-the-badge)](https://dof.gob.mx)
[![CIE-10](https://img.shields.io/badge/Catálogo-CIE--10%20México-indigo?style=for-the-badge)](https://www.gob.mx/salud)
[![Filosofía](https://img.shields.io/badge/Architecture-Local--First%20%7C%20Zero--Install-orange?style=for-the-badge)](#filosofía-y-arquitectura-local-first)

**Transformando la consulta médica tradicional en una experiencia digital empática, ágil y jurídicamente blindada mediante Inteligencia Artificial soberana.**

[Comenzar Ahora](#-puesta-en-marcha-rápida) • [Estructura del Proyecto](#-estructura-del-repositorio-y-carpetas) • [Modelo SMART](#-modelo-de-emprendimiento-smart) • [Documentación](#-documentación-técnica-incluida)

</div>

---

## 📌 ¿Qué es MedicAItion? (Guía de Entrada Rápida)

En una consulta médica tradicional, los profesionales de la salud pasan entre **40% y 50% de su tiempo escribiendo frente al teclado** en lugar de mirar y escuchar al paciente. Esto genera agotamiento en el médico, notas apresuradas y riesgo de errores legales.

**MedicAItion** es un copiloto clínico inteligente que escucha la consulta médica (o recibe el dictado de voz/texto), extrae los síntomas, signos vitales y recetas, asigna automáticamente los códigos oficiales de enfermedad (**CIE-10**) y genera al instante una **Nota Médica legal (NOM-004-SSA3)** lista para firma, operando de manera **100% privada dentro de la computadora del consultorio**, sin enviar información confidencial a servidores externos.

### 💡 Glosario Sencillo para Nuevos Colaboradores
* 🎙️ **Transcripción (Whisper):** Como un taquígrafo digital que convierte la conversación de voz entre médico y paciente a texto sin perder detalles.
* 🧠 **Extracción de Entidades (NER):** Como un asistente médico que subraya en colores lo importante: signos vitales, síntomas, alergias y dosis.
* 🏷️ **CIE-10:** El "código postal" de las enfermedades: un catálogo internacional obligatorio de la OMS para nombrar enfermedades sin confusiones (ej. *I10* para Hipertensión).
* 📄 **NOM-004-SSA3:** La ley mexicana que define qué datos obligatorios debe contener toda nota médica para proteger al paciente y al doctor.
* 🔒 **Local-First & Zero-Install:** El sistema funciona dentro del consultorio sin depender de internet y no requiere instalar programas complejos previos.

---

## 🚀 Modelo de Emprendimiento SMART

El desarrollo y proyección de **MedicAItion** se rige bajo la metodología estratégica **SMART** (Específico, Medible, Alcanzable, Relevante y Temporalizado):

```
       S                      M                     A                     R                     T
  [Específico]           [Medible]            [Alcanzable]          [Relevante]          [Temporalizado]
Automatizar la         Reducir de 12 min    Zero-Install con      Erradicar burnout    Roadmap en 3 fases
documentación          a < 60 seg la nota;  FastAPI, Whisper y    médico y blindar     desde Core local a
clínica y CIE-10       98% de precisión en  CUDA portátil sin     expedientes bajo     interoperabilidad
en entorno local.      mapeo CIE-10.        fricción de software. NOM-004 mexicana.    federada nacional.
```

### 1. 🎯 S — Specific (Específico)
* **Problema Concreto:** Eliminar la carga burocrática de captura manual del expediente clínico en la consulta médica externa y urgencias en México.
* **Solución Específica:** Un sistema de escritorio autónomo que procesa audio o texto en lenguaje médico, aplica reconocimiento de entidades (NER), mapea diagnósticos al catálogo oficial CIE-10 México 2024 y emite notas médicas estandarizadas vinculadas a la **CURP** del paciente y la clave **CLUES** de la unidad médica.

### 2. 📊 M — Measurable (Medible)
* **Tiempo de Documentación:** Reducción de **10–15 minutos a menos de 60 segundos** por consulta médica.
* **Precisión Diagnóstica:** Tasa de acierto de sugerencia semántica superior al **96%** en codificación CIE-10 mediante búsqueda vectorial con ChromaDB.
* **Apego Normativo:** **100% de cumplimiento** de los campos requeridos por la NOM-004-SSA3-2012.
* **Eficiencia de Almacenamiento:** **0 KB de HTML estático duplicado** en bases de datos (renderizado dinámico bajo demanda, ahorrando ~12KB por consulta).
* **Privacidad de Datos:** **0% de fuga de datos clínicos** a la nube pública en operación local.

### 3. 🛠️ A — Achievable (Alcanzable)
* **Factibilidad Tecnológica Validada:** Implementado sobre un stack probado y robusto (FastAPI en el backend, motor Whisper ASR local, cuantización GGUF para modelos de lenguaje médico y base vectorial ligera).
* **Adopción Sin Barreras (*Zero-Install*):** Instalador asistido (`setup_wizard.py`) que detecta automáticamente si el equipo cuenta con tarjetas gráficas NVIDIA (inyección dinámica de CUDA) o si debe optimizarse para CPU con memoria RAM estándar, eliminando la necesidad de soporte técnico especializado en cada consultorio.

### 4. 🌟 R — Relevant (Relevante)
* **Impacto Humano:** Devuelve el contacto visual y la escucha activa a la relación médico-paciente, previniendo el síndrome de desgaste profesional (*burnout*).
* **Impacto Jurídico y Financiero:** Mitiga riesgos legales y demandas por expedientes incompletos o ilegibles; facilita auditorías médicas y aceleración de reembolsos de aseguradoras.
* **Soberanía y Seguridad Sanitaria:** Resuelve la barrera de adopción en clínicas rurales o centros de salud con conectividad intermitente o sin internet.

### 5. ⏱️ T — Time-bound (Temporalizado)
* **Fase 1 (Completada):** Motor Core en FastAPI, supresor de ruido, pipeline de transcripción, catalogación CIE-10 2024 y generador de notas en tiempo real.
* **Fase 2 (Actual):** Ecosistema multiplataforma (Windows y Linux), interfaz web interactiva, asistente de instalación y separación modular de terminologías (`terminology_database`).
* **Fase 3 (Siguiente Hito):** Módulos de interoperabilidad semántica federada, telemedicina y ampliación al catálogo de Clasificación Internacional del Funcionamiento (CIF) y CLUES.

---

## 📂 Estructura del Repositorio y Carpetas

A continuación se detallan las carpetas principales del proyecto con enlaces directos:

| Carpeta / Recurso | Descripción |
| :--- | :--- |
| 📁 [**`app/`**](./app) | **Núcleo del Backend (FastAPI)**: Rutas de la API (`app/api`), motores centrales de IA (`app/core`), bases de datos SQLite (`app/db`) y esquemas clínicos (`app/models`). |
| 📁 [**`Archivos_CIE10/`**](./Archivos_CIE10) | **Catálogos CIE-10**: Tablas, códigos y descripciones oficiales de la Clasificación Internacional de Enfermedades (Diagnósticos, Procedimientos, CIF y Establecimientos). |
| 📁 [**`data/`**](./data) | **Almacenamiento Local**: Bases de datos SQLite locales (`medicaition_local.db`) y base vectorial de ChromaDB (`chroma/`). |
| 📁 [**`deps/`**](./deps) | **Dependencias Nativas**: Librerías de tiempo de ejecución (C/C++ runtime, DLLs de compatibilidad) para entornos Windows. |
| 📁 [**`frontend/`**](./frontend) | **Interfaz de Usuario Web**: Pantallas de consulta clínica, visualizadores de expedientes, captura de audio y componentes interactivos. |
| 📁 [**`future_update/`**](./future_update) | **Actualizaciones Futuras**: Módulos experimentales, extensiones de interoperabilidad semántica y hojas de ruta técnicas. |
| 📁 [**`Linux_Ver/`**](./Linux_Ver) | **Soporte Linux**: Scripts de configuración, arranque y dependencias adaptadas para entornos basados en UNIX/Linux. |
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
Copia la plantilla de variables de entorno y personaliza los parámetros de tu institución:
```bash
cp .env.example .env
```

### 2. Instalación Asistida (Zero-Install)
Para una instalación automática que detecte aceleración GPU (NVIDIA CUDA) y configure el entorno virtual sin interferir con tu sistema operativo:
```bash
python setup_wizard.py
```

### 3. Ejecución de la Plataforma
* **En Windows:** Haz doble clic en [`run.bat`](./run.bat) o ejecuta desde tu consola:
  ```cmd
  python run.py
  ```
* **En Linux:**
  ```bash
  chmod +x run.sh
  ./run.sh
  ```

---

## 📦 Dependencias y Requisitos del Sistema

* **Entorno de Ejecución:** Python 3.10 o superior (definido en [`requirements.txt`](./requirements.txt)).
* **Hardware Recomendado:**
  * **Modo Acelerado (GPU):** Tarjeta gráfica NVIDIA (>= 6GB VRAM) para inferencia local rápida en segundos.
  * **Modo Estándar (CPU):** Procesador multinúcleo con >= 16GB de memoria RAM.
* **Modelos Principales:** Whisper (medium/small) para transcripción de audio, Med42-8B / LLM clínico y SentenceTransformers para búsqueda semántica vectorial.

---

<div align="center">
Desarrollado con compromiso por la innovación médica y la privacidad del paciente.
</div>
