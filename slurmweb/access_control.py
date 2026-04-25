# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from rfl.authentication.user import AuthenticatedUser

from .permission_rules import (
    legacy_actions_to_rules,
    merged_legacy_permission_map,
    permission_rules_allow,
    permission_rules_to_legacy_actions,
    sort_permission_rules,
)


logger = logging.getLogger(__name__)


class AccessControlPolicyManager:
    """Wrap the file-backed RBAC policy and merge DB-backed custom roles."""

    def __init__(
        self,
        file_policy,
        access_control_enabled: bool = False,
        access_control_store=None,
        permission_map_path: Path = None,
    ):
        self._file_policy = file_policy
        self._access_control_enabled = access_control_enabled
        self._access_control_store = access_control_store
        self._legacy_permission_map = merged_legacy_permission_map(permission_map_path)

    @property
    def loader(self):
        return self._file_policy.loader

    @property
    def allow_anonymous(self) -> bool:
        return self._file_policy.allow_anonymous

    @property
    def definition_actions(self) -> Set[str]:
        return set(self._file_policy.loader.definition.actions)

    @property
    def legacy_permission_map(self) -> Dict[str, List[str]]:
        return self._legacy_permission_map

    @property
    def access_control_available(self) -> bool:
        return self._access_control_enabled and self._access_control_store is not None

    def set_access_control_store(self, access_control_store):
        self._access_control_store = access_control_store

    def disable_anonymous(self) -> None:
        self._file_policy.disable_anonymous()

    def file_roles_actions(self, user: AuthenticatedUser) -> Tuple[Set[str], Set[str]]:
        roles, actions = self._file_policy.roles_actions(user)
        return set(roles), set(actions)

    def file_rules(self, user: AuthenticatedUser) -> Set[str]:
        _, actions = self.file_roles_actions(user)
        return set(legacy_actions_to_rules(actions, self._legacy_permission_map))

    def custom_roles_actions_rules(
        self, user: AuthenticatedUser
    ) -> Tuple[Set[str], Set[str], Set[str]]:
        if user.is_anonymous() or not self.access_control_available:
            return set(), set(), set()
        try:
            result = self._access_control_store.user_permissions(user.login)
            if len(result) == 2:
                roles, actions = result
                rules = []
            else:
                roles, actions, rules = result
        except Exception as err:
            logger.warning(
                "Unable to retrieve custom roles for user %s, falling back to file policy only: %s",
                user.login,
                err,
            )
            return set(), set(), set()
        custom_rules = set(legacy_actions_to_rules(actions, self._legacy_permission_map))
        custom_rules.update(rules)
        return set(roles), set(actions), custom_rules

    def roles_actions_sources(self, user: AuthenticatedUser):
        policy_roles, policy_actions = self.file_roles_actions(user)
        policy_rules = self.file_rules(user)
        custom_roles, custom_actions, custom_rules = self.custom_roles_actions_rules(user)
        merged_roles = set(policy_roles)
        merged_roles.update(custom_roles)
        merged_actions = set(policy_actions)
        merged_actions.update(custom_actions)
        merged_rules = set(policy_rules)
        merged_rules.update(custom_rules)
        merged_actions.update(
            permission_rules_to_legacy_actions(merged_rules, self._legacy_permission_map)
        )
        return {
            "roles": merged_roles,
            "actions": merged_actions,
            "rules": merged_rules,
            "sources": {
                "policy": {
                    "roles": policy_roles,
                    "actions": policy_actions,
                    "rules": policy_rules,
                },
                "custom": {
                    "roles": custom_roles,
                    "actions": custom_actions,
                    "rules": custom_rules,
                },
                "merged": {
                    "roles": merged_roles,
                    "actions": merged_actions,
                    "rules": merged_rules,
                },
            },
        }

    def roles_actions(self, user: AuthenticatedUser) -> Tuple[Set[str], Set[str]]:
        merged = self.roles_actions_sources(user)
        return merged["roles"], merged["actions"]

    def roles_actions_rules(self, user: AuthenticatedUser):
        merged = self.roles_actions_sources(user)
        return merged["roles"], merged["actions"], merged["rules"]

    def allowed_anonymous_action(self, action: str) -> bool:
        return self._file_policy.allowed_anonymous_action(action)

    def allowed_user_action(self, user: AuthenticatedUser, action: str) -> bool:
        if user.is_anonymous():
            return self.allowed_anonymous_action(action)
        return action in self.roles_actions(user)[1]

    def allowed_user_permission(
        self,
        user: AuthenticatedUser,
        resource: str,
        operation: str,
        scope: str = "*",
    ) -> bool:
        if self.access_control_available:
            if user.is_anonymous():
                return False
            return permission_rules_allow(
                self.roles_actions_sources(user)["rules"],
                resource,
                operation,
                scope,
            )
        for action, rules in self._legacy_permission_map.items():
            if not permission_rules_allow(rules, resource, operation, scope):
                continue
            if user.is_anonymous():
                if self.allowed_anonymous_action(action):
                    return True
            elif self.allowed_user_action(user, action):
                return True
        return False

    def action_rules(self, actions: Iterable[str]) -> List[str]:
        return legacy_actions_to_rules(actions, self._legacy_permission_map)

    def normalize_rules(self, rules: Iterable[str]) -> List[str]:
        return sort_permission_rules(rules)
