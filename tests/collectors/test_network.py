from homeport.collectors import network

# Sortie réelle capturée sur homeserver (2026-08-19), tronquée.
TAILSCALE_JSON = """
{
  "Version": "1.102.2-t6cac91817-g6ff0ddc72",
  "Self": {"HostName": "homeserver", "DNSName": "homeserver.example.ts.net.",
            "TailscaleIPs": ["100.100.100.100"], "Online": true},
  "Peer": {
    "n1": {"HostName": "MBA13M5", "DNSName": "mba13m5.example.ts.net.",
           "TailscaleIPs": ["100.90.1.2"], "Online": true},
    "n2": {"HostName": "localhost", "DNSName": "localhost.example.ts.net.",
           "TailscaleIPs": ["100.90.1.3"], "Online": true},
    "n3": {"HostName": "offsite", "DNSName": "offsite.example.ts.net.",
           "TailscaleIPs": ["100.90.1.4"], "Online": false}
  }
}
"""

# Sortie réelle de `ip neigh show` sur homeserver (2026-08-19), avec deux lignes ajoutées :
# une entrée IPv6 avec le drapeau "router" intercalé (même MAC que la ligne REACHABLE — un
# routeur annonce souvent une adresse IPv4 et une IPv6 pour la même carte), et le bridge Docker.
IP_NEIGH_OUTPUT = """\
192.168.68.28 dev eth0 lladdr 9e:7a:37:d2:64:aa STALE
192.168.68.1 dev eth0 lladdr 9c:a2:f4:af:b4:f4 REACHABLE
192.168.68.50 dev eth0 FAILED
172.17.0.4 dev docker0 lladdr c6:c6:cd:a3:7c:40 STALE
192.168.68.99 dev eth0 lladdr aa:bb:cc:dd:ee:ff INCOMPLETE
fe80::1 dev eth0 lladdr 9c:a2:f4:af:b4:f4 router STALE
"""


def test_parse_tailscale_peers_excludes_self_and_localhost():
    peers = network.parse_tailscale_peers(TAILSCALE_JSON)

    names = {p["hostname"] for p in peers}
    assert names == {"MBA13M5", "offsite"}


def test_parse_tailscale_peers_reports_online_state():
    peers = network.parse_tailscale_peers(TAILSCALE_JSON)

    online = {p["hostname"]: p["online"] for p in peers}
    assert online == {"MBA13M5": True, "offsite": False}


def test_parse_tailscale_summary_counts_online_peers_out_of_the_displayed_list():
    summary = network.parse_tailscale_summary(TAILSCALE_JSON)

    # 2 pairs affichés (Self et "localhost" exclus, comme parse_tailscale_peers) : 1 en ligne.
    assert summary["peers_total"] == 2
    assert summary["peers_online"] == 1


def test_parse_tailscale_summary_strips_the_build_suffix_from_the_version():
    summary = network.parse_tailscale_summary(TAILSCALE_JSON)

    assert summary["version"] == "1.102.2"


def test_parse_tailscale_summary_reports_the_self_tailscale_ip():
    summary = network.parse_tailscale_summary(TAILSCALE_JSON)

    assert summary["self_ip"] == "100.100.100.100"


def test_parse_ip_neigh_excludes_failed_and_incomplete_states():
    neighbors = network.parse_ip_neigh(IP_NEIGH_OUTPUT)

    ips = {n["ip"] for n in neighbors}
    assert "192.168.68.50" not in ips
    assert "192.168.68.99" not in ips


def test_parse_ip_neigh_excludes_docker_bridge_interfaces():
    neighbors = network.parse_ip_neigh(IP_NEIGH_OUTPUT)

    ips = {n["ip"] for n in neighbors}
    assert "172.17.0.4" not in ips


def test_parse_ip_neigh_extracts_mac_address():
    neighbors = network.parse_ip_neigh(IP_NEIGH_OUTPUT)

    by_ip = {n["ip"]: n["mac"] for n in neighbors}
    assert by_ip["192.168.68.1"] == "9c:a2:f4:af:b4:f4"


def test_parse_ip_neigh_dedupes_the_same_device_seen_on_two_addresses():
    neighbors = network.parse_ip_neigh(IP_NEIGH_OUTPUT)

    # 192.168.68.1 (REACHABLE) et fe80::1 (router STALE) partagent la même MAC : un seul
    # appareil, une seule entrée.
    assert len(neighbors) == 2
    assert "fe80::1" not in {n["ip"] for n in neighbors}


def test_parse_ip_neigh_tolerates_a_flag_between_mac_and_state():
    neighbors = network.parse_ip_neigh(
        "fe80::9 dev eth0 lladdr 11:22:33:44:55:66 router REACHABLE\n"
    )

    assert neighbors == [{"ip": "fe80::9", "mac": "11:22:33:44:55:66", "interface": "eth0"}]


def test_parse_ip_neigh_ignores_blank_lines():
    neighbors = network.parse_ip_neigh("\n\n" + IP_NEIGH_OUTPUT + "\n")

    assert len(neighbors) == 2
