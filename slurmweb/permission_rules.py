import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

import yaml


logger = logging.getLogger(__name__)


PERMISSION_SCOPES = ("*", "self")
PERMISSION_OPERATIONS = ("view", "edit", "delete", "*")


PERMISSION_CATALOG = [
    {
        "group": "main-routes",
        "label": "Main Routes",
        "resources": [
            {
                "resource": "dashboard",
                "label": "Dashboard",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "analysis",
                "label": "Analysis",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "ai",
                "label": "AI Workspace",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "jobs",
                "label": "Jobs",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*", "self"],
                "owner_aware": True,
            },
            {
                "resource": "jobs-history",
                "label": "Jobs History",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "resources",
                "label": "Resources",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*"],
            },
            {
                "resource": "qos",
                "label": "QOS",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*"],
            },
            {
                "resource": "reservations",
                "label": "Reservations",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*"],
            },
            {
                "resource": "accounts",
                "label": "Accounts",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*"],
            },
            {
                "resource": "users-admin",
                "label": "Users Admin",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*"],
            },
        ],
    },
    {
        "group": "settings",
        "label": "Settings",
        "resources": [
            {
                "resource": "settings/general",
                "label": "Settings / General",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "settings/errors",
                "label": "Settings / Errors",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "settings/account",
                "label": "Settings / Account",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "admin/ai",
                "label": "Admin / AI",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*"],
            },
            {
                "resource": "admin/access-control",
                "label": "Admin / Access Control",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*"],
            },
            {
                "resource": "admin/cache",
                "label": "Admin / Cache",
                "operations": ["view", "edit"],
                "scopes": ["*"],
            },
            {
                "resource": "admin/ldap-cache",
                "label": "Admin / LDAP Cache",
                "operations": ["view", "edit"],
                "scopes": ["*"],
            },
            {
                "resource": "admin/system",
                "label": "Admin / System",
                "operations": ["view", "edit", "delete"],
                "scopes": ["*"],
            },
        ],
    },
    {
        "group": "user-workspace",
        "label": "User Workspace",
        "resources": [
            {
                "resource": "user/profile",
                "label": "User Profile",
                "operations": ["view"],
                "scopes": ["*", "self"],
                "owner_aware": True,
            },
            {
                "resource": "user/analysis",
                "label": "User Analysis",
                "operations": ["view"],
                "scopes": ["*", "self"],
                "owner_aware": True,
            },
        ],
    },
    {
        "group": "filters",
        "label": "Shared Filters",
        "resources": [
            {
                "resource": "jobs/filter-accounts",
                "label": "Jobs Filter / Accounts",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "jobs/filter-partitions",
                "label": "Jobs Filter / Partitions",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "jobs/filter-qos",
                "label": "Jobs Filter / QOS",
                "operations": ["view"],
                "scopes": ["*"],
            },
            {
                "resource": "resources/filter-partitions",
                "label": "Resources Filter / Partitions",
                "operations": ["view"],
                "scopes": ["*"],
            },
        ],
    },
]


DEFAULT_LEGACY_PERMISSION_MAP = {
    "view-stats": ["dashboard:view:*", "analysis:view:*"],
    "view-jobs": ["jobs:view:*"],
    "view-own-jobs": ["jobs:view:self", "user/analysis:view:self"],
    "cancel-own-jobs": ["jobs:delete:self"],
    "view-history-jobs": ["jobs-history:view:*"],
    "view-nodes": ["resources:view:*"],
    "view-qos": ["qos:view:*", "jobs/filter-qos:view:*"],
    "view-reservations": ["reservations:view:*"],
    "associations-view": ["accounts:view:*", "user/profile:view:*"],
    "view-accounts": ["jobs/filter-accounts:view:*"],
    "view-partitions": [
        "jobs/filter-partitions:view:*",
        "resources/filter-partitions:view:*",
    ],
    "cache-view": ["admin/cache:view:*", "admin/ldap-cache:view:*"],
    "cache-reset": ["admin/cache:edit:*"],
    "roles-view": ["admin/access-control:view:*"],
    "roles-manage": [
        "admin/access-control:edit:*",
        "admin/access-control:delete:*",
    ],
    "view-ai": ["ai:view:*", "admin/ai:view:*"],
    "manage-ai": ["admin/ai:view:*", "admin/ai:edit:*", "admin/ai:delete:*"],
}


def normalize_permission_rule(rule: str) -> str:
    if not isinstance(rule, str):
        raise ValueError("Permission rule must be a string")
    normalized = rule.strip()
    parts = normalized.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid permission rule {rule}")
    resource, operation, scope = parts
    if not resource:
        raise ValueError(f"Invalid permission rule {rule}")
    if operation not in PERMISSION_OPERATIONS:
        raise ValueError(f"Invalid permission operation {operation}")
    if scope not in PERMISSION_SCOPES:
        raise ValueError(f"Invalid permission scope {scope}")
    return f"{resource}:{operation}:{scope}"


