# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging
import re
from typing import Iterable, Optional
from datetime import datetime, timezone

from .crypto import AISecretCipher
from .providers import (
    OPENAI_COMPATIBLE_PROVIDER,
    PROVIDER_LABELS,
    SUPPORTED_PROVIDERS,
    get_provider_client,
    summarize_provider_config,
)
from .tools import AIToolExecutionError, AIToolPermissionError, AIToolRegistry


logger = logging.getLogger(__name__)

UNIQUE_CONFIG_NAME_CONSTRAINT = "uq_ai_model_configs_cluster_name"
UNIQUE_DEFAULT_CONFIG_INDEX = "uq_ai_model_configs_cluster_default"
DEFAULT_MAX_ROUNDS = 4
DEFAULT_MAX_HISTORY_MESSAGES = 24
DEFAULT_STREAM_CHUNK_SIZE = 32

SYSTEM_TOOL_PROMPT = """You are the Slurm Web cluster assistant.
You can answer only with information available from agent interfaces and previous conversation context.
Never invent cluster data.
You may call multiple tools across the same user request when one interface is not enough.
Only call another interface when the current information is insufficient.
Before giving the final answer, consolidate, deduplicate, and explain the facts you gathered.
If a write-capable interface is needed, the current user's interface permission still applies and denied calls will return tool errors.
When requesting a tool, reply with strict JSON only:
{"type":"tool_call","tool":"TOOL_NAME","arguments":{"interface_key":"INTERFACE_KEY","arguments":{"key":"value"}}}
When you have enough information, reply with strict JSON only:
{"type":"final","content":"your final user-facing answer"}
Do not wrap JSON in markdown fences.
"""


class AIRequestError(RuntimeError):
    pass


class AIProviderValidationError(ValueError):
    pass


def _raise_model_config_store_error(err: Exception):
    if getattr(err, "pgcode", None) == "23505":
        message = str(err)
        if UNIQUE_CONFIG_NAME_CONSTRAINT in message:
            raise AIProviderValidationError(
                "AI model config name must be unique within the cluster"
            ) from err
        if UNIQUE_DEFAULT_CONFIG_INDEX in message:
            raise AIProviderValidationError(
                "Only one default AI model is allowed per cluster"
            ) from err
    raise err


def _normalize_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def normalize_model_config_payload(payload: dict, partial=False) -> dict:
    payload = payload or {}
    normalized = {}
    required_fields = ["name", "provider", "model", "display_name"]
    for field in required_fields:
        if field in payload:
            value = str(payload.get(field) or "").strip()
            if not partial and not value:
                raise AIProviderValidationError(f"{field} is required")
            if value:
                normalized[field] = value
        elif not partial:
            raise AIProviderValidationError(f"{field} is required")

    provider = normalized.get("provider") or payload.get("provider")
    if provider is not None and provider not in SUPPORTED_PROVIDERS:
        raise AIProviderValidationError(f"Unsupported provider {provider}")

    if "enabled" in payload or not partial:
        normalized["enabled"] = _normalize_bool(payload.get("enabled"), default=True)
    if "is_default" in payload or not partial:
        normalized["is_default"] = _normalize_bool(payload.get("is_default"), default=False)
        if normalized["is_default"]:
            normalized["enabled"] = True
    if "sort_order" in payload or not partial:
        try:
            normalized["sort_order"] = int(payload.get("sort_order", 0) or 0)
        except (TypeError, ValueError):
            raise AIProviderValidationError("sort_order must be an integer")

    for field in ["base_url", "deployment", "api_version", "system_prompt"]:
        if field in payload or not partial:
            value = payload.get(field)
            normalized[field] = None if value in (None, "") else str(value).strip()

    for field in ["request_timeout"]:
        if field in payload or not partial:
            value = payload.get(field)
            if value in (None, ""):
                normalized[field] = None
            else:
                try:
                    normalized[field] = int(value)
                except (TypeError, ValueError):
                    raise AIProviderValidationError(f"{field} must be an integer")

    if "temperature" in payload or not partial:
        value = payload.get("temperature")
        if value in (None, ""):
            normalized["temperature"] = None
        else:
            try:
                normalized["temperature"] = float(value)
            except (TypeError, ValueError):
                raise AIProviderValidationError("temperature must be numeric")

    if "extra_options" in payload or not partial:
        extra_options = payload.get("extra_options")
        if extra_options in (None, ""):
            normalized["extra_options"] = {}
        elif not isinstance(extra_options, dict):
            raise AIProviderValidationError("extra_options must be an object")
        else:
            normalized["extra_options"] = extra_options

    if provider == "azure-openai":
        if not partial or "base_url" in payload:
            if not normalized.get("base_url"):
                raise AIProviderValidationError("Azure OpenAI requires base_url")
        if not partial or "deployment" in payload:
            if not normalized.get("deployment"):
                raise AIProviderValidationError("Azure OpenAI requires deployment")

    return normalized


