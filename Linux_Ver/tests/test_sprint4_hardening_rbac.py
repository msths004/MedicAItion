import socket
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.db.local_db import (
    AuditLog,
    SessionLocal,
    VitalReading,
    create_tables,
    delete_patient,
)


class TestSprint4HardeningAndRbac(unittest.TestCase):
    TEST_CURP = "TESTSPR4010185HYN09"

    @classmethod
    def setUpClass(cls):
        create_tables()
        cls.client = TestClient(app)
        cls._cleanup()

        res = cls.client.post("/api/patients/register", json={
            "curp": cls.TEST_CURP,
            "nombres": "Roberto Carlos",
            "primer_apellido": "Pech",
            "segundo_apellido": "Canul",
            "fecha_nacimiento": "1985-04-10",
            "sexo": "Masculino",
            "tipo_sangre": "O+",
            "altura_cm": 174,
            "peso_kg": 76,
            "contacto_emergencia_nombre": "María Pech",
            "contacto_emergencia_tel": "9992345678",
        })
        assert res.status_code == 201, res.text

        res_alg = cls.client.post(f"/api/patients/{cls.TEST_CURP}/alergias", json={
            "descripcion": "Penicilina",
            "tipo": "Fármaco",
            "severidad": "Severa",
        })
        assert res_alg.status_code == 201, res_alg.text

        res_ev = cls.client.post(f"/api/patients/{cls.TEST_CURP}/events", json={
            "nombre_evento": "Urgencia Respiratoria Prueba S4",
            "doctor_creador": "Dr. Roberto Morales",
        })
        assert res_ev.status_code == 201, res_ev.text
        cls.evento_id = res_ev.json()["id"]

    @classmethod
    def _cleanup(cls):
        db = SessionLocal()
        try:
            db.query(VitalReading).filter(VitalReading.patient_curp == cls.TEST_CURP).delete()
            db.query(AuditLog).filter(AuditLog.patient_curp == cls.TEST_CURP).delete()
            db.commit()
        finally:
            db.close()
        delete_patient(cls.TEST_CURP)

    @classmethod
    def tearDownClass(cls):
        # Restaurar rol Médico activo por defecto en caso de cambios durante test
        cls.client.post("/api/security/profile", json={
            "role": "Médico",
            "full_name": "Dr. Roberto Morales",
            "cedula_profesional": "CED-9482710",
            "specialty": "Medicina General / Urgencias",
            "clues_institucion": "YUC-CR-001",
            "activate": True,
        })
        cls._cleanup()

    def test_rbac_roles_and_cedula_stamp(self):
        # 1. Perfil y matriz RBAC completos
        prof_res = self.client.get("/api/security/profile")
        self.assertEqual(prof_res.status_code, 200)
        prof_data = prof_res.json()
        roles = {p["role"] for p in prof_data["profiles"]}
        self.assertTrue({"Médico", "Enfermería / Triaje", "Recepción", "Administrador"}.issubset(roles))

        # 2. Recepción bloqueada al firmar consulta o registrar signos vitales
        rec_hdrs = {"X-Operator-Role": "Recepcion", "X-Operator-Name": "Lic. Sofia"}
        r_con = self.client.post("/api/consultations/", headers=rec_hdrs, json={
            "evento_id": self.evento_id,
            "nota_medica": {"motivo_consulta": "Intento sin permiso"},
        })
        self.assertEqual(r_con.status_code, 403)

        r_vit = self.client.post("/api/wearables/readings", headers=rec_hdrs, json={
            "curp": self.TEST_CURP,
            "heart_rate": 78,
            "spo2": 98,
        })
        self.assertEqual(r_vit.status_code, 403)

        # 3. Enfermería puede registrar vitales, pero NO firmar consultas médicas
        enf_hdrs = {"X-Operator-Role": "Enfermeria / Triaje", "X-Operator-Name": "Enf. Mariana"}
        e_vit = self.client.post("/api/wearables/readings", headers=enf_hdrs, json={
            "curp": self.TEST_CURP,
            "heart_rate": 82,
            "spo2": 98,
            "source": "manual",
        })
        self.assertEqual(e_vit.status_code, 201)

        e_con = self.client.post("/api/consultations/", headers=enf_hdrs, json={
            "evento_id": self.evento_id,
            "nota_medica": {"motivo_consulta": "Intento enfermería"},
        })
        self.assertEqual(e_con.status_code, 403)

        # 4. Actualizar cédula del Médico y confirmar sello en consulta y verificación QR
        up_res = self.client.post("/api/security/profile", json={
            "role": "Médico",
            "full_name": "Dr. Roberto Morales",
            "cedula_profesional": "CED-9988776",
            "activate": True,
        })
        self.assertEqual(up_res.status_code, 200)
        self.assertEqual(up_res.json()["active"]["cedula_profesional"], "CED-9988776")

    def test_api_allergy_block_and_nom004_immutability(self):
        med_hdrs = {
            "X-Operator-Role": "Medico",
            "X-Operator-Name": "Dr. Roberto Morales",
            "X-Operator-Cedula": "CED-9482710",
        }

        # 1. Prescribir Amoxicilina a paciente alérgico a Penicilina sin justificación -> 409 Conflict
        blocked = self.client.post("/api/consultations/", headers=med_hdrs, json={
            "evento_id": self.evento_id,
            "doctor_nombre": "Dr. Roberto Morales",
            "nota_medica": {"motivo_consulta": "Faringitis", "diagnostico_integral": "Faringoamigdalitis"},
            "receta": {
                "medicamentos": [{"nombre": "Amoxicilina", "dosis": "500 mg", "via": "oral", "periodicidad": "cada 8 horas"}],
                "instrucciones": "Tomar con agua",
            },
            "entidades": {"sintomas_referidos": ["Odinofagia"]},
            "texto_original": "Faringitis aguda, indico Amoxicilina 500 mg.",
        })
        self.assertEqual(blocked.status_code, 409)
        self.assertIn("Bloqueo de seguridad", str(blocked.json()))

        # 2. Prescripción segura -> 201 + cédula estampada
        created = self.client.post("/api/consultations/", headers=med_hdrs, json={
            "evento_id": self.evento_id,
            "doctor_nombre": "Dr. Roberto Morales",
            "nota_medica": {"motivo_consulta": "Faringitis", "diagnostico_integral": "Faringitis viral"},
            "receta": {
                "medicamentos": [{"nombre": "Paracetamol", "dosis": "500 mg", "via": "oral", "periodicidad": "cada 8 horas", "duracion": "por 3 días"}],
                "instrucciones": "Hidratación oral abundante",
            },
            "entidades": {"sintomas_referidos": ["Fiebre"]},
            "texto_original": "Faringitis viral, se prescribe Paracetamol 500 mg cada 8 horas.",
        })
        self.assertEqual(created.status_code, 201, created.text)
        con_data = created.json()
        cid = con_data["id"]
        self.assertEqual(con_data["cedula_profesional"], "CED-9482710")

        # Verificar que la página de verificación muestra la cédula profesional
        verif = self.client.get(f"/api/consultations/{cid}/verificar")
        self.assertEqual(verif.status_code, 200)
        self.assertIn("CED-9482710", verif.text)

        # 3. Inmutabilidad NOM-004: PUT directo prohibido (405) y Recepción bloqueada en addendum (403)
        put_res = self.client.put(f"/api/consultations/{cid}", json={"nota_medica": {"diagnostico_integral": "Alterado"}})
        self.assertEqual(put_res.status_code, 405)

        bad_add = self.client.patch(
            f"/api/consultations/{cid}/addendum",
            headers={"X-Operator-Role": "Recepcion"},
            json={"texto": "Intento no autorizado"},
        )
        self.assertEqual(bad_add.status_code, 403)

        # 4. Addendum válido por Médico conserva nota/receta originales y registra auditoría NOM-024
        ok_add = self.client.patch(
            f"/api/consultations/{cid}/addendum",
            headers=med_hdrs,
            json={"texto": "Paciente toleró adecuadamente la primera toma."},
        )
        self.assertEqual(ok_add.status_code, 200)
        after = self.client.get(f"/api/consultations/{cid}").json()
        self.assertEqual(after["nota_medica"]["diagnostico_integral"], "Faringitis viral")
        self.assertIn("Paciente toleró adecuadamente", after["notas_addendum"])

        audit_res = self.client.get(f"/api/security/audit-logs?curp={self.TEST_CURP}")
        self.assertEqual(audit_res.status_code, 200)
        actions = {row["action"] for row in audit_res.json()["logs"]}
        self.assertIn("FIRMA_CONSULTA", actions)
        self.assertIn("ADDENDUM", actions)

    def test_offline_readiness_and_no_network_dependency(self):
        real_create_conn = socket.create_connection

        def _offline_guard(address, *args, **kwargs):
            host = str(address[0]) if isinstance(address, (tuple, list)) else str(address)
            if host not in ("127.0.0.1", "localhost", "::1"):
                raise OSError(f"Red externa bloqueada en prueba offline: {host}")
            return real_create_conn(address, *args, **kwargs)

        with patch("socket.create_connection", side_effect=_offline_guard):
            ready = self.client.get("/api/security/offline-readiness")
            self.assertEqual(ready.status_code, 200)
            body = ready.json()
            self.assertTrue(body["offline_capable"], body)
            self.assertFalse(body["external_network_required"])
            by_id = {c["id"]: c for c in body["checks"]}
            self.assertTrue(by_id["sqlite"]["ok"])
            self.assertTrue(by_id["chromadb"]["ok"])
            self.assertTrue(by_id["cdss"]["ok"])
            self.assertTrue(by_id["qr_fhir"]["ok"])

            # Pipeline clínico completo con paciente grave (Dengue con signos de alarma) 100% offline
            pipe = self.client.post("/api/input/text", data={
                "text": "Paciente con fiebre de 39.3 C, dolor abdominal intenso, vómitos persistentes y sangrado de encías. TA 92/60 mmHg, FC 122 lpm.",
                "clues": "YUC-CR-001",
            })
            self.assertEqual(pipe.status_code, 200, pipe.text)
            pdata = pipe.json()
            cie10 = pdata.get("codigos_cie10", {})
            sintomas = cie10.get("sintomas_referidos", [])
            self.assertGreater(len(sintomas), 0)
            self.assertTrue(all((s.get("similitud") or 0) > 0 and s.get("codigo") for s in sintomas), sintomas)
            self.assertTrue(len(pdata.get("seguridad_clinica", {}).get("banderas_rojas", [])) > 0)


if __name__ == "__main__":
    unittest.main()
