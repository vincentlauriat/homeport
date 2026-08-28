"""system.py lit /proc directement (voir son en-tête) : sur une machine où ces fichiers
n'existent pas (macOS, ou /proc temporairement illisible), l'absence doit rester visible
comme telle — jamais un zéro qui se ferait passer pour une mesure réelle."""

from homeport.collectors import system


def test_uptime_returns_none_fields_when_source_is_absent(tmp_path):
    result = system.uptime(str(tmp_path / "no-such-uptime"))

    assert result == {"seconds": None, "human": None}


def test_uptime_parses_a_real_source_file(tmp_path):
    path = tmp_path / "uptime"
    path.write_text("172930.55 1523000.02\n")

    result = system.uptime(str(path))

    assert result["seconds"] == 172930
    assert result["human"] is not None


def test_memory_returns_none_fields_when_source_is_absent(tmp_path):
    result = system.memory(str(tmp_path / "no-such-meminfo"))

    assert result == {"total_mb": None, "used_mb": None, "percent": None}


def test_memory_parses_a_real_source_file(tmp_path):
    path = tmp_path / "meminfo"
    path.write_text("MemTotal:       16384000 kB\nMemAvailable:    8192000 kB\n")

    result = system.memory(str(path))

    assert result == {"total_mb": 16000, "used_mb": 8000, "percent": 50.0}


def test_load_returns_none_fields_when_source_is_absent(tmp_path):
    result = system.load(str(tmp_path / "no-such-loadavg"))

    assert result["avg1"] is None
    assert result["avg5"] is None
    assert result["avg15"] is None
    assert result["percent"] is None
    assert result["cores"] > 0


def test_load_parses_a_real_source_file(tmp_path):
    path = tmp_path / "loadavg"
    path.write_text("1.50 1.20 1.00 2/300 12345\n")

    result = system.load(str(path))

    assert result["avg1"] == 1.5
    assert result["avg5"] == 1.2
    assert result["avg15"] == 1.0


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
