from __future__ import annotations

import json
import time

from .agent_interfaces import (
    AIAgentInterfaceError,
    AIAgentInterfaceRegistry,
)


def _truncate_text(value, limit=2400):
    text = json.dumps(value, default=str, ensure_ascii=True)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class AIToolPermissionError(PermissionError):
    def __init__(self, message: str, *, interface_key: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.interface_key = interface_key
        self.status_code = status_code


class AIToolExecutionError(RuntimeError):
    def __init__(self, message: str, *, interface_key: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.interface_key = interface_key
        self.status_code = status_code


class AIToolRegistry:
    def __init__(self, app, conversation_store):
        self.app = app
        self.conversation_store = conversation_store
        self.interfaces = AIAgentInterfaceRegistry(app)

    def definitions(self, user):
        return [
            {
                "name": "query_agent_interface",
                "permission": "dynamic-query",
                "description": "Call one read-only agent interface using interface_key and arguments.",
            },
            {
                "name": "mutate_agent_interface",
                "permission": "dynamic-mutate",
                "description": "Call one write-capable agent interface using interface_key and arguments. Execution is checked against the current user's interface permissions.",
            },
        ]

    def interface_catalog(self, user):
        return self.interfaces.catalog(user)

    def _record_tool_call(
        self,
        *,
        conversation_id: int,
        message_id,
        user,
        tool_name: str,
        permission: str,
        interface_key: str,
        status_code: int | None,
        input_payload: dict,
        result_summary,
        status: str,
        error,
        duration_ms: int,
    ):
        self.conversation_store.record_tool_call(
            conversation_id=conversation_id,
            message_id=message_id,
            cluster=self.app.settings.service.cluster,
            username=user.login,
            tool_name=tool_name,
            permission=permission,
            interface_key=interface_key,
            status_code=status_code,
            input_payload=input_payload,
            result_summary=result_summary,
            status=status,
            error=error,
            duration_ms=duration_ms,
        )

    def execute(self, user, conversation_id: int, tool_name: str, arguments: dict, message_id=None):
        arguments = arguments or {}
        started = time.time()
        permission = "dynamic-query"
        interface_key = str(arguments.get("interface_key") or "").strip()
        interface_arguments = arguments.get("arguments") or {}
        if not isinstance(interface_arguments, dict):
            interface_arguments = {}
        status_code = None
        try:
            if tool_name == "query_agent_interface":
                permission = "dynamic-query"
            elif tool_name == "mutate_agent_interface":
                permission = "dynamic-mutate"
            else:
                raise AIToolExecutionError(f"Unsupported tool {tool_name}")

            if not interface_key:
                raise AIToolExecutionError("interface_key is required")

            result = self.interfaces.execute(user, interface_key, interface_arguments)
            status_code = result.status_code
            duration_ms = int((time.time() - started) * 1000)
            summary = _truncate_text(result.payload, limit=1200)
            self._record_tool_call(
                conversation_id=conversation_id,
                message_id=message_id,
                user=user,
                tool_name=tool_name,
                permission=permission,
                interface_key=result.interface_key,
                status_code=result.status_code,
                input_payload=interface_arguments,
                result_summary=summary,
                status="ok",
                error=None,
                duration_ms=duration_ms,
            )
            return {
                "tool_name": tool_name,
                "permission": permission,
                "interface_key": result.interface_key,
                "arguments": interface_arguments,
                "result": result.payload,
                "result_summary": _truncate_text(result.payload, limit=2400),
                "status_code": result.status_code,
                "duration_ms": duration_ms,
            }
        except AIAgentInterfaceError as err:
            duration_ms = int((time.time() - started) * 1000)
            self._record_tool_call(
                conversation_id=conversation_id,
                message_id=message_id,
                user=user,
                tool_name=tool_name,
                permission=permission,
                interface_key=interface_key or tool_name,
                status_code=err.status_code,
                input_payload=interface_arguments,
                result_summary=None,
                status="error",
                error=err.message,
                duration_ms=duration_ms,
            )
            if err.status_code == 403:
                raise AIToolPermissionError(
                    err.message,
                    interface_key=interface_key or tool_name,
                    status_code=err.status_code,
                ) from err
            raise AIToolExecutionError(
                err.message,
                interface_key=interface_key or tool_name,
                status_code=err.status_code,
            ) from err
        except Exception as err:
            duration_ms = int((time.time() - started) * 1000)
            self._record_tool_call(
                conversation_id=conversation_id,
                message_id=message_id,
                user=user,
                tool_name=tool_name,
                permission=permission,
                interface_key=interface_key or tool_name,
                status_code=status_code,
                input_payload=interface_arguments,
                result_summary=None,
                status="error",
                error=str(err),
                duration_ms=duration_ms,
            )
            raise
