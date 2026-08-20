from homeport.collectors import systemd


def test_clean_timestamp_strips_weekday_seconds_and_timezone():
    assert systemd._clean_timestamp("Thu 2026-08-20 03:32:38 CEST") == "2026-08-20 03:32"


def test_clean_timestamp_returns_empty_string_for_unset_value():
    assert systemd._clean_timestamp("n/a") == ""


def test_clean_timestamp_returns_empty_string_for_empty_input():
    assert systemd._clean_timestamp("") == ""
