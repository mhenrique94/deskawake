import json
from pathlib import Path

import pytest

import core.config


def _config_path(monkeypatch, tmp_path: Path) -> Path:
    path = tmp_path / "deskawake" / "config.json"
    monkeypatch.setattr(core.config, "CONFIG_PATH", path)
    return path


def test_load_missing_returns_defaults_without_creating_file(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)

    assert core.config.load_config() == {"version": 1, "theme": "auto"}
    assert not path.exists()
    assert not path.parent.exists()


def test_save_load_roundtrip(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)
    config = {"version": 1, "theme": "dark", "position": {"x": 10, "y": 20}}

    core.config.save_config(config)

    assert path.is_file()
    assert core.config.load_config() == config


def test_save_leaves_no_tmp(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)

    core.config.save_config({"version": 1, "theme": "auto"})

    assert path.is_file()
    assert list(path.parent.glob("*.tmp")) == []


def test_save_config_whitelists_keys(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)

    core.config.save_config({"theme": "dark", "active": True, "extra": {"a": 1}})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"version", "theme"}

    core.config.save_config(
        {"theme": "dark", "position": {"x": 1, "y": 2, "z": 3}, "active": False}
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"version", "theme", "position"}
    assert data["position"] == {"x": 1, "y": 2}


def test_save_config_normalizes_invalid_theme(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)

    core.config.save_config({"theme": "blue", "position": {"x": 10, "y": 20}})

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["theme"] == "auto"
    assert data["position"] == {"x": 10, "y": 20}


def test_save_config_accepts_position_tuple(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)

    core.config.save_config({"theme": "light", "position": (10, 20)})

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["position"] == {"x": 10, "y": 20}


def test_save_failure_removes_tmp(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)

    def failing_replace(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(core.config.os, "replace", failing_replace)

    with pytest.raises(OSError):
        core.config.save_config({"version": 1, "theme": "auto"})

    assert list(path.parent.glob("*.tmp")) == []


def test_corrupt_json_quarantines_and_recovers(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)
    path.parent.mkdir(parents=True)
    original = "{oops"
    path.write_text(original, encoding="utf-8")

    assert core.config.load_config() == {"version": 1, "theme": "auto"}

    bak = path.with_name("config.json.bak")
    assert bak.read_text(encoding="utf-8") == original
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "theme": "auto",
    }


def test_invalid_theme_quarantines(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"version": 1, "theme": "blue"}', encoding="utf-8")

    assert core.config.load_config() == {"version": 1, "theme": "auto"}

    assert path.with_name("config.json.bak").is_file()
    assert json.loads(path.read_text(encoding="utf-8"))["theme"] == "auto"


@pytest.mark.parametrize("root", [[], "x"])
def test_non_dict_root_quarantines(monkeypatch, tmp_path, root):
    path = _config_path(monkeypatch, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(root), encoding="utf-8")

    assert core.config.load_config() == {"version": 1, "theme": "auto"}

    assert path.with_name("config.json.bak").is_file()


def test_unknown_version_quarantines(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"version": 2, "theme": "auto"}', encoding="utf-8")

    assert core.config.load_config() == {"version": 1, "theme": "auto"}

    assert path.with_name("config.json.bak").is_file()


@pytest.mark.parametrize("data", [{"version": 1}, {"theme": "auto"}, {}])
def test_missing_theme_or_version_quarantines(monkeypatch, tmp_path, data):
    path = _config_path(monkeypatch, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data), encoding="utf-8")

    assert core.config.load_config() == {"version": 1, "theme": "auto"}

    assert path.with_name("config.json.bak").is_file()


def test_read_oserror_returns_defaults_without_bak(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)
    path.mkdir(parents=True)

    assert core.config.load_config() == {"version": 1, "theme": "auto"}

    assert not path.with_name("config.json.bak").exists()
    assert path.is_dir()


@pytest.mark.parametrize(
    "position",
    ["oops", [10, 20], {"x": "10", "y": 20}, {"x": 10}, {"x": True, "y": 20}],
)
def test_malformed_position_is_dropped_without_bak(monkeypatch, tmp_path, position):
    path = _config_path(monkeypatch, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"version": 1, "theme": "dark", "position": position}),
        encoding="utf-8",
    )

    assert core.config.load_config() == {"version": 1, "theme": "dark"}

    assert not path.with_name("config.json.bak").exists()
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "version": 1,
        "theme": "dark",
    }


def test_extra_keys_are_dropped_without_bak(monkeypatch, tmp_path):
    path = _config_path(monkeypatch, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "theme": "dark",
                "position": {"x": 10, "y": 20, "z": 5},
                "active": True,
            }
        ),
        encoding="utf-8",
    )

    expected = {"version": 1, "theme": "dark", "position": {"x": 10, "y": 20}}
    assert core.config.load_config() == expected

    assert not path.with_name("config.json.bak").exists()
    assert json.loads(path.read_text(encoding="utf-8")) == expected


def test_default_position_primary_monitor():
    assert core.config.default_position([(0, 0, 1920, 1050)]) == (1772, 24)


def test_default_position_empty_workareas():
    assert core.config.default_position([]) == (24, 24)


def test_default_position_narrow_workarea():
    assert core.config.default_position([(0, 0, 100, 100)]) == (24, 24)


def test_validate_position_inside_keeps():
    assert core.config.validate_position((100, 100), [(0, 0, 1920, 1050)]) == (
        100,
        100,
    )


def test_validate_position_outside_falls_back():
    assert core.config.validate_position((5000, 5000), [(0, 0, 1920, 1050)]) == (
        1772,
        24,
    )


def test_validate_position_accepts_secondary_monitor():
    workareas = [(0, 0, 1920, 1080), (-1280, 0, 1280, 1024)]

    assert core.config.validate_position((-100, 50), workareas) == (-100, 50)


def test_validate_position_accepts_position_mapping():
    assert core.config.validate_position({"x": 100, "y": 100}, [(0, 0, 1920, 1050)]) == (
        100,
        100,
    )


@pytest.mark.parametrize(
    "position",
    [None, "100,100", (100,), {"x": "100", "y": 100}, {"x": True, "y": 100}],
)
def test_validate_position_invalid_input_falls_back(position):
    assert core.config.validate_position(position, [(0, 0, 1920, 1050)]) == (
        1772,
        24,
    )


def test_validate_position_boundary_is_half_open():
    workareas = [(0, 0, 1920, 1050)]

    assert core.config.validate_position((1919, 1049), workareas) == (1919, 1049)
    assert core.config.validate_position((1920, 1049), workareas) == (1772, 24)
    assert core.config.validate_position((1919, 1050), workareas) == (1772, 24)
