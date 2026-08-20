

# --- vérification de nouvelle version (system de mise à jour, opt-out) ---

def test_parse_latest_release():
    from homeport.collectors import updates
    assert updates.parse_latest_release('{"tag_name": "v0.2.0"}') == "0.2.0"
    assert updates.parse_latest_release('{"message": "Not Found"}') is None
    assert updates.parse_latest_release('pas du json') is None


def test_update_summary():
    from homeport.collectors import updates
    assert updates.update_summary("0.1.0", "0.2.0") == {
        "current": "0.1.0", "latest": "0.2.0", "available": True,
    }
    assert updates.update_summary("0.2.0", "0.2.0")["available"] is False
    assert updates.update_summary("0.1.0", None) == {
        "current": "0.1.0", "latest": None, "available": False,
    }
