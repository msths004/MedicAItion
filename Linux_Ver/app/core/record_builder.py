from datetime import datetime
import uuid


def build_record(
    curp: str,
    clues: str,
    texto_original: str,
    entidades: dict,
    codigos_cie10: dict,
) -> dict:
    """
    Construye el expediente estandarizado final del paciente.
    Combina texto libre, entidades extraídas, códigos CIE-10
    y las secciones narrativas de la Nota Médica NOM-004.
    """
    return {
        "id": str(uuid.uuid4()),
        "curp": curp,
        "clues_institucion": clues,
        "timestamp": datetime.utcnow().isoformat(),
        "texto_original": texto_original,
        "datos_demograficos": entidades.get("demograficos", {}),
        "entidades_extraidas": {
            "sintomas_referidos": entidades.get("sintomas_referidos", []),
            "diagnosticos_tentativos": entidades.get("diagnosticos_tentativos", []),
            "signos_vitales": entidades.get("signos_vitales", []),
            "tratamientos": entidades.get("tratamientos", []),
            "medicamentos": entidades.get("medicamentos", []),
        },
        "codigos_cie10": codigos_cie10,
        "nota_clinica": entidades.get("nota_clinica", {
            "motivo_consulta": "No especificado",
            "evolucion_padecimiento": "Paciente de ingreso reciente. Sin evolución previa documentada.",
            "exploracion_fisica": "Pendiente de exploración física.",
            "diagnostico_integral": "Pendiente de diagnóstico. Se requiere valoración clínica integral.",
            "pronostico": "Pendiente de valoración para establecer pronóstico.",
            "plan_tratamiento": "No especificado",
        }),
        "version": "2.0-NOM004",
    }


