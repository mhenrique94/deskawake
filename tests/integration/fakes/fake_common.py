"""Helpers compartilhados pelos fakes de integração em subprocesso."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Permite importar o contrato compartilhado sem depender do cwd do subprocesso.
TESTS_DIR = Path(__file__).resolve().parents[2]
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


def _plain(value):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class JsonlLog:
    def __init__(self, path):
        self._file = open(path, "a", encoding="utf-8") if path else None

    def write(self, **entry):
        if self._file is None:
            return
        self._file.write(json.dumps(_plain(entry), ensure_ascii=False) + "\n")
        self._file.flush()

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
