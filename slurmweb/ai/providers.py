# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging
from typing import Iterable, List

import requests


logger = logging.getLogger(__name__)

OPENAI_PROVIDER = "openai"
AZURE_OPENAI_PROVIDER = "azure-openai"
ANTHROPIC_PROVIDER = "anthropic"
GOOGLE_PROVIDER = "google"
OPENAI_COMPATIBLE_PROVIDER = "openai-compatible"
QWEN_PROVIDER = "qwen"
DEEPSEEK_PROVIDER = "deepseek"
KIMI_PROVIDER = "kimi"
OLLAMA_PROVIDER = "ollama"

OPENAI_COMPATIBLE_PROVIDERS = {
    OPENAI_PROVIDER,
    OPENAI_COMPATIBLE_PROVIDER,
    QWEN_PROVIDER,
    DEEPSEEK_PROVIDER,
    KIMI_PROVIDER,
}

SUPPORTED_PROVIDERS = {
    OPENAI_PROVIDER,
    AZURE_OPENAI_PROVIDER,
    ANTHROPIC_PROVIDER,
    GOOGLE_PROVIDER,
    OPENAI_COMPATIBLE_PROVIDER,
    QWEN_PROVIDER,
    DEEPSEEK_PROVIDER,
    KIMI_PROVIDER,
    OLLAMA_PROVIDER,
}

PROVIDER_LABELS = {
    OPENAI_PROVIDER: "OpenAI",
    AZURE_OPENAI_PROVIDER: "Azure OpenAI",
    ANTHROPIC_PROVIDER: "Anthropic",
    GOOGLE_PROVIDER: "Google Gemini",
    OPENAI_COMPATIBLE_PROVIDER: "OpenAI Compatible",
    QWEN_PROVIDER: "Qwen",
    DEEPSEEK_PROVIDER: "DeepSeek",
    KIMI_PROVIDER: "Kimi",
    OLLAMA_PROVIDER: "Ollama",
}


class AIProviderError(RuntimeError):
    pass


def _json_headers(secret: str):
    return {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }


def _join_message_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content or "")


def _normalize_messages(messages: Iterable[dict]) -> List[dict]:
    normalized = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = _join_message_content(message.get("content"))
        if role not in {"system", "user", "assistant"}:
            role = "user"
        normalized.append({"role": role, "content": content})
    return normalized


class BaseProviderClient:
    def complete(self, config: dict, secret: str, messages: Iterable[dict]) -> str:
        raise NotImplementedError

    @staticmethod
    def _timeout(config: dict) -> int:
        return int(config.get("request_timeout") or 60)

    @staticmethod
    def _temperature(config: dict):
        value = config.get("temperature")
        return 0.2 if value is None else value

    @staticmethod
    def _system_prompt(config: dict) -> str:
        return str(config.get("system_prompt") or "").strip()

    def validate(self, config: dict, secret: str) -> dict:
        content = self.complete(
            config,
            secret,
            [{"role": "user", "content": "Reply with the exact text PONG."}],
        )
        return {"ok": bool(content), "sample": content[:80]}


