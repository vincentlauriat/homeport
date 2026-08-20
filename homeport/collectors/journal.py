"""Erreurs récentes du journal systemd.

Deux précautions qui décident si cette tuile sert à quelque chose ou devient un décor :

1. **`_SYSTEMD_UNIT` est absent de nombreuses entrées** (messages noyau, logs sans unité).
   Un accès direct au champ ferait planter le regroupement ou perdre des lignes en silence,
   et le total affiché ne correspondrait plus à `journalctl -p err | wc -l`.
2. **Le bruit de fond doit pouvoir être tu.** Sur cet hôte, l'essentiel des erreurs est
   `sshd: kex_exchange_identification` — des scans venus d'Internet frappant le port 22, pas
   une panne. Sans liste d'exclusion, le compteur reste rouge en permanence et on apprend à
   l'ignorer. Les motifs exclus sont comptés à part, jamais effacés.
"""

from __future__ import annotations

import asyncio
import json
import re

MAX_ENTRIES = 2000


def _message(entry: dict) -> str:
    raw = entry.get("MESSAGE", "")
    if isinstance(raw, list):  # message non-UTF-8 : journald renvoie une liste d'octets
        return bytes(raw).decode("utf-8", "replace")
    return str(raw)


def _source(entry: dict) -> str:
    return entry.get("_SYSTEMD_UNIT") or entry.get("SYSLOG_IDENTIFIER") or "(sans unité)"


async def collect(since: str = "24 hours ago", ignore: list[str] | None = None) -> dict:
    patterns = [re.compile(p) for p in (ignore or [])]

    args = [
        "journalctl", "-p", "err", "--since", since, "--no-pager", "-q",
        "-o", "json", "--output-fields=_SYSTEMD_UNIT,SYSLOG_IDENTIFIER,MESSAGE",
        "-n", str(MAX_ENTRIES),
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=15.0)
    except Exception:
        return {"available": False, "total": 0, "muted": 0, "by_source": [], "recent": [], "since": since}

    total = muted = 0
    by_source: dict[str, int] = {}
    recent: list[dict] = []

    for line in stdout.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        total += 1
        message = _message(entry)
        if any(p.search(message) for p in patterns):
            muted += 1
            continue

        source = _source(entry)
        by_source[source] = by_source.get(source, 0) + 1
        recent.append({"source": source, "message": message[:200]})

    ranked = sorted(by_source.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "available": True,
        "total": total,            # brut : doit correspondre à `journalctl -p err | wc -l`
        "muted": muted,            # exclus par la configuration
        "counted": total - muted,
        "by_source": [{"source": s, "count": c} for s, c in ranked[:5]],
        "recent": recent[-5:][::-1],
        "since": since,
    }
