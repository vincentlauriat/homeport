import json

from homeport.collectors import nvme

# Sortie réelle de `nvme smart-log /dev/nvme0 -o json` sur homeserver (2026-08-19), tronquée.
SMART_JSON = json.dumps(
    {
        "critical_warning": 0,
        "temperature": 321,           # Kelvin -> 48 °C
        "avail_spare": 100,
        "percent_used": 0,
        "power_on_hours": 215,
        "data_units_written": 36754,  # unités de 512 000 octets (spec NVMe)
    }
)


def test_parse_smart_log_extracts_wear_and_hours():
    result = nvme.parse_smart_log(SMART_JSON)

    assert result["percent_used"] == 0
    assert result["power_on_hours"] == 215


def test_parse_smart_log_converts_temperature_from_kelvin():
    result = nvme.parse_smart_log(SMART_JSON)

    assert result["temperature_c"] == 48


def test_parse_smart_log_converts_data_units_to_gigabytes():
    result = nvme.parse_smart_log(SMART_JSON)

    # 36754 * 512000 octets = ~18.8 Go.
    assert result["written_gb"] == 18.8


def test_parse_smart_log_reports_health_from_critical_warning():
    assert nvme.parse_smart_log(SMART_JSON)["healthy"] is True
    warned = json.dumps({**json.loads(SMART_JSON), "critical_warning": 4})
    assert nvme.parse_smart_log(warned)["healthy"] is False


def test_collect_returns_none_when_the_file_is_absent(tmp_path):
    assert nvme.collect(tmp_path / "nvme.json") is None


def test_collect_reads_and_parses_the_written_file(tmp_path):
    path = tmp_path / "nvme.json"
    path.write_text(SMART_JSON)

    result = nvme.collect(path)

    assert result["percent_used"] == 0
    assert result["temperature_c"] == 48
