from __future__ import annotations

import json
import re
from pathlib import Path

import core

REPO_ROOT = Path(__file__).resolve().parents[2]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', text)
    assert match is not None, "versão ausente em pyproject.toml"
    return match.group(1)


def _metadata_version() -> str:
    metadata = json.loads(
        (REPO_ROOT / "plasmoid" / "metadata.json").read_text(encoding="utf-8")
    )
    return metadata["KPlugin"]["Version"]


def test_version_is_semver():
    assert isinstance(core.__version__, str)
    assert SEMVER.match(core.__version__)


def test_version_matches_pyproject():
    assert core.__version__ == _pyproject_version()


def test_version_matches_plasmoid_metadata():
    assert core.__version__ == _metadata_version()


def test_version_has_single_source_in_core_init():
    text = (REPO_ROOT / "core" / "__init__.py").read_text(encoding="utf-8")
    assert f'__version__ = "{core.__version__}"' in text
