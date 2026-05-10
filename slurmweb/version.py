# Copyright (c) 2023 Rackslab
#
# This file is part of Slurm Web Plus.
#
# SPDX-License-Identifier: MIT

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata

import re
from pathlib import Path


def _workspace_version():
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None

    match = re.search(
        r'(?ms)^\[project\]\s.*?^version\s*=\s*"([^"]+)"',
        content,
    )
    return match.group(1) if match else None


def get_version():
    for package_name in ("slurm-web-plus", "slurm-web"):
        try:
            return metadata.version(package_name)
        except metadata.PackageNotFoundError:
            continue

    workspace_version = _workspace_version()
    if workspace_version is not None:
        return workspace_version

    raise metadata.PackageNotFoundError("Neither slurm-web-plus nor slurm-web is installed")