def sort_permission_rules(rules: Iterable[str]) -> List[str]:
    return sorted({normalize_permission_rule(rule) for rule in rules})


def _resource_matches(granted: str, requested: str) -> bool:
    if granted == "*":
        return True
    if granted == requested:
        return True
    if granted.endswith("/*"):
        return requested.startswith(granted[:-1])
    return False


def permission_rule_allows(rule: str, resource: str, operation: str, scope: str) -> bool:
    granted_resource, granted_operation, granted_scope = normalize_permission_rule(rule).split(":")
    if granted_operation == "*":
        operation_allowed = True
    elif operation == "view":
        operation_allowed = granted_operation in {"view", "edit", "delete"}
    else:
        operation_allowed = granted_operation == operation
    return (
        _resource_matches(granted_resource, resource)
        and operation_allowed
        and (granted_scope == "*" or granted_scope == scope)
    )


def permission_rules_allow(
    rules: Iterable[str],
    resource: str,
    operation: str,
    scope: str = "*",
) -> bool:
    for rule in rules:
        if permission_rule_allows(rule, resource, operation, scope):
            return True
    return False


def load_legacy_permission_map(path: Optional[Path]) -> Dict[str, List[str]]:
    if path is None or not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError("permission_map must be a mapping")
    normalized = {}
    for action, rules in raw.items():
        if not isinstance(rules, list):
            raise ValueError(f"permission_map entry for {action} must be a list")
        normalized[str(action)] = sort_permission_rules(rules)
    return normalized


def merged_legacy_permission_map(path: Optional[Path]) -> Dict[str, List[str]]:
    merged = {
        action: sort_permission_rules(rules)
        for action, rules in DEFAULT_LEGACY_PERMISSION_MAP.items()
    }
    for action, rules in load_legacy_permission_map(path).items():
        merged[action] = rules
    return merged


def legacy_actions_to_rules(
    actions: Iterable[str],
    legacy_map: Dict[str, Sequence[str]],
) -> List[str]:
    rules = []
    for action in actions:
        mapped = legacy_map.get(action, [])
        rules.extend(mapped)
    return sort_permission_rules(rules)


def permission_rules_to_legacy_actions(
    rules: Iterable[str],
    legacy_map: Dict[str, Sequence[str]],
) -> List[str]:
    normalized_rules = sort_permission_rules(rules)
    actions = []
    for action, required_rules in legacy_map.items():
        if any(
            permission_rules_allow(
                normalized_rules,
                normalize_permission_rule(required_rule).split(":")[0],
                normalize_permission_rule(required_rule).split(":")[1],
                normalize_permission_rule(required_rule).split(":")[2],
            )
            for required_rule in required_rules
        ):
            actions.append(action)
    return sorted(actions)


def access_control_catalog() -> Dict[str, object]:
    return {
        "operations": list(PERMISSION_OPERATIONS[:-1]),
        "scopes": list(PERMISSION_SCOPES),
        "groups": PERMISSION_CATALOG,
        "legacy_map": {
            action: list(rules)
            for action, rules in DEFAULT_LEGACY_PERMISSION_MAP.items()
        },
    }


def default_seed_roles() -> List[Dict[str, object]]:
    user_rules = [
        "dashboard:view:*",
        "analysis:view:*",
        "ai:view:*",
        "jobs:view:self",
        "jobs:delete:self",
        "jobs-history:view:*",
        "resources:view:*",
        "qos:view:*",
        "reservations:view:*",
        "accounts:view:*",
        "user/profile:view:self",
        "user/analysis:view:self",
        "jobs/filter-accounts:view:*",
        "jobs/filter-partitions:view:*",
        "jobs/filter-qos:view:*",
        "resources/filter-partitions:view:*",
        "settings/general:view:*",
        "settings/errors:view:*",
        "settings/account:view:*",
    ]
    admin_rules = []
    for group in PERMISSION_CATALOG:
        for resource in group["resources"]:
            scopes = resource.get("scopes", ["*"])
            for operation in resource.get("operations", []):
                admin_rules.append(f"{resource['resource']}:{operation}:{scopes[0]}")
    return [
        {
            "name": "user",
            "description": "Read-only access to available routes and settings.",
            "permissions": sort_permission_rules(user_rules),
        },
        {
            "name": "admin",
            "description": "Operational access across routes and editable settings.",
            "permissions": sort_permission_rules(admin_rules),
        },
        {
            "name": "super-admin",
            "description": "Full access to all resources and operations.",
            "permissions": ["*:*:*"],
        },
    ]
