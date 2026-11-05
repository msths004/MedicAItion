"""
Motor de renderizado de Notas Médicas usando plantillas Jinja2.
Toma un registro de paciente (dict) y genera HTML listo para impresión/PDF.
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

load_dotenv()

# Ruta a la carpeta de plantillas
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "templates")

# Nombre de la institución por defecto (se puede sobreescribir desde .env)
DEFAULT_INSTITUCION = os.getenv("DEFAULT_INSTITUCION", "Cruz Roja Mérida")

_env = None


def _get_jinja_env() -> Environment:
    """Inicializa el entorno Jinja2 una sola vez."""
    global _env
    if _env is None:
        templates_path = os.path.abspath(TEMPLATES_DIR)
        if not os.path.exists(templates_path):
            raise FileNotFoundError(
                f"Carpeta de plantillas no encontrada: {templates_path}"
            )
        _env = Environment(
            loader=FileSystemLoader(templates_path),
            autoescape=select_autoescape(["html"]),
        )
    return _env


def _format_timestamp(iso_str: str) -> str:
    """Convierte un timestamp ISO a formato legible en español."""
    try:
        dt = datetime.fromisoformat(iso_str)
        meses = [
            "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        return (
            f"{dt.day} de {meses[dt.month]} de {dt.year} — "
            f"{dt.hour:02d}:{dt.minute:02d} hrs"
        )
    except Exception:
        return iso_str or "Fecha no disponible"


def render_nota_medica(record: dict, template_name: str = "nota_evolucion.html") -> str:
    """
    Renderiza una Nota Médica HTML a partir del registro del paciente.

    Args:
        record: Diccionario completo del expediente (output de record_builder).
        template_name: Nombre del archivo de plantilla a usar.

    Returns:
        String HTML renderizado, listo para mostrarse o imprimirse.
    """
    env = _get_jinja_env()
    template = env.get_template(template_name)

    # Preparar el contexto de la plantilla
    context = {
        **record,
        "institucion_nombre": DEFAULT_INSTITUCION,
        "timestamp_formateado": _format_timestamp(record.get("timestamp", "")),
    }

    # Asegurar que nota_clinica exista incluso si el LLM no la generó
    if "nota_clinica" not in context or not context["nota_clinica"]:
        context["nota_clinica"] = {
            "motivo_consulta": "No especificado",
            "evolucion_padecimiento": "No especificado",
            "exploracion_fisica": "No especificado",
            "diagnostico_integral": "No especificado",
            "pronostico": "No especificado",
            "plan_tratamiento": "No especificado",
        }

    # Asegurar que entidades_extraidas exista
    if "entidades_extraidas" not in context:
        context["entidades_extraidas"] = {
            "sintomas_referidos": [],
            "diagnosticos_tentativos": [],
            "signos_vitales": [],
            "tratamientos": [],
            "medicamentos": [],
        }

    return template.render(**context)
