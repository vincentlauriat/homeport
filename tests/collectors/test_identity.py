"""L'epoch de l'historique : stable tant que la base l'est, neuf dès qu'elle est remplacée.

Ces tests portent sur la seule chose que l'epoch doit garantir au client : deux générations
distinctes de l'historique ne partagent jamais un epoch. Le cas central — une base restaurée
depuis une archive — est reproduit en écrasant réellement le fichier.
"""
import shutil
from pathlib import Path

from homeport.collectors import identity


def test_epoch_stable_entre_deux_lectures(tmp_path: Path):
    db = tmp_path / "history.db"
    assert identity.epoch(db) == identity.epoch(db)


def test_deux_bases_neuves_ont_des_epochs_distincts(tmp_path: Path):
    a = identity.epoch(tmp_path / "a.db")
    b = identity.epoch(tmp_path / "b.db")
    assert a != b


def test_une_base_restauree_produit_un_nouvel_epoch(tmp_path: Path):
    """Le cas que le contrat cherche à rendre visible : `hpm restore` remet en place une base
    d'hier, dont l'epoch reviendrait avec elle si rien ne le détectait."""
    db = tmp_path / "history.db"
    ancien = identity.epoch(db)
    archive = tmp_path / "archive.db"
    shutil.copy(db, archive)  # sauvegarde prise à cet instant

    # La base vit sa vie et change d'identité (réinitialisation explicite entre-temps).
    identity.regenerate(db)

    # Puis on restaure l'archive PAR-DESSUS, comme le ferait hpm : la sentinelle, elle, reste.
    shutil.copy(archive, db)

    nouveau = identity.epoch(db)
    assert nouveau != ancien, "l'epoch de l'archive ne doit pas ressusciter tel quel"
    assert identity.epoch(db) == nouveau, "et le nouvel epoch doit être stable à son tour"


def test_sentinelle_absente_n_est_pas_une_restauration(tmp_path: Path):
    """Un `/var` nettoyé ou une première montée après mise à jour efface la sentinelle sans que
    la base ait bougé. Inventer un nouvel epoch là ferait repartir tous les clients de zéro."""
    db = tmp_path / "history.db"
    initial = identity.epoch(db)
    identity._sentinel_path(db).unlink()

    assert identity.epoch(db) == initial
    assert identity._sentinel_path(db).exists(), "la sentinelle est réécrite au passage"


def test_regenerate_change_l_epoch_et_la_sentinelle(tmp_path: Path):
    db = tmp_path / "history.db"
    avant = identity.epoch(db)
    apres = identity.regenerate(db)

    assert apres != avant
    assert identity._sentinel_path(db).read_text(encoding="utf-8") == apres
    assert identity.epoch(db) == apres


def test_sentinelle_vide_traitee_comme_absente(tmp_path: Path):
    """Une écriture interrompue laisse un fichier vide ; le lire comme un epoch valide ferait
    diverger base et sentinelle à chaque appel."""
    db = tmp_path / "history.db"
    initial = identity.epoch(db)
    identity._sentinel_path(db).write_text("", encoding="utf-8")

    assert identity.epoch(db) == initial
