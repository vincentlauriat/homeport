from homeport.collectors import docker_api

# Extrait réel d'un payload `GET /containers/{id}/stats?stream=false` (champs inutiles retirés).
# system_cpu_usage est la somme sur TOUS les cœurs : un conteprocesseur qui sature un cœur sur
# quatre pèse donc 25 %, pas 100 %.
SAMPLE = {
    "cpu_stats": {
        "cpu_usage": {"total_usage": 150_000_000},
        "system_cpu_usage": 1_400_000_000,
        "online_cpus": 4,
    },
    "precpu_stats": {
        "cpu_usage": {"total_usage": 100_000_000},
        "system_cpu_usage": 1_000_000_000,
    },
}


def test_cpu_percent_scales_by_online_cpu_count():
    # cpu_delta = 50M, system_delta = 400M -> 0.125 ; * 4 coeurs * 100 = 50 %.
    assert docker_api._cpu_percent(SAMPLE) == 50.0


def test_cpu_percent_is_zero_when_system_delta_is_zero():
    payload = {
        "cpu_stats": {"cpu_usage": {"total_usage": 100}, "system_cpu_usage": 500, "online_cpus": 4},
        "precpu_stats": {"cpu_usage": {"total_usage": 100}, "system_cpu_usage": 500},
    }
    assert docker_api._cpu_percent(payload) == 0.0


def test_cpu_percent_handles_missing_precpu_first_sample():
    payload = {
        "cpu_stats": {"cpu_usage": {"total_usage": 100}, "system_cpu_usage": 500, "online_cpus": 4},
        "precpu_stats": {},
    }
    assert docker_api._cpu_percent(payload) == 0.0


def test_cpu_percent_falls_back_to_percpu_length_when_online_cpus_absent():
    payload = {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 150_000_000, "percpu_usage": [1, 2]},
            "system_cpu_usage": 1_400_000_000,
        },
        "precpu_stats": {"cpu_usage": {"total_usage": 100_000_000}, "system_cpu_usage": 1_000_000_000},
    }
    # 0.125 * 2 coeurs * 100 = 25 %.
    assert docker_api._cpu_percent(payload) == 25.0
