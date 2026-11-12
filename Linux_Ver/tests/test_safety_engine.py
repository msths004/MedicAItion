import unittest
from app.core.safety_engine import evaluate_clinical_safety, extract_linked_evidence
from app.core.entity_extractor import _heuristic_extract
from app.core.qr_svg import generate_qr_svg


class TestSafetyEngineAndCDSS(unittest.TestCase):
    def test_penicillin_allergy_blocks_amoxicillin(self):
        patient = {
            "curp": "TESTCURP1234567890",
            "edad": 35,
            "peso_kg": 72,
            "altura_cm": 175,
            "alergias": [{"sustancia": "Penicilina", "severidad": "Severa"}],
            "antecedentes": [],
        }
        entities = {
            "sintomas_referidos": ["Fiebre"],
            "diagnosticos_tentativos": ["Faringoamigdalitis"],
            "signos_vitales": ["Temp 38.2 °C"],
            "medicamentos": [
                {"nombre": "Amoxicilina", "dosis": "500 mg", "via": "oral", "periodicidad": "cada 8 horas", "duracion": "por 7 días"}
            ],
        }
        res = evaluate_clinical_safety(entities, patient, "Paciente con fiebre 38.2 °C, se indica Amoxicilina 500 mg cada 8 horas.")
        self.assertTrue(res["bloqueo_seguridad"])
        self.assertEqual(res["calculos_clinicos"]["imc"]["valor"], 23.5)
        self.assertTrue(any(a["severidad"] == "CRITICA" and "Penicilina" in a["titulo"] for a in res["alertas_medicamentos"]))

    def test_dengue_alarm_signs_and_nsaid_block(self):
        text = (
            "Paciente refiere fiebre de 39.2 °C, dolor retroocular, dolor abdominal intenso, "
            "sangrado de encías y vómito persistente. TA 95/60 mmHg, FC 118 lpm, FR 24 rpm. "
            "Se sugiere Ketorolaco 10 mg cada 8 horas por 3 días."
        )
        entities = _heuristic_extract(text)
        res = evaluate_clinical_safety(entities, None, text)

        codes = [rf["codigo"] for rf in res["banderas_rojas"]]
        self.assertIn("DENGUE CON SIGNOS DE ALARMA", codes)
        self.assertIn("CODIGO SEPSIS", codes)
        self.assertIn(res["triaje"]["nivel"], ("ROJO", "NARANJA"))
        self.assertTrue(res["bloqueo_seguridad"])
        self.assertTrue(any(a["tipo"] == "CONTRAINDICACION_CLINICA" for a in res["alertas_medicamentos"]))
        self.assertGreater(len(res["signos_alarma_casa"]), 0)
        self.assertGreaterEqual(len(entities["diagnostico_diferencial"]), 2)

    def test_codigo_infarto_and_ddi_nitrates_pde5(self):
        text = "Masculino de 58 años con dolor en el pecho opresivo irradiado al brazo izquierdo y diaforesis. SpO2 88%."
        entities = {
            "sintomas_referidos": ["Dolor torácico", "Diaforesis"],
            "diagnosticos_tentativos": ["Síndrome coronario agudo"],
            "signos_vitales": ["SatO2 88%"],
            "medicamentos": [
                {"nombre": "Isosorbida", "dosis": "10 mg", "via": "sublingual", "periodicidad": "dosis única"},
                {"nombre": "Sildenafil", "dosis": "50 mg", "via": "oral", "periodicidad": "cada 24 horas"},
            ],
        }
        res = evaluate_clinical_safety(entities, {"edad": 58}, text)
        codes = [rf["codigo"] for rf in res["banderas_rojas"]]
        self.assertIn("CODIGO INFARTO", codes)
        self.assertIn("INSUFICIENCIA RESPIRATORIA", codes)
        self.assertEqual(res["triaje"]["nivel"], "ROJO")
        self.assertEqual(res["triaje"]["codigo_esi"], 1)
        self.assertTrue(res["bloqueo_seguridad"])
        self.assertTrue(any(a["tipo"] == "INTERACCION_DDI" for a in res["alertas_medicamentos"]))

    def test_paracetamol_overdose_and_inline_allergy(self):
        text = "Paciente alérgica a ibuprofeno. Se prescribe Paracetamol 1000 mg cada 4 horas por 3 días."
        entities = {
            "sintomas_referidos": ["Cefalea"],
            "diagnosticos_tentativos": [],
            "signos_vitales": [],
            "medicamentos": [
                {"nombre": "Paracetamol", "dosis": "1000 mg", "via": "oral", "periodicidad": "cada 4 horas", "duracion": "por 3 días"},
                {"nombre": "Ketorolaco", "dosis": "10 mg", "via": "oral", "periodicidad": "cada 8 horas", "duracion": "por 7 días"},
            ],
        }
        res = evaluate_clinical_safety(entities, None, text)
        types = {a["tipo"] for a in res["alertas_medicamentos"]}
        self.assertIn("SOBREDOSIS", types)
        self.assertIn("ALERGIA_CRUZADA", types)
        self.assertIn("DURACION_EXCEDIDA", types)

    def test_linked_evidence_and_qr_svg(self):
        text = "Refiere fiebre desde ayer. TA 120/80 mmHg. Se indica Paracetamol 500 mg cada 8 horas."
        entities = _heuristic_extract(text)
        ev = extract_linked_evidence(text, entities)
        self.assertTrue(any(item["categoria"] == "Medicamento" and "Paracetamol" in item["cita_textual"] for item in ev))

        svg = generate_qr_svg("http://localhost:8000/api/consultations/1234/verificar")
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("viewBox=", svg)
        self.assertIn("<rect", svg)


if __name__ == "__main__":
    unittest.main()
