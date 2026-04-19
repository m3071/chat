from __future__ import annotations

from base64 import urlsafe_b64encode
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

ENC_PREFIX = "enc:v1:"
SECRET_FIELD_NAMES = {"api_key", "api_password", "webhook_secret", "password", "secret", "token"}


class SecretManager:
    def __init__(self, key: str | None = None) -> None:
        self.raw_key = key if key is not None else settings.secrets_encryption_key
        self._fernet = Fernet(self._derive_key(self.raw_key)) if self.raw_key else None

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt(self, value: str | None) -> str | None:
        if value is None or value == "" or value.startswith(ENC_PREFIX) or not self._fernet:
            return value
        token = self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        return f"{ENC_PREFIX}{token}"

    def decrypt(self, value: str | None) -> str | None:
        if value is None or value == "" or not value.startswith(ENC_PREFIX):
            return value
        if not self._fernet:
            raise ValueError("Secret is encrypted but SECRETS_ENCRYPTION_KEY is not configured.")
        try:
            return self._fernet.decrypt(value[len(ENC_PREFIX) :].encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Secret could not be decrypted with the configured key.") from exc

    def encrypt_config(self, value):
        if isinstance(value, dict):
            encrypted = {}
            for key, item in value.items():
                if key in SECRET_FIELD_NAMES and isinstance(item, str):
                    encrypted[key] = self.encrypt(item)
                else:
                    encrypted[key] = self.encrypt_config(item)
            return encrypted
        if isinstance(value, list):
            return [self.encrypt_config(item) for item in value]
        return value

    def decrypt_config(self, value):
        if isinstance(value, dict):
            return {key: self.decrypt_config(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.decrypt_config(item) for item in value]
        if isinstance(value, str):
            return self.decrypt(value)
        return value

    def is_encrypted(self, value: str | None) -> bool:
        return bool(value and value.startswith(ENC_PREFIX))

    def _derive_key(self, key: str) -> bytes:
        if key.startswith("fernet:"):
            return key.removeprefix("fernet:").encode("utf-8")
        return urlsafe_b64encode(sha256(key.encode("utf-8")).digest())


def redact_secret(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(ENC_PREFIX):
        return "encrypted:****"
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"
