"""
fhir_exporter.py — Generador de Bundles HL7 FHIR R4 (NOM-024-SSA3-2012)
========================================================================
Convierte el expediente longitudinal de un paciente MedicAItion
(demografía, alergias, antecedentes, consultas, diagnósticos CIE-10,
recetas, lecturas de wearables y bitácora diaria del paciente) en un
Bundle estándar HL7 FHIR R4 interoperable.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid


def _fhir_gender(sexo: Optional[str]) -> str:
    s = (sexo or "").strip().lower()
    if s in ("m", "masculino", "hombre", "male"):
        return "male"
    if s in ("f", "femenino", "mujer", "female"):
        return "female"
    if s:
        return "other"
    return "unknown"


def _loinc_observation(
    patient_ref: str,
    code: str,
    display: str,
    value: Optional[float],
    unit: str,
    ucum: str,
    effective: Optional[str],
    category_code: str = "vital-signs",
    obs_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    oid = obs_id or str(uuid.uuid4())
    return {
        "fullUrl": f"urn:uuid:{oid}",
        "resource": {
            "resourceType": "Observation",
            "id": oid,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": category_code,
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": code,
                        "display": display,
                    }
                ],
                "text": display,
            },
            "subject": {"reference": patient_ref},
            "effectiveDateTime": effective or datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {
                "value": round(float(value), 2),
                "unit": unit,
                "system": "http://unitsofmeasure.org",
                "code": ucum,
            },
        },
    }


def build_fhir_bundle(
    patient: Dict[str, Any],
    eventos: List[Dict[str, Any]],
    vitals: List[Dict[str, Any]] | None = None,
    daily_logs: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Construye un Bundle HL7 FHIR R4 completo a partir del expediente local."""
    vitals = vitals or []
    daily_logs = daily_logs or []

    patient_id = patient.get("id") or str(uuid.uuid4())
    curp = patient.get("curp") or ""
    patient_ref = f"Patient/{patient_id}"
    entries: List[Dict[str, Any]] = []

    # 1. Patient
    identifiers = [
        {
            "use": "official",
            "system": "https://www.gob.mx/curp",
            "value": curp,
        }
    ]
    if patient.get("folio_hospital"):
        identifiers.append({
            "use": "usual",
            "system": "urn:medicaition:folio-hospital",
            "value": str(patient["folio_hospital"]),
        })
    if patient.get("nss"):
        identifiers.append({
            "use": "secondary",
            "system": "http://imss.gob.mx/nss",
            "value": str(patient["nss"]),
        })

    telecom = []
    if patient.get("celular"):
        telecom.append({"system": "phone", "value": patient["celular"], "use": "mobile"})
    if patient.get("telefono_local"):
        telecom.append({"system": "phone", "value": patient["telefono_local"], "use": "home"})
    if patient.get("email"):
        telecom.append({"system": "email", "value": patient["email"]})

    family_parts = [patient.get("primer_apellido") or "", patient.get("segundo_apellido") or ""]
    family_name = " ".join(p for p in family_parts if p).strip() or None
    given_names = [g for g in (patient.get("nombres") or "").split() if g]

    patient_res: Dict[str, Any] = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"],
            "tag": [{"system": "urn:medicaition:norma", "code": "NOM-024-SSA3-2012"}],
        },
        "identifier": identifiers,
        "active": True,
        "name": [
            {
                "use": "official",
                "text": patient.get("nombre_completo") or curp,
                **({"family": family_name} if family_name else {}),
                **({"given": given_names} if given_names else {}),
            }
        ],
        "gender": _fhir_gender(patient.get("sexo")),
    }
    if patient.get("fecha_nacimiento"):
        patient_res["birthDate"] = patient["fecha_nacimiento"]
    if telecom:
        patient_res["telecom"] = telecom
    if patient.get("ubicacion_casa"):
        patient_res["address"] = [{"text": patient["ubicacion_casa"], "country": "MX"}]
    if patient.get("contacto_emergencia_nombre") or patient.get("contacto_emergencia_tel"):
        patient_res["contact"] = [
            {
                "relationship": [{"text": "Contacto de emergencia (ICE)"}],
                **({"name": {"text": patient["contacto_emergencia_nombre"]}} if patient.get("contacto_emergencia_nombre") else {}),
                **({"telecom": [{"system": "phone", "value": patient["contacto_emergencia_tel"]}]} if patient.get("contacto_emergencia_tel") else {}),
            }
        ]
    if patient.get("tipo_sangre"):
        patient_res["extension"] = [
            {
                "url": "http://medicaition.mx/fhir/StructureDefinition/blood-type",
                "valueString": patient["tipo_sangre"],
            }
        ]

    entries.append({"fullUrl": f"urn:uuid:{patient_id}", "resource": patient_res})

    # 2. AllergyIntolerance
    for alg in patient.get("alergias") or []:
        aid = alg.get("id") or str(uuid.uuid4())
        sev = (alg.get("severidad") or "").lower()
        crit = "high" if any(k in sev for k in ("severa", "alta", "anafil")) else "low"
        entries.append({
            "fullUrl": f"urn:uuid:{aid}",
            "resource": {
                "resourceType": "AllergyIntolerance",
                "id": aid,
                "clinicalStatus": {
                    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
                },
                "verificationStatus": {
                    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]
                },
                "criticality": crit,
                "code": {"text": alg.get("descripcion") or "Alergia"},
                "patient": {"reference": patient_ref},
            },
        })

    # 3. Antecedentes -> Condition
    for ant in patient.get("antecedentes") or []:
        cid = ant.get("id") or str(uuid.uuid4())
        entries.append({
            "fullUrl": f"urn:uuid:{cid}",
            "resource": {
                "resourceType": "Condition",
                "id": cid,
                "clinicalStatus": {
                    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
                },
                "category": [{"text": ant.get("tipo") or "Antecedente"}],
                "code": {"text": ant.get("descripcion") or ""},
                "subject": {"reference": patient_ref},
                **({"recordedDate": ant["fecha"]} if ant.get("fecha") else {}),
            },
        })

    # 4. Antropometría actual
    for obs in (
        _loinc_observation(patient_ref, "29463-7", "Peso corporal", patient.get("peso_kg"), "kg", "kg", patient.get("updated_at")),
        _loinc_observation(patient_ref, "8302-2", "Estatura", patient.get("altura_cm"), "cm", "cm", patient.get("updated_at")),
        _loinc_observation(patient_ref, "39156-5", "Índice de Masa Corporal (IMC)", patient.get("bmi"), "kg/m2", "kg/m2", patient.get("updated_at")),
    ):
        if obs:
            entries.append(obs)

    # 5. Eventos Clínicos y Consultas (Encounter + Condition CIE-10 + MedicationRequest)
    for ev in eventos:
        for con in ev.get("consultas") or []:
            enc_id = con.get("id") or str(uuid.uuid4())
            fecha = con.get("fecha_hora")
            nota = con.get("nota_medica") or {}
            receta = con.get("receta") or {}
            entidades = con.get("entidades") or {}

            entries.append({
                "fullUrl": f"urn:uuid:{enc_id}",
                "resource": {
                    "resourceType": "Encounter",
                    "id": enc_id,
                    "status": "finished",
                    "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "ambulatory"},
                    "type": [{"text": ev.get("nombre_evento") or "Consulta Médica NOM-004"}],
                    "subject": {"reference": patient_ref},
                    **({"period": {"start": fecha}} if fecha else {}),
                    **({"participant": [{"individual": {"display": con["doctor_nombre"]}}]} if con.get("doctor_nombre") else {}),
                    **({"reasonCode": [{"text": nota["motivo_consulta"]}]} if nota.get("motivo_consulta") else {}),
                },
            })

            cie_map = entidades.get("codigos_cie10") or {}
            if isinstance(cie_map, dict):
                for dx_name, cie_info in cie_map.items():
                    cond_id = str(uuid.uuid4())
                    codigo = cie_info.get("codigo") if isinstance(cie_info, dict) else str(cie_info)
                    desc = cie_info.get("descripcion") if isinstance(cie_info, dict) else dx_name
                    coding = []
                    if codigo:
                        coding.append({
                            "system": "http://hl7.org/fhir/sid/icd-10",
                            "code": codigo,
                            "display": desc or dx_name,
                        })
                    entries.append({
                        "fullUrl": f"urn:uuid:{cond_id}",
                        "resource": {
                            "resourceType": "Condition",
                            "id": cond_id,
                            "clinicalStatus": {
                                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
                            },
                            "code": {"coding": coding, "text": dx_name},
                            "subject": {"reference": patient_ref},
                            "encounter": {"reference": f"Encounter/{enc_id}"},
                            **({"recordedDate": fecha} if fecha else {}),
                        },
                    })

            for med in receta.get("medicamentos") or []:
                if not isinstance(med, dict) or not med.get("nombre"):
                    continue
                med_id = str(uuid.uuid4())
                dosage_txt = " ".join(
                    str(x) for x in [med.get("dosis"), med.get("via"), med.get("periodicidad"), med.get("duracion")] if x
                )
                entries.append({
                    "fullUrl": f"urn:uuid:{med_id}",
                    "resource": {
                        "resourceType": "MedicationRequest",
                        "id": med_id,
                        "status": "active",
                        "intent": "order",
                        "medicationCodeableConcept": {"text": med["nombre"]},
                        "subject": {"reference": patient_ref},
                        "encounter": {"reference": f"Encounter/{enc_id}"},
                        **({"authoredOn": fecha} if fecha else {}),
                        **({"dosageInstruction": [{"text": dosage_txt}]} if dosage_txt else {}),
                    },
                })

    # 6. Signos Vitales / Wearables -> Observation
    for vr in vitals[:25]:
        eff = vr.get("recorded_at")
        for obs in (
            _loinc_observation(patient_ref, "8867-4", "Frecuencia cardíaca", vr.get("heart_rate"), "lpm", "/min", eff),
            _loinc_observation(patient_ref, "59408-5", "Saturación arterial de oxígeno (SpO2)", vr.get("spo2"), "%", "%", eff),
            _loinc_observation(patient_ref, "8480-6", "Presión arterial sistólica", vr.get("systolic_bp"), "mmHg", "mm[Hg]", eff),
            _loinc_observation(patient_ref, "8462-4", "Presión arterial diastólica", vr.get("diastolic_bp"), "mmHg", "mm[Hg]", eff),
            _loinc_observation(patient_ref, "8310-5", "Temperatura corporal", vr.get("temperature"), "°C", "Cel", eff),
        ):
            if obs:
                entries.append(obs)

    # 7. Bitácora diaria del paciente -> Observation
    for dl in daily_logs[:25]:
        eff = dl.get("recorded_at")
        for obs in (
            _loinc_observation(patient_ref, "2339-0", "Glucosa capilar (Bitácora paciente)", dl.get("glucose_mg_dl"), "mg/dL", "mg/dL", eff, category_code="laboratory"),
            _loinc_observation(patient_ref, "8480-6", "Presión sistólica (Bitácora paciente)", dl.get("systolic_bp"), "mmHg", "mm[Hg]", eff),
            _loinc_observation(patient_ref, "8462-4", "Presión diastólica (Bitácora paciente)", dl.get("diastolic_bp"), "mmHg", "mm[Hg]", eff),
            _loinc_observation(patient_ref, "8310-5", "Temperatura (Bitácora paciente)", dl.get("temperature_c"), "°C", "Cel", eff),
        ):
            if obs:
                entries.append(obs)

    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "meta": {
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
            "profile": ["http://hl7.org/fhir/StructureDefinition/Bundle"],
            "tag": [
                {"system": "urn:medicaition:standard", "code": "NOM-024-SSA3-2012"},
                {"system": "urn:medicaition:institution", "code": patient.get("clues_institucion") or "YUC-CR-001"},
            ],
        },
        "type": "collection",
        "total": len(entries),
        "entry": entries,
    }
