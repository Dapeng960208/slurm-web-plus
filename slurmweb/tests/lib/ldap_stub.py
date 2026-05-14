# Copyright (c) 2026 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import sys
import types


def ensure_ldap_stub():
    if "ldap" in sys.modules:
        return

    ldap_stub = types.ModuleType("ldap")
    ldap_stub.__path__ = []
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
    ldap_stub.SIZELIMIT_EXCEEDED = type("SIZELIMIT_EXCEEDED", (Exception,), {})
    ldap_stub.INVALID_CREDENTIALS = type("INVALID_CREDENTIALS", (Exception,), {})
    ldap_stub.UNWILLING_TO_PERFORM = type("UNWILLING_TO_PERFORM", (Exception,), {})
    ldap_stub.ldapobject = types.SimpleNamespace(LDAPObject=object)
    ldap_stub.initialize = lambda *args, **kwargs: object()

    ldap_filter_stub = types.ModuleType("ldap.filter")
    ldap_filter_stub.filter_format = lambda pattern, values: pattern % tuple(values)

    ldap_controls_stub = types.ModuleType("ldap.controls")
    ldap_controls_libldap_stub = types.ModuleType("ldap.controls.libldap")

    class _SimplePagedResultsControl:
        controlType = "1.2.840.113556.1.4.319"

        def __init__(self, criticality, size=0, cookie=b""):
            self.criticality = criticality
            self.size = size
            self.cookie = cookie

    ldap_controls_libldap_stub.SimplePagedResultsControl = _SimplePagedResultsControl

    ldap_stub.filter = ldap_filter_stub
    sys.modules["ldap"] = ldap_stub
    sys.modules["ldap.filter"] = ldap_filter_stub
    sys.modules["ldap.controls"] = ldap_controls_stub
    sys.modules["ldap.controls.libldap"] = ldap_controls_libldap_stub
