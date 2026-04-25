# Copyright (c) 2023 Rackslab
#
# This file is part of Slurm Web Plus.
#
# SPDX-License-Identifier: MIT

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata


def get_version():
    for package_name in ("slurm-web-plus", "slurm-web"):
        try:
            return metadata.version(package_name)
        except metadata.PackageNotFoundError:
            continue

    raise metadata.PackageNotFoundError("Neither slurm-web-plus nor slurm-web is installed")
