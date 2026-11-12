# Pulso — Asistente Clínico con Avatar e IA 100% Local (`MedicAItion`)

**Pulso** es el copiloto clínico interactivo integrado en **MedicAItion**. Funciona **100% en local**, sin enviar datos sensibles de pacientes a servicios externos, cumpliendo con la **LFPDPPP (México / Yucatán)**, **NOM-004-SSA3-2012** y **NOM-024-SSA3-2012**.

---

## 1. Arquitectura de Doble Motor Local

Pulso opera bajo dos motores locales complementarios:

1. **Motor LLM Local vía Ollama (`http://localhost:11434`)**:
   - Conecta con cualquier modelo local ejecutándose en Ollama (recomendado: `qwen2.5:7b-instruct`, `llama3.1:8b` o `gemma2:9b`) con **respuestas en streaming**.
2. **Motor Clínico Local Integrado (`embedded_clinical_local`)**:
   - Activo de inmediato incluso si Ollama está cerrado.
   - Utiliza **ChromaDB CIE-10 México (14,202 diagnósticos + 4,009 procedimientos)**, el extractor clínico heurístico SOAP y la base local SQLite descifrada en memoria.

---

## 2. Cómo instalar y probar el modelo local con Ollama

### Paso 1: Instalar Ollama
- **Windows:** Descarga el instalador oficial desde [https://ollama.com/download/windows](https://ollama.com/download/windows) y ejecútalo.
- **Linux:**
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

### Paso 2: Descargar un modelo médico/clínico potente en español
En una terminal ejecuta cualquiera de los siguientes modelos recomendados:

```bash
# Opción 1 (Recomendada por precisión en español médico y formato SOAP):
ollama pull qwen2.5:7b-instruct

# Opción 2 (Ligera y rápida para equipos con 8 GB de RAM):
ollama pull llama3.2:3b

# Opción 3 (Alta capacidad clínica general):
ollama pull llama3.1:8b
```

### Paso 3: Verificar que el servidor local responde en `http://localhost:11434`
```bash
curl http://localhost:11434/api/tags
```

### Paso 4: Configurar y probar dentro de MedicAItion
1. Inicia MedicAItion (`.\.python_env\python.exe -m uvicorn app.main:app --port 8000`) y abre `http://localhost:8000`.
2. Entra a **Configuración → Ajustes de Pulso (IA Local — Ollama)** y verifica:
   - **URL Servidor Local:** `http://localhost:11434`
   - **Modelo:** `qwen2.5:7b-instruct` (o el modelo descargado)
   - Haz clic en **Probar y Guardar IA Local**. El indicador cambiará a **🟢 IA local conectada**.
3. Abre a **Pulso** con clic en el robot turquesa abajo a la derecha o con el atajo de teclado **`Ctrl+J` / `Cmd+J`**.
4. También puedes **arrastrar a Pulso por toda la pantalla** y devolverlo a su lugar con el botón **"Volver a la esquina"**.

---

## 3. Reglas Clínicas, Privacidad y Auditoría

- **No invención de datos:** Todo dato no mencionado se marca literalmente como `[PENDIENTE]`.
- **Supervisión médica obligatoria:** Toda sugerencia diagnóstica o terapéutica incluye el aviso `⚠️ Revisar por el médico`.
- **Memoria efímera:** La conversación vive únicamente en memoria RAM local y puede limpiarse en cualquier momento con el botón **Borrar conversación**.
- **Bitácora NOM-024:** Cada interacción se registra en `AuditLog` (`PULSO_RESUMEN_PACIENTE`, `PULSO_BORRADOR_SOAP`, `PULSO_BUSQUEDA_NATURAL`, `PULSO_BORRAR_CONVERSACION`) guardando únicamente **usuario, fecha/hora y acción**, sin almacenar texto clínico sensible.
