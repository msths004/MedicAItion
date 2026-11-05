# Guía Detallada de Actualización: MedicAItion 2.0 (Reversión)

Este documento explica en detalle todas las nuevas características, mejoras y cambios arquitectónicos implementados en la versión de prueba `medicaition_reversion`. Está dividido en tres secciones principales: **Guía de Uso**, **Explicación Coloquial** y **Detalles Técnicos**.

---

## 1. Guía de Uso (Cómo usar las nuevas funciones)

Al abrir la aplicación, notarás varios cambios importantes en la interfaz y en el flujo de trabajo. Aquí te explicamos cómo aprovecharlos:

### A. La Pantalla de Carga Inteligente
- **Lo que ves:** Al abrir la app (`run.bat`), verás una pantalla de carga que dice "Iniciando el sistema...", "Cargando motor de IA...", etc.
- **Cómo funciona:** Ya no necesitas recargar la página manualmente. La pantalla desaparecerá *automáticamente* y te dará acceso a la aplicación **solo cuando el motor de Inteligencia Artificial (Cerebro IA) esté 100% cargado y listo** para procesar a tu primer paciente.

### B. Navegación Principal (Las Pestañas de Arriba)
En la parte superior verás dos botones nuevos:
- **Nueva Consulta:** Usa esta pantalla cuando tienes a un paciente en frente y necesitas capturar su información por voz o texto. La pantalla es limpia y está enfocada solo en la captura y el resultado de esa captura.
- **Expedientes Clínicos:** Usa esta pantalla cuando necesites buscar a un paciente anterior, revisar su historial, leer notas antiguas o buscar a un paciente basándote en sus síntomas.

### C. Búsqueda Semántica con Inteligencia Artificial
En la pestaña de **Expedientes Clínicos**, debajo de la barra de búsqueda de pacientes, hay un nuevo checkbox: **"Búsqueda Semántica con IA"**.
- **Si está desactivado:** La búsqueda funciona de manera normal y ultra rápida buscando coincidencias exactas por CURP o Nombre del paciente.
- **Si lo activas:** El Cerebro IA leerá el texto que escribas (por ejemplo: *"paciente con dolor abdominal y fiebre"* o *"fractura de tibia"*) y buscará en toda la historia de notas médicas de todos los pacientes, ordenando los resultados por el nivel de "Coincidencia de IA (%)". Esto te permite buscar pacientes no por su nombre, sino por su **cuadro clínico**.

