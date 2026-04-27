# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from unittest import mock

from ..lib.agent import TestAgentBase
from slurmweb.ai.crypto import AISecretCipher, derive_ai_encryption_key


class TestAgentAIApp(TestAgentBase):
    @mock.patch("slurmweb.ai.service.AIService")
    @mock.patch("slurmweb.ai.crypto.AISecretCipher.from_jwt_key_file")
    @mock.patch("slurmweb.persistence.ai_conversation_store.AIConversationStore")
    @mock.patch("slurmweb.persistence.ai_model_config_store.AIModelConfigStore")
    @mock.patch("slurmweb.persistence.users_store.UsersStore")
    def test_app_enables_ai_when_dependencies_ready(
        self,
        mock_users_store,
        mock_ai_model_config_store,
        mock_ai_conversation_store,
        mock_secret_cipher_from_jwt_key_file,
        mock_ai_service,
    ):
        self.setup_client(database=True, ai_enabled=True)

        mock_users_store.assert_called_once()
        mock_ai_model_config_store.assert_called_once()
        mock_ai_model_config_store.return_value.validate_connection.assert_called_once_with()
        mock_ai_conversation_store.assert_called_once()
        mock_ai_conversation_store.return_value.validate_connection.assert_called_once_with()
        mock_secret_cipher_from_jwt_key_file.assert_called_once_with(self.app.settings.jwt.key)
        mock_ai_service.assert_called_once()
        self.assertTrue(self.app.ai_enabled)

    def test_ai_encryption_key_derivation_is_stable_and_usable(self):
        derived = derive_ai_encryption_key(b"jwt-signing-key")
        self.assertEqual(derived, derive_ai_encryption_key(b"jwt-signing-key"))

        cipher = AISecretCipher(derived)
        ciphertext, mask = cipher.encrypt("sk-secret-1234")

        self.assertEqual(mask, "***1234")
        self.assertEqual(cipher.decrypt(ciphertext), "sk-secret-1234")