def _serialize_json(value) -> str:
    return json.dumps(value, ensure_ascii=True, default=str)


def _extract_json_object(value: str):
    text = value.strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


class AIService:
    def __init__(
        self,
        app,
        config_store,
        conversation_store,
        secret_cipher: AISecretCipher,
    ):
        self.app = app
        self.config_store = config_store
        self.conversation_store = conversation_store
        self.secret_cipher = secret_cipher
        self.tools = AIToolRegistry(app, conversation_store)

    def _runtime_setting(self, name: str, default: int) -> int:
        settings = getattr(self.app.settings, "ai", None)
        value = getattr(settings, name, default)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_default_state(config: dict) -> dict:
        normalized = dict(config)
        if normalized.get("is_default"):
            normalized["enabled"] = True
        if not normalized.get("enabled", True):
            normalized["is_default"] = False
        return normalized

    @staticmethod
    def _connection_fields_changed(previous: dict, current: dict) -> bool:
        fields = [
            "provider",
            "model",
            "base_url",
            "deployment",
            "api_version",
            "request_timeout",
            "temperature",
            "system_prompt",
            "extra_options",
        ]
        return any(previous.get(field) != current.get(field) for field in fields)

    def capabilities(self):
        enabled_count = self.config_store.count_enabled_configs(
            self.app.settings.service.cluster
        )
        default_config = self.config_store.get_default_config(
            self.app.settings.service.cluster
        )
        return {
            "enabled": bool(getattr(self.app, "ai_enabled", False)),
            "configurable": True,
            "streaming": True,
            "persistence": True,
            "available_models_count": enabled_count,
            "default_model_id": None if default_config is None else default_config["id"],
            "providers": [
                {"key": key, "label": PROVIDER_LABELS.get(key, key)}
                for key in sorted(SUPPORTED_PROVIDERS)
            ],
            "tool_mode": "mixed",
        }

    def list_configs(self):
        cluster = self.app.settings.service.cluster
        return [summarize_provider_config(item) for item in self.config_store.list_configs(cluster)]

    def get_model_config(self, config_id: int, include_secret=False):
        cluster = self.app.settings.service.cluster
        config = self.config_store.get_config(cluster, config_id)
        if config is None:
            return None
        if include_secret and config.get("secret_ciphertext"):
            config["api_key"] = self.secret_cipher.decrypt(config["secret_ciphertext"])
        return config

    def get_default_model_config(self):
        cluster = self.app.settings.service.cluster
        return self.config_store.get_default_config(cluster)

    def create_model_config(self, payload: dict):
        normalized = self._normalize_default_state(
            normalize_model_config_payload(payload, partial=False)
        )
        secret = str(payload.get("api_key") or "").strip()
        if not secret and normalized["provider"] != "ollama":
            raise AIProviderValidationError("api_key is required")
        ciphertext, mask = self.secret_cipher.encrypt(secret) if secret else (None, None)
        normalized["secret_ciphertext"] = ciphertext
        normalized["secret_mask"] = mask
        normalized["last_validated_at"] = None
        normalized["last_validation_error"] = None
        try:
            created = self.config_store.create_config(
                self.app.settings.service.cluster,
                normalized,
            )
        except Exception as err:
            _raise_model_config_store_error(err)
        return summarize_provider_config(created)

    def update_model_config(self, config_id: int, payload: dict):
        current = self.get_model_config(config_id, include_secret=False)
        if current is None:
            return None
        updates = normalize_model_config_payload(payload, partial=True)
        merged = dict(current)
        merged.update(updates)
        merged = self._normalize_default_state(merged)
        normalized = normalize_model_config_payload(merged, partial=False)
        normalized = self._normalize_default_state(normalized)

        secret_changed = False
        secret_ciphertext = current.get("secret_ciphertext")
        secret_mask = current.get("secret_mask")
        if "api_key" in payload or payload.get("clear_secret"):
            secret = str(payload.get("api_key") or "").strip()
            if secret:
                secret_ciphertext, secret_mask = self.secret_cipher.encrypt(secret)
                secret_changed = True
            elif payload.get("clear_secret"):
                secret_ciphertext, secret_mask = None, None
                secret_changed = True

        if normalized["provider"] != "ollama" and not secret_ciphertext:
            raise AIProviderValidationError("api_key is required")

        normalized["secret_ciphertext"] = secret_ciphertext
        normalized["secret_mask"] = secret_mask
        if secret_changed or self._connection_fields_changed(current, normalized):
            normalized["last_validated_at"] = None
            normalized["last_validation_error"] = None

        try:
            updated = self.config_store.update_config(
                self.app.settings.service.cluster,
                config_id,
                normalized,
            )
        except Exception as err:
            _raise_model_config_store_error(err)
        return None if updated is None else summarize_provider_config(updated)

    def delete_model_config(self, config_id: int) -> bool:
        return self.config_store.delete_config(self.app.settings.service.cluster, config_id)

    def validate_model_config(self, config_id: int):
        config = self.get_model_config(config_id, include_secret=True)
        if config is None:
            return None
        if config["provider"] != "ollama" and not config.get("api_key"):
            raise AIProviderValidationError("Configured model secret is missing")
        client = get_provider_client(config["provider"])
        try:
            result = client.validate(config, config.get("api_key", ""))
            updated = self.config_store.update_config(
                self.app.settings.service.cluster,
                config_id,
                {
                    "last_validated_at": datetime.now(timezone.utc),
                    "last_validation_error": None,
                },
            )
        except Exception as err:
            self.config_store.update_config(
                self.app.settings.service.cluster,
                config_id,
                {
                    "last_validated_at": datetime.now(timezone.utc),
                    "last_validation_error": str(err),
                },
            )
            raise
        return {
            "result": "ok",
            "provider": config["provider"],
            "model": config["model"],
            "sample": result["sample"],
            "last_validated_at": None if updated is None else updated["last_validated_at"],
        }

    @staticmethod
    def _conversation_title(message: str) -> str:
        compact = " ".join(str(message or "").split())
        if not compact:
            return "New conversation"
        return compact[:80]

    def _resolve_conversation(self, user, message: str, conversation_id: Optional[int], model_config_id):
        cluster = self.app.settings.service.cluster
        if conversation_id is not None:
            conversation = self.conversation_store.get_conversation(cluster, user.login, conversation_id)
            if conversation is None:
                raise AIRequestError(f"Conversation {conversation_id} not found")
            return conversation
        return self.conversation_store.create_conversation(
            cluster=cluster,
            username=user.login,
            title=self._conversation_title(message),
            model_config_id=model_config_id,
        )

    def _resolve_model_config(self, model_config_id: Optional[int]):
        if model_config_id is not None:
            config = self.get_model_config(int(model_config_id), include_secret=True)
            if config is None:
                raise AIRequestError(f"Model config {model_config_id} not found")
        else:
            config = self.get_default_model_config()
            if config is None:
                raise AIRequestError("No default AI model is configured for this cluster")
            if config.get("secret_ciphertext"):
                config["api_key"] = self.secret_cipher.decrypt(config["secret_ciphertext"])
            else:
                config["api_key"] = ""
        if not config.get("enabled"):
            raise AIRequestError("Selected AI model is disabled")
        if config["provider"] != "ollama" and not config.get("api_key"):
            raise AIRequestError("Selected AI model has no configured secret")
        return config

    def _conversation_context_messages(self, user, conversation_id: int):
        history_limit = self._runtime_setting(
            "max_history_messages", DEFAULT_MAX_HISTORY_MESSAGES
        )
        messages = self.conversation_store.list_messages(
            self.app.settings.service.cluster,
            user.login,
            conversation_id,
            limit=history_limit,
        )
        return [{"role": item["role"], "content": item["content"]} for item in messages]

    def _build_planner_messages(self, user, model_config: dict, conversation_messages: Iterable[dict]):
        tool_descriptions = "\n".join(
            f"- {tool['name']} (permission={tool['permission']}): {tool['description']}"
            for tool in self.tools.definitions(user)
        )
        interface_descriptions = "\n".join(
            (
                f"- {interface['key']} [{interface['method']}]"
                f" {'(write, permission checked at runtime)' if interface['write'] else '(read-only)'}:"
                f" {interface['description']} Inputs: {interface['arguments_description']}"
            )
            for interface in self.tools.interface_catalog(user)
        )
        messages = [
            {
                "role": "system",
                "content": SYSTEM_TOOL_PROMPT
                + "\nAvailable tools:\n"
                + tool_descriptions
                + "\nAvailable agent interfaces:\n"
                + interface_descriptions,
            }
        ]
        if model_config.get("system_prompt"):
            messages.append({"role": "system", "content": model_config["system_prompt"]})
        messages.extend(conversation_messages)
        return messages

    @staticmethod
    def _action_from_model_output(output: str):
        parsed = _extract_json_object(output)
        if not isinstance(parsed, dict):
            return {"type": "final", "content": output.strip()}
        if parsed.get("type") == "tool_call":
            return {
                "type": "tool_call",
                "tool": parsed.get("tool"),
                "arguments": parsed.get("arguments") or {},
            }
        content = parsed.get("content")
        return {
            "type": "final",
            "content": output.strip() if not isinstance(content, str) else content.strip(),
        }

    def _chunk_text(self, text: str):
        chunk_size = self._runtime_setting("stream_chunk_size", DEFAULT_STREAM_CHUNK_SIZE)
        for index in range(0, len(text), chunk_size):
            yield text[index : index + chunk_size]

    @staticmethod
    def sse_event(event: str, payload: dict):
        return f"event: {event}\ndata: {_serialize_json(payload)}\n\n"

    def stream_chat(self, user, payload: dict):
        message = str(payload.get("message") or "").strip()
        if not message:
            raise AIRequestError("message is required")
        model_config = self._resolve_model_config(payload.get("model_config_id"))
        conversation = self._resolve_conversation(
            user=user,
            message=message,
            conversation_id=payload.get("conversation_id"),
            model_config_id=model_config["id"],
        )
        user_message = self.conversation_store.add_message(
            conversation["id"],
            "user",
            message,
            model_config_id=model_config["id"],
            metadata={"provider": model_config["provider"]},
        )
        working_messages = self._conversation_context_messages(user, conversation["id"])
        client = get_provider_client(model_config["provider"])
        max_rounds = self._runtime_setting("max_rounds", DEFAULT_MAX_ROUNDS)

        def generate():
            yield self.sse_event(
                "conversation",
                {
                    "conversation_id": conversation["id"],
                    "message_id": user_message["id"],
                    "model_config_id": model_config["id"],
                },
            )
            final_answer = None
            try:
                for _ in range(max_rounds):
                    planner_messages = self._build_planner_messages(
                        user,
                        model_config,
                        working_messages,
                    )
                    raw_output = client.complete(
                        model_config,
                        model_config.get("api_key", ""),
                        planner_messages,
                    )
                    action = self._action_from_model_output(raw_output)
                    if action["type"] == "tool_call":
                        tool_name = str(action.get("tool") or "").strip()
                        arguments = action.get("arguments") or {}
                        yield self.sse_event(
                            "tool_start",
                            {
                                "tool_name": tool_name,
                                "interface_key": str(arguments.get("interface_key") or "").strip() or None,
                                "arguments": arguments.get("arguments") or {},
                            },
                        )
                        try:
                            tool_result = self.tools.execute(
                                user,
                                conversation["id"],
                                tool_name,
                                arguments,
                                message_id=user_message["id"],
                            )
                            yield self.sse_event(
                                "tool_end",
                                {
                                    "tool_name": tool_name,
                                    "interface_key": tool_result["interface_key"],
                                    "arguments": tool_result["arguments"],
                                    "duration_ms": tool_result["duration_ms"],
                                    "status_code": tool_result["status_code"],
                                    "result_summary": tool_result["result_summary"],
                                },
                            )
                            working_messages.append(
                                {
                                    "role": "assistant",
                                    "content": _serialize_json(
                                        {
                                            "tool_request": tool_name,
                                            "interface_key": tool_result["interface_key"],
                                            "arguments": tool_result["arguments"],
                                        }
                                    ),
                                }
                            )
                            working_messages.append(
                                {
                                    "role": "user",
                                    "content": "Tool result: "
                                    + _serialize_json(tool_result["result"]),
                                }
                            )
                            continue
                        except (AIToolExecutionError, AIToolPermissionError, KeyError, ValueError) as err:
                            yield self.sse_event(
                                "tool_end",
                                {
                                    "tool_name": tool_name,
                                    "interface_key": getattr(err, "interface_key", None)
                                    or str(arguments.get("interface_key") or "").strip()
                                    or None,
                                    "arguments": arguments.get("arguments") or {},
                                    "duration_ms": None,
                                    "status_code": getattr(err, "status_code", 500) or 500,
                                    "result_summary": None,
                                    "error": str(err),
                                },
                            )
                            working_messages.append(
                                {
                                    "role": "user",
                                    "content": f"Tool error for {tool_name}: {err}",
                                }
                            )
                            continue
                    final_answer = action.get("content") or raw_output.strip()
                    break

                if not final_answer:
                    final_answer = (
                        "I could not complete the request within the allowed tool rounds. "
                        "Please refine the question."
                    )

                assistant_message = self.conversation_store.add_message(
                    conversation["id"],
                    "assistant",
                    final_answer,
                    model_config_id=model_config["id"],
                    metadata={"provider": model_config["provider"]},
                )
                for chunk in self._chunk_text(final_answer):
                    yield self.sse_event("content", {"delta": chunk})
                yield self.sse_event(
                    "complete",
                    {
                        "conversation_id": conversation["id"],
                        "message_id": assistant_message["id"],
                        "model_config_id": model_config["id"],
                    },
                )
            except Exception as err:
                logger.exception("AI chat request failed")
                yield self.sse_event("error", {"message": str(err)})
            yield self.sse_event("done", {"conversation_id": conversation["id"]})

        return generate

    def list_conversations(self, user):
        cluster = self.app.settings.service.cluster
        conversations = self.conversation_store.list_conversations(cluster, user.login)
        return {
            "items": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "model_config_id": item["model_config_id"],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "last_message": item.get("last_message"),
                }
                for item in conversations
            ]
        }

    def get_conversation_detail(self, user, conversation_id: int):
        cluster = self.app.settings.service.cluster
        conversation = self.conversation_store.get_conversation(cluster, user.login, conversation_id)
        if conversation is None:
            return None
        messages = self.conversation_store.list_messages(cluster, user.login, conversation_id)
        tool_calls = self.conversation_store.list_tool_calls(
            cluster,
            user.login,
            conversation_id,
        )
        return {
            "id": conversation["id"],
            "title": conversation["title"],
            "model_config_id": conversation["model_config_id"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "messages": [
                {
                    "id": message["id"],
                    "role": message["role"],
                    "content": message["content"],
                    "model_config_id": message["model_config_id"],
                    "metadata": message["metadata"] or {},
                    "created_at": message["created_at"],
                }
                for message in messages
            ],
            "tool_calls": [
                {
                    "id": tool_call["id"],
                    "message_id": tool_call.get("message_id"),
                    "tool_name": tool_call["tool_name"],
                    "permission": tool_call["permission"],
                    "interface_key": tool_call.get("interface_key"),
                    "status_code": tool_call.get("status_code"),
                    "input_payload": tool_call.get("input_payload") or {},
                    "result_summary": tool_call.get("result_summary"),
                    "status": tool_call["status"],
                    "error": tool_call.get("error"),
                    "duration_ms": tool_call.get("duration_ms"),
                    "created_at": tool_call.get("created_at"),
                }
                for tool_call in tool_calls
            ],
        }
