"""system.py lit /proc directement (voir son en-tête) : sur une machine où ces fichiers
n'existent pas (macOS, ou /proc temporairement illisible), l'absence doit rester visible
comme telle — jamais un zéro qui se ferait passer pour une mesure réelle."""

import sys

import pytest

from homeport.collectors import system


def test_uptime_from_proc_returns_none_fields_when_source_is_absent(tmp_path):
    result = system._uptime_from_proc(str(tmp_path / "no-such-uptime"))

    assert result == {"seconds": None, "human": None}


def test_uptime_from_proc_parses_a_real_source_file(tmp_path):
    path = tmp_path / "uptime"
    path.write_text("172930.55 1523000.02\n")

    result = system._uptime_from_proc(str(path))

    assert result["seconds"] == 172930
    assert result["human"] is not None


def test_memory_from_proc_returns_none_fields_when_source_is_absent(tmp_path):
    result = system._memory_from_proc(str(tmp_path / "no-such-meminfo"))

    assert result == {"total_mb": None, "used_mb": None, "percent": None}


def test_memory_from_proc_parses_a_real_source_file(tmp_path):
    path = tmp_path / "meminfo"
    path.write_text("MemTotal:       16384000 kB\nMemAvailable:    8192000 kB\n")

    result = system._memory_from_proc(str(path))

    assert result == {"total_mb": 16000, "used_mb": 8000, "percent": 50.0}


def test_load_reads_getloadavg_cross_platform(monkeypatch):
    monkeypatch.setattr(system.os, "getloadavg", lambda: (1.5, 1.2, 1.0))
    monkeypatch.setattr(system.os, "cpu_count", lambda: 4)

    result = system.load()

    assert result == {"avg1": 1.5, "avg5": 1.2, "avg15": 1.0, "cores": 4, "percent": 37.5}


def test_load_returns_none_fields_when_getloadavg_unavailable(monkeypatch):
    def boom():
        raise OSError("not supported")

    monkeypatch.setattr(system.os, "getloadavg", boom)

    result = system.load()

    assert result["avg1"] is None
    assert result["avg5"] is None
    assert result["avg15"] is None
    assert result["percent"] is None
    assert result["cores"] > 0


def test_format_uptime_formats_days_hours_minutes():
    result = system._format_uptime(90000)  # 1 j 1 h 0 min

    assert result["seconds"] == 90000
    assert result["human"] is not None


def test_uptime_dispatches_to_macos_when_platform_is_darwin(monkeypatch):
    monkeypatch.setattr(system.sys, "platform", "darwin")
    monkeypatch.setattr(system, "_uptime_macos", lambda: {"seconds": 42, "human": "42 min"})

    assert system.uptime() == {"seconds": 42, "human": "42 min"}


def test_uptime_dispatches_to_proc_when_platform_is_not_darwin(monkeypatch):
    monkeypatch.setattr(system.sys, "platform", "linux")
    monkeypatch.setattr(system, "_uptime_from_proc", lambda: {"seconds": 1, "human": "1 min"})

    assert system.uptime() == {"seconds": 1, "human": "1 min"}


def test_memory_dispatches_to_macos_when_platform_is_darwin(monkeypatch):
    monkeypatch.setattr(system.sys, "platform", "darwin")
    monkeypatch.setattr(
        system, "_memory_macos", lambda: {"total_mb": 1, "used_mb": 1, "percent": 100.0}
    )

    assert system.memory() == {"total_mb": 1, "used_mb": 1, "percent": 100.0}


def test_memory_dispatches_to_proc_when_platform_is_not_darwin(monkeypatch):
    monkeypatch.setattr(system.sys, "platform", "linux")
    monkeypatch.setattr(
        system, "_memory_from_proc", lambda: {"total_mb": 2, "used_mb": 1, "percent": 50.0}
    )

    assert system.memory() == {"total_mb": 2, "used_mb": 1, "percent": 50.0}


# Sortie réelle de `sysctl -n kern.boottime` sur ce Mac (2026-08-28).
BOOTTIME_TEXT = "{ sec = 1787834574, usec = 241337 } Thu Aug 27 14:42:54 2026"


def test_boottime_seconds_parses_real_sysctl_output():
    assert system._boottime_seconds(BOOTTIME_TEXT) == 1787834574


def test_boottime_seconds_returns_none_when_unparseable():
    assert system._boottime_seconds("no sec here") is None


# Sortie réelle de `vm_stat` sur ce Mac (2026-08-28), tronquée aux champs utilisés.
VM_STAT_TEXT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                    33288.
Pages active:                                 323586.
Pages inactive:                               319213.
Pages speculative:                              3756.
Pages wired down:                             231552.
"""


def test_parse_vm_stat_extracts_page_size_and_counts():
    page_size, pages = system._parse_vm_stat(VM_STAT_TEXT)

    assert page_size == 16384
    assert pages["Pages free"] == 33288
    assert pages["Pages inactive"] == 319213


def test_parse_vm_stat_defaults_page_size_when_header_is_missing():
    page_size, pages = system._parse_vm_stat("Pages free:                1234.\n")

    assert page_size == 4096
    assert pages["Pages free"] == 1234


@pytest.mark.skipif(sys.platform != "darwin", reason="collecteur macOS uniquement")
def test_uptime_macos_returns_plausible_values_on_a_real_mac():
    result = system._uptime_macos()

    assert result["seconds"] > 0
    assert result["human"] is not None


@pytest.mark.skipif(sys.platform != "darwin", reason="collecteur macOS uniquement")
def test_memory_macos_returns_plausible_values_on_a_real_mac():
    result = system._memory_macos()

    assert result["total_mb"] > 0
    assert 0 <= result["percent"] <= 100


def test_temperature_returns_none_when_source_is_absent(tmp_path):
    assert system.temperature(str(tmp_path / "no-such-temp")) is None


def test_temperature_parses_millidegrees(tmp_path):
    path = tmp_path / "temp"
    path.write_text("48200\n")

    assert system.temperature(str(path)) == 48.2


def test_hwmon_skips_a_sensor_directory_missing_its_name_file(tmp_path):
    (tmp_path / "hwmon0").mkdir()
    (tmp_path / "hwmon1").mkdir()
    (tmp_path / "hwmon1" / "name").write_text("nvme\n")

    result = system._hwmon(str(tmp_path))

    assert result == {"nvme": tmp_path / "hwmon1"}


def test_int_from_returns_none_when_file_is_absent(tmp_path):
    assert system._int_from(tmp_path / "missing") is None


def test_int_from_parses_a_real_file(tmp_path):
    path = tmp_path / "value"
    path.write_text("1234\n")

    assert system._int_from(path) == 1234
