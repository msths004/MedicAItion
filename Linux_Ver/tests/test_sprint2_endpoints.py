import unittest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.db.local_db import create_tables
from app.api.routes_wearables import evaluate_vital_alert
from app.api.routes_analytics import classify_consulta


class TestSprint2ClinicalOps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        create_tables()
        cls.client = TestClient(app)

    def test_vital_alert_thresholds(self):
        flag_ok, msg_ok = evaluate_vital_alert(hr=74, spo2=98, sbp=120, dbp=80, temp=36.6)
        self.assertFalse(flag_ok)
        self.assertIsNone(msg_ok)

        flag_bad, msg_bad = evaluate_vital_alert(hr=134, spo2=88, sbp=85, dbp=55, temp=39.4)
        self.assertTrue(flag_bad)
        self.assertIn("SpO2 88%", msg_bad)
        self.assertIn("FC crítica", msg_bad)
        self.assertIn("Hipotensión", msg_bad)
        self.assertIn("Fiebre alta", msg_bad)

    def test_epidemiology_classifier(self):
        groups = classify_consulta(
            entidades={"codigos_cie10": {"diagnosticos_tentativos": [{"codigo": "A90", "descripcion": "Dengue"}]}},
            nota={"diagnostico_integral": "Dengue sin signos de alarma"},
            texto="",
        )
        self.assertIn("dengue", groups)

    def test_appointments_crud_and_today_queue(self):
        today = datetime.now().strftime("%Y-%m-%d")
        res = self.client.post("/api/appointments/", json={
            "patientName": "Paciente Prueba Unitaria",
            "curp": "TESTCURP1234567890",
            "date": today,
            "time": "16:30",
            "reason": "Valoración dolor torácico",
            "triage": "ROJO",
            "status": "En Sala / Triaje",
            "wearable": True,
        })
        self.assertEqual(res.status_code, 201)
        appt = res.json()
        appt_id = appt["id"]
        try:
            q_res = self.client.get("/api/appointments/today")
            self.assertEqual(q_res.status_code, 200)
            q_data = q_res.json()
            self.assertTrue(any(i["id"] == appt_id for i in q_data["items"]))

            p_res = self.client.patch(f"/api/appointments/{appt_id}", json={"status": "Atendida"})
            self.assertEqual(p_res.status_code, 200)
            self.assertEqual(p_res.json()["status"], "Atendida")
        finally:
            del_res = self.client.delete(f"/api/appointments/{appt_id}")
            self.assertEqual(del_res.status_code, 200)

    def test_wearables_and_analytics_endpoints(self):
        w_latest = self.client.get("/api/wearables/latest")
        self.assertEqual(w_latest.status_code, 200)
        self.assertIsInstance(w_latest.json(), list)

        epi = self.client.get("/api/analytics/epidemiology?weeks=8")
        self.assertEqual(epi.status_code, 200)
        self.assertIn("groups", epi.json())

        tasks = self.client.get("/api/analytics/tasks")
        self.assertEqual(tasks.status_code, 200)
        self.assertIn("tasks", tasks.json())

        summary = self.client.get("/api/analytics/summary")
        self.assertEqual(summary.status_code, 200)
        self.assertIn("pacientes", summary.json())
        self.assertIn("triaje_hoy", summary.json())


if __name__ == "__main__":
    unittest.main()
