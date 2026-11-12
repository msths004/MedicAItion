import json
import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.core.crypto_vault import encrypt_text, decrypt_text, is_encrypted
from app.db.local_db import (
    Alergia,
    AuditLog,
    ConsentRecord,
    Consulta,
    EventoClinico,
    Patient,
    SessionLocal,
    create_tables,
    delete_patient,
)


class TestLegalEncryptionAndConsent(unittest.TestCase):
    CURP_ENC = "TESTLEG880312HYNLR01"
    CURP_REJECT = "TESTLEG900101HYNLR02"

    @classmethod
    def setUpClass(cls):
        create_tables()
        cls.client = TestClient(app)
        cls._cleanup()

    @classmethod
    def _cleanup(cls):
        db = SessionLocal()
        try:
            for curp in (cls.CURP_ENC, cls.CURP_REJECT):
                ev_ids = [e.id for e in db.query(EventoClinico).filter(EventoClinico.patient_curp == curp).all()]
                if ev_ids:
                    db.query(Consulta).filter(Consulta.evento_id.in_(ev_ids)).delete(synchronize_session=False)
                db.query(Alergia).filter(Alergia.patient_curp == curp).delete(synchronize_session=False)
                db.query(ConsentRecord).filter(ConsentRecord.patient_curp == curp).delete(synchronize_session=False)
                db.query(AuditLog).filter(AuditLog.patient_curp == curp).delete(synchronize_session=False)
        finally:
            db.commit()
            db.close()
        delete_patient(cls.CURP_ENC)
        delete_patient(cls.CURP_REJECT)

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()

    def test_01_chacha20_hmac_vault_and_tamper_detection(self):
        secret = "Calle 60 #420 Centro, Mérida, Yucatán - Penicilina severa"
        enc = encrypt_text(secret)
        self.assertTrue(is_encrypted(enc))
        self.assertTrue(enc.startswith("ENC1:"))
        self.assertEqual(decrypt_text(enc), secret)
        # Idempotencia si ya está cifrado
        self.assertEqual(encrypt_text(enc), enc)

        # Cualquier alteración de un byte debe fallar verificación HMAC
        tampered = enc[:-2] + ("AA" if enc[-2:] != "AA" else "BB")
        with self.assertRaises(ValueError):
            decrypt_text(tampered)

    def test_02_framework_mexico_yucatan_and_scalable(self):
        res = self.client.get("/api/legal/framework")
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        raw = json.dumps(data, ensure_ascii=False)
        for keyword in ("Yucatán", "SSY", "INAIP", "LFPDPPP", "NOM-004-SSA3-2012", "NOM-024-SSA3-2012", "CLUES"):
            self.assertIn(keyword, raw)

    def test_03_patient_registration_requires_informed_consent(self):
        bad_res = self.client.post("/api/patients/register", json={
            "curp": self.CURP_REJECT,
            "nombres": "Rechazo",
            "primer_apellido": "Prueba",
            "segundo_apellido": "Legal",
            "ubicacion_casa": "Mérida, Yucatán",
            "consent": {
                "accepted_privacy_notice": False,
                "accepted_clinical_processing": False,
                "signed_by_name": "Rechazo Prueba",
            },
        })
        self.assertEqual(bad_res.status_code, 422, bad_res.text)

        ok_res = self.client.post("/api/patients/register", json={
            "curp": self.CURP_ENC,
            "nombres": "Ana María",
            "primer_apellido": "Chan",
            "segundo_apellido": "Dzib",
            "fecha_nacimiento": "1988-03-12",
            "sexo": "Femenino",
            "tipo_sangre": "O+",
            "ubicacion_casa": "Calle 21 #105 Col. México, Mérida, Yucatán",
            "telefono_local": "9991112233",
            "contacto_emergencia_nombre": "Luis Chan",
            "contacto_emergencia_tel": "9998887766",
            "consent": {
                "accepted_privacy_notice": True,
                "accepted_clinical_processing": True,
                "accepted_ai_local_processing": True,
                "accepted_cloud_llm_transfer": False,
                "accepted_ice_qr_emergency": True,
                "accepted_wearables_monitoring": True,
                "signed_by_name": "Ana María Chan Dzib",
                "signer_role": "patient_or_representative",
            },
        })
        self.assertEqual(ok_res.status_code, 201, ok_res.text)

        # Verificar que en SQLite crudo la PII sensible está cifrada con ENC1:
        db = SessionLocal()
        try:
            row = db.query(Patient).filter(Patient.curp == self.CURP_ENC).first()
            self.assertIsNotNone(row)
            self.assertTrue(is_encrypted(row.ubicacion_casa))
            self.assertTrue(is_encrypted(row.telefono_local))
            self.assertTrue(is_encrypted(row.contacto_emergencia_nombre))
            self.assertNotIn("Calle 21", row.ubicacion_casa)
        finally:
            db.close()

        # Al consultar por API debe regresar descifrado para el médico autorizado
        get_res = self.client.get(f"/api/patients/{self.CURP_ENC}")
        self.assertEqual(get_res.status_code, 200, get_res.text)
        p_json = get_res.json()
        self.assertEqual(p_json["ubicacion_casa"], "Calle 21 #105 Col. México, Mérida, Yucatán")

        # Consentimiento firmado y con hash SHA-256
        c_res = self.client.get(f"/api/legal/consent/{self.CURP_ENC}")
        self.assertEqual(c_res.status_code, 200, c_res.text)
        c_data = c_res.json()
        self.assertTrue(c_data["has_consent"])
        self.assertEqual(len(c_data["consent"]["proof_hash"]), 64)

    def test_04_cloud_transfer_blocked_without_consent_and_seal_verified(self):
        # Intentar enviar en modo claude con API Key cuando accepted_cloud_llm_transfer=False
        r_in = self.client.post("/api/input/text", data={
            "text": "Paciente con fiebre de 38.7 C, cefalea retroocular y mialgias en Mérida.",
            "curp": self.CURP_ENC,
            "clues": "YUC-CR-001",
            "llm_mode": "claude",
            "api_key": "sk-ant-fake-blocked-test",
        })
        self.assertEqual(r_in.status_code, 200, r_in.text)
        body = r_in.json()
        guard = body.get("legal_privacy_guard", {})
        self.assertTrue(guard.get("cloud_transfer_blocked"), body)

        # Guardar consulta vía evento y verificar cifrado + sello HMAC NOM-004
        ev_res = self.client.post(f"/api/patients/{self.CURP_ENC}/events", json={
            "nombre_evento": "Consulta Prueba Cifrado Legal",
            "doctor_creador": "Dr. Roberto Morales",
        })
        self.assertEqual(ev_res.status_code, 201, ev_res.text)
        evento_id = ev_res.json()["id"]

        con_res = self.client.post("/api/consultations/", json={
            "evento_id": evento_id,
            "doctor_nombre": "Dr. Roberto Morales",
            "texto_original": "Fiebre 38.7 y cefalea retroocular.",
            "nota_medica": {
                "motivo_consulta": "Fiebre y cefalea",
                "diagnostico_integral": "Sospecha de Dengue sin signos de alarma",
            },
            "receta": {
                "medicamentos": [{"nombre": "Paracetamol", "dosis": "500 mg", "via": "oral", "periodicidad": "cada 8 horas"}],
                "instrucciones": "Hidratación oral abundante",
            },
            "entidades": {"sintomas_referidos": ["Fiebre", "Cefalea retroocular"]},
        })
        self.assertEqual(con_res.status_code, 201, con_res.text)
        cid = con_res.json()["id"]

        db = SessionLocal()
        try:
            crow = db.query(Consulta).filter(Consulta.id == cid).first()
            self.assertIsNotNone(crow)
            self.assertTrue(is_encrypted(crow.texto_original))
            self.assertTrue(is_encrypted(crow.nota_medica_json))
            self.assertTrue(crow.integrity_seal and len(crow.integrity_seal) == 64)
        finally:
            db.close()

        audit_res = self.client.get("/api/legal/security-audit")
        self.assertEqual(audit_res.status_code, 200, audit_res.text)
        audit = audit_res.json()
        self.assertTrue(audit["patient_safety_ok"], audit)
        self.assertTrue(audit["vault"]["key_loaded"], audit)
        self.assertEqual(audit["consultas_tampered"], 0)
        self.assertGreaterEqual(audit["consultas_seal_verified"], 1)

    def test_05_arco_export_revocation_and_ice_passport_lock(self):
        # Antes de revocar, ICE debe responder 200
        ice_ok = self.client.get(f"/api/ice/{self.CURP_ENC}")
        self.assertEqual(ice_ok.status_code, 200, ice_ok.text)

        # Portabilidad ARCO JSON
        arco_res = self.client.get(f"/api/legal/arco/{self.CURP_ENC}/export")
        self.assertEqual(arco_res.status_code, 200, arco_res.text)
        arco = arco_res.json()
        self.assertEqual(arco["patient"]["curp"], self.CURP_ENC)
        self.assertGreaterEqual(len(arco["eventos_clinicos"]), 1)
        self.assertGreaterEqual(len(arco["eventos_clinicos"][0]["consultas"]), 1)

        # Revocación de usos opcionales (ICE + Cloud + Wearables) manteniendo custodia NOM-004
        rev_res = self.client.post(f"/api/legal/consent/{self.CURP_ENC}/revoke", json={
            "revoke_cloud_llm": True,
            "revoke_ice_qr": True,
            "revoke_wearables": True,
            "reason": "Solicitud ARCO de oposición a usos opcionales",
        })
        self.assertEqual(rev_res.status_code, 200, rev_res.text)
        self.assertTrue(rev_res.json().get("nom004_custody_lock"))

        # Tras revocar ICE QR, el endpoint público ICE debe denegar acceso con 403
        ice_blocked = self.client.get(f"/api/ice/{self.CURP_ENC}")
        self.assertEqual(ice_blocked.status_code, 403, ice_blocked.text)

        ice_html_blocked = self.client.get(f"/ice/{self.CURP_ENC}")
        self.assertEqual(ice_html_blocked.status_code, 403)
        self.assertNotIn("Ana María", ice_html_blocked.text)


if __name__ == "__main__":
    unittest.main()
