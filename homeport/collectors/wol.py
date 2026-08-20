"""Wake-on-LAN : réveil d'un appareil de l'inventaire par paquet magique.

Stdlib pure, aucun privilège : un datagramme UDP broadcast sur le port 9 contenant
6 × 0xFF puis la MAC répétée 16 fois. Ne fonctionne que pour les appareils ethernet
dont le réveil réseau est activé — l'échec est silencieux par nature (UDP).
"""

from __future__ import annotations

import re
import socket

_MAC = re.compile(r"^[0-9a-f]{2}([:-][0-9a-f]{2}){5}$")


def magic_packet(mac: str) -> bytes:
    cleaned = mac.strip().lower()
    if not _MAC.match(cleaned):
        raise ValueError(f"MAC invalide : {mac!r}")
    mac_bytes = bytes.fromhex(cleaned.replace(":", "").replace("-", ""))
    return b"\xff" * 6 + mac_bytes * 16


def send(mac: str, broadcast: str = "255.255.255.255") -> None:
    packet = magic_packet(mac)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (broadcast, 9))
