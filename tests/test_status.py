from homeport import config as cfg
from homeport import status


def _item(id_, state):
    return {"id": id_, "state": state}


def _service(**overrides):
    defaults = {"id": "svc", "name": "Service"}
    return cfg.Service(**{**defaults, **overrides})


def test_sort_by_severity_puts_down_before_warn_before_unknown_before_up():
    items = [_item("a", "up"), _item("b", "down"), _item("c", "unknown"), _item("d", "warn")]

    ordered = status._sort_by_severity(items)

    assert [i["id"] for i in ordered] == ["b", "d", "c", "a"]


def test_sort_by_severity_preserves_relative_order_within_the_same_state():
    items = [_item("a", "up"), _item("b", "up"), _item("c", "down"), _item("d", "down")]

    ordered = status._sort_by_severity(items)

    assert [i["id"] for i in ordered] == ["c", "d", "a", "b"]


def test_source_rows_reports_a_row_per_declared_source():
    service = _service(docker="ha", probe=cfg.Probe(type="http", port=8123))

    rows = status._source_rows({"state": "running"}, None, status.UP, service)

    assert [r["label"] for r in rows] == ["docker", "port 8123"]


def test_source_rows_marks_a_running_container_as_ok():
    service = _service(docker="ha")

    rows = status._source_rows({"state": "running"}, None, status.UP, service)

    assert rows == [{"label": "docker", "value": "running", "ok": True}]


def test_source_rows_marks_a_missing_container_as_not_ok():
    service = _service(docker="ha")

    rows = status._source_rows(None, None, status.UNKNOWN, service)

    assert rows == [{"label": "docker", "value": "absent", "ok": False}]


def test_source_rows_reports_a_dead_probe_as_silent_and_not_ok():
    service = _service(probe=cfg.Probe(type="tcp", port=3000))

    rows = status._source_rows(None, None, status.DOWN, service)

    assert rows == [{"label": "port 3000", "value": "silent", "ok": False}]


def test_source_rows_reports_an_inactive_systemd_unit():
    service = _service(systemd="docker.service")

    rows = status._source_rows(None, {"active_state": "failed"}, status.UNKNOWN, service)

    assert rows == [{"label": "systemd", "value": "failed", "ok": False}]


def test_extra_info_reports_running_and_total_container_counts_for_docker():
    service = _service(id="docker", systemd="docker.service")
    containers = {"a": {"state": "running"}, "b": {"state": "running"}, "c": {"state": "exited"}}

    extra = status._extra_info(service, containers, None, {}, [], [])

    assert extra == [{"label": "conteneurs", "value": "2 actif(s) / 3 au total"}]


def test_extra_info_reports_tailscale_peers_and_version():
    service = _service(id="tailscale", systemd="tailscaled.service")
    network_data = {"tailscale_summary": {"version": "1.102.2", "peers_online": 1, "peers_total": 2}}

    extra = status._extra_info(service, {}, None, network_data, [], [])

    assert extra == [
        {"label": "version", "value": "1.102.2"},
        {"label": "pairs", "value": "1/2 en ligne"},
    ]


def test_extra_info_reports_no_ssh_sessions():
    service = _service(id="ssh", systemd="ssh.service")

    extra = status._extra_info(service, {}, None, {}, [], [])

    assert extra == [{"label": "sessions", "value": "aucune"}]


def test_extra_info_lists_active_ssh_sessions_with_their_host():
    service = _service(id="ssh", systemd="ssh.service")
    sessions = [{"user": "alice", "host": "192.168.68.44"}]

    extra = status._extra_info(service, {}, None, {}, [], sessions)

    assert extra == [{"label": "sessions", "value": "1 active(s) — 192.168.68.44"}]


def test_extra_info_lists_cron_jobs_as_schedule_command_rows():
    service = _service(id="cron", systemd="cron.service")
    jobs = [{"schedule": "17 * * * *", "user": "root", "command": "run-parts /etc/cron.hourly"}]

    extra = status._extra_info(service, {}, None, {}, jobs, [])

    assert extra == [{"label": "17 * * * *", "value": "run-parts /etc/cron.hourly"}]


def test_extra_info_reports_next_and_last_run_for_the_backup_timer():
    service = _service(id="backup-timer", systemd="homeserver-backup.timer")
    unit = {"next_run": "2026-08-20 03:32", "last_run": "2026-08-19 03:30"}

    extra = status._extra_info(service, {}, unit, {}, [], [])

    assert extra == [
        {"label": "prochaine", "value": "2026-08-20 03:32"},
        {"label": "dernière", "value": "2026-08-19 03:30"},
    ]


def test_extra_info_is_empty_for_a_service_without_special_handling():
    service = _service(id="avahi", systemd="avahi-daemon.service")

    assert status._extra_info(service, {}, None, {}, [], []) == []


def test_extra_info_appends_start_time_for_any_systemd_unit_that_has_one():
    service = _service(id="avahi", systemd="avahi-daemon.service")
    unit = {"since": "2026-08-14 10:23"}

    extra = status._extra_info(service, {}, unit, {}, [], [])

    assert extra == [{"label": "démarré", "value": "2026-08-14 10:23"}]


def test_extra_info_start_time_comes_after_tile_specific_rows():
    service = _service(id="tailscale", systemd="tailscaled.service")
    unit = {"since": "2026-08-14 10:23"}
    network_data = {"tailscale_summary": {"version": "1.102.2", "peers_online": 1, "peers_total": 2}}

    extra = status._extra_info(service, {}, unit, network_data, [], [])

    assert extra[-1] == {"label": "démarré", "value": "2026-08-14 10:23"}
    assert [r["label"] for r in extra] == ["version", "pairs", "démarré"]


def test_network_compte_les_nouveaux(tmp_path, monkeypatch):
    from homeport.collectors import devices as devices_collector

    db = tmp_path / "t.db"
    devices_collector.init_db(db)
    devices_collector.upsert_seen(db, [{"ip": "1.1.1.1", "mac": "aa:aa:aa:aa:aa:aa"}], now=1000)
    devices_collector.upsert_seen(db, [{"ip": "2.2.2.2", "mac": "bb:bb:bb:bb:bb:bb"}], now=2000)
    monkeypatch.setattr(status.cfg, "DB_PATH", db)

    result = status._network()

    assert result["new_devices"]["count"] == 1


def test_extra_info_reports_next_and_last_run_for_any_timer_unit():
    service = _service(id="auto-updates", systemd="apt-daily-upgrade.timer")
    unit = {"next_run": "2026-08-21 06:14", "last_run": "2026-08-20 06:47"}

    extra = status._extra_info(service, {}, unit, {}, [], [])

    assert {"label": "prochaine", "value": "2026-08-21 06:14"} in extra
    assert {"label": "dernière", "value": "2026-08-20 06:47"} in extra
