# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import base64
import hashlib
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class AIEncryptionError(ValueError):
    pass


def derive_ai_encryption_key(jwt_key_bytes: bytes) -> str:
    if not jwt_key_bytes:
        raise AIEncryptionError("JWT key is empty, unable to derive AI encryption key")
    digest = hashlib.sha256(b"slurmweb-ai-fernet-v1\x00" + bytes(jwt_key_bytes)).digest()
    return base64.urlsafe_b64encode(digest).decode()


class AISecretCipher:
    def __init__(self, key: str):
        if not key:
            raise AIEncryptionError("AI encryption key is required")
        try:
            self._fernet = Fernet(str(key).encode())
        except Exception as err:
            raise AIEncryptionError("Invalid AI encryption key") from err

    @classmethod
    def from_jwt_key_file(cls, path) -> "AISecretCipher":
        try:
            jwt_key_bytes = Path(path).read_bytes()
        except Exception as err:
            raise AIEncryptionError(
                f"Unable to read JWT key file for AI encryption key derivation: {path}"
            ) from err
        return cls(derive_ai_encryption_key(jwt_key_bytes))

    @staticmethod
    def mask_secret(secret: str) -> str:
        if not secret:
            return ""
        visible = secret[-4:] if len(secret) >= 4 else secret
        return f"***{visible}"

    def encrypt(self, secret: str):
        if not secret:
            return None, None
        ciphertext = self._fernet.encrypt(secret.encode()).decode()
        return ciphertext, self.mask_secret(secret)

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as err:
            raise AIEncryptionError("Unable to decrypt AI provider secret") from err
