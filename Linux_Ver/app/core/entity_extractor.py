import json
import os

CONFIG_PATH = "config.json"

SYSTEM_PROMPT = """Eres un asistente médico especializado en extracción y redacción de información clínica en español mexicano.
Analiza el texto médico y realiza DOS tareas:
1. Extrae las entidades clínicas presentes.
2. Redacta las secciones narrativas de una Nota Médica de Evolución conforme a la NOM-004-SSA3-2012.

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta, sin texto adicional:
{
  "demograficos": {
    "nombre": null,
    "edad": null,
    "sexo": null,
    "curp": null
  },
  "sintomas_referidos": [],
  "diagnosticos_tentativos": [],
  "signos_vitales": [],
  "tratamientos": [],
  "medicamentos": [
    {
      "nombre": "Nombre del fármaco",
      "dosis": "cantidad y unidad",
      "via": "oral/IV/IM/tópica/etc",
      "periodicidad": "cada X horas/días/según sea necesario"
    }
  ],
  "nota_clinica": {
    "motivo_consulta": "Razón principal por la que acude el paciente, redactada en lenguaje médico formal",
    "evolucion_padecimiento": "SOLO si el texto menciona evolución previa o seguimiento. Si es un ingreso nuevo o de urgencias, escribir exactamente: 'Paciente de ingreso reciente. Sin evolución previa documentada.'",
    "exploracion_fisica": "Hallazgos relevantes de la exploración física. Si no se mencionan, escribir: 'Pendiente de exploración física.'",
    "diagnostico_integral": "SOLO diagnósticos explícitamente mencionados en el texto. NO inventar diagnósticos a partir de los síntomas. Si no se menciona ningún diagnóstico, escribir: 'Pendiente de diagnóstico. Se requiere valoración clínica integral.'",
    "pronostico": "SOLO si el texto lo menciona o puede inferirse claramente. Si no hay información suficiente, escribir: 'Pendiente de valoración para establecer pronóstico.'",
    "plan_tratamiento": "Indicaciones médicas mencionadas en el texto: medicamentos con dosis, vía y periodicidad; estudios solicitados; medidas indicadas."
  }
}

Reglas ESTRICTAS:
- "sintomas_referidos": manifestaciones clínicas que refiere o presenta el paciente (dolor, mareo, fiebre, etc.). Son SOLO síntomas, NUNCA diagnósticos.
- "diagnosticos_tentativos": diagnósticos o enfermedades EXPLÍCITAMENTE mencionados en el texto (ejemplo: "se diagnosticó diabetes", "tiene hipertensión"). NUNCA inferir diagnósticos a partir de los síntomas. Si el texto solo menciona síntomas y no un diagnóstico formal, dejar esta lista VACÍA [].
- "signos_vitales": valores numéricos como temperatura, presión arterial, frecuencia cardíaca, SpO2, peso, talla.
- "tratamientos": procedimientos o terapias indicadas (NO medicamentos). Por ejemplo: "sutura", "reducción de fractura", "lavado gástrico".
- "medicamentos": fármacos prescritos. OBLIGATORIO incluir dosis, vía de administración y periodicidad en ESPAÑOL. Traducir TODA la información al español (ejemplo: "as needed" → "según sea necesario", "twice daily" → "cada 12 horas").
- "nota_clinica": Redacta cada sección en lenguaje médico formal. NO repetir la misma información entre secciones. Cada sección debe contener información DIFERENTE y ÚNICA. Si una sección no tiene información suficiente, usar las frases por defecto indicadas arriba.
- NUNCA llenar "diagnostico_integral" con los síntomas del paciente. Los síntomas van en "sintomas_referidos", los diagnósticos SOLO si fueron explícitamente dados.
- TODA la respuesta DEBE estar en español. NUNCA usar palabras en inglés.
- Si un campo no está presente en el texto, déjalo como null o lista vacía.
- Responde solo con el JSON, sin explicaciones."""

_llm = None


def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            "config.json no encontrado. Corre setup_wizard.py primero."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_llm():
    global _llm
    if _llm is None:
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python no está instalado. Corre setup_wizard.py primero."
            )
        config = _load_config()
        model_path   = config["model_path"]
        n_gpu_layers = config.get("n_gpu_layers", 0)
        n_ctx        = config.get("n_ctx", 4096)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Modelo no encontrado en '{model_path}'. Corre setup_wizard.py primero."
            )

        print(f"[EntityExtractor] Cargando modelo: {config.get('model_name', model_path)}")
        print(f"[EntityExtractor] Dispositivo: {config.get('device', 'cpu').upper()} "
              f"(n_gpu_layers={n_gpu_layers})")

        _llm = Llama(
            model_path=model_path,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=False,
        )
        print("[EntityExtractor] Modelo cargado correctamente ✅")
    return _llm


def _parse_json_from_response(content: str) -> dict:
    start = content.find("{")
    end = content.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No se encontró JSON en la respuesta del modelo")
    return json.loads(content[start:end])


def _empty_structure() -> dict:
    return {
        "demograficos": {"nombre": None, "edad": None, "sexo": None, "curp": None},
        "sintomas_referidos": [],
        "diagnosticos_tentativos": [],
        "signos_vitales": [],
        "tratamientos": [],
        "medicamentos": [],
        "nota_clinica": {
            "motivo_consulta": "No especificado",
            "evolucion_padecimiento": "Paciente de ingreso reciente. Sin evolución previa documentada.",
            "exploracion_fisica": "Pendiente de exploración física.",
            "diagnostico_integral": "Pendiente de diagnóstico. Se requiere valoración clínica integral.",
            "pronostico": "Pendiente de valoración para establecer pronóstico.",
            "plan_tratamiento": "No especificado",
        },
    }


def extract_entities(text: str) -> dict:
    """
    Extrae entidades clínicas y genera secciones narrativas NOM-004
    del texto usando llama-cpp-python (sin Ollama).
    El modelo se carga una sola vez en memoria al primer uso.
    """
    try:
        llm = _get_llm()
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Extrae las entidades médicas y redacta la nota clínica del siguiente texto:\n\n{text}"},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        content = response["choices"][0]["message"]["content"]
        return _parse_json_from_response(content)

    except Exception as e:
        print(f"[EntityExtractor] Error: {e}")
        return _empty_structure()

