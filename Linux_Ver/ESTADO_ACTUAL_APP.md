# 📂 MedicAItion — Manual de Usuario y Estado del Sistema
**Estado:** Prototipo de Despliegue Zero-Install | **Versión:** 1.0 (Modular)

---

## 📖 GUÍA DE USO (Tutorial Paso a Paso)

### Fase 1: Instalación y Configuración Inicial
1.  **Inicio:** Ejecuta el archivo `run.bat` en la carpeta descargada. Verás un banner azul que dice "Instalador Inicial".
2.  **Selección de Hardware:** El sistema te preguntará si quieres usar **GPU (NVIDIA)** o **CPU**. 
    *   *Tip:* Si tienes una tarjeta NVIDIA, elígela siempre para que la IA responda 10 veces más rápido.
3.  **Ruta de Destino:** Elige dónde quieres que viva la aplicación definitiva (ej. tu Escritorio o un Disco Local). El instalador creará una carpeta limpia llamada `MedicAItion` ahí.
4.  **La Gran Descarga (Paciencia):** El sistema descargará el "cerebro" de la IA (aprox. 5GB). 
    *   *Importante:* Esto depende de tu velocidad de internet. Si se corta, no te preocupes, el instalador te preguntará si quieres reintentar. **No cierres la ventana hasta que veas el mensaje de éxito.**
5.  **Finalización:** Presiona ENTER cuando el mensaje verde te lo indique. Se habrá creado un acceso directo en tu Escritorio.

### Fase 2: Primera Ejecución (Preparando los Datos)
1.  Abre el programa desde el acceso directo del Escritorio.
2.  **Ingesta de Datos:** La primera vez, verás que el sistema "vectoriza" los catálogos médicos. Esto solo ocurre una vez para preparar el buscador inteligente. Cuando diga "Bases de datos médicas listas", la app se abrirá en tu navegador automáticamente.

### Fase 3: Uso Diario en Consulta
1.  **Dictado:** Presiona el botón de micrófono en la pantalla y describe el caso del paciente (ej: *"Paciente con cefalea intensa y fiebre de 38 grados, se sospecha de faringitis"*).
2.  **Transcripción:** Verás el texto aparecer casi instantáneamente.
3.  **Mapeo Inteligente:** La IA detectará automáticamente los síntomas y diagnósticos y buscará los códigos oficiales (CIE-10/SNOMED) en tu base de datos modular.
4.  **Confirmación:** Revisa que los códigos sean correctos y presiona "Guardar Registro".

---

## 🛠️ Arquitectura Técnica (Registro de Estado)

### 1. El Instalador Inteligente (`setup_wizard.py`)
Crea un entorno de Python aislado (`.python_env`) para que la app no dependa de nada instalado en la computadora del doctor. Gestiona dinámicamente los drivers de NVIDIA para aceleración por hardware.

### 2. Bases Médicas Modulares (`terminology_database`)
El sistema es una "estantería de cajones". Cada carpeta dentro de `terminology_database` representa un catálogo médico diferente. Gracias a los archivos `info.json` (etiquetas), puedes añadir o quitar repertorios sin tocar el código.

### 3. Prerrequisitos de Hardware
*   **Ideal:** Windows 10/11 + GPU NVIDIA RTX (6GB VRAM).
*   **Mínimo:** Windows 10/11 + 16GB de Memoria RAM.
*   **Espacio en Disco:** Al menos 10GB libres para modelos y bases de datos.

---

## ⚠️ Consideraciones de Mantenimiento
*   **Actualización de Catálogos:** Para actualizar los códigos CIE-10, solo debes reemplazar los archivos JSON dentro de `terminology_database/cie10_mexico/` y reiniciar la app.
*   **Base de Datos Activa:** El sistema utiliza por defecto el catálogo definido en el archivo `.env` bajo la variable `ACTIVE_TERMINOLOGY`.
