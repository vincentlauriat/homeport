"""Antenne Starlink — statut, historique et carte d'obstruction via l'API gRPC du dish.

L'antenne expose `SpaceX.API.Device.Device/Handle` en gRPC **cleartext** sur
192.168.100.1:9200 (joignable seulement depuis le LAN Starlink ou une route vers lui).
Plutôt que d'embarquer grpcio + des stubs générés pour trois appels unaires, on parle
HTTP/2 prior-knowledge avec httpx et le codec wire minimal de `_protowire` : les numéros
de champ protobuf sont un contrat stable, ils sont mappés ici vers des noms.

Numéros extraits du protoset du dish (dump par réflexion serveur, projet StarlinkInfos).
Un champ à sa valeur par défaut (0, false, "") n'est PAS sérialisé par protobuf : chaque
lecture passe par les helpers `_f/_i/_b/_s` qui appliquent le défaut.
"""

from __future__ import annotations

import logging

import httpx

from . import _protowire as pw

log = logging.getLogger("homeport.starlink")

DEFAULT_ADDRESS = "192.168.100.1:9200"
_PATH = "/SpaceX.API.Device.Device/Handle"

# Request / Response (oneof)
_REQ_GET_STATUS = 1004
_REQ_GET_HISTORY = 1007
_REQ_GET_MAP = 2008
_RESP_STATUS = 2004
_RESP_HISTORY = 2006
_RESP_MAP = 2008

_OUTAGE_CAUSES = {
    0: "UNKNOWN", 1: "BOOTING", 2: "STOWED", 3: "THERMAL_SHUTDOWN", 4: "NO_SCHEDULE",
    5: "NO_SATS", 6: "OBSTRUCTED", 7: "NO_DOWNLINK", 8: "NO_PINGS", 9: "ACTUATOR_ACTIVITY",
}

# DishAlerts : numéro de champ -> nom (booléens, absents quand false)
_ALERTS = {
    1: "motors_stuck", 2: "thermal_shutdown", 3: "thermal_throttle", 4: "unexpected_location",
    5: "mast_not_near_vertical", 6: "slow_ethernet_speeds", 7: "roaming", 8: "install_pending",
    9: "is_heating", 10: "power_supply_thermal_throttle", 11: "is_power_save_idle",
    14: "dbf_telem_stale", 16: "low_motor_current", 17: "lower_signal_than_predicted",
}


def _first(fields: dict, number: int):
    values = fields.get(number)
    return values[0] if values else None


def _f(fields: dict, number: int, default: float = 0.0) -> float:
    raw = _first(fields, number)
    return pw.as_float(raw) if raw is not None else default


def _i(fields: dict, number: int, default: int = 0) -> int:
    value = _first(fields, number)
    return value if isinstance(value, int) else default


def _b(fields: dict, number: int) -> bool:
    return bool(_i(fields, number))


def _s(fields: dict, number: int, default: str = "") -> str:
    raw = _first(fields, number)
    return pw.as_str(raw) if raw is not None else default


def _sub(fields: dict, number: int) -> dict:
    raw = _first(fields, number)
    return pw.decode_message(raw) if raw else {}


async def _call(request_field: int, address: str, timeout: float = 8.0) -> bytes | None:
    """Un appel unaire : trame gRPC (compression 0 + longueur + protobuf) sur h2c."""
    payload = pw.encode_message({request_field: {}})
    frame = b"\x00" + len(payload).to_bytes(4, "big") + payload
    try:
        async with httpx.AsyncClient(http1=False, http2=True, timeout=timeout) as client:
            response = await client.post(
                f"http://{address}{_PATH}",
                content=frame,
                headers={"content-type": "application/grpc", "te": "trailers"},
            )
        if response.status_code != 200 or len(response.content) < 5:
            return None
        body = response.content
        length = int.from_bytes(body[1:5], "big")
        return body[5:5 + length]
    except (httpx.HTTPError, OSError) as exc:
        log.debug("dish injoignable (%s): %s", address, exc)
        return None


def parse_status(raw: bytes) -> dict:
    status = _sub(pw.decode_message(raw), _RESP_STATUS)
    device = _sub(status, 1)
    state = _sub(status, 2)
    obstruction = _sub(status, 1004)
    alerts = _sub(status, 1005)
    outage = _sub(status, 1014)
    gps = _sub(status, 1015)
    alignment = _sub(status, 1027)

    return {
        "online": not outage,
        "outage_cause": _OUTAGE_CAUSES.get(_i(outage, 1), "UNKNOWN") if outage else None,
        "latency_ms": round(_f(status, 1009), 1),
        "drop_rate": round(_f(status, 1003), 4),
        "downlink_bps": round(_f(status, 1007)),
        "uplink_bps": round(_f(status, 1008)),
        "hardware": _s(device, 2),
        "software": _s(device, 3),
        "country": _s(device, 4),
        "uptime_s": _i(state, 1),
        "eth_speed_mbps": _i(status, 1016),
        "snr_above_noise_floor": _b(status, 1018),
        "software_update_state": None,
        "gps": {"valid": _b(gps, 1), "sats": _i(gps, 2)},
        "obstruction": {
            "fraction": round(_f(obstruction, 1), 6),
            "currently": _b(obstruction, 5),
            "time_obstructed": round(_f(obstruction, 9), 6),
            "valid_s": round(_f(obstruction, 4)),
            "avg_prolonged_s": round(_f(obstruction, 6), 1),
        },
        "alignment": {
            "tilt_deg": round(_f(alignment, 3), 1),
            "azimuth_deg": round(_f(alignment, 4), 1),
            "elevation_deg": round(_f(alignment, 5), 1),
        },
        "alerts": [name for number, name in _ALERTS.items() if _b(alerts, number)],
    }


def parse_history(raw: bytes) -> dict:
    """Buffers circulaires de l'antenne (~15 min à 1 Hz). `current` est le compteur total
    d'échantillons : l'index du plus récent est (current - 1) % taille — on réordonne du
    plus ancien au plus récent pour que le front trace directement."""
    history = _sub(pw.decode_message(raw), _RESP_HISTORY)
    current = _i(history, 1)

    def series(number: int) -> list[float]:
        raw_values = _first(history, number)
        if not raw_values:
            return []
        values = pw.packed_floats(raw_values)
        if not values:
            return []
        pivot = current % len(values)
        return [round(v, 2) for v in values[pivot:] + values[:pivot]]

    return {
        "latency_ms": series(1002),
        "downlink_bps": series(1003),
        "uplink_bps": series(1004),
        "drop_rate": series(1001),
    }


def parse_map(raw: bytes) -> dict:
    omap = _sub(pw.decode_message(raw), _RESP_MAP)
    snr_raw = _first(omap, 3)
    return {
        "rows": _i(omap, 1),
        "cols": _i(omap, 2),
        "snr": [round(v, 3) for v in pw.packed_floats(snr_raw)] if snr_raw else [],
    }


async def fetch_status(settings: dict) -> dict | None:
    raw = await _call(_REQ_GET_STATUS, settings.get("address", DEFAULT_ADDRESS))
    return parse_status(raw) if raw else None


async def fetch_history(settings: dict) -> dict | None:
    raw = await _call(_REQ_GET_HISTORY, settings.get("address", DEFAULT_ADDRESS))
    return parse_history(raw) if raw else None


async def fetch_map(settings: dict) -> dict | None:
    raw = await _call(_REQ_GET_MAP, settings.get("address", DEFAULT_ADDRESS), timeout=15.0)
    return parse_map(raw) if raw else None