### D. El Árbol de Historial Clínico (Agrupación por Eventos)
En la pestaña de **Expedientes Clínicos**, al seleccionar a un paciente en la lista de la izquierda:
- El panel central mostrará su **Historial Clínico**.
- Ahora, las notas no aparecen como una lista desordenada, sino **agrupadas por "Eventos de Salud"** o "Enfermedades". 
- *Ejemplo:* Si un paciente vino 3 veces por una "Neumonía", verás una tarjeta que dice "Neumonía" y dentro de ella, las 3 consultas (Consulta #1, Consulta #2, Consulta #3).
- **Renombrar Eventos:** Junto al título del evento (ej. "Dolor Abdominal"), verás un pequeño botón con un **ícono de lápiz**. Al hacer clic en él, puedes cambiar el nombre de esa enfermedad/evento para organizarlo mejor (ej. cambiarlo a "Apendicitis Confirmada").
- Al hacer clic en cualquier "Consulta #X" dentro de un evento, el panel de la derecha cargará instantáneamente esa nota.

### E. Visor de Documentos de Tres Caras e Impresión
Cuando procesas un expediente nuevo o revisas uno antiguo, el panel derecho tiene 3 pestañas (caras):
1. **Original:** Muestra exactamente lo que dictaste o escribiste, además de los códigos CIE-10 (enfermedades) y CIE-9MC (tratamientos) estandarizados que la IA detectó.
2. **NOM-004:** Muestra la nota médica de evolución redactada formalmente según la norma oficial de salud.
3. **Receta Médica:** Muestra una receta limpia con formato de la Cruz Roja, una tabla fácil de leer con los medicamentos (dosis, vía y frecuencia) y las indicaciones generales para el paciente.

**Impresión Profesional:** 
En ese mismo panel derecho, hay un botón de **"Imprimir"**.
- Si estás en la pestaña **NOM-004**, imprimirá la nota médica.
- Si estás en la pestaña **Receta Médica**, imprimirá la receta en un formato limpio, sin sombras ni botones de la interfaz, lista para que la firmes y se la des al paciente.

### F. Minitítulos de Ayuda (Tooltips)
- Ahora, si pasas el ratón (cursor) y lo dejas quieto unos segundos sobre *cualquier botón* de la aplicación, aparecerá un pequeño recuadro de texto explicando exactamente para qué sirve ese botón.

---

## 2. Explicación Coloquial (¿Qué cambió tras bambalinas?)

Sin entrar en tecnicismos complicados, esto es lo que le enseñamos a la aplicación para que sea más inteligente:

* **Separación Inteligente de Conceptos:** Antes, la IA a veces se confundía y ponía medicamentos donde iban enfermedades, o mezclaba los síntomas. Ahora, le enseñamos a ser extremadamente estricta. Entiende que un *síntoma* (como dolor) no es un *diagnóstico* (como migraña), y que los *medicamentos* van en un área exclusiva para generar recetas.
* **Memoria de "Enfermedades" (Eventos Clínicos):** Antes, la aplicación solo guardaba una lista infinita de notas por paciente. Ahora, la aplicación sabe que varias consultas pueden pertenecer a una misma enfermedad. Crea una "carpeta" para la enfermedad y guarda las notas de seguimiento ahí dentro.
* **Confirmación Contextual (Reranking):** Cuando tú dices un síntoma raro, la aplicación busca en el diccionario médico (CIE-10). Antes, a veces elegía la primera palabra que se parecía aunque no tuviera sentido médico. Ahora, hace algo llamado *Reranking*: encuentra 4 opciones posibles y *se detiene a pensar* evaluando el contexto completo del paciente antes de decidir cuál es la más correcta.
* **Sincronización del Arranque:** Le dijimos a la página web que no te deje empezar a dictar hasta que la Inteligencia Artificial no le mande una señal confirmando que "ya despertó" por completo. Así evitamos esos errores donde le dabas a procesar y la aplicación no respondía.

---

## 3. Detalles Técnicos (Para Desarrolladores / Arquitectura)

Esta sección resume los cambios estructurales a nivel de código para el mantenimiento del proyecto.

### A. Base de Datos Local (`local_db.py`)
- Se introdujo un nuevo modelo SQLAlchemy: `ClinicalEvent`.
- La tabla `NotaEvolucion` ahora posee una `ForeignKey` apuntando a `ClinicalEvent.id`.
- Se rediseñó `save_patient()`: Ahora verifica si se le provee un `event_id`. Si no se provee (ej. un nuevo ingreso), crea un `ClinicalEvent` usando el motivo de consulta como nombre, y luego asocia la `NotaEvolucion` a ese evento.
- Endpoint `get_patient_events()` extrae la data anidada y agrupada cronológicamente.
- Se implementó indexación en `ChromaDB` a nivel de *Evento Clínico*, fusionando los resúmenes y cuadros clínicos de todas las notas de ese evento en un solo documento vectorial.

### B. Módulo de IA y Prompting (`entity_extractor.py`)
- **JSON Estricto:** El `SYSTEM_PROMPT` fue reescrito. Se obligó a la IA a retornar listas específicas (`diagnosticos_tentativos`, `tratamientos`, `medicamentos` como array de objetos con dosis, vía y frecuencia).
- **Receta Paciente:** Se forzó la creación de un campo `receta_paciente` que es la destilación de la información clínica orientada exclusivamente a instrucciones para el paciente civil en segunda persona.
- **Reranker de CIE-10:** Se agregó la función `validate_cie10_candidates` que actúa como un agente LLM de segunda pasada. Toma la lista de opciones de búsqueda vectorial y devuelve el índice del candidato más preciso contextualmente, previniendo ambigüedades semánticas.

### C. Backend API (`routes_patients.py` & `main.py`)
- **Estado de Carga (`/api/status`):** Se implementó una variable global asíncrona `llm_preload_finished`. Un hilo en background inicializa el modelo Llama.cpp y, al terminar (éxito o fallo), marca la bandera. El frontend hace *polling* a este endpoint en vez de a SQLite, previniendo cuelgues del UI.
- **Endpoints CRUD Eventos:** Añadidos `/api/patients/{curp}/events` y `/api/patients/events/rename`.
- **Búsqueda Semántica:** Endpoint `/api/patients/search/semantic` realiza queries directamente al motor vectorial y cruza metadata con SQLite.

### D. Frontend (`index.html`, `style.css`, `app.js`)
- **SPA Layout:** Transición a un layout de *Single Page Application* controlado por una variable de estado en el `<body>` (`mode-consulta` vs `mode-expedientes`).
- **Data Caching:** En el frontend, el árbol jerárquico se carga a memoria (`currentPatientEvents`) al hacer clic en un paciente, permitiendo el renderizado instantáneo de notas antiguas sin llamadas HTTP adicionales por nota.
- **Impresión por iFrame/Pop-up:** Se construyó una función de impresión `printActiveTab()` que aísla el DOM deseado (Nota o Receta) y le inyecta CSS de impresión especializado, disparando el modal nativo de impresión del sistema operativo.
