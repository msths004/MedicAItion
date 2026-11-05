# EXPLICACIÓN Y REGISTRO DE ESTADO DE LA APP: MedicAItion

Este documento sirve como un registro minucioso, específico y descriptivo del estado actual de la aplicación MedicAItion, detallando su arquitectura, el funcionamiento de sus componentes principales y los cambios implementados para asegurar un despliegue exitoso.

---

## 1. Visión General de la Aplicación
MedicAItion es un sistema médico avanzado, diseñado bajo una filosofía "Zero-Install" (Cero Instalación) y "Local-First" (Prioridad Local). Su propósito es procesar notas de voz o texto médico, transcribirlas utilizando Inteligencia Artificial, extraer entidades clínicas y estandarizar estos datos mapeándolos contra vocabularios médicos oficiales (como el CIE-10), operando de manera completamente autónoma y aislada de otras configuraciones del sistema operativo.

---

## 2. El Instalador (`setup_wizard.py`)
El instalador es el núcleo de la portabilidad del sistema. No es un simple copiador de archivos, sino un orquestador de entornos.

*   **¿Qué hace exactamente?:** Al ejecutarse, el instalador clona la carpeta origen hacia un destino elegido por el usuario (ej. el Escritorio). Durante este proceso, crea un entorno virtual de Python (`.python_env`) completamente aislado. Esto significa que la aplicación incluye su propio motor de ejecución y no requiere que el usuario instale Python en su máquina.
*   **Gestión de Rutas y Exclusiones:** Se modificó la lógica de copia (`shutil.copytree`) para que ignore directorios de caché pesados y bases de datos vectorizadas en crudo (como la carpeta interna `data`), pero que preserve estrictamente los pesos de los modelos de IA descargados. Esto soluciona problemas previos donde los modelos desaparecían en la nueva ruta.
*   **Inyección Dinámica de CUDA:** El instalador detecta si el equipo posee una GPU NVIDIA. De ser así, descarga librerías portátiles de CUDA y modifica la variable de entorno `PATH` en tiempo real mediante el archivo `run.bat`. Esto permite aceleración por hardware sin obligar al usuario a instalar los pesados "NVIDIA CUDA Toolkits" a nivel sistema.
*   **Interacción y Resiliencia:** Cuenta con menús interactivos para elegir la ruta de instalación y mecanismos de reintento. Si ocurre un fallo de red al descargar dependencias, el sistema atrapa el error y permite al usuario reintentar sin que la consola colapse.

---

## 3. Consideraciones de las Bases de Datos (Los Repertorios)
La arquitectura de datos sufrió un cambio fundamental para volverse modular, pasando de estar anidada y fijada al CIE-10, a un sistema de estantería múltiple.

*   **Directorio `terminology_database`:** Toda la información médica cruda (JSONs, CSVs) ya no reside en la carpeta `data`. Ahora vive en `terminology_database`. Este directorio funciona como un archivero donde cada subcarpeta es un repertorio distinto (ej. `cie10_mexico_2024`, `snomed_ct`).
*   **El Manifiesto (`info.json`):** Para resolver el problema de cómo la app distingue un repertorio de otro cuando un usuario añade carpetas manualmente, se introdujo el concepto de manifiesto. Toda subcarpeta debe contener un `info.json` que dicta el "tipo", "versión" y "nombre" de la base de datos.
*   **Ingesta Inteligente (`ingest_terminologies.py`):** El antiguo script rígido fue reemplazado. El nuevo motor escanea el `terminology_database`, lee los manifiestos, verifica que no falten archivos esenciales, y vectoriza el texto hacia ChromaDB añadiendo un prefijo único para cada repertorio (ej. `cie10_mexico_2024_diagnosticos`).
*   **Variables de Entorno (`ACTIVE_TERMINOLOGY`):** Para dictaminar qué repertorio usará la IA al buscar similitudes en un momento dado, se lee la variable `ACTIVE_TERMINOLOGY` desde el archivo `.env`. Esto mantiene el código intacto mientras permite cambiar de base de datos rápidamente.

---

## 4. Prerrequisitos Independientes
A pesar de la autonomía del instalador, existen barreras de hardware y sistema operativo que el usuario debe proveer:

1.  **Sistema Operativo:** Windows 10 o Windows 11 a 64 bits. El archivo `run.bat` y las rutas están optimizados para este ecosistema.
2.  **Hardware (Procesamiento):** Para una experiencia fluida con modelos locales de 8 billones de parámetros (como Med42-8B), es imperativa una GPU NVIDIA con al menos 6GB a 8GB de VRAM. Si el sistema corre en modo CPU (solo procesador), se requiere un mínimo de 16GB de memoria RAM del sistema para evitar bloqueos.
3.  **Conectividad Restringida:** Solo se requiere una conexión a Internet estable durante la **primera ejecución** o instalación para descargar el modelo de Lenguaje y el modelo de Embeddings (~5.5GB en total). Posterior a esto, la aplicación es 100% Offline.

---

## 5. Estado Actual y Cambios en el Código
*   **`run.py` y `run.bat` (Estética y Flujo):** Se alteró la interfaz de la consola. El `run.py` evalúa si el archivo `config.json` existe; si no existe, asume que es una instalación y muestra un banner Azul Cyan ("Instalador Inicial"). Si ya está configurado, muestra un banner Verde ("Listo para usar"), otorgando claridad visual al estado operativo.
*   **Manejo de Errores de Red:** En los scripts de ingesta y carga de modelos de `SentenceTransformer`, se agregaron bloques `try/except` envueltos en bucles `while True`. Esto neutraliza el error `WinError 10054` (desconexiones abruptas de HuggingFace) y le cede el control al usuario para reintentar la descarga.
*   **Dependencias de Python (`requirements.txt`):** Se fijaron las versiones exactas (`==` en lugar de `>=`) para asegurar que el entorno virtual del instalador siempre construya un ecosistema idéntico y predecible en cualquier computadora.
*   **El Modelo de Lenguaje:** La ruta de descarga de Med42-8B se migró a repositorios de QuantFactory para garantizar la persistencia y velocidad de los archivos GGUF.

**Conclusión:**
MedicAItion es actualmente un producto estructurado, blindado contra errores de infraestructura en Windows, con una separación limpia entre la lógica del programa, los pesos de la IA y el conocimiento médico (terminologías), listo para ser desplegado en entornos clínicos cerrados.
