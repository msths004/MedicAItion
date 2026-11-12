import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.db.local_db import (
    SessionLocal,
    PatientDailyLog,
    create_tables,
    delete_patient,
)


class TestSprint3CitizenAndFhir(unittest.TestCase):
    TEST_CURP = "TESTSPR3010190HYN01"

    @classmethod
    def setUpClass(cls):
        create_tables()
        cls.client = TestClient(app)

        # Limpiar por si quedó de una corrida abortada
        cls._cleanup_curp(cls.TEST_CURP)

        res = cls.client.post("/api/patients/register", json={
            "curp": cls.TEST_CURP,
            "nombres": "Ana Sofía",
            "primer_apellido": "Peña",
            "segundo_apellido": "Dzib",
            "fecha_nacimiento": "1990-05-14",
            "sexo": "Femenino",
            "tipo_sangre": "O-",
            "altura_cm": 164,
            "peso_kg": 62,
            "contacto_emergencia_nombre": "Luis Peña",
            "contacto_emergencia_tel": "9991234567",
        })
        assert res.status_code == 201, res.text

        res_alg = cls.client.post(f"/api/patients/{cls.TEST_CURP}/alergias", json={
            "descripcion": "Penicilina",
            "tipo": "Fármaco",
            "severidad": "Severa (Anafilaxia)",
        })
        assert res_alg.status_code == 201, res_alg.text

        res_ev = cls.client.post(f"/api/patients/{cls.TEST_CURP}/events", json={
            "nombre_evento": "Control Diabetes Mellitus y Fiebre",
            "doctor_creador": "Dr. Roberto M.",
        })
        assert res_ev.status_code == 201, res_ev.text
        evento_id = res_ev.json()["id"]

        res_con = cls.client.post("/api/consultations/", json={
            "evento_id": evento_id,
            "doctor_nombre": "Dr. Roberto M.",
            "nota_medica": {
                "motivo_consulta": "Control metabólico y cuadro gripal",
                "diagnostico_integral": "Diabetes Mellitus tipo 2 controlada",
                "plan_tratamiento": "Continuar Metformina y Paracetamol PRN",
            },
            "receta": {
                "medicamentos": [
                    {
                        "nombre": "Metformina",
                        "dosis": "850 mg",
                        "via": "oral",
                        "periodicidad": "cada 12 horas",
                        "duracion": "uso crónico",
                    },
                    {
                        "nombre": "Paracetamol",
                        "dosis": "500 mg",
                        "via": "oral",
                        "periodicidad": "cada 8 horas",
                        "duracion": "por 3 días",
                    },
                ],
                "instrucciones": "Tomar Metformina con alimentos.",
            },
            "entidades": {
                "codigos_cie10": {
                    "Diabetes Mellitus tipo 2": {"codigo": "E11.9", "descripcion": "Diabetes mellitus tipo 2"}
                },
                "sintomas_referidos": ["cefalea leve"],
            },
            "texto_original": "NOTA PRIVADA CONFIDENCIAL QUE NO DEBE SALIR EN ICE",
        })
        assert res_con.status_code == 201, res_con.text

    @classmethod
    def _cleanup_curp(cls, curp: str):
        db = SessionLocal()
        try:
            db.query(PatientDailyLog).filter(PatientDailyLog.patient_curp == curp).delete()
            db.commit()
        finally:
            db.close()
        delete_patient(curp)

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_curp(cls.TEST_CURP)

    def test_ice_passport_endpoints_and_privacy(self):
        r_json = self.client.get(f"/api/ice/{self.TEST_CURP}")
        self.assertEqual(r_json.status_code, 200)
        ice = r_json.json()
        self.assertEqual(ice["tipo_sangre"], "O-")
        self.assertTrue(any("Penicilina" in a["descripcion"] for a in ice["alergias"]))
        self.assertTrue(any("Metformina" in m["nombre"] for m in ice["medicamentos_actuales"]))
        self.assertEqual(ice["contacto_emergencia"]["telefono"], "9991234567")

        r_qr = self.client.get(f"/api/ice/{self.TEST_CURP}/qr")
        self.assertEqual(r_qr.status_code, 200)
        self.assertIn("image/svg+xml", r_qr.headers.get("content-type", ""))
        self.assertIn("<svg", r_qr.text)

        r_html = self.client.get(f"/ice/{self.TEST_CURP}")
        self.assertEqual(r_html.status_code, 200)
        self.assertIn("Penicilina", r_html.text)
        self.assertIn("O-", r_html.text)
        self.assertNotIn("NOTA PRIVADA CONFIDENCIAL", r_html.text)

    def test_patient_portal_schedule_and_daily_logs(self):
        r_portal = self.client.get(f"/api/patient-portal/{self.TEST_CURP}")
        self.assertEqual(r_portal.status_code, 200)
        p_data = r_portal.json()
        self.assertTrue(len(p_data["horario_visual"]["Mañana"]) >= 1)
        self.assertTrue(len(p_data["horario_visual"]["Noche"]) >= 1)
        self.assertTrue(len(p_data["banderas_rojas"]) >= 3)

        r_ok = self.client.post(f"/api/patient-portal/{self.TEST_CURP}/logs", json={
            "systolic_bp": 118,
            "diastolic_bp": 76,
            "glucose_mg_dl": 104,
            "temperature_c": 36.5,
            "medication_taken": True,
            "mood_or_pain": "Bien",
            "symptoms_note": "Chequeo normal matutino",
        })
        self.assertEqual(r_ok.status_code, 201)
        self.assertFalse(r_ok.json()["alert_flag"])

        r_bad = self.client.post(f"/api/patient-portal/{self.TEST_CURP}/logs", json={
            "systolic_bp": 176,
            "diastolic_bp": 104,
            "glucose_mg_dl": 62,
            "temperature_c": 39.0,
            "medication_taken": False,
            "mood_or_pain": "Síntomas importantes",
        })
        self.assertEqual(r_bad.status_code, 201)
        bad = r_bad.json()
        self.assertTrue(bad["alert_flag"])
        self.assertIn("Hipoglucemia", bad["alert_message"])
        self.assertIn("Presión sistólica", bad["alert_message"])

        r_html = self.client.get(f"/mi-salud/{self.TEST_CURP}")
        self.assertEqual(r_html.status_code, 200)
        self.assertIn("Metformina", r_html.text)

    def test_fhir_r4_bundle_export(self):
        r_fhir = self.client.get(f"/api/patients/{self.TEST_CURP}/fhir")
        self.assertEqual(r_fhir.status_code, 200)
        bundle = r_fhir.json()
        self.assertEqual(bundle["resourceType"], "Bundle")
        self.assertEqual(bundle["type"], "collection")

        rtypes = [e["resource"]["resourceType"] for e in bundle["entry"]]
        self.assertIn("Patient", rtypes)
        self.assertIn("AllergyIntolerance", rtypes)
        self.assertIn("Condition", rtypes)
        self.assertIn("MedicationRequest", rtypes)
        self.assertIn("Encounter", rtypes)
        self.assertIn("Observation", rtypes)

        conds = [e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Condition"]
        self.assertTrue(any(
            any(c.get("code") == "E11.9" for c in (cond.get("code", {}).get("coding") or []))
            for cond in conds
        ))

    def test_ask_expediente_grounded_response(self):
        r_ask = self.client.post(f"/api/patients/{self.TEST_CURP}/ask", json={
            "question": "¿Qué alergias y medicamentos actuales tiene?",
        })
        self.assertEqual(r_ask.status_code, 200)
        ans = r_ask.json()
        self.assertIn("Penicilina", ans["answer"])
        self.assertIn("Metformina", ans["answer"])
        self.assertTrue(len(ans["citations"]) >= 2)
