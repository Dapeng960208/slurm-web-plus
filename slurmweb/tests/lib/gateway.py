# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import typing as t
import unittest
import tempfile
import os
import time
import sys
import types

import werkzeug
import jinja2

from rfl.authentication.user import AuthenticatedUser, AnonymousUser

# The gateway app imports LDAP support unconditionally, while the test
# environment may not have python-ldap installed. Provide a minimal stub so
# gateway-only tests can still import the module graph.
if "ldap" not in sys.modules:
    ldap_stub = types.ModuleType("ldap")
    ldap_stub.VERSION3 = 3
    ldap_stub.OPT_X_TLS_REQUIRE_CERT = 0
    ldap_stub.OPT_X_TLS_DEMAND = 0
    ldap_stub.OPT_X_TLS_CACERTDIR = 0
    ldap_stub.OPT_X_TLS_CACERTFILE = 0
    ldap_stub.OPT_X_TLS_NEWCTX = 0
    ldap_stub.SCOPE_BASE = 0
    ldap_stub.SCOPE_SUBTREE = 1
    ldap_stub.CONNECT_ERROR = type("CONNECT_ERROR", (Exception,), {})
    ldap_stub.SERVER_DOWN = type("SERVER_DOWN", (Exception,), {})
    ldap_stub.NO_SUCH_OBJECT = type("NO_SUCH_OBJECT", (Exception,), {})
    ldap_stub.OPERATIONS_ERROR = type("OPERATIONS_ERROR", (Exception,), {})
    ldap_stub.INVALID_CREDENTIALS = type("INVALID_CREDENTIALS", (Exception,), {})
    ldap_stub.UNWILLING_TO_PERFORM = type("UNWILLING_TO_PERFORM", (Exception,), {})
    ldap_stub.ldapobject = types.SimpleNamespace(LDAPObject=object)
    ldap_stub.initialize = lambda *args, **kwargs: object()
    sys.modules["ldap"] = ldap_stub

from slurmweb.version import get_version
from slurmweb.apps import SlurmwebAppSeed
from slurmweb.apps.gateway import SlurmwebAppGateway
from slurmweb.apps.gateway import SlurmwebAgent, SlurmwebAgentRacksDBSettings
from slurmweb.views.agent import racksdb_get_version

from .utils import SlurmwebCustomTestResponse


CONF_TPL = """
[agents]
url=http://localhost
{% if agents_extra %}
{% for key, value in agents_extra.items() %}
{{ key }}={{ value }}
{% endfor %}
{% endif %}

[jwt]
key={{ key }}

[ui]
{% if ui_enabled is defined and ui_enabled %}
enabled=yes
{% if ui_host is defined %}host={{ ui_host }}{% endif %}
{% if ui_path is defined %}path={{ ui_path }}{% endif %}
{% else %}
enabled=no
{% endif %}

{% if ldap %}
[authentication]
enabled=yes

[ldap]
uri=ldap://localhost
user_base=ou=people,dc=example,dc=org
group_base=ou=groups,dc=example,dc=org
{% endif %}
"""


def fake_slurmweb_agent(cluster: str):
    return SlurmwebAgent(
        get_version(),
        cluster,
        SlurmwebAgentRacksDBSettings(
            enabled=True, version=racksdb_get_version(), infrastructure=cluster
        ),
        metrics=True,
        cache=True,
        database=True,
        url=f"http://{cluster}",
        user_metrics=False,
        ai={
            "enabled": False,
            "configurable": False,
            "streaming": False,
            "persistence": False,
            "available_models_count": 0,
            "default_model_id": None,
            "providers": [],
            "tool_mode": "mixed",
        },
        capabilities={
            "job_history": True,
            "ldap_cache": True,
            "access_control": False,
            "node_metrics": False,
            "ai": {
                "enabled": False,
                "configurable": False,
                "streaming": False,
                "persistence": False,
                "available_models_count": 0,
                "default_model_id": None,
                "providers": [],
                "tool_mode": "mixed",
            },
        },
        persistence=False,
        access_control=False,
        node_metrics=False,
    )


class TestGatewayConfBase(unittest.TestCase):
    def setup_gateway_conf(self, **template_overrides):
        # Generate JWT signing key
        self.key = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        self.key.write("hey")
        self.key.flush()
        self.key.close()

        self.vendor_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "conf", "vendor"
        )

        # Generate configuration file
        self.conf = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        conf_template = jinja2.Template(CONF_TPL)
        template_vars = {"key": self.key.name}
        template_vars.update(template_overrides)
        self.conf.write(conf_template.render(**template_vars))
        self.conf.flush()
        self.conf.close()

        # Configuration definition path
        self.conf_defs = os.path.join(self.vendor_path, "gateway.yml")


class TestGatewayBase(TestGatewayConfBase):
    def setup_app(
        self,
        anonymous_user=False,
        use_token=True,
        conf_overrides=None,
    ):
        self.setup_gateway_conf(**(conf_overrides or {}))

        self.app = SlurmwebAppGateway(
            SlurmwebAppSeed.with_parameters(
                debug=False,
                log_flags=["ALL"],
                log_component=None,
                debug_flags=[],
                conf_defs=self.conf_defs,
                conf=self.conf.name,
            )
        )

        # Close conf and key file handlers to remove temporary files
        try:
            os.unlink(self.conf.name)
        except FileNotFoundError:
            pass
        try:
            os.unlink(self.key.name)
        except FileNotFoundError:
            pass
        self.app.config.update(
            {
                "TESTING": True,
            }
        )

        # Get token valid to get user role with all permissions as defined in
        # default policy.
        if anonymous_user:
            self.user = AnonymousUser()
        else:
            self.user = AuthenticatedUser(
                login="test", fullname="Testing User", groups=["group"]
            )

        # werkzeug.test.TestResponse class does not have text and json
        # properties in werkzeug <= 0.15. When such version is installed, use
        # custom test response class to backport these text and json properties.
        try:
            getattr(werkzeug.test.TestResponse, "text")
            getattr(werkzeug.test.TestResponse, "json")
        except AttributeError:
            self.app.response_class = SlurmwebCustomTestResponse

        self.client = self.app.test_client()
        if use_token:
            token = self.app.jwt.generate(
                user=self.user,
                duration=3600,
            )
            self.client.environ_base["HTTP_AUTHORIZATION"] = "Bearer " + token

    def app_set_agents(self, agents: t.Dict[str, SlurmwebAgent]):
        """Set gateway application _agents attribute with timeout in future to
        avoid application sending GET requests to retrieve /info."""
        self.app._agents = agents
        self.app._agents_timeout = int(time.time()) + 300