class OpenAICompatibleClient(BaseProviderClient):
    def complete(self, config: dict, secret: str, messages: Iterable[dict]) -> str:
        base_url = str(config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        body = {
            "model": config["model"],
            "messages": _normalize_messages(messages),
            "temperature": self._temperature(config),
            "stream": False,
        }
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=_json_headers(secret),
            json=body,
            timeout=self._timeout(config),
        )
        if response.status_code >= 400:
            raise AIProviderError(f"{config['provider']} request failed: {response.text}")
        payload = response.json()
        try:
            return _join_message_content(payload["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as err:
            raise AIProviderError("Invalid OpenAI-compatible response payload") from err


class AzureOpenAIClient(BaseProviderClient):
    def complete(self, config: dict, secret: str, messages: Iterable[dict]) -> str:
        base_url = str(config.get("base_url") or "").rstrip("/")
        deployment = str(config.get("deployment") or "").strip()
        api_version = str(config.get("api_version") or "2024-08-01-preview").strip()
        if not base_url or not deployment:
            raise AIProviderError("Azure OpenAI requires base_url and deployment")
        body = {
            "messages": _normalize_messages(messages),
            "temperature": self._temperature(config),
        }
        response = requests.post(
            f"{base_url}/openai/deployments/{deployment}/chat/completions?api-version={api_version}",
            headers={
                "api-key": secret,
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self._timeout(config),
        )
        if response.status_code >= 400:
            raise AIProviderError(f"azure-openai request failed: {response.text}")
        payload = response.json()
        try:
            return _join_message_content(payload["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as err:
            raise AIProviderError("Invalid Azure OpenAI response payload") from err


class AnthropicClient(BaseProviderClient):
    def complete(self, config: dict, secret: str, messages: Iterable[dict]) -> str:
        base_url = str(config.get("base_url") or "https://api.anthropic.com/v1").rstrip("/")
        system_prompt = self._system_prompt(config)
        anthropic_messages = []
        for message in _normalize_messages(messages):
            if message["role"] == "system":
                if not system_prompt:
                    system_prompt = message["content"]
                continue
            anthropic_messages.append(
                {
                    "role": message["role"],
                    "content": [{"type": "text", "text": message["content"]}],
                }
            )
        body = {
            "model": config["model"],
            "max_tokens": 1024,
            "messages": anthropic_messages,
        }
        if system_prompt:
            body["system"] = system_prompt
        response = requests.post(
            f"{base_url}/messages",
            headers={
                "x-api-key": secret,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self._timeout(config),
        )
        if response.status_code >= 400:
            raise AIProviderError(f"anthropic request failed: {response.text}")
        payload = response.json()
        try:
            return "".join(
                block.get("text", "")
                for block in payload["content"]
                if isinstance(block, dict) and block.get("type") == "text"
            ).strip()
        except (KeyError, TypeError) as err:
            raise AIProviderError("Invalid Anthropic response payload") from err


class GoogleGeminiClient(BaseProviderClient):
    def complete(self, config: dict, secret: str, messages: Iterable[dict]) -> str:
        base_url = str(
            config.get("base_url") or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        system_prompt = self._system_prompt(config)
        contents = []
        for message in _normalize_messages(messages):
            if message["role"] == "system":
                if not system_prompt:
                    system_prompt = message["content"]
                continue
            contents.append(
                {
                    "role": "model" if message["role"] == "assistant" else "user",
                    "parts": [{"text": message["content"]}],
                }
            )
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": self._temperature(config),
            },
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        response = requests.post(
            f"{base_url}/models/{config['model']}:generateContent?key={secret}",
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=self._timeout(config),
        )
        if response.status_code >= 400:
            raise AIProviderError(f"google request failed: {response.text}")
        payload = response.json()
        try:
            candidate = payload["candidates"][0]["content"]["parts"]
            return "".join(
                item.get("text", "")
                for item in candidate
                if isinstance(item, dict)
            ).strip()
        except (KeyError, IndexError, TypeError) as err:
            raise AIProviderError("Invalid Google Gemini response payload") from err


class OllamaClient(BaseProviderClient):
    def complete(self, config: dict, secret: str, messages: Iterable[dict]) -> str:
        base_url = str(config.get("base_url") or "http://localhost:11434").rstrip("/")
        body = {
            "model": config["model"],
            "messages": _normalize_messages(messages),
            "stream": False,
            "options": {
                "temperature": self._temperature(config),
            },
        }
        response = requests.post(
            f"{base_url}/api/chat",
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=self._timeout(config),
        )
        if response.status_code >= 400:
            raise AIProviderError(f"ollama request failed: {response.text}")
        payload = response.json()
        try:
            return str(payload["message"]["content"]).strip()
        except (KeyError, TypeError) as err:
            raise AIProviderError("Invalid Ollama response payload") from err


def get_provider_client(provider: str) -> BaseProviderClient:
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return OpenAICompatibleClient()
    if provider == AZURE_OPENAI_PROVIDER:
        return AzureOpenAIClient()
    if provider == ANTHROPIC_PROVIDER:
        return AnthropicClient()
    if provider == GOOGLE_PROVIDER:
        return GoogleGeminiClient()
    if provider == OLLAMA_PROVIDER:
        return OllamaClient()
    raise AIProviderError(f"Unsupported AI provider {provider}")


def summarize_provider_config(config: dict) -> dict:
    provider = config.get("provider")
    return {
        "id": config.get("id"),
        "cluster": config.get("cluster"),
        "name": config.get("name"),
        "provider": provider,
        "provider_label": PROVIDER_LABELS.get(provider, provider),
        "model": config.get("model"),
        "display_name": config.get("display_name"),
        "enabled": bool(config.get("enabled")),
        "is_default": bool(config.get("is_default")),
        "sort_order": config.get("sort_order"),
        "base_url": config.get("base_url"),
        "deployment": config.get("deployment"),
        "api_version": config.get("api_version"),
        "request_timeout": config.get("request_timeout"),
        "temperature": config.get("temperature"),
        "system_prompt": config.get("system_prompt"),
        "extra_options": config.get("extra_options") or {},
        "secret_configured": bool(config.get("secret_ciphertext")),
        "secret_mask": config.get("secret_mask"),
        "last_validated_at": config.get("last_validated_at"),
        "last_validation_error": config.get("last_validation_error"),
        "created_at": config.get("created_at"),
        "updated_at": config.get("updated_at"),
    }
