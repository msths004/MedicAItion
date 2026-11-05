import json
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = "config.json"

SYSTEM_PROMPT = """Eres un asistente médico especializado en extracción y redacción de información clínica en español mexicano.
Analiza el texto médico y realiza las siguientes tareas:
1. Extrae las entidades clínicas presentes (sintomas, diagnósticos, signos vitales, tratamientos, medicamentos).
2. Redacta las secciones narrativas de una Nota Médica de Evolución conforme a la NOM-004-SSA3-2012.
3. Genera indicaciones claras y directas redactadas para el paciente (Receta y cuidados).

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta, sin texto adicional:
{
  "demograficos": {
    "nombre": null,
    "edad": null,
    "sexo": null,
    "curp": null
  },
  "texto_redactado": "Resumen formal y redactado de la consulta en lenguaje médico profesional, omitiendo titubeos, muletillas o repeticiones del diálogo original.",
  "sintomas_referidos": [],
  "diagnosticos_tentativos": [],
  "signos_vitales": [],
  "tratamientos": [],
  "medicamentos": [
    {
      "nombre": "Nombre del fármaco",
      "dosis": "cantidad y unidad",
      "via": "oral/IV/IM/tópica/etc",
      "periodicidad": "cada X horas/días/según sea necesario",
      "duracion": "duración del tratamiento (ej: por 7 días, dosis única, hasta terminar caja)"
    }
  ],
  "nota_clinica": {
    "motivo_consulta": "Razón principal por la que acude el paciente, redactada en lenguaje médico formal",
    "evolucion_padecimiento": "SOLO si el texto menciona evolución previa o seguimiento. Si es un ingreso nuevo o de urgencias, escribir exactamente: 'Paciente de ingreso reciente. Sin evolución previa documentada.'",
    "exploracion_fisica": "Hallazgos relevantes de la exploración física. Si no se mencionan, escribir: 'Pendiente de exploración física.'",
    "diagnostico_integral": "SOLO diagnósticos explícitamente mencionados en el texto. NO inventar diagnósticos a partir de los síntomas. Si no se menciona ningún diagnóstico, escribir: 'Pendiente de diagnóstico. Se requiere valoración clínica integral.'",
    "pronostico": "SOLO si el texto lo menciona o puede inferirse claramente. Si no hay información suficiente, escribir: 'Pendiente de valoración para establecer pronóstico.'",
    "plan_tratamiento": "Indicaciones médicas mencionadas en el texto: medicamentos con dosis, vía y periodicidad; estudios solicitados; medidas indicadas."
  },
  "receta_paciente": "Instrucciones de cuidado y administración de medicamentos redactadas de forma clara y directa en español para que el paciente las entienda (ej: '1. Tomar Paracetamol 500mg cada 8 horas por 3 días...')"
}

Reglas ESTRICTAS:
- "texto_redactado": Redacción resumida y formal del encuentro médico libre de repeticiones, titubeos, muletillas o pausas de la conversación original, redactado con terminología médica profesional coherente.
- "sintomas_referidos": manifestaciones clínicas que refiere o presenta el paciente (dolor, mareo, fiebre, etc.). Son SOLO síntomas, NUNCA diagnósticos, ni tratamientos, ni medicamentos (ej: NO poner 'Paracetamol' aquí).
- "diagnosticos_tentativos": diagnósticos o enfermedades EXPLÍCIPAMENTE mencionados en el texto (ejemplo: "se diagnosticó diabetes", "tiene hipertensión"). NUNCA inferir diagnósticos a partir de los síntomas. Si el texto solo menciona síntomas y no un diagnóstico formal, dejar esta lista VACÍA []. NUNCA incluir medicamentos aquí.
- "signos_vitales": valores numéricos como temperatura, presión arterial, frecuencia cardíaca, SpO2, peso, talla.
- "tratamientos": procedimientos o terapias indicadas (NO medicamentos). Por ejemplo: "sutura", "reducción de fractura", "lavado gástrico".
- "medicamentos": fármacos prescritos. OBLIGATORIO incluir dosis, vía de administración, periodicidad y duración en ESPAÑOL. Traducir TODA la información al español (ejemplo: "as needed" → "según sea necesario", "twice daily" → "cada 12 horas", "for 7 days" → "por 7 días").
- "nota_clinica": Redacta cada sección en lenguaje médico formal. NO repetir la misma información entre secciones. Cada sección debe contener información DIFERENTE y ÚNICA. Si una sección no tiene información suficiente, usar las frases por defecto indicadas arriba.
- "receta_paciente": Debe ser una redacción amigable en segunda persona (dirigida al paciente), listando los medicamentos y recomendaciones para llevarse a casa.
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


def setup_cuda_dll_path():
    """
    Registra las rutas de las DLLs de NVIDIA (cublas64_12.dll, cudart64_12.dll, etc.)
    para que Windows pueda encontrarlas al cargar llama.dll.

    Usa MÚLTIPLES estrategias porque el entorno puede ser:
      - Python embebido/portable (.python_env descargado como .zip)
      - venv estándar
      - Instalación global de Python
    Y registra las rutas tanto en os.environ['PATH'] (método legacy, funciona siempre)
    como en os.add_dll_directory() (método moderno Python 3.8+).
    """
    import sys
    if sys.platform != "win32":
        return

    nvidia_dll_dirs = set()

    # ── Estrategia 1: Ruta relativa al ejecutable de Python ──
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    possible_site_packages = [
        os.path.join(exe_dir, "Lib", "site-packages"),                       # Python embebido
        os.path.join(os.path.dirname(exe_dir), "Lib", "site-packages"),      # venv
    ]

    # ── Estrategia 2: site.getsitepackages() ──
    try:
        import site
        possible_site_packages.extend(site.getsitepackages())
        possible_site_packages.append(site.getusersitepackages())
    except Exception:
        pass

    # ── Estrategia 3: sys.path ──
    for p in sys.path:
        if "site-packages" in p:
            possible_site_packages.append(p)

    # ── Buscar carpetas nvidia/*/bin y nvidia/*/lib en cada site-packages ──
    seen = set()
    for sp in possible_site_packages:
        sp = os.path.abspath(sp) if sp else ""
        if not sp or sp in seen or not os.path.isdir(sp):
            continue
        seen.add(sp)

        nvidia_root = os.path.join(sp, "nvidia")
        if not os.path.isdir(nvidia_root):
            continue

        for pkg_name in os.listdir(nvidia_root):
            pkg_path = os.path.join(nvidia_root, pkg_name)
            if not os.path.isdir(pkg_path):
                continue
            for subdir in ("bin", "lib"):
                dll_dir = os.path.join(pkg_path, subdir)
                if os.path.isdir(dll_dir):
                    if any(f.lower().endswith(".dll") for f in os.listdir(dll_dir)):
                        nvidia_dll_dirs.add(dll_dir)

    if not nvidia_dll_dirs:
        return

    # ── Registrar en PATH (método legacy — funciona en TODOS los escenarios) ──
    current_path = os.environ.get("PATH", "")
    new_entries = [d for d in nvidia_dll_dirs if d not in current_path]
    if new_entries:
        os.environ["PATH"] = ";".join(new_entries) + ";" + current_path

    # ── Registrar con os.add_dll_directory (método moderno Python 3.8+) ──
    for d in nvidia_dll_dirs:
        try:
            os.add_dll_directory(d)
        except (OSError, AttributeError):
            pass


def _get_llm():
    global _llm
    if _llm is None:
        try:
            setup_cuda_dll_path()
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python no está instalado o faltan dependencias C++. Corre setup_wizard.py primero."
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
        "texto_redactado": "",
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
        "receta_paciente": "No especificada"
    }


def extract_entities(text: str, mode: str = "auto", api_key: str = None) -> dict:
    """
    Extrae entidades clínicas y genera secciones narrativas NOM-004.
    mode: "auto", "claude", o "local"
    """
    anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    use_cloud = mode in ["auto", "claude"]

    if use_cloud:
        if not anthropic_key:
            if mode == "claude":
                print("[EntityExtractor] Error: Modo Claude forzado pero no hay API Key.")
                return _empty_structure()
            print("[EntityExtractor] No hay API Key de Anthropic. Cambiando a LOCAL.")
            use_cloud = False
        else:
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=anthropic_key)
                print("[EntityExtractor] Usando nube (Claude)...")
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=2048,
                    temperature=0.1,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": f"Extrae las entidades médicas y redacta la nota clínica del siguiente texto:\n\n{text}"}
                    ]
                )
                content = response.content[0].text
                return _parse_json_from_response(content)
            except Exception as e:
                print(f"[EntityExtractor] Error con Claude: {e}")
                if mode == "claude":
                    return _empty_structure()
                print("[EntityExtractor] Falló Claude. Cambiando a LOCAL como fallback...")
                use_cloud = False

    if not use_cloud or mode == "local":
        try:
            print("[EntityExtractor] Usando modelo LOCAL (llama.cpp)...")
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
            print(f"[EntityExtractor] Error Local: {e}")
            return _empty_structure()


def validate_cie10_candidates(
    term: str,
    context: str,
    candidates: list,
    mode: str = "auto",
    api_key: str = None
) -> int:
    """
    Le pregunta al LLM cuál de los candidatos CIE-10/CIE-9MC describe mejor el término en el contexto clínico.
    Devuelve el índice del mejor candidato (0 a len-1) o -1 si ninguno aplica.
    """
    if not candidates:
        return -1
        
    candidates_str = ""
    for i, c in enumerate(candidates):
        candidates_str += f"{i}. Código: {c['codigo']} - Descripción: {c['descripcion']}\n"
        
    prompt = f"""Eres un médico experto y auditor clínico de la Cruz Roja. Tu tarea es validar la correspondencia de un término clínico con los códigos CIE-10 (o CIE-9MC) propuestos.
