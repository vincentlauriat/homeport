"""Le fabricant est déduit du préfixe OUI (3 premiers octets) de la MAC."""
from pathlib import Path

from homeport.collectors import oui


def test_vendor_prefixe_connu(tmp_path: Path):
    table_file = tmp_path / "oui.tsv"
    table_file.write_text("9ca2f4\tTP-Link Corporation\n102cb1\tApple, Inc.\n")
    table = oui._load_table(table_file)
    assert oui.vendor("9C:A2:F4:AF:B4:F4", table) == "TP-Link Corporation"


def test_vendor_normalise_separateurs_et_casse(tmp_path: Path):
    table_file = tmp_path / "oui.tsv"
    table_file.write_text("102cb1\tApple, Inc.\n")
    table = oui._load_table(table_file)
    assert oui.vendor("10-2C-B1-7C-D6-FB", table) == "Apple, Inc."


def test_vendor_prefixe_inconnu(tmp_path: Path):
    table_file = tmp_path / "oui.tsv"
    table_file.write_text("102cb1\tApple, Inc.\n")
    table = oui._load_table(table_file)
    assert oui.vendor("00:00:00:11:22:33", table) is None


def test_vendor_mac_malformee(tmp_path: Path):
    table = oui._load_table(tmp_path / "absent.tsv")  # fichier absent -> table vide
    assert oui.vendor("pas-une-mac", table) is None


def test_is_local_mac():
    # bit 0x02 du premier octet = adresse administrée localement (MAC privée iOS/Android)
    assert oui.is_local_mac("d2:11:22:33:44:55") is True   # 0xd2 & 0x02
    assert oui.is_local_mac("9c:a2:f4:af:b4:f4") is False  # 0x9c & 0x02 == 0


def test_table_embarquee_presente():
    """La vraie base committée existe et contient des fabricants réels du LAN de Alice."""
    table = oui._load_table(oui.DATA_PATH)
    assert len(table) > 10000
    assert oui.vendor("9c:a2:f4:00:00:00", table) is not None  # préfixe TP-Link vu sur le LAN
