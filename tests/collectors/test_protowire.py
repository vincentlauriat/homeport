"""Codec protobuf wire minimal — juste ce qu'il faut pour parler à l'antenne Starlink.

Références : https://protobuf.dev/programming-guides/encoding/ . Les octets attendus des
tests sont calculés à la main d'après la spec (varint, tag = field<<3 | wire_type).
"""
import math
import struct

from homeport.collectors import _protowire as pw


def test_encode_message_vide_dans_un_champ():
    # Request{get_status = 1004: {}} : tag varint (1004<<3|2 = 8034) + longueur 0
    encoded = pw.encode_message({1004: {}})
    assert encoded == b"\xe2\x3e\x00"


def test_varint_multi_octets():
    assert pw.encode_varint(1) == b"\x01"
    assert pw.encode_varint(300) == b"\xac\x02"


def test_roundtrip_imbrique():
    data = pw.encode_message({1: {2: b"rev2", 3: b"2026.08"}, 5: 42})
    fields = pw.decode_message(data)
    inner = pw.decode_message(fields[1][0])
    assert inner[2][0] == b"rev2"
    assert fields[5][0] == 42


def test_decode_fixed32_float():
    payload = struct.pack("<f", 19.8)
    data = pw.encode_message({1009: payload}, wire_types={1009: 5})
    fields = pw.decode_message(data)
    assert math.isclose(pw.as_float(fields[1009][0]), 19.8, rel_tol=1e-6)


def test_packed_floats():
    values = [1.5, -2.0, 0.0]
    packed = b"".join(struct.pack("<f", v) for v in values)
    assert pw.packed_floats(packed) == values


def test_decode_ignore_wire_types_inconnus_sans_crash():
    # fixed64 (wire 1) au champ 7 : doit être consommé proprement
    data = bytes([7 << 3 | 1]) + b"\x00" * 8 + pw.encode_message({2: b"ok"})
    fields = pw.decode_message(data)
    assert fields[2][0] == b"ok"
