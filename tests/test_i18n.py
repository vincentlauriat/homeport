"""Couche i18n : catalogues EN/FR/ZH à parité, variables, pluriels, repli sur la clé."""
from homeport import i18n


def test_parite_des_catalogues():
    en = i18n.catalog("en")
    assert en  # jamais vide
    for lang in i18n.SUPPORTED:
        assert set(i18n.catalog(lang)) == set(en), lang


def test_variables():
    out = i18n.t("summary.up_count", "en", count=3)
    assert "{count}" not in out and "3" in out


def test_fallback_cle_inconnue():
    assert i18n.t("cle.inconnue", "en") == "cle.inconnue"


def test_langue_inconnue_retombe_sur_en():
    assert i18n.t("state.up", "xx") == i18n.t("state.up", "en")


def test_pluriel():
    one = i18n.tn("journal.coupure", 1, "fr")
    many = i18n.tn("journal.coupure", 2, "fr")
    assert one != many


def test_etats_traduits():
    assert i18n.t("state.up", "fr") == "Actif"
    assert i18n.t("state.up", "en") == "Running"


def test_zh_traduit():
    assert i18n.t("state.up", "zh") == "运行中"
    assert "个" in i18n.t("summary.up_count", "zh", count=3)
