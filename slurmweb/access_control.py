# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import logging
from typing import Set, Tuple

from rfl.authentication.user import AuthenticatedUser


logger = logging.getLogger(__name__)


class AccessControlPolicyManager:
    """Wrap the file-backed RBAC policy and merge DB-backed custom roles."""

    def __init__(
        self,
        file_policy,
        access_control_enabled: bool = False,
        access_control_store=None,
    ):
        self._file_policy = file_policy
        self._access_control_enabled = access_control_enabled
        self._access_control_store = access_control_store

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
    def access_control_available(self) -> bool:
        return self._access_control_enabled and self._access_control_store is not None

    def set_access_control_store(self, access_control_store):
        self._access_control_store = access_control_store

    def disable_anonymous(self) -> None:
        self._file_policy.disable_anonymous()

    def file_roles_actions(self, user: AuthenticatedUser) -> Tuple[Set[str], Set[str]]:
        roles, actions = self._file_policy.roles_actions(user)
        return set(roles), set(actions)

    def custom_roles_actions(self, user: AuthenticatedUser) -> Tuple[Set[str], Set[str]]:
        if user.is_anonymous() or not self.access_control_available:
            return set(), set()
        try:
            roles, actions = self._access_control_store.user_permissions(user.login)
        except Exception as err:
            logger.warning(
                "Unable to retrieve custom roles for user %s, falling back to file policy only: %s",
                user.login,
                err,
            )
            return set(), set()
        return set(roles), set(actions)

    def roles_actions_sources(self, user: AuthenticatedUser):
        policy_roles, policy_actions = self.file_roles_actions(user)
        custom_roles, custom_actions = self.custom_roles_actions(user)
        merged_roles = set(policy_roles)
        merged_roles.update(custom_roles)
        merged_actions = set(policy_actions)
        merged_actions.update(custom_actions)
        return {
            "roles": merged_roles,
            "actions": merged_actions,
            "sources": {
                "policy": {
                    "roles": policy_roles,
                    "actions": policy_actions,
                },
                "custom": {
                    "roles": custom_roles,
                    "actions": custom_actions,
                },
            },
        }

    def roles_actions(self, user: AuthenticatedUser) -> Tuple[Set[str], Set[str]]:
        merged = self.roles_actions_sources(user)
        return merged["roles"], merged["actions"]

    def allowed_anonymous_action(self, action: str) -> bool:
        return self._file_policy.allowed_anonymous_action(action)

    def allowed_user_action(self, user: AuthenticatedUser, action: str) -> bool:
        if user.is_anonymous():
            return self.allowed_anonymous_action(action)
        return action in self.roles_actions(user)[1]
