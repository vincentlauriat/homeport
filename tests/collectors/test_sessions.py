from homeport.collectors import sessions

# Sortie réelle de `who` sur homeserver (2026-08-19) : les sessions sans tty (tailscale SSH,
# console locale) affichent le nom du service PAM à la place d'un tty, d'où le filtrage sur le
# mot « sshd » plutôt que sur la position d'une colonne.
WHO_OUTPUT = """\
alice  tailscaled   2026-08-19 12:38 (admin@example.com@100.102.102.102)
alice  sshd         2026-08-19 11:39 (192.168.68.44)
alice  sshd pts/1   2026-08-18 06:37 (192.168.68.39)
alice  seat0        2026-08-16 13:30
alice  tty1         2026-08-16 13:30
"""


def test_parse_who_keeps_only_sshd_sessions():
    result = sessions.parse_who(WHO_OUTPUT)

    assert len(result) == 2


def test_parse_who_extracts_the_remote_host():
    result = sessions.parse_who(WHO_OUTPUT)

    assert {r["host"] for r in result} == {"192.168.68.44", "192.168.68.39"}


def test_parse_who_ignores_sessions_without_a_parenthesized_host():
    result = sessions.parse_who("alice  seat0        2026-08-16 13:30\n")

    assert result == []


def test_parse_who_handles_empty_output():
    assert sessions.parse_who("") == []
