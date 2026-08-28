"""Sortie réelle de `sudo powermetrics -i1 -n1 --samplers thermal` sur ce Mac (Mac17,3,
macOS 26, 2026-08-28) : pas de température en °C ni de RPM sur cette machine — seulement un
niveau qualitatif. Vérifié en root avant d'écrire ce module, `--samplers smc` n'existe pas ici."""

from homeport.collectors import thermal_pressure

REAL_SAMPLE = """Machine model: Mac17,3
OS version: 26A5421a
Boot arguments:
Boot time: Thu Aug 27 14:42:54 2026



*** Sampled system activity (Fri Aug 28 17:59:48 2026 +0200) (1.20ms elapsed) ***



**** Thermal pressure ****

Current pressure level: Moderate
"""


def test_parse_thermal_pressure_extracts_the_level():
    assert thermal_pressure.parse_thermal_pressure(REAL_SAMPLE) == "moderate"


def test_parse_thermal_pressure_returns_none_when_section_is_absent():
    assert thermal_pressure.parse_thermal_pressure("no such section here") is None


def test_parse_thermal_pressure_returns_none_for_an_unknown_level():
    text = "**** Thermal pressure ****\nCurrent pressure level: Whatever\n"
    assert thermal_pressure.parse_thermal_pressure(text) is None


def test_collect_returns_none_when_file_is_absent(tmp_path):
    assert thermal_pressure.collect(tmp_path / "missing.txt") is None


def test_collect_reads_and_parses_the_written_file(tmp_path):
    path = tmp_path / "thermal_pressure.txt"
    path.write_text(REAL_SAMPLE)

    assert thermal_pressure.collect(path) == "moderate"