Término original extraído del paciente: "{term}"
Contexto de la consulta médica: "{context}"

Candidatos propuestos:
{candidates_str}

Instrucciones:
1. Evalúa si alguno de los códigos describe de manera precisa el término original en el contexto clínico provisto.
2. Ten mucho cuidado con la pérdida de contexto (por ejemplo, si el término es "dolor menstrual", no debe asociarse a un código de "dolor de pecho" o "dolor torácico general").
3. Verifica la compatibilidad biológica y demográfica de los candidatos con el sexo y edad descritos en el contexto clínico del paciente. Por ejemplo, un código para complicaciones del embarazo o ginecológico femenino no es compatible con un paciente de sexo masculino, y códigos perinatales no son compatibles con adultos.
4. Si uno de los candidatos es una correspondencia médica correcta y adecuada en este contexto, responde ÚNICAMENTE con el número del índice (ej: 0, 1, 2, etc.).
5. Si NINGUNO de los candidatos es una correspondencia aceptable (por ejemplo, si todos sugieren diagnósticos en partes del cuerpo o sistemas completamente distintos, o son totalmente incorrectos), responde ÚNICAMENTE con "-1".
6. NO incluyas ninguna explicación, texto adicional, ni formato. Solo responde con el número (ej: "0" o "-1")."""

    anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    use_cloud = mode in ["auto", "claude"]

    if use_cloud:
        if not anthropic_key:
            use_cloud = False
        else:
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=anthropic_key)
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=10,
                    temperature=0.0,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                res_text = response.content[0].text.strip()
                # Extraer cualquier entero
                import re
                match = re.search(r'-?\d+', res_text)
                if match:
                    return int(match.group())
                return -1
            except Exception as e:
                print(f"[CIE10Validation] Error con Claude: {e}")
                use_cloud = False

    if not use_cloud or mode == "local":
        try:
            llm = _get_llm()
            response = llm.create_chat_completion(
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=10,
            )
            res_text = response["choices"][0]["message"]["content"].strip()
            import re
            match = re.search(r'-?\d+', res_text)
            if match:
                return int(match.group())
            return -1
        except Exception as e:
            print(f"[CIE10Validation] Error Local: {e}")
            return -1
    return -1



