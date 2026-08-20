"""Wake-on-LAN : 6 octets 0xFF puis la MAC répétée 16 fois, en broadcast UDP port 9."""
from homeport.collectors import wol


def test_magic_packet_structure():
    packet = wol.magic_packet("9c:a2:f4:af:b4:f4")
    assert len(packet) == 102                     # 6 + 16 × 6
    assert packet[:6] == b"\xff" * 6
    mac_bytes = bytes.fromhex("9ca2f4afb4f4")
    assert packet[6:12] == mac_bytes
    assert packet[6:] == mac_bytes * 16


def test_magic_packet_mac_invalide():
    import pytest
    with pytest.raises(ValueError):
        wol.magic_packet("pas-une-mac")


def test_send_utilise_le_broadcast(monkeypatch):
    sent = {}

    class FakeSocket:
        def __init__(self, *a): pass
        def setsockopt(self, *a): sent["broadcast"] = True
        def sendto(self, data, addr): sent["data"], sent["addr"] = data, addr
        def close(self): sent["closed"] = True
        def __enter__(self): return self
        def __exit__(self, *a): self.close()

    monkeypatch.setattr(wol.socket, "socket", FakeSocket)
    wol.send("9c:a2:f4:af:b4:f4")
    assert sent["broadcast"] is True
    assert sent["addr"] == ("255.255.255.255", 9)
    assert len(sent["data"]) == 102
