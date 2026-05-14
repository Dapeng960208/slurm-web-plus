"""Extensions for upstream RFL LDAP authentifier."""

from typing import Iterable, List, Optional, Sequence
from pathlib import Path
import logging

import ldap

from rfl.authentication.ldap import LDAPAuthentifier
from rfl.authentication.user import AuthenticatedUser
from rfl.authentication.errors import LDAPAuthenticationError


logger = logging.getLogger(__name__)


try:
    from ldap.controls.libldap import SimplePagedResultsControl
except Exception:  # pragma: no cover
    SimplePagedResultsControl = None


def _as_bases(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [base for base in value if base]
    return [value]


def _iter_user_bases(self) -> Iterable[str]:
    bases = getattr(self, "_slurmweb_user_bases", None)
    if bases:
        return bases
    return [self.user_base]


def _iter_group_bases(self) -> Iterable[str]:
    bases = getattr(self, "_slurmweb_group_bases", None)
    if bases:
        return bases
    return [self.group_base]


def _patched_init(
    self,
    uri,
    user_base,
    group_base,
    user_class: str = "posixAccount",
    user_name_attribute: str = "uid",
    user_fullname_attribute: str = "cn",
    user_primary_group_attribute: str = "gidNumber",
    group_name_attribute: str = "cn",
    group_object_classes: Optional[List[str]] = None,
    cacert: Optional[Path] = None,
    starttls: bool = False,
    bind_dn: Optional[str] = None,
    bind_password: Optional[str] = None,
    restricted_groups: Optional[List[str]] = None,
    lookup_user_dn: bool = False,
    lookup_as_user: Optional[bool] = True,
):
    self._slurmweb_user_bases = _as_bases(user_base)
    self._slurmweb_group_bases = _as_bases(group_base)
    LDAPAuthentifier._slurmweb_original_init(
        self,
        uri=uri,
        user_base=self._slurmweb_user_bases[0] if self._slurmweb_user_bases else user_base,
        group_base=self._slurmweb_group_bases[0] if self._slurmweb_group_bases else group_base,
        user_class=user_class,
        user_name_attribute=user_name_attribute,
        user_fullname_attribute=user_fullname_attribute,
        user_primary_group_attribute=user_primary_group_attribute,
        group_name_attribute=group_name_attribute,
        group_object_classes=group_object_classes,
        cacert=cacert,
        starttls=starttls,
        bind_dn=bind_dn,
        bind_password=bind_password,
        restricted_groups=restricted_groups,
        lookup_user_dn=lookup_user_dn,
        lookup_as_user=lookup_as_user,
    )


def _patched_get_groups(self, connection, user_name: str, user_dn: str, gid: Optional[int]):
    object_class_filter = "".join(
        [f"(objectClass={object_class})" for object_class in self.group_object_classes]
    )
    gid_filter = f"(gidNumber={gid})" if gid is not None else ""
    search_filter = (
        "(&"
        f"(|{object_class_filter})"
        f"(|(memberUid={user_name})(member={user_dn}){gid_filter}))"
    )
    groups = []
    found_any_base = False
    for group_base in _iter_group_bases(self):
        try:
            results = connection.search_s(
                group_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                [self.group_name_attribute],
            )
        except ldap.NO_SUCH_OBJECT:
            continue
        found_any_base = True
        logger.debug(
            "LDAP search base: %s, scope: subtree, filter: %s, results: %s",
            group_base,
            search_filter,
            str(results),
        )
        try:
            groups.extend(
                [result[1][self.group_name_attribute][0].decode() for result in results]
            )
        except KeyError as err:
            raise LDAPAuthenticationError(
                f"Unable to extract group name with {self.group_name_attribute} "
                "attribute from group entries"
            ) from err
    if not found_any_base:
        raise LDAPAuthenticationError(
            f"Unable to find any configured group base {list(_iter_group_bases(self))}"
        )
    if not groups:
        logger.warning(
            "Unable to find groups in LDAP for user %s%s",
            user_name,
            f" or gidNumber {gid}" if gid is not None else "",
        )
        return []
    return sorted(set(groups))


def _patched_lookup_user_dn(self, user):
    if not self.lookup_user_dn:
        return f"{self.user_name_attribute}={user},{self.user_base}"

    search_filter = f"(&(objectClass={self.user_class})({self.user_name_attribute}={user}))"
    matches = []

    for user_base in _iter_user_bases(self):
        connection = self.connection()
        try:
            self._bind(connection)
            results = connection.search_s(
                user_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                [self.user_name_attribute],
            )
        except ldap.SERVER_DOWN as err:
            raise LDAPAuthenticationError(
                f"LDAP server {self.uri.geturl()} is unreachable"
            ) from err
        except ldap.NO_SUCH_OBJECT:
            continue
        except ldap.OPERATIONS_ERROR as err:
            raise LDAPAuthenticationError(
                f"Operations error on user DN lookup: {err}"
            ) from err
        finally:
            connection.unbind_s()
        logger.debug(
            "LDAP search base: %s, scope: subtree, filter: %s, results: %s",
            user_base,
            search_filter,
            str(results),
        )
        matches.extend(results)

    if not matches:
        raise LDAPAuthenticationError(
            f"Unable to find user {user} in bases {list(_iter_user_bases(self))}"
        )
    dns = list(dict.fromkeys(result[0] for result in matches))
    if len(dns) > 1:
        raise LDAPAuthenticationError(
            f"Too many users found ({len(dns)}) with username {user} in bases "
            f"{list(_iter_user_bases(self))}"
        )
    return dns[0]


def _paged_search(self, connection, base: str, search_filter: str, attributes: Sequence[str], page_size: int):
    if SimplePagedResultsControl is None:
        return connection.search_s(base, ldap.SCOPE_SUBTREE, search_filter, list(attributes))

    results = []
    page_control = SimplePagedResultsControl(True, size=page_size, cookie=b"")
    while True:
        msgid = connection.search_ext(
            base,
            ldap.SCOPE_SUBTREE,
            search_filter,
            list(attributes),
            serverctrls=[page_control],
        )
        _rtype, rdata, rmsgid, serverctrls = connection.result3(msgid)
        if rmsgid != msgid:
            raise LDAPAuthenticationError("Unexpected LDAP paged search response")
        results.extend(rdata)
        cookie = b""
        for serverctrl in serverctrls:
            if getattr(serverctrl, "controlType", None) == page_control.controlType:
                cookie = serverctrl.cookie
                break
        if not cookie:
            break
        page_control.cookie = cookie
    return results


def _patched_list_user_dn(self, connection):
    search_filter = f"(objectClass={self.user_class})"
    picked = []
    user_name_attribute_found = False
    found_any_base = False

    for user_base in _iter_user_bases(self):
        try:
            results = _paged_search(
                self,
                connection,
                user_base,
                search_filter,
                [self.user_name_attribute],
                500,
            )
        except ldap.NO_SUCH_OBJECT:
            continue
        except ldap.OPERATIONS_ERROR as err:
            raise LDAPAuthenticationError(f"Operations error on users search: {err}") from err
        except ldap.SIZELIMIT_EXCEEDED as err:
            raise LDAPAuthenticationError(
                f"Users search exceeded directory size limit in base {user_base}: {err}"
            ) from err
        found_any_base = True
        logger.debug(
            "LDAP search base: %s, scope: subtree, filter: %s, results: %s",
            user_base,
            search_filter,
            str(results),
        )
        for result in results:
            if self.user_name_attribute not in result[1]:
                logger.warning(
                    "Unable to find %s from user entry %s",
                    self.user_name_attribute,
                    result[0],
                )
                continue
            user_name_attribute_found = True
            picked.append((result[1][self.user_name_attribute][0].decode(), result[0]))

    if not found_any_base:
        raise LDAPAuthenticationError(
            f"Unable to find any configured user base {list(_iter_user_bases(self))}"
        )
    if not picked:
        logger.warning("Unable to find users in LDAP in bases %s", list(_iter_user_bases(self)))
        return []
    if not user_name_attribute_found:
        raise LDAPAuthenticationError(
            f"Unable to extract user {self.user_name_attribute} from user entries"
        )
    dedup = {}
    for username, dn in picked:
        dedup[(username, dn)] = None
    return list(dedup.keys())


def _patched_users(self, with_groups: bool = False) -> List[AuthenticatedUser]:
    result = []
    connection = self.connection()
    self._bind(connection)

    try:
        for user, user_dn in self._list_user_dn(connection):
            fullname, gid = self._get_user_info(connection, user_dn)
            groups = []
            if with_groups:
                groups = self._get_groups(connection, user, user_dn, gid)
                if not self._in_restricted_groups(groups):
                    logger.debug("Discarding user %s not member of restricted groups", user)
                    continue
            result.append(AuthenticatedUser(login=user, fullname=fullname, groups=groups))
    except ldap.SERVER_DOWN as err:
        raise LDAPAuthenticationError(f"LDAP server {self.uri.geturl()} is unreachable") from err
    except ldap.UNWILLING_TO_PERFORM as err:
        raise LDAPAuthenticationError(
            f"LDAP server is unwilling to perform: {str(err)}"
        ) from err
    finally:
        connection.unbind_s()
    return result


def patch_ldap_authentifier():
    if getattr(LDAPAuthentifier, "_slurmweb_patched", False):
        return
    LDAPAuthentifier._slurmweb_original_init = LDAPAuthentifier.__init__
    LDAPAuthentifier.__init__ = _patched_init
    LDAPAuthentifier._get_groups = _patched_get_groups
    LDAPAuthentifier._lookup_user_dn = _patched_lookup_user_dn
    LDAPAuthentifier._list_user_dn = _patched_list_user_dn
    LDAPAuthentifier.users = _patched_users
    LDAPAuthentifier._slurmweb_patched = True
