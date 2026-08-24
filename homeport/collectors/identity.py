"""L'epoch de l'historique : l'identité d'une génération de `history.db`.

Le contrat API v1 (voir `docs/api/homeport-api-v1.md` dans HomePortManager) fait de l'epoch la
moitié gauche du curseur `(epoch, id)` d'un client. Sa règle : deux générations distinctes de
l'historique ne partagent jamais un epoch, et toute restauration en produit une nouvelle.

Homeport n'a pas de chemin de restauration à lui — c'est `hpm restore` qui remet la base en place,
depuis une autre machine. L'epoch ne peut donc pas être régénéré par un geste local : il doit
**constater** la substitution. D'où le fichier sentinelle posé à côté de la base : restaurer
`history.db` ramène l'epoch de l'archive, mais laisse la sentinelle intacte. Les deux divergent, et
c'est ce désaccord — pas une notification — qui déclenche la régénération.

Les deux copies ne peuvent redevenir cohérentes à tort que si la restauration remplace la base
*et* la sentinelle. `latest_id`, servi à chaque réponse d'événements, reste le garde-fou de ce
dernier cas : un identifiant qui recule invalide le curseur du client même sous un epoch familier.
"""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history_identity (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    epoch TEXT NOT NULL
)
"""


def _sentinel_path(path: Path) -> Path:
    """La sentinelle vit à côté de la base, sous le même nom suffixé `.epoch`."""
    return path.with_suffix(path.suffix + ".epoch")


def _read_sentinel(path: Path) -> str | None:
    try:
        value = _sentinel_path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _write_sentinel(path: Path, epoch: str) -> None:
    """Écriture atomique : une sentinelle tronquée ferait passer une base saine pour restaurée."""
    sentinel = _sentinel_path(path)
    tmp = sentinel.with_suffix(sentinel.suffix + ".tmp")
    try:
        tmp.write_text(epoch, encoding="utf-8")
        tmp.replace(sentinel)
    except OSError:
        # Une sentinelle absente est un état géré (voir `epoch`) : mieux vaut la perdre que
        # d'empêcher le démarrage d'un outil de diagnostic.
        tmp.unlink(missing_ok=True)


def _stored_epoch(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT epoch FROM history_identity WHERE id = 1").fetchone()
    return row[0] if row else None


def _store_epoch(conn: sqlite3.Connection, epoch: str) -> None:
    conn.execute(
        "INSERT INTO history_identity (id, epoch) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET epoch = excluded.epoch",
        (epoch,),
    )


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(_SCHEMA)


def epoch(path: Path) -> str:
    """L'epoch courant, régénéré si la base et sa sentinelle ne s'accordent pas.

    Quatre situations, toutes normales :
    - base et sentinelle d'accord : l'epoch est rendu tel quel ;
    - base neuve, aucun epoch : un epoch est créé ;
    - sentinelle absente (première montée après mise à jour, `/var` nettoyé) : l'epoch de la base
      fait foi et la sentinelle est réécrite — un fichier manquant n'est pas une preuve de
      restauration ;
    - désaccord franc : la base a été remplacée, un nouvel epoch est émis.
    """
    init_db(path)
    with sqlite3.connect(path) as conn:
        stored = _stored_epoch(conn)
        sentinel = _read_sentinel(path)

        if stored is not None and sentinel is not None and stored == sentinel:
            return stored

        if stored is not None and sentinel is None:
            _write_sentinel(path, stored)
            return stored

        current = uuid.uuid4().hex if stored is None or sentinel is not None else stored
        _store_epoch(conn, current)

    _write_sentinel(path, current)
    return current


def regenerate(path: Path) -> str:
    """Force une nouvelle génération. Pour un chemin de réinitialisation explicite."""
    init_db(path)
    fresh = uuid.uuid4().hex
    with sqlite3.connect(path) as conn:
        _store_epoch(conn, fresh)
    _write_sentinel(path, fresh)
    return fresh
