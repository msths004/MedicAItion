"""
crypto_vault.py — MedicAItion Legal & Seguridad Clínica
=================================================================
Cifrado autenticado en reposo (ChaCha20 + HMAC-SHA256 Encrypt-then-MAC,
llave de 256 bits) y sellos criptográficos NOM-004 / LFPDPPP, sin
dependencias binarias externas para garantizar operación 100% offline.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from typing import Any, Dict, Optional

_ENC_PREFIX = "ENC1:"
_NONCE_SIZE = 12
_MAC_SIZE = 32
_KEY_PATH = os.environ.get("MEDICAITION_KEY_PATH", os.path.join("data", ".medicaition_master.key"))

_MASTER_KEY_CACHE: Optional[bytes] = None


def _rotl32(v: int, n: int) -> int:
    return ((v << n) & 0xFFFFFFFF) | (v >> (32 - n))


def _quarter_round(state: list[int], a: int, b: int, c: int, d: int) -> None:
    state[a] = (state[a] + state[b]) & 0xFFFFFFFF
    state[d] = _rotl32(state[d] ^ state[a], 16)
    state[c] = (state[c] + state[d]) & 0xFFFFFFFF
    state[b] = _rotl32(state[b] ^ state[c], 12)
    state[a] = (state[a] + state[b]) & 0xFFFFFFFF
    state[d] = _rotl32(state[d] ^ state[a], 8)
    state[c] = (state[c] + state[d]) & 0xFFFFFFFF
    state[b] = _rotl32(state[b] ^ state[c], 7)


def _chacha20_block(key: bytes, counter: int, nonce: bytes) -> bytes:
    """Genera un bloque de 64 bytes del flujo ChaCha20 (RFC 7539)."""
    constants = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)
    key_words = struct.unpack("<8I", key)
    nonce_words = struct.unpack("<3I", nonce)
    initial = list(constants) + list(key_words) + [counter & 0xFFFFFFFF] + list(nonce_words)
    working = list(initial)
    for _ in range(10):
        _quarter_round(working, 0, 4, 8, 12)
        _quarter_round(working, 1, 5, 9, 13)
        _quarter_round(working, 2, 6, 10, 14)
        _quarter_round(working, 3, 7, 11, 15)
        _quarter_round(working, 0, 5, 10, 15)
        _quarter_round(working, 1, 6, 11, 12)
        _quarter_round(working, 2, 7, 8, 13)
        _quarter_round(working, 3, 4, 9, 14)
    out_words = [(w + i) & 0xFFFFFFFF for w, i in zip(working, initial)]
    return struct.pack("<16I", *out_words)


def _chacha20_xor(key: bytes, nonce: bytes, data: bytes) -> bytes:
    if not data:
        return b""
    out = bytearray(len(data))
    counter = 1
    offset = 0
    total = len(data)
    while offset < total:
        block = _chacha20_block(key, counter, nonce)
        chunk = min(64, total - offset)
        for i in range(chunk):
            out[offset + i] = data[offset + i] ^ block[i]
        offset += chunk
        counter += 1
    return bytes(out)


def _get_master_key() -> bytes:
    global _MASTER_KEY_CACHE
    if _MASTER_KEY_CACHE is not None:
        return _MASTER_KEY_CACHE

    env_key = os.environ.get("MEDICAITION_MASTER_KEY", "").strip()
    if env_key:
        _MASTER_KEY_CACHE = hashlib.sha256(env_key.encode("utf-8")).digest()
        return _MASTER_KEY_CACHE

    key_dir = os.path.dirname(_KEY_PATH) or "data"
    os.makedirs(key_dir, exist_ok=True)
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as fh:
            raw = fh.read().strip()
        try:
            decoded = base64.b64decode(raw)
            if len(decoded) >= 32:
                _MASTER_KEY_CACHE = decoded[:32]
                return _MASTER_KEY_CACHE
        except Exception:
            pass

    key = secrets.token_bytes(32)
    with open(_KEY_PATH, "wb") as fh:
        fh.write(base64.b64encode(key))
    try:
        os.chmod(_KEY_PATH, 0o600)
    except Exception:
        pass
    _MASTER_KEY_CACHE = key
    return key


def _derive_subkey(label: bytes) -> bytes:
    return hmac.new(_get_master_key(), label, hashlib.sha256).digest()


def is_encrypted(value: Optional[str]) -> bool:
    return isinstance(value, str) and value.startswith(_ENC_PREFIX)


def encrypt_text(plaintext: Optional[str]) -> Optional[str]:
    """Cifra un texto con ChaCha20 + HMAC-SHA256 (Encrypt-then-MAC)."""
    if plaintext is None or plaintext == "":
        return plaintext
    if is_encrypted(plaintext):
        return plaintext

    enc_key = _derive_subkey(b"medicaition:enc:v1")
    mac_key = _derive_subkey(b"medicaition:mac:v1")
    nonce = secrets.token_bytes(_NONCE_SIZE)
    raw_bytes = str(plaintext).encode("utf-8")
    ciphertext = _chacha20_xor(enc_key, nonce, raw_bytes)
    tag = hmac.new(mac_key, b"ENC1" + nonce + ciphertext, hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(nonce + ciphertext + tag).decode("ascii")
    return f"{_ENC_PREFIX}{token}"


def decrypt_text(value: Optional[str]) -> Optional[str]:
    """Verifica el HMAC-SHA256 en tiempo constante y descifra el texto."""
    if value is None or value == "":
        return value
    if not is_encrypted(value):
        return value

    payload = value[len(_ENC_PREFIX):]
    try:
        blob = base64.urlsafe_b64decode(payload.encode("ascii"))
    except Exception as exc:
        raise ValueError("Token cifrado malformado") from exc

    if len(blob) < _NONCE_SIZE + _MAC_SIZE:
        raise ValueError("Token cifrado truncado")

    nonce = blob[:_NONCE_SIZE]
    ciphertext = blob[_NONCE_SIZE:-_MAC_SIZE]
    tag = blob[-_MAC_SIZE:]

    mac_key = _derive_subkey(b"medicaition:mac:v1")
    expected_tag = hmac.new(mac_key, b"ENC1" + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Integridad criptográfica comprometida (MAC inválido)")

    enc_key = _derive_subkey(b"medicaition:enc:v1")
    raw_bytes = _chacha20_xor(enc_key, nonce, ciphertext)
    return raw_bytes.decode("utf-8")


def compute_consulta_seal(fields: Dict[str, Any]) -> str:
    """Calcula el sello HMAC-SHA256 de integridad NOM-004 sobre la consulta descifrada."""
    canonical_obj = {
        "id": str(fields.get("id") or ""),
        "evento_id": str(fields.get("evento_id") or ""),
        "patient_curp": str(fields.get("patient_curp") or ""),
        "doctor_nombre": str(fields.get("doctor_nombre") or ""),
        "cedula_profesional": str(fields.get("cedula_profesional") or ""),
        "fecha_hora": str(fields.get("fecha_hora") or ""),
        "nota_medica_json": str(fields.get("nota_medica_json") or ""),
        "receta_json": str(fields.get("receta_json") or ""),
        "entidades_json": str(fields.get("entidades_json") or ""),
        "texto_original": str(fields.get("texto_original") or ""),
    }
    msg = json.dumps(canonical_obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    seal_key = _derive_subkey(b"medicaition:nom004-seal:v1")
    return hmac.new(seal_key, msg, hashlib.sha256).hexdigest()


def verify_consulta_seal(fields: Dict[str, Any], stored_seal: Optional[str]) -> Optional[bool]:
    """Devuelve True si el sello NOM-004 coincide, False si fue alterado, None si es legado sin sello."""
    if not stored_seal:
        return None
    expected = compute_consulta_seal(fields)
    return hmac.compare_digest(expected, str(stored_seal).strip())


def compute_consent_hash(consent_fields: Dict[str, Any]) -> str:
    """Firma HMAC-SHA256 de prueba de consentimiento informado LFPDPPP."""
    msg = json.dumps(consent_fields, sort_keys=True, ensure_ascii=False).encode("utf-8")
    consent_key = _derive_subkey(b"medicaition:lfpdppp-consent:v1")
    return hmac.new(consent_key, msg, hashlib.sha256).hexdigest()


def vault_status() -> Dict[str, Any]:
    """Devuelve el estado público del módulo criptográfico sin exponer secretos."""
    master = _get_master_key()
    fingerprint = hashlib.sha256(master).hexdigest()[:16].upper()
    return {
        "cipher_suite": "ChaCha20 + HMAC-SHA256 (Encrypt-then-MAC, 256-bit)",
        "key_loaded": True,
        "key_fingerprint": fingerprint,
        "key_storage": "local-file" if not os.environ.get("MEDICAITION_MASTER_KEY") else "env",
        "key_path": _KEY_PATH if not os.environ.get("MEDICAITION_MASTER_KEY") else "ENV",
    }


# ---------------------------------------------------------------------------
# Credenciales locales (PIN PBKDF2-HMAC-SHA256) y Tokens de Sesión Firmados
# ---------------------------------------------------------------------------

def hash_pin(pin: str, salt: Optional[str] = None) -> str:
    """Genera un hash PBKDF2-HMAC-SHA256 con sal aleatoria para PIN de acceso."""
    clean = str(pin or "").strip()
    if len(clean) < 4:
        raise ValueError("El PIN debe tener al menos 4 caracteres.")
    salt_hex = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", clean.encode("utf-8"), bytes.fromhex(salt_hex), 100_000)
    return f"PBKDF2${salt_hex}${dk.hex()}"


def verify_pin(pin: str, stored_hash: Optional[str]) -> bool:
    """Verifica en tiempo constante un PIN contra su hash PBKDF2 almacenado."""
    if not stored_hash or not str(stored_hash).startswith("PBKDF2$"):
        return False
    parts = str(stored_hash).split("$")
    if len(parts) != 3:
        return False
    _, salt_hex, expected_hex = parts
    try:
        dk = hashlib.pbkdf2_hmac("sha256", str(pin or "").strip().encode("utf-8"), bytes.fromhex(salt_hex), 100_000)
        return hmac.compare_digest(dk.hex(), expected_hex)
    except Exception:
        return False


def sign_session_token(claims: Dict[str, Any], ttl_seconds: int = 43200) -> str:
    """Firma un token de sesión compacto con HMAC-SHA256 usando subclave derivada."""
    now = int(time.time())
    payload = dict(claims)
    payload["iat"] = now
    payload["exp"] = now + max(60, int(ttl_seconds))
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    key = _derive_subkey(b"medicaition:session:v1")
    sig = base64.urlsafe_b64encode(hmac.new(key, b64.encode("ascii"), hashlib.sha256).digest()).decode("ascii").rstrip("=")
    return f"{b64}.{sig}"


def verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Valida firma y expiración de un token de sesión emitido localmente."""
    if not token or "." not in token:
        return None
    try:
        b64, sig = token.strip().split(".", 1)
        key = _derive_subkey(b"medicaition:session:v1")
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(key, b64.encode("ascii"), hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
        if not hmac.compare_digest(sig, expected_sig):
            return None
        padded = b64 + "=" * (-len(b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
