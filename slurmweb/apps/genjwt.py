# Copyright (c) 2024 Rackslab
#
# This file is part of Slurm-web.
#
# SPDX-License-Identifier: MIT

import os
import shutil
import sys
import subprocess
import logging

from . import SlurmwebAppSeed, SlurmwebGenericApp

from rfl.core.utils import shlex_join
from rfl.authentication.jwt import jwt_gen_key
from rfl.authentication.errors import JWTPrivateKeyGeneratorError

logger = logging.getLogger(__name__)

try:
    import pwd
except ImportError:
    class _PwdCompat:
        @staticmethod
        def getpwnam(_user):
            raise OSError("pwd module is not available on this platform")

    pwd = _PwdCompat()


if not hasattr(os, "geteuid"):
    os.geteuid = lambda: 1


class SlurmwebAppGenJWT(SlurmwebGenericApp):
    NAME = "slurm-web gen-jwt-key"

    def __init__(self, seed: SlurmwebAppSeed):
        super().__init__(seed)
        self.with_slurm = seed.with_slurm

    def run(self):
        logger.info("Running %s", self.NAME)

        if os.geteuid():
            logger.critical("This script must run as root")
            sys.exit(1)
        if self.settings.jwt.key.exists():
            logger.warning("JWT key %s already exist", self.settings.jwt.key)
        else:
            try:
                jwt_gen_key(self.settings.jwt.key)
            except JWTPrivateKeyGeneratorError as err:
                logger.critical("Error while generating JWT key: %s", err)
                sys.exit(1)

        self.set_user_permission("slurm-web")
        if self.with_slurm:
            self.set_user_permission("slurm", acl=True)

    def set_user_permission(self, user, acl=False):
        try:
            pwd.getpwnam(user)
        except KeyError:
            logger.warning(
                "User %s not found, unable to set permission on JWT key for this user",
                user,
            )
        except OSError as err:
            logger.warning(
                "Unable to validate user %s on this platform before setting JWT key "
                "permissions: %s",
                user,
                err,
            )
        else:
            logger.info("Setting read permission on key for %s user", user)
            if acl:
                try:
                    cmd = ["setfacl", "-m", f"u:{user}:r", self.settings.jwt.key]
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as err:
                    logger.error(
                        "Error while running command: %s: %s", shlex_join(cmd), err
                    )
            else:
                shutil.chown(self.settings.jwt.key, user=user)
