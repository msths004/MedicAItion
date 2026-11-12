import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.db.local_db import (
    AuditLog,
    ConsentRecord,
    PractitionerProfile,
    SessionLocal,
    create_tables,
    delete_patient,
)


class TestRoleSeparationAndAuth(unittest.TestCase):
    CURP_P1 = "TESTAUTH880101HYN01"
    CURP_P2 = "TESTAUTH920202HYN02"

    @classmethod
    def setUpClass(cls):
        create_tables()
        cls.client = TestClient(app)
        cls._cleanup()

        for curp, nom, dob, folio in [
            (cls.CURP_P1, "Lucía", "1988-01-01", "FOL-PAT-101"),
            (cls.CURP_P2, "Mateo", "1992-02-02", "FOL-PAT-202"),
        ]:
            res = cls.client.post("/api/patients/register", json={
                "curp": curp,
                "nombres": nom,
                "primer_apellido": "Dzul",
                "segundo_apellido": "Pech",
                "fecha_nacimiento": dob,
                "folio_hospital": folio,
                "sexo": "Femenino" if curp == cls.CURP_P1 else "Masculino",
                "tipo_sangre": "O+",
                "ubicacion_casa": "Mérida, Yucatán",
                "consent": {
                    "accepted_privacy_notice": True,
                    "accepted_clinical_processing": True,
                    "accepted_ice_qr_emergency": True,
                    "signed_by_name": nom,
                },
            })
            assert res.status_code == 201, res.text

    @classmethod
    def _cleanup(cls):
        db = SessionLocal()
        try:
            for c in (cls.CURP_P1, cls.CURP_P2):
                db.query(ConsentRecord).filter(ConsentRecord.patient_curp == c).delete(synchronize_session=False)
                db.query(AuditLog).filter(AuditLog.patient_curp == c).delete(synchronize_session=False)
            # Restaurar PIN y perfil Médico activo
            db.query(PractitionerProfile).update({"is_active": False})
            med = db.query(PractitionerProfile).filter(PractitionerProfile.role == "Médico").first()
            if med:
                med.is_active = True
            db.commit()
        finally:
            db.close()
        delete_patient(cls.CURP_P1)
        delete_patient(cls.CURP_P2)

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    def test_01_staff_login_pin_and_confidentiality_ack(self):
        # PIN erróneo -> 401
        bad = self.client.post("/api/auth/staff-login", json={"role": "Médico", "pin": "0000"})
        self.assertEqual(bad.status_code, 401)

        # PIN inicial 1234 -> 200 con token firmado
        ok = self.client.post("/api/auth/staff-login", json={"role": "Médico", "pin": "1234"})
        self.assertEqual(ok.status_code, 200, ok.text)
        body = ok.json()
        self.assertEqual(body["user_type"], "staff")
        self.assertTrue(len(body["token"]) > 20)

        # Personal firma compromiso de confidencialidad NOM-024 (no aviso de paciente)
        ack = self.client.post("/api/auth/staff-confidentiality", json={
            "role": "Médico",
            "full_name": "Dr. Roberto Morales",
            "accepted_confidentiality": True,
            "accepted_cdss_responsibility": True,
        })
        self.assertEqual(ack.status_code, 200, ack.text)
        self.assertTrue(ack.json()["profile"]["confidentiality_accepted"])

    def test_02_staff_pin_change_and_restore(self):
        r1 = self.client.post("/api/auth/staff-pin", json={
            "role": "Enfermería / Triaje",
            "current_pin": "1234",
            "new_pin": "5678",
        })
        self.assertEqual(r1.status_code, 200, r1.text)
        self.assertEqual(self.client.post("/api/auth/staff-login", json={"role": "Enfermería / Triaje", "pin": "1234"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/staff-login", json={"role": "Enfermería / Triaje", "pin": "5678"}).status_code, 200)

        # Restaurar PIN 1234
        r2 = self.client.post("/api/auth/staff-pin", json={
            "role": "Enfermería / Triaje",
            "current_pin": "5678",
            "new_pin": "1234",
        })
        self.assertEqual(r2.status_code, 200, r2.text)

    def test_03_patient_login_and_strict_privacy_isolation(self):
        # Verificación inválida -> 401
        bad = self.client.post("/api/auth/patient-login", json={
            "curp": self.CURP_P1,
            "verification_secret": "1999-12-31",
        })
        self.assertEqual(bad.status_code, 401)

        # Login con fecha de nacimiento o folio -> 200 + token exclusivo de Paciente
        ok = self.client.post("/api/auth/patient-login", json={
            "curp": self.CURP_P1,
            "verification_secret": "1988-01-01",
        })
        self.assertEqual(ok.status_code, 200, ok.text)
        pdata = ok.json()
        self.assertEqual(pdata["user_type"], "patient")
        self.assertEqual(pdata["role"], "Paciente")
        token = pdata["token"]
        headers = {"X-Session-Token": token, "X-Operator-Role": "Paciente"}

        # Puede consultar su propio portal, citas, chequeo y ARCO
        self.assertEqual(self.client.get(f"/api/patient-portal/{self.CURP_P1}", headers=headers).status_code, 200)
        self.assertEqual(self.client.get(f"/api/auth/patient-appointments/{self.CURP_P1}", headers=headers).status_code, 200)
        self.assertEqual(self.client.get(f"/api/legal/arco/{self.CURP_P1}/export", headers=headers).status_code, 200)

        # BLOQUEO ESTRICTO DE PRIVACIDAD: no puede ver otros pacientes, lista general, consultas ni sistema
        self.assertEqual(self.client.get("/api/patients/", headers=headers).status_code, 403)
        self.assertEqual(self.client.get(f"/api/patient-portal/{self.CURP_P2}", headers=headers).status_code, 403)
        self.assertEqual(self.client.get(f"/api/legal/arco/{self.CURP_P2}/export", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/legal/consent/SYSTEM", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/legal/security-audit", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/consultations/fake-id", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/security/audit-logs", headers=headers).status_code, 403)

    def test_04_recepcion_cannot_read_clinical_records(self):
        rec_headers = {"X-Operator-Role": "Recepcion", "X-Operator-Name": "Lic. Sofia"}
        self.assertEqual(self.client.get("/api/patients/", headers=rec_headers).status_code, 200)
        self.assertEqual(self.client.get("/api/consultations/fake-id", headers=rec_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/security/audit-logs", headers=rec_headers).status_code, 403)
        self.assertEqual(self.client.get(f"/api/patients/{self.CURP_P1}/fhir", headers=rec_headers).status_code, 403)


if __name__ == "__main__":
    unittest.main()
