# Copyright (c) 2023 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import sys
import urllib
import logging
from types import SimpleNamespace
from datetime import datetime, timezone

from rfl.authentication.user import AuthenticatedUser
from rfl.web.tokens import RFLTokenizedRBACWebApp

try:
    from werkzeug.middleware import dispatcher
except ModuleNotFoundError:
    # In Werkzeug < 0.15, dispatcher was not in a dedicated module, it was included in a
    # big wsgi module. This old version of werkzeug must be fully supported because it
    # is included in el8. See https://github.com/rackslab/Slurm-web/issues/419 for
    # reference.
    from werkzeug import wsgi as dispatcher

from . import SlurmwebWebApp
from ..access_control import AccessControlPolicyManager
from ..version import get_version
from ..views import SlurmwebAppRoute
from ..views import agent as views
from ..slurmrestd import SlurmrestdFilteredCached
from ..slurmrestd.auth import SlurmrestdAuthentifier
from ..cache import CachingService
from ..errors import SlurmwebConfigurationError

logger = logging.getLogger(__name__)


class SlurmwebAppAgent(SlurmwebWebApp, RFLTokenizedRBACWebApp):
    NAME = "slurm-web agent"
    VIEWS = {
        SlurmwebAppRoute("/version", views.version),
        SlurmwebAppRoute("/info", views.info),
        SlurmwebAppRoute(f"/v{get_version()}/permissions", views.permissions),
        SlurmwebAppRoute(f"/v{get_version()}/ping", views.ping),
        SlurmwebAppRoute(f"/v{get_version()}/stats", views.stats),
        SlurmwebAppRoute(f"/v{get_version()}/analysis/ping", views.analysis_ping),
        SlurmwebAppRoute(f"/v{get_version()}/analysis/diag", views.analysis_diag),
        SlurmwebAppRoute(
            f"/v{get_version()}/admin/system/<path:query>",
            views.admin_system_query,
            methods=["GET", "POST"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/jobs", views.jobs),
        SlurmwebAppRoute(f"/v{get_version()}/job/<int:job>", views.job),
        SlurmwebAppRoute(
            f"/v{get_version()}/jobs/submit",
            views.job_submit,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/job/<int:job>/update",
            views.job_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/job/<int:job>/cancel",
            views.job_cancel,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/nodes", views.nodes),
        SlurmwebAppRoute(f"/v{get_version()}/node/<name>", views.node),
        SlurmwebAppRoute(
            f"/v{get_version()}/node/<name>/update",
            views.node_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/node/<name>/delete",
            views.node_delete,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/partitions", views.partitions),
        SlurmwebAppRoute(f"/v{get_version()}/qos", views.qos),
        SlurmwebAppRoute(
            f"/v{get_version()}/qos",
            views.qos_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/qos/<name>/delete",
            views.qos_delete,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/reservations", views.reservations),
        SlurmwebAppRoute(
            f"/v{get_version()}/reservation",
            views.reservation_create,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/reservation/<name>/update",
            views.reservation_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/reservation/<name>/delete",
            views.reservation_delete,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/accounts", views.accounts),
        SlurmwebAppRoute(
            f"/v{get_version()}/accounts",
            views.accounts_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/account/<name>", views.account),
        SlurmwebAppRoute(
            f"/v{get_version()}/account/<name>/delete",
            views.account_delete,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/associations", views.associations),
        SlurmwebAppRoute(
            f"/v{get_version()}/associations",
            views.associations_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/associations",
            views.associations_delete,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/users", views.users),
        SlurmwebAppRoute(
            f"/v{get_version()}/users",
            views.users_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/user/<name>", views.user),
        SlurmwebAppRoute(
            f"/v{get_version()}/user/<name>/delete",
            views.user_delete,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/wckeys", views.wckeys),
        SlurmwebAppRoute(
            f"/v{get_version()}/wckeys",
            views.wckeys_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/wckey/<wckey_id>/delete",
            views.wckey_delete,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/clusters", views.clusters_admin),
        SlurmwebAppRoute(
            f"/v{get_version()}/clusters",
            views.clusters_update,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/cluster/<name>/delete",
            views.cluster_delete,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/cache/stats", views.cache_stats),
        SlurmwebAppRoute(
            f"/v{get_version()}/cache/reset", views.cache_reset, methods=["POST"]
        ),
        SlurmwebAppRoute(f"/v{get_version()}/metrics/<metric>", views.metrics),
        SlurmwebAppRoute(f"/v{get_version()}/jobs/history", views.jobs_history),
        SlurmwebAppRoute(f"/v{get_version()}/jobs/history/<int:record_id>", views.job_history_detail),
        SlurmwebAppRoute(f"/v{get_version()}/users/cache", views.ldap_cache_users),
        SlurmwebAppRoute(f"/v{get_version()}/access/roles", views.access_roles),
        SlurmwebAppRoute(f"/v{get_version()}/access/catalog", views.access_catalog),
        SlurmwebAppRoute(
            f"/v{get_version()}/access/roles",
            views.create_access_role,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/access/roles/<int:role_id>",
            views.update_access_role,
            methods=["PATCH"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/access/roles/<int:role_id>",
            views.delete_access_role,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/access/users", views.access_users),
        SlurmwebAppRoute(
            f"/v{get_version()}/access/users/<username>/roles",
            views.access_user_roles,
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/access/users/<username>/roles",
            views.update_access_user_roles,
            methods=["PUT"],
        ),
        SlurmwebAppRoute(f"/v{get_version()}/ai/configs", views.ai_configs),
        SlurmwebAppRoute(
            f"/v{get_version()}/ai/configs",
            views.create_ai_config,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/ai/configs/<int:config_id>",
            views.update_ai_config,
            methods=["PATCH"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/ai/configs/<int:config_id>",
            views.delete_ai_config,
            methods=["DELETE"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/ai/configs/<int:config_id>/validate",
            views.validate_ai_config,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/ai/chat/stream",
            views.ai_chat_stream,
            methods=["POST"],
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/ai/conversations",
            views.ai_conversations,
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/ai/conversations/<int:conversation_id>",
            views.ai_conversation_detail,
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/user/<username>/metrics/history",
            views.user_metrics_history,
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/user/<username>/activity/summary",
            views.user_activity_summary,
        ),
        SlurmwebAppRoute(
            f"/v{get_version()}/users/cache", views.cache_authenticated_user, methods=["POST"]
        ),
        SlurmwebAppRoute(f"/v{get_version()}/node/<name>/metrics", views.node_metrics),
        SlurmwebAppRoute(
            f"/v{get_version()}/node/<name>/metrics/history", views.node_metrics_history
        ),
    }

    def __init__(self, seed):
        SlurmwebWebApp.__init__(self, seed)

        # If enabled, load RacksDB blueprint and fail with error if unable to load
        # schema or database.
        if self.settings.racksdb.enabled:
            # Lazy load RacksDB module to avoid failing on missing optional external
            # dependency when feature is actually disabled.
            from racksdb.errors import RacksDBSchemaError, RacksDBFormatError
            from racksdb.web.app import RacksDBWebBlueprint

            try:
                self.register_blueprint(
                    RacksDBWebBlueprint(
                        db=self.settings.racksdb.db,
                        ext=self.settings.racksdb.extensions,
                        schema=self.settings.racksdb.schema,
                        drawings_schema=self.settings.racksdb.drawings_schema,
                        default_drawing_parameters={
                            "infrastructure": {
                                "equipment_tags": self.settings.racksdb.tags
                            }
                        },
                    ),
                    url_prefix="/racksdb",
                )
            except RacksDBSchemaError as err:
                logger.error("Unable to load RacksDB schema: %s", err)
            except RacksDBFormatError as err:
                logger.error("Unable to load RacksDB database: %s", err)

        if self.settings.policy.roles.exists():
            logger.debug("Select RBAC site roles policy %s", self.settings.policy.roles)
            selected_roles_policy_path = self.settings.policy.roles
        else:
            logger.debug(
                "Select default RBAC vendor roles policy %s",
                self.settings.policy.vendor_roles,
            )
            selected_roles_policy_path = self.settings.policy.vendor_roles
        RFLTokenizedRBACWebApp.__init__(
            self,
            audience=self.settings.jwt.audience,
            algorithm=self.settings.jwt.algorithm,
            key=self.settings.jwt.key,
            policy=self.settings.policy.definition,
            roles=selected_roles_policy_path,
        )
        self.policy = AccessControlPolicyManager(
            self.policy,
            permission_map_path=getattr(self.settings.policy, "permission_map", None),
        )
        if self.settings.cache.enabled:
            self.cache = CachingService(
                host=self.settings.cache.host,
                port=self.settings.cache.port,
                password=self.settings.cache.password,
            )
        else:
            logger.warning("Caching is disabled")
            self.cache = None

        if self.settings.slurmrestd.socket:
            logger.warning(
                "Using deprecated parameter [slurmrestd]>socket to define "
                "[slurmrest]>uri, update your site agent configuration file"
            )
            socket_path = str(self.settings.slurmrestd.socket).replace("\\", "/")
            if not socket_path.startswith("/"):
                socket_path = f"/{socket_path}"
            self.settings.slurmrestd.uri = urllib.parse.urlparse(
                f"unix://{socket_path}"
            )

        # Warn deprecated local authentication method to slurmrestd
        if self.settings.slurmrestd.auth == "local":
            logger.warning(
                "Using deprecated slurmrestd local authentication method, it is "
                "recommended to migrate to jwt authentication"
            )

        # Warn deprecated slurmrestd version parameter
        if self.settings.slurmrestd.version:
            logger.warning(
                "Deprecated parameter [slurmrestd]>version is defined but ignored. "
                "Use [slurmrestd]>versions instead to specify a list of supported "
                "slurmrestd API versions."
            )

        try:
            self.slurmrestd = SlurmrestdFilteredCached(
                self.settings.slurmrestd.uri,
                SlurmrestdAuthentifier(
                    self.settings.slurmrestd.auth,
                    self.settings.slurmrestd.jwt_mode,
                    self.settings.slurmrestd.jwt_user,
                    self.settings.slurmrestd.jwt_key,
                    self.settings.slurmrestd.jwt_lifespan,
                    self.settings.slurmrestd.jwt_token,
                ),
                self.settings.slurmrestd.versions,
                self.settings.filters,
                self.settings.cache,
                self.cache,
                cluster_name_hint=self.settings.service.cluster,
            )
        except SlurmwebConfigurationError as err:
            logger.critical("Configuration error: %s", err)
            sys.exit(1)

        # Default RacksDB infrastructure is the cluster name.
        if self.settings.racksdb.infrastructure is None:
            self.settings.racksdb.infrastructure = self.settings.service.cluster

        self.metrics_collector = None
        self.metrics_db = None
        if self.settings.metrics.enabled:
            # Lazy load metrics module to avoid failing on missing optional external
            # dependency when feature is actually disabled.
            from ..metrics.collector import SlurmWebMetricsCollector, make_wsgi_app
            from ..metrics.db import SlurmwebMetricsDB

            self.metrics_collector = SlurmWebMetricsCollector(
                self.slurmrestd,
                self.cache,
            )
            self.wsgi_app = dispatcher.DispatcherMiddleware(
                self.wsgi_app, {"/metrics": make_wsgi_app(self.settings.metrics)}
            )
            self.metrics_db = SlurmwebMetricsDB(
                self.settings.metrics.host, self.settings.metrics.job
            )

        self.users_store = None
        self.jobs_store = None
        self.user_analytics_store = None
        self.user_metrics_store = None
        self.user_metrics_enabled = False
        self.access_control_store = None
        self.access_control_enabled = False
        self.ai_config_store = None
        self.ai_conversation_store = None
        self.ai_service = None
        self.ai_enabled = False
        database_ready = False
        database_error = None
        if self.settings.database.enabled:
            try:
                from ..persistence.users_store import UsersStore

                self.users_store = UsersStore(self.settings.database)
                self.users_store.validate_connection()
                database_ready = True
                logger.info("Database support enabled")
            except Exception as err:
                self.users_store = None
                database_error = err
                logger.warning("Unable to initialize database support: %s", err)
        else:
            database_error = RuntimeError("[database] enabled = no")
            logger.debug("Database support is disabled")

        if database_ready:
            try:
                from ..persistence.access_control_store import AccessControlStore

                self.access_control_store = AccessControlStore(
                    self.settings.database,
                    legacy_permission_map=self.policy.legacy_permission_map,
                )
                self.access_control_store.validate_connection()
                self.access_control_store.normalize_legacy_role_actions()
                self.access_control_store.seed_default_roles()
                self.access_control_enabled = True
                logger.info("Access control support enabled")
            except Exception as err:
                logger.warning("Unable to initialize access control support: %s", err)
        else:
            logger.debug("Access control is disabled")

        self.policy._access_control_enabled = self.access_control_enabled
        self.policy.set_access_control_store(self.access_control_store)
        self._refresh_cached_policy_snapshots_on_startup()

        if database_ready:
            try:
                from ..persistence.jobs_store import JobsStore

                store_settings = SimpleNamespace(
                    host=self.settings.database.host,
                    port=self.settings.database.port,
                    database=self.settings.database.database,
                    user=self.settings.database.user,
                    password=self.settings.database.password,
                    snapshot_interval=self.settings.persistence.snapshot_interval,
                    retention_days=self.settings.persistence.retention_days,
                )
                self.jobs_store = JobsStore(store_settings, self.slurmrestd)
                self.jobs_store.start()
                logger.info("Job history persistence enabled")
            except Exception as err:
                logger.warning("Unable to initialize job history persistence: %s", err)
        else:
            logger.debug("Job history persistence is disabled")

        user_metrics_settings = getattr(self.settings, "user_metrics", None)
        if user_metrics_settings and database_ready and self.settings.metrics.enabled and self.jobs_store is not None:
            try:
                from ..persistence.user_analytics_store import UserAnalyticsStore

                store_settings = SimpleNamespace(
                    host=self.settings.database.host,
                    port=self.settings.database.port,
                    database=self.settings.database.database,
                    user=self.settings.database.user,
                    password=self.settings.database.password,
                    aggregation_interval=self.settings.user_metrics.aggregation_interval,
                    tool_mapping_file=self.settings.user_metrics.tool_mapping_file,
                )
                self.user_analytics_store = UserAnalyticsStore(
                    store_settings, users_store=self.users_store
                )
                self.user_analytics_store.start()
                self.user_metrics_store = self.user_analytics_store
                self.user_metrics_enabled = True
                logger.info("User metrics persistence enabled")
            except Exception as err:
                logger.warning("Unable to initialize user metrics persistence: %s", err)
        else:
            logger.debug("User metrics is disabled")

        if self.metrics_collector is not None:
            self.metrics_collector.user_analytics_store = self.user_analytics_store
            self.metrics_collector.user_metrics_store = self.user_metrics_store
            self.metrics_collector.user_metrics_enabled = bool(
                self.user_metrics_enabled
            )

        # Initialize node real-time metrics (new, optional)
        self.node_metrics_db = None
        node_metrics_host = getattr(self.settings.node_metrics, "prometheus_host", None)
        if node_metrics_host:
            from ..metrics.db import SlurmwebMetricsDB as _MetricsDB

            self.node_metrics_db = _MetricsDB(
                node_metrics_host,
                self.settings.node_metrics.node_exporter_job,
            )
            logger.info("Node real-time metrics enabled")
        else:
            logger.debug("Node real-time metrics is disabled")

        if database_ready:
            try:
                from ..ai.crypto import AISecretCipher
                from ..ai.service import AIService
                from ..persistence.ai_conversation_store import AIConversationStore
                from ..persistence.ai_model_config_store import AIModelConfigStore

                secret_cipher = AISecretCipher.from_jwt_key_file(self.settings.jwt.key)
                self.ai_config_store = AIModelConfigStore(self.settings.database)
                self.ai_conversation_store = AIConversationStore(self.settings.database)
                self.ai_config_store.validate_connection()
                self.ai_conversation_store.validate_connection()
                self.ai_service = AIService(
                    app=self,
                    config_store=self.ai_config_store,
                    conversation_store=self.ai_conversation_store,
                    secret_cipher=secret_cipher,
                )
                self.ai_enabled = True
                logger.info("AI assistant support enabled")
            except Exception as err:
                logger.warning("Unable to initialize AI assistant support: %s", err)
        else:
            logger.debug("AI assistant is disabled")

    def _refresh_cached_policy_snapshots_on_startup(self):
        if not self.access_control_enabled:
            return
        if self.users_store is None:
            return

        try:
            cached_users = self.users_store.list_cached_users_for_policy_refresh()
        except Exception as err:
            logger.warning(
                "Unable to load cached users for startup policy snapshot refresh: %s",
                err,
            )
            return

        logger.info(
            "Refreshing policy snapshots for %d cached users on startup",
            len(cached_users),
        )
        refreshed = 0
        failed = 0
        for cached_user in cached_users:
            try:
                user = AuthenticatedUser(
                    login=cached_user["username"],
                    fullname=cached_user.get("fullname"),
                    groups=cached_user.get("groups") or [],
                )
                policy_roles, policy_actions = self.policy.file_roles_actions(user)
                self.users_store.update_policy_snapshot(
                    cached_user["username"],
                    sorted(policy_roles),
                    sorted(policy_actions),
                )
                refreshed += 1
            except Exception as err:
                failed += 1
                logger.warning(
                    "Unable to refresh startup policy snapshot for cached user %s: %s",
                    cached_user.get("username"),
                    err,
                )

        logger.info(
            "Startup policy snapshot refresh completed: scanned=%d refreshed=%d failed=%d",
            len(cached_users),
            refreshed,
            failed,
        )

    @staticmethod
    def now():
        return datetime.now(timezone.utc)
