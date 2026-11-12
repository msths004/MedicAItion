from datetime import datetime
import uuid
from app.core.qr_svg import generate_qr_svg


def build_record(
    curp: str,
    clues: str,
    texto_original: str,
    entidades: dict,
    codigos_cie10: dict,
    seguridad_clinica: dict = None,
    evidencia_vinculada: list = None,
) -> dict:
    """
    Construye el expediente estandarizado final del paciente.
    Combina texto libre, entidades extraídas, códigos CIE-10,
    evaluación CDSS salva-vidas, evidencia vinculada y Nota Médica NOM-004.
    """
    record_id = str(uuid.uuid4())
    verif_code = f"MED-{record_id[:8].upper()}"
    return {
        "id": record_id,
        "codigo_verificacion": verif_code,
        "receta_qr_svg": generate_qr_svg(f"MEDICAI:{verif_code}:{curp}"),
        "curp": curp,
        "clues_institucion": clues,
        "timestamp": datetime.utcnow().isoformat(),
        "texto_original": texto_original,
        "texto_redactado": entidades.get("texto_redactado", ""),
        "datos_demograficos": entidades.get("demograficos", {}),
        "entidades_extraidas": {
            "sintomas_referidos": entidades.get("sintomas_referidos", []),
            "diagnosticos_tentativos": entidades.get("diagnosticos_tentativos", []),
            "signos_vitales": entidades.get("signos_vitales", []),
            "tratamientos": entidades.get("tratamientos", []),
            "medicamentos": entidades.get("medicamentos", []),
        },
        "codigos_cie10": codigos_cie10,
        "medicamentos": entidades.get("medicamentos", []),
        "receta_paciente": entidades.get("receta_paciente", ""),
        "diagnostico_diferencial": entidades.get("diagnostico_diferencial", []),
        "evidencia_vinculada": evidencia_vinculada or [],
        "seguridad_clinica": seguridad_clinica or {},
        "plan_tratamiento": entidades.get("nota_clinica", {}).get("plan_tratamiento", "") if isinstance(entidades.get("nota_clinica"), dict) else "",
        "nota_clinica": entidades.get("nota_clinica", {
            "motivo_consulta": "No especificado",
            "evolucion_padecimiento": "Paciente de ingreso reciente. Sin evolución previa documentada.",
            "exploracion_fisica": "Pendiente de exploración física.",
            "diagnostico_integral": "Pendiente de diagnóstico. Se requiere valoración clínica integral.",
            "pronostico": "Pendiente de valoración para establecer pronóstico.",
            "plan_tratamiento": "No especificado",
        }),
        "version": "3.1-NOM004-CDSS",
    }


