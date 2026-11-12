import json
import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.db.local_db import SessionLocal, AuditLog, Patient, Appointment


class TestPulsoLocalAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_pulso_status_and_config(self):
        """Verifica estado de IA local (Ollama localhost:11434 + motor clínico local) y actualización de modelo."""
        res = self.client.get("/api/pulso/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("ollama_url", data)
        self.assertIn("http://localhost:11434", data["ollama_url"])
        self.assertIn("active_engine", data)
        self.assertIn(data["active_engine"], ("ollama_local", "embedded_clinical_local"))

        # Actualizar configuración del modelo local
        cfg_res = self.client.post(
            "/api/pulso/config",
            json={
                "ollama_url": "http://localhost:11434",
                "model": "qwen2.5:7b-instruct",
                "temperature": 0.1,
                "user": "Dr. Test Pulso",
            },
        )
        self.assertEqual(cfg_res.status_code, 200)
        cfg_data = cfg_res.json()
        self.assertEqual(cfg_data["status"], "updated")
        self.assertEqual(cfg_data["settings"]["model"], "qwen2.5:7b-instruct")

    def test_02_pulso_streaming_soap_draft_rules(self):
        """Verifica streaming NDJSON de borrador SOAP con reglas estrictas: [PENDIENTE] y 'Revisar por el médico'."""
        db = SessionLocal()
        patient = db.query(Patient).first()
        patient_curp = patient.curp if patient else None
        db.close()

        secret_dictation = "Paciente refiere dolor abdominal de 2 dias en epigastrio sin irradiacion, FC 84, Temp 37.9"
        res = self.client.post(
            "/api/pulso/chat-stream",
            json={
                "prompt": f"Genera borrador SOAP del dictado: {secret_dictation}",
                "curp": patient_curp,
            },
        )
        self.assertEqual(res.status_code, 200)
        lines = [line for line in res.text.strip().split("\n") if line.strip()]
        self.assertGreater(len(lines), 2)

        full_text = ""
        meta_evt = None
        for line in lines:
            evt = json.loads(line)
            if evt.get("type") == "meta":
                meta_evt = evt
            elif evt.get("type") == "token":
                full_text += evt.get("content", "")

        self.assertIn("Borrador de Nota Clínica SOAP", full_text)
        self.assertIn("[PENDIENTE", full_text)
        self.assertIn("Revisar por el médico", full_text)
        self.assertIsNotNone(meta_evt)
        self.assertIn("soap_structured", meta_evt)

        # Verificar que en la bitácora NOM-024 se registró la acción SIN almacenar el contenido clínico sensible
        db = SessionLocal()
        last_log = (
            db.query(AuditLog)
            .filter(AuditLog.action == "PULSO_BORRADOR_SOAP")
            .order_by(AuditLog.id.desc())
            .first()
        )
        self.assertIsNotNone(last_log)
        details_obj = json.loads(last_log.details) if isinstance(last_log.details, str) else last_log.details
        self.assertEqual(details_obj.get("sensitive_content_stored"), False)
        self.assertNotIn("epigastrio", json.dumps(details_obj))
        db.close()

    def test_03_pulso_streaming_patient_summary_and_search(self):
        """Verifica resumen previo del paciente y búsqueda natural de pacientes/citas en streaming."""
        db = SessionLocal()
        patient = db.query(Patient).first()
        patient_curp = patient.curp if patient else None
        db.close()

        # 1. Resumen previo
        res_sum = self.client.post(
            "/api/pulso/chat-stream",
            json={
                "prompt": "Dame el resumen previo del paciente actual.",
                "curp": patient_curp,
            },
        )
        self.assertEqual(res_sum.status_code, 200)
        sum_text = "".join(
            json.loads(line).get("content", "")
            for line in res_sum.text.strip().split("\n")
            if line.strip() and json.loads(line).get("type") == "token"
        )
        self.assertIn("Resumen Previo del Paciente", sum_text)
        self.assertIn("Revisar por el médico", sum_text)

        # 2. Búsqueda natural de pacientes y citas
        res_search = self.client.post(
            "/api/pulso/chat-stream",
            json={
                "prompt": "Buscar pacientes y citas registradas hoy",
            },
        )
        self.assertEqual(res_search.status_code, 200)
        search_text = "".join(
            json.loads(line).get("content", "")
            for line in res_search.text.strip().split("\n")
            if line.strip() and json.loads(line).get("type") == "token"
        )
        self.assertIn("Resultados de Búsqueda Local en Memoria", search_text)

    def test_04_pulso_clear_conversation_audit_and_role_isolation(self):
        """Verifica auditoría de borrado de conversación y bloqueo de Pulso para el rol básico Paciente."""
        audit_res = self.client.post(
            "/api/pulso/audit",
            json={"action": "PULSO_BORRAR_CONVERSACION"},
        )
        self.assertEqual(audit_res.status_code, 200)
        self.assertEqual(audit_res.json()["status"], "logged")

        # El rol Paciente no debe poder acceder a /api/pulso/chat-stream
        blocked_res = self.client.post(
            "/api/pulso/chat-stream",
            headers={"X-Operator-Role": "Paciente"},
            json={"prompt": "Intentar usar IA clínica desde portal paciente"},
        )
        self.assertEqual(blocked_res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
