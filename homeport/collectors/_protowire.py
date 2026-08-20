"""Codec protobuf wire minimal — juste ce qu'il faut pour parler gRPC à une antenne Starlink.

Pourquoi pas grpcio + stubs générés : une dépendance native lourde et un pipeline protoc
pour trois appels unaires. Les numéros de champ protobuf sont un contrat stable (c'est le
principe même du format) ; on encode/décode donc au niveau du wire format, et
`starlink.py` mappe les numéros vers des noms. Spec : protobuf.dev/programming-guides/encoding.

Couverture volontairement partielle : varint (wire 0), fixed64 (wire 1, consommé mais brut),
length-delimited (wire 2), fixed32 (wire 5). Les groupes (wire 3/4) n'existent plus dans
les protos modernes — une trame qui en contiendrait lève ValueError plutôt que de dérailler.
"""

from __future__ import annotations

import struct


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _decode_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if not byte & 0x80:
            return result, pos
        shift += 7


def encode_message(fields: dict[int, object], wire_types: dict[int, int] | None = None) -> bytes:
    """Encode {numéro: valeur}. Valeurs : dict (message imbriqué), bytes (length-delimited),
    int (varint). `wire_types` force le type d'un champ (5 = fixed32 pour un float déjà packé
    en bytes)."""
    out = bytearray()
    for number, value in fields.items():
        forced = (wire_types or {}).get(number)
        if isinstance(value, dict):
            payload = encode_message(value)
            out += encode_varint(number << 3 | 2) + encode_varint(len(payload)) + payload
        elif isinstance(value, bytes):
            wire = forced if forced is not None else 2
            if wire == 5:
                out += encode_varint(number << 3 | 5) + value
            else:
                out += encode_varint(number << 3 | 2) + encode_varint(len(value)) + value
        elif isinstance(value, int):
            out += encode_varint(number << 3 | 0) + encode_varint(value)
        else:
            raise TypeError(f"type non encodable pour le champ {number}: {type(value)}")
    return bytes(out)


def decode_message(data: bytes) -> dict[int, list]:
    """Décode une trame en {numéro: [valeurs]} — liste car un champ `repeated` non packé
    apparaît plusieurs fois. wire 0 → int ; wire 1/5 → bytes bruts (8/4 octets) ;
    wire 2 → bytes (au consommateur de savoir si c'est une string, un message ou du packé)."""
    fields: dict[int, list] = {}
    pos = 0
    while pos < len(data):
        tag, pos = _decode_varint(data, pos)
        number, wire = tag >> 3, tag & 0x07
        if wire == 0:
            value, pos = _decode_varint(data, pos)
        elif wire == 1:
            value, pos = data[pos:pos + 8], pos + 8
        elif wire == 2:
            length, pos = _decode_varint(data, pos)
            value, pos = data[pos:pos + length], pos + length
        elif wire == 5:
            value, pos = data[pos:pos + 4], pos + 4
        else:
            raise ValueError(f"wire type {wire} non géré (champ {number})")
        fields.setdefault(number, []).append(value)
    return fields


def as_float(raw: bytes) -> float:
    return struct.unpack("<f", raw)[0]


def as_double(raw: bytes) -> float:
    return struct.unpack("<d", raw)[0]


def as_str(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def packed_floats(raw: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(raw) // 4}f", raw))
