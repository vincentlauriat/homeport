"""Homeport — application FastAPI.

Deux routes utiles :
  GET /            page HTML (rendue côté serveur, puis rafraîchie en fond par /api/status)
  GET /api/status  état complet en JSON
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__, actions, background, demo, events_watch, i18n, mqtt, status
from . import config as cfg
from .collectors import (
    backups,
    devices,
    docker_api,
    events,
    hardware,
    history,
    identity,
    journal,
    livebox,
    mdns,
    metrics,
    network,
    oui,
    public_ip,
    service_history,
    sessions,
    starlink,
    updates,
    wan,
    wol,
)
from .collectors import system as system_collector
from .links import request_hostname

BASE_DIR = Path(__file__).resolve().parent

# HOMEPORT_DEMO=1 : tout le dashboard sur des données simulées (voir demo.py).
DEMO = os.environ.get("HOMEPORT_DEMO") == "1"

# La doc OpenAPI (Swagger) énumère toute la surface d'API : on ne l'expose pas par défaut,
# seulement quand HOMEPORT_DOCS=1 (développement local).
DOCS_ENABLED = os.environ.get("HOMEPORT_DOCS") == "1"

# Uvicorn ne configure que ses propres loggers. Sans handler sur la racine, les messages de
# Raspberry restent invisibles : seuls les WARNING passent, via le handler de dernier recours de
# `logging`. On perdrait donc la confirmation « connecté au courtier » — exactement ce qu'on
# vient chercher dans le journal quand une intégration ne publie rien.
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
log = logging.getLogger("homeport")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Démarre les mesures lentes en tâche de fond.

    Volontairement ici et pas au moment de l'import : un import du module (test, rechargement
    à chaud d'uvicorn) ne doit pas lancer de boucles de mesure.
    """
    if DEMO:
        log.info("mode démo : données simulées, aucun accès système")
        yield
        return

    health = cfg.load_health()
    intervals = health["intervals"]
    journal_config = health["journal"]

    _safe_init_history_db(cfg.DB_PATH)
    try:
        devices.init_db(cfg.DB_PATH)
        actions.init_db(cfg.DB_PATH)
        wan.init_db(cfg.DB_PATH)
        service_history.init_db(cfg.DB_PATH)
        public_ip.init_db(cfg.DB_PATH)
        events.init_db(cfg.DB_PATH)
        identity.init_db(cfg.DB_PATH)
        metrics.init_db(cfg.DB_PATH)
    except OSError as exc:
        log.warning("inventaire appareils désactivé : %s", exc)

    # Un uptime machine plus jeune que le seuil : ce démarrage suit un boot, pas un
    # simple restart du service — le seul événement écrit sans transition observée.
    try:
        events_watch.boot(cfg.DB_PATH, system_collector.uptime()["seconds"])
    except (sqlite3.Error, OSError) as exc:
        log.warning("livre de bord indisponible au démarrage : %s", exc)

    background.start(
        {
            "backups": (lambda: _to_async(_backups_and_watch, health["backups"]), intervals["backups"]),
            "journal": (
                lambda: journal.collect(
                    since=journal_config.get("since", "24 hours ago"),
                    ignore=journal_config.get("ignore", []),
                ),
                intervals["journal"],
            ),
            "throttling": (_throttling_and_watch, intervals["throttling"]),
            "apt": (updates.apt, intervals["apt"]),
            "docker_images": (updates.docker_images, intervals["docker_images"]),
            "history": (
                lambda: _to_async(_record_history_sample, cfg.DB_PATH, health["history_retention_days"]),
                intervals["history"],
            ),
            "network": (_network_and_track, intervals["network"]),
            "sessions": (sessions.collect, intervals["sessions"]),
            "docker_stats": (_container_cpu, intervals["docker_stats"]),
            "mdns": (_refresh_mdns, intervals["mdns"]),
            "wan": (_wan_probe, intervals["wan"]),
            "service_states": (_record_service_states, intervals["service_states"]),
            "availability": (_availability_stats, intervals["availability"]),
            "public_ip": (_track_public_ip, intervals["public_ip"]),
            "update_check": (updates.latest_release, intervals["update_check"]),
            **({
                "starlink_status": (lambda: starlink.fetch_status(cfg.load_starlink()), intervals["starlink_status"]),
                "starlink_history": (lambda: starlink.fetch_history(cfg.load_starlink()), intervals["starlink_history"]),
                "starlink_map": (lambda: starlink.fetch_map(cfg.load_starlink()), intervals["starlink_map"]),
            } if cfg.load_starlink()["enabled"] else {}),
            **({
                "livebox_status": (_livebox_probe, intervals["livebox_status"]),
            } if cfg.load_livebox()["enabled"] else {}),
        }
    )
    # L'état publié sur MQTT est celui du tableau de bord, lu par le même chemin (donc via le
    # même cache) : les deux ne peuvent pas diverger.
    local_hostname = system_collector.hostname()
    skipped = mqtt.start(cfg.load_mqtt(), local_hostname, lambda: status.build(local_hostname))
    if skipped:
        log.warning("publication MQTT désactivée : %s", skipped)

    try:
        yield
    finally:
        mqtt.stop()
        background.stop()


async def _to_async(function, *args):
    """Enveloppe un collecteur synchrone (lectures de fichiers, rapides) pour le rafraîchisseur."""
    return function(*args)


def _safe_init_history_db(path: Path) -> bool:
    """L'historique est une fonctionnalité optionnelle ; le tableau de bord ne l'est pas.

    Si `init_db` lève ici (ex. `/mnt/ssd` non monté après un reboot), une exception non
    rattrapée dans `lifespan` fait échouer le démarrage d'uvicorn tout entier — précisément le
    moment où l'outil de diagnostic est le plus nécessaire. Le job de fond `history` échouera
    ensuite tout seul, à chaque cycle, via la gestion d'erreur déjà en place dans
    `background._loop`."""
    try:
        history.init_db(path)
        return True
    except OSError as exc:
        log.warning("historique désactivé : %s", exc)
        return False


def _known_container(name: str) -> bool:
    """Le nom correspond-il à un conteneur déclaré dans `services.yaml` ?

    Point d'entrée de la sécurité de `/api/logs/{name}` : le nom vient de l'URL, donc de
    l'utilisateur. Le restreindre à la liste connue empêche qu'un nom forgé (`../../version`)
    ne détourne l'appel vers un autre endpoint du socket Docker."""
    return name in {s.docker for s in cfg.all_services(cfg.load_groups()) if s.docker}


async def _container_cpu() -> dict[str, float]:
    """% CPU de chaque conteneur déclaré — la liste est relue à chaque cycle, comme partout
    ailleurs, pour qu'ajouter un service dans `services.yaml` suffise."""
    names = [s.docker for s in cfg.all_services(cfg.load_groups()) if s.docker]
    return await docker_api.stats(names)


async def _network_and_track() -> dict:
    """Le job réseau existant, plus l'alimentation de l'inventaire : mêmes données, un seul
    passage de sous-processus. L'inventaire est optionnel (base absente = LAN toujours
    visible), le snapshot réseau ne l'est pas."""
    data = await network.collect()
    try:
        created = devices.upsert_seen(cfg.DB_PATH, data.get("lan_neighbors", []))
        events_watch.devices_new(cfg.DB_PATH, created)
    except (sqlite3.Error, OSError) as exc:
        log.warning("inventaire appareils indisponible : %s", exc)
    return data


async def _refresh_mdns() -> int:
    """Résout en mDNS les IP connues de l'inventaire et met les noms en cache. Un nom déjà
    en cache n'est jamais effacé par un échec — l'appareil dort peut-être."""
    try:
        known = devices.list_devices(cfg.DB_PATH)
    except sqlite3.Error:
        return 0
    ips = {d["last_ip"]: d["mac"] for d in known if d["last_ip"]}
    resolved = await mdns.resolve_many(list(ips))
    for ip, name in resolved.items():
        devices.update_meta(cfg.DB_PATH, ips[ip], {"mdns_name": name})
    return len(resolved)


async def _record_service_states() -> int:
    """Un échantillon d'état par service par minute — la matière première de la
    disponibilité. Passe par status.build : exactement les états que le dashboard affiche,
    lus derrière le même cache."""
    snapshot = await status.build("localhost")
    states = {s["id"]: s["state"] for g in snapshot["groups"] for s in g["services"]}
    service_history.record_states(cfg.DB_PATH, states)
    service_history.prune(cfg.DB_PATH, retention_days=7)
    try:
        events_watch.services(cfg.DB_PATH, states)
        events.prune(cfg.DB_PATH, retention_days=365)
    except (sqlite3.Error, OSError) as exc:
        log.warning("livre de bord indisponible : %s", exc)
    return len(states)


async def _availability_stats() -> dict:
    """Statistiques 7 j précalculées toutes les 5 min : la requête parcourt ~150k lignes,
    trop lourd pour le chemin d'une requête, négligeable en tâche de fond."""
    return service_history.stats(cfg.DB_PATH, hours=168)


async def _track_public_ip() -> dict | None:
    """Relevé horaire de l'IP publique — le seul appel sortant de Homeport. Un échec (WAN
    coupé, service indisponible) laisse simplement la dernière valeur connue."""
    ip = await public_ip.fetch()
    if ip is not None:
        try:
            public_ip.track(cfg.DB_PATH, ip)
            events_watch.public_ip(cfg.DB_PATH, ip)
        except (sqlite3.Error, OSError) as exc:
            log.warning("historique IP publique indisponible : %s", exc)
    try:
        return public_ip.current(cfg.DB_PATH)
    except sqlite3.Error:
        return {"ip": ip, "changed_ts": None} if ip else None


async def _wan_probe() -> dict:
    """Mesure la santé Internet et l'historise — les coupures sont dérivées des échantillons
    (voir collectors/wan.py). L'historique est optionnel, la mesure instantanée ne l'est pas."""
    sample = await wan.measure()
    try:
        wan.record(cfg.DB_PATH, sample)
        wan.prune(cfg.DB_PATH, retention_days=7)
        events_watch.wan(cfg.DB_PATH, bool(sample.get("online")))
    except (sqlite3.Error, OSError) as exc:
        log.warning("historique WAN indisponible : %s", exc)
    return sample


async def _livebox_probe() -> dict:
    """État de la box Orange + transition livebox.up/down dans le livre de bord."""
    data = await livebox.fetch_status(cfg.load_livebox())
    try:
        events_watch.livebox(cfg.DB_PATH, bool(data.get("online")))
    except (sqlite3.Error, OSError) as exc:
        log.warning("événement livebox indisponible : %s", exc)
    return data


def _record_history_sample(path: Path, retention_days: int) -> None:
    """Un point d'historique = un instantané de `system.collect()`, pas un nouveau collecteur :
    les mêmes valeurs que la tuile Métriques, juste conservées dans le temps."""
    sample = system_collector.collect(cfg.load_health()["disks"])
    history.record(
        path,
        {
            "cpu_pct": sample["load"]["percent"],
            "mem_pct": sample["memory"]["percent"],
            "temp_c": sample["temperature_c"],
            "nvme_temp_c": sample["storage_temperature_c"],
        },
    )
    history.prune(path, retention_days)
    # Les seaux de l'API v1 sont nourris par le même instantané : un second collecteur
    # produirait deux vérités sur la même mesure.
    try:
        racine = next((d for d in sample["disks"] if d["mount"] == "/"), None)
        metrics.record(
            path,
            {
                "cpu_pct": sample["load"]["percent"],
                "mem_pct": sample["memory"]["percent"],
                "disk_pct": racine["percent"] if racine else None,
                "temp_c": sample["temperature_c"],
            },
        )
        metrics.prune(path)
    except (sqlite3.Error, OSError) as exc:
        log.warning("métriques agrégées indisponibles : %s", exc)
    try:
        events_watch.temperature(path, sample["temperature_c"])
    except (sqlite3.Error, OSError) as exc:
        log.warning("livre de bord (température) indisponible : %s", exc)


def _backups_and_watch(entries: list[dict]) -> list[dict]:
    """Le collecteur backups existant, plus le scribe : mêmes données, un seul passage."""
    data = backups.collect(entries)
    try:
        events_watch.backups(cfg.DB_PATH, data)
    except (sqlite3.Error, OSError) as exc:
        log.warning("livre de bord (backups) indisponible : %s", exc)
    return data


async def _throttling_and_watch() -> dict:
    data = await hardware.throttling()
    try:
        events_watch.throttling(cfg.DB_PATH, data)
    except (sqlite3.Error, OSError) as exc:
        log.warning("livre de bord (alimentation) indisponible : %s", exc)
    return data


app = FastAPI(
    title="Homeport",
    version=__version__,
    docs_url="/api/docs" if DOCS_ENABLED else None,
    # Sans openapi_url, /openapi.json resterait servi et énumérerait toute l'API même Swagger coupé.
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Content-Security-Policy : `frame-ancestors 'none'` (doublé par X-Frame-Options) empêche le
# clickjacking, `default-src 'self'` cloisonne les ressources au même hôte. `script-src`/`style-src`
# gardent `'unsafe-inline'` car plusieurs pages portent des blocs inline (thème, catalogue i18n,
# navigation) ; la discipline XSS côté JS (textContent systématique) reste la première ligne.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", _CSP)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    # `same-origin` (et non `no-referrer`) : conserve le `Referer` en same-origin — le repli du
    # contrôle anti-CSRF reste donc opérant — tout en ne fuitant aucun référent vers un tiers.
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


def _same_origin(request: Request) -> bool:
    """Protège les actions d'écriture contre le CSRF : l'appel doit provenir d'une page Homeport.

    On compare l'hôte de l'en-tête `Origin` (ou `Referer` en repli) à l'hôte de la requête. Un
    POST cross-site — formulaire piégé auto-soumis — porte l'`Origin` de l'attaquant et est rejeté ;
    les `fetch` de l'app, eux, sont same-origin et le navigateur y attache l'`Origin`. Sans aucun
    des deux en-têtes, on refuse."""
    host = request.headers.get("host")
    if not host:
        return False
    source = request.headers.get("origin") or request.headers.get("referer")
    if not source:
        return False
    return urlsplit(source).netloc == host


def _request_lang(request: Request | None) -> str | None:
    """Langue du cookie navigateur si elle est connue, sinon None (→ config serveur)."""
    if request is None:
        return None
    cookie = request.cookies.get("homeport_lang")
    return cookie if cookie in i18n.SUPPORTED else None


def _i18n_context(request: Request | None = None) -> dict:
    """Contexte de rendu commun : `t` pour Jinja, le catalogue sérialisé pour le JS,
    et le flag Starlink pour la barre de navigation partagée (_nav.html).

    La langue vient du cookie du navigateur quand il porte une valeur connue — chacun la
    sienne (sélecteur du pied de page) — sinon de la config serveur. MQTT et les capteurs
    Home Assistant restent sur la langue de la config : un cookie ne les concerne pas."""
    lang = _request_lang(request) or cfg.load_language()
    return {
        "t": lambda key, **variables: i18n.t(key, lang, **variables),
        "lang": lang,
        # `<` échappé en < : une chaîne de traduction contenant « </script> » ne peut pas
        # clore le bloc <script> inline où ce JSON est injecté (défense en profondeur ; le
        # catalogue vient des fichiers serveur, jamais de l'utilisateur).
        "i18n_json": json.dumps(i18n.catalog(lang), ensure_ascii=False).replace("<", "\\u003c"),
        "starlink_enabled": DEMO or cfg.load_starlink()["enabled"],
        "livebox_enabled": DEMO or cfg.load_livebox()["enabled"],
        # Identité affichée en haut à gauche de chaque page (nom court, sans domaine).
        "hostname": "demo" if DEMO else system_collector.hostname().split(".")[0],
    }


def _hostname(request: Request) -> str:
    """Hôte par lequel le navigateur a joint Homeport — c'est lui qui détermine les liens."""
    return request_hostname(
        request.headers.get("host"),
        fallback=request.url.hostname or "localhost",
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    data = await (demo.build if DEMO else status.build)(_hostname(request), _request_lang(request))
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={**data, "version": __version__, **_i18n_context(request)},
    )


@app.get("/reseau", response_class=HTMLResponse)
async def reseau(request: Request) -> HTMLResponse:
    """La page Réseau est rendue vide puis peuplée par /api/devices — contrairement à
    index.html (rendu serveur), tout y est dynamique et éditable : le JS est la seule source
    de rendu, pas de double implémentation Jinja + JS à maintenir."""
    return templates.TemplateResponse(
        request=request, name="reseau.html", context={"version": __version__, **_i18n_context(request)}
    )


@app.get("/api/status")
async def api_status(request: Request) -> JSONResponse:
    return JSONResponse(await (demo.build if DEMO else status.build)(_hostname(request), _request_lang(request)))


@app.get("/api/history")
async def api_history(hours: float = 24.0) -> JSONResponse:
    if DEMO:
        return JSONResponse(demo.history(hours))
    try:
        samples = await _to_async(history.query_range, cfg.DB_PATH, hours)
    except sqlite3.Error:
        # L'historique peut être désactivé (voir `_safe_init_history_db`) sans que le reste du
        # tableau de bord en souffre : une fenêtre vide plutôt qu'une erreur 500.
        samples = []
    return JSONResponse(samples)


@app.get("/api/devices")
async def api_devices() -> JSONResponse:
    if DEMO:
        return JSONResponse(demo.devices())
    raw = background.snapshot().get("network")
    live = (raw.get("data") if raw else None) or {}
    online_macs = {devices.normalize_mac(n["mac"]) for n in live.get("lan_neighbors", [])}
    try:
        inventory = devices.list_devices(cfg.DB_PATH)
        available = True
    except sqlite3.Error:
        inventory, available = [], False

    enriched = []
    for device in inventory:
        vendor = oui.vendor(device["mac"])
        label, source = devices.display_name(device, vendor)
        enriched.append(
            {
                **device,
                "online": device["mac"] in online_macs,
                "vendor": vendor,
                "local_mac": oui.is_local_mac(device["mac"]),
                "display_name": label,
                "name_source": source,
            }
        )

    return JSONResponse(
        {
            "devices": enriched,
            "tailscale_peers": live.get("tailscale_peers", []),
            "summary": {
                "total": len(enriched),
                "online": sum(1 for d in enriched if d["online"]),
                "new": sum(1 for d in enriched if not d["acknowledged"]),
            },
            "inventory_available": available,
        }
    )


# Bornes du PATCH : le corps vient du navigateur, donc de n'importe qui sur le LAN.
_PATCH_LIMITS = {"name": 64, "note": 500}


@app.patch("/api/devices/{mac}")
async def api_patch_device(mac: str, payload: dict = Body(...)) -> JSONResponse:  # noqa: B008
    """Seul endpoint d'écriture du projet : nom, note, catégorie, acquittement d'un appareil.

    Pas d'authentification — assumé tant que le service n'est joignable que du LAN et de
    Tailscale (audit 2026-08-19). Toute exposition plus large imposerait une auth d'abord."""
    normalized = devices.normalize_mac(mac)
    if normalized is None:
        return JSONResponse({"error": "MAC malformée"}, status_code=404)

    fields: dict = {}
    for key, value in payload.items():
        if key in ("name", "note"):
            if value is not None and (not isinstance(value, str) or len(value) > _PATCH_LIMITS[key]):
                return JSONResponse({"error": f"{key} invalide"}, status_code=422)
            fields[key] = (value.strip() or None) if isinstance(value, str) else None
        elif key == "category":
            if value is not None and value not in devices.CATEGORIES:
                return JSONResponse({"error": "catégorie inconnue"}, status_code=422)
            fields[key] = value
        elif key == "acknowledged":
            if not isinstance(value, bool):
                return JSONResponse({"error": "acknowledged doit être booléen"}, status_code=422)
            fields[key] = 1 if value else 0
        else:
            return JSONResponse({"error": f"champ inconnu : {key}"}, status_code=422)

    try:
        updated = devices.update_meta(cfg.DB_PATH, normalized, fields)
    except sqlite3.Error:
        return JSONResponse({"error": "inventaire indisponible"}, status_code=503)
    if not updated:
        return JSONResponse({"error": "appareil inconnu"}, status_code=404)
    return JSONResponse({"ok": True})


async def _can_act(request: Request) -> bool:
    """La requête vient-elle de l'admin, par le tailnet ? Voir app/actions.py — le LAN reste
    strictement lecture seule, quel que soit l'utilisateur."""
    admin = cfg.load_actions()["admin"]
    client_ip = request.client.host if request.client else ""
    return await actions.authorize(client_ip, admin)


@app.get("/api/whoami")
async def api_whoami(request: Request) -> JSONResponse:
    return JSONResponse({"can_act": await _can_act(request)})


@app.get("/api/actions")
async def api_actions(request: Request) -> JSONResponse:
    try:
        journal_rows = actions.recent(cfg.DB_PATH)
    except sqlite3.Error:
        journal_rows = []
    # L'identité de l'admin (login Tailscale) n'est révélée qu'à l'admin lui-même : un lecteur
    # LAN non authentifié ne doit pas récupérer l'e-mail ni la chronologie nominative des gestes.
    if not await _can_act(request):
        for row in journal_rows:
            row.pop("identity", None)
    return JSONResponse({"actions": journal_rows})


@app.post("/api/actions/restart/{service_id}")
async def api_restart(service_id: str, request: Request) -> JSONResponse:
    if not _same_origin(request):
        return JSONResponse({"error": "origine de la requête invalide"}, status_code=403)
    if not await _can_act(request):
        return JSONResponse({"error": "action réservée à l'admin via Tailscale"}, status_code=403)
    restartables = {s.id: s for s in cfg.all_services(cfg.load_groups()) if s.restartable}
    service = restartables.get(service_id)
    if service is None:
        return JSONResponse({"error": "service inconnu ou non redémarrable"}, status_code=404)
    ok = await actions.restart(service)
    admin = cfg.load_actions()["admin"] or "?"
    try:
        actions.record(cfg.DB_PATH, admin, "restart", service_id, ok)
    except sqlite3.Error:
        pass
    status_code = 200 if ok else 502
    return JSONResponse({"ok": ok}, status_code=status_code)


@app.post("/api/actions/wake/{mac}")
async def api_wake(mac: str, request: Request) -> JSONResponse:
    if not _same_origin(request):
        return JSONResponse({"error": "origine de la requête invalide"}, status_code=403)
    if not await _can_act(request):
        return JSONResponse({"error": "action réservée à l'admin via Tailscale"}, status_code=403)
    normalized = devices.normalize_mac(mac)
    known = {d["mac"] for d in devices.list_devices(cfg.DB_PATH)} if normalized else set()
    if normalized is None or normalized not in known:
        return JSONResponse({"error": "appareil inconnu"}, status_code=404)
    wol.send(normalized)
    admin = cfg.load_actions()["admin"] or "?"
    try:
        actions.record(cfg.DB_PATH, admin, "wake", normalized, True)
    except sqlite3.Error:
        pass
    return JSONResponse({"ok": True})


@app.get("/historique", response_class=HTMLResponse)
async def historique(request: Request) -> HTMLResponse:
    """Courbes 7 jours (CPU/mémoire/température) avec les coupures Internet surimprimées —
    voir la corrélation, pas deux listes. Page dynamique, peuplée par /api/history."""
    return templates.TemplateResponse(
        request=request, name="historique.html", context={"version": __version__, **_i18n_context(request)}
    )


# Les trois vues candidates de la refonte v1.0 — coquilles peuplées côté client par
# /api/status (même pattern que /reseau et /historique) ; le sélecteur de vue présent sur
# chacune permet de passer de l'une à l'autre pendant l'évaluation.
@app.get("/controle", response_class=HTMLResponse)
async def vue_controle(request: Request) -> HTMLResponse:
    """Vue A — salle de contrôle : dense, deux colonnes, tableau de services."""
    return templates.TemplateResponse(
        request=request, name="controle.html", context={"version": __version__, **_i18n_context(request)}
    )


@app.get("/journal", response_class=HTMLResponse)
async def vue_journal(request: Request) -> HTMLResponse:
    """Vue B — le journal de la maison : verdict, attention, faits."""
    return templates.TemplateResponse(
        request=request, name="journal.html", context={"version": __version__, **_i18n_context(request)}
    )


@app.get("/mur", response_class=HTMLResponse)
async def vue_mur(request: Request) -> HTMLResponse:
    """Vue C — le mur : tablette murale, chiffres géants, horloge."""
    return templates.TemplateResponse(
        request=request, name="mur.html", context={"version": __version__, **_i18n_context(request)}
    )


@app.get("/starlink", response_class=HTMLResponse)
async def vue_starlink(request: Request) -> HTMLResponse:
    """Page complète de l'antenne Starlink — même pattern coquille + JS que /reseau."""
    return templates.TemplateResponse(
        request=request, name="starlink.html", context={"version": __version__, **_i18n_context(request)}
    )


@app.get("/api/starlink")
async def api_starlink() -> JSONResponse:
    if DEMO:
        return JSONResponse(demo.starlink())
    settings = cfg.load_starlink()
    if not settings["enabled"]:
        return JSONResponse({"enabled": False, "status": None, "history": None, "map": None})
    snapshot = background.snapshot()

    def data(key):
        entry = snapshot.get(key)
        return entry.get("data") if entry else None

    return JSONResponse({
        "enabled": True,
        "status": data("starlink_status"),
        "history": data("starlink_history"),
        "map": data("starlink_map"),
    })


@app.get("/livebox", response_class=HTMLResponse)
async def vue_livebox(request: Request) -> HTMLResponse:
    """Page de la box Orange — même pattern coquille + JS que /starlink."""
    return templates.TemplateResponse(
        request=request, name="livebox.html", context={"version": __version__, **_i18n_context(request)}
    )


@app.get("/api/livebox")
async def api_livebox() -> JSONResponse:
    if DEMO:
        return JSONResponse(demo.livebox())
    if not cfg.load_livebox()["enabled"]:
        return JSONResponse({"enabled": False, "status": None})
    entry = background.snapshot().get("livebox_status")
    return JSONResponse({"enabled": True, "status": entry.get("data") if entry else None})


@app.get("/api/outages")
async def api_outages(hours: float = 24.0) -> JSONResponse:
    if DEMO:
        return JSONResponse(demo.outages(hours))
    try:
        result = wan.outages(cfg.DB_PATH, hours=hours)
    except sqlite3.Error:
        result = []
    return JSONResponse({"outages": result})


@app.get("/livre-de-bord", response_class=HTMLResponse)
async def livre_de_bord(request: Request) -> HTMLResponse:
    """Le livre de bord : la chronique des événements marquants — transitions de services,
    pannes Internet, appareils inconnus, gestes d'admin — peuplée par /api/events."""
    return templates.TemplateResponse(
        request=request, name="livrebord.html", context={"version": __version__, **_i18n_context(request)}
    )


@app.get("/api/events")
async def api_events(
    request: Request, days: float = 7, limit: int = 200, kinds: str | None = None
) -> JSONResponse:
    """Le livre de bord : événements consignés + actions admin, fusionnés à la lecture.

    La table `actions` reste l'autorité des actions (elle sert aussi /api/actions) ; les
    dupliquer dans `events` créerait deux vérités. `kinds` filtre par préfixes de famille,
    séparés par des virgules (« service.,internet. »)."""
    days = max(0.25, min(days, 365.0))
    limit = max(1, min(limit, 1000))
    prefixes = [k.strip() for k in kinds.split(",") if k.strip()] if kinds else None
    if DEMO:
        return JSONResponse({"events": demo.events(days=days, limit=limit, kinds=prefixes)})
    try:
        rows = events.query(cfg.DB_PATH, days=days, kinds=prefixes, limit=limit)
    except sqlite3.Error:
        rows = []
    if prefixes is None or any(p.startswith("action") for p in prefixes):
        cutoff = time.time() - days * 86400
        # `detail` porte le login Tailscale de l'admin : réservé à l'admin, masqué pour le LAN.
        show_identity = await _can_act(request)
        try:
            for act in actions.recent(cfg.DB_PATH, limit=limit):
                if act["ts"] < cutoff:
                    break  # recent est trié du plus récent au plus ancien
                rows.append(
                    {
                        "ts": act["ts"],
                        "kind": f"action.{act['kind']}",
                        "severity": "up" if act["ok"] else "down",
                        "subject": act["target"],
                        "detail": act["identity"] if show_identity else None,
                    }
                )
        except sqlite3.Error:
            pass
        rows.sort(key=lambda e: e["ts"], reverse=True)
        rows = rows[:limit]
    return JSONResponse({"events": rows})


@app.get("/api/logs/{name}")
async def api_logs(name: str, tail: int = 100) -> JSONResponse:
    if not _known_container(name):
        return JSONResponse({"error": "conteneur inconnu"}, status_code=404)
    tail = max(1, min(tail, 1000))
    return JSONResponse({"logs": await docker_api.logs(name, tail)})


# — API v1 —————————————————————————————————————————————————————————————————————
#
# Contrat inter-dépôts : `docs/api/homeport-api-v1.md` dans HomePortManager, dont ce dépôt garde
# la source de vérité. Ces routes s'ajoutent aux routes non versionnées ci-dessus, qui servent le
# front web et ne bougent pas. `/healthz` reste indépendant de `capabilities` : le premier est le
# diagnostic interrogé par SSH, le second la poignée de main du contrat HTTP.

#: Version du contrat servi. À incrémenter avec le document, jamais séparément.
API_V1_CONTRACT = "1.0.0"

_V1_UNAVAILABLE = {"error": "historique indisponible"}


def _int_param(raw: str | None, default: int, low: int, high: int) -> int:
    """Le contrat impose de ramener dans les bornes plutôt que de rejeter, et de retomber sur le
    défaut si la valeur est illisible. D'où des paramètres reçus en texte : la validation
    automatique de FastAPI répondrait 422 là où le contrat exige une réponse servie."""
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(low, min(value, high))


@app.get("/api/v1/capabilities")
async def api_v1_capabilities() -> JSONResponse:
    try:
        current = identity.epoch(cfg.DB_PATH)
    except (sqlite3.Error, OSError) as exc:
        log.warning("capabilities indisponible : %s", exc)
        return JSONResponse(_V1_UNAVAILABLE, status_code=503)
    return JSONResponse(
        {
            "contract": API_V1_CONTRACT,
            "server": __version__,
            "epoch": current,
            "features": ["events", "metrics"],
        }
    )


@app.get("/api/v1/events")
async def api_v1_events(
    since_id: str | None = None,
    since_epoch: str | None = None,
    limit: str | None = None,
    severity: str | None = None,
) -> JSONResponse:
    """Lecture par curseur : identifiants croissants, `latest_id` à chaque réponse.

    Les actions administratives ne sont pas fusionnées ici, contrairement à `/api/events` : elles
    portent leur propre séquence d'identifiants, et les mêler casserait la monotonie sur laquelle
    le curseur d'un client repose.
    """
    cursor = _int_param(since_id, 0, 0, 2**63 - 1)
    page = _int_param(limit, 200, 1, 1000)
    severities = [s.strip() for s in severity.split(",") if s.strip()] if severity else None

    try:
        current = identity.epoch(cfg.DB_PATH)
        # Un curseur d'une autre génération ne veut rien dire ici : on sert depuis le début et
        # on annonce l'epoch courant, au client d'en tirer les conséquences. Jamais une erreur.
        if since_epoch is not None and since_epoch != current:
            cursor = 0
        # Une ligne de plus que demandé : `has_more` devient exact, filtre compris.
        rows = events.query_since(cfg.DB_PATH, since_id=cursor, limit=page + 1, severities=severities)
        newest = events.latest_id(cfg.DB_PATH)
    except (sqlite3.Error, OSError) as exc:
        log.warning("événements v1 indisponibles : %s", exc)
        return JSONResponse(_V1_UNAVAILABLE, status_code=503)

    has_more = len(rows) > page
    return JSONResponse(
        {"epoch": current, "latest_id": newest, "events": rows[:page], "has_more": has_more}
    )


@app.get("/api/v1/metrics")
async def api_v1_metrics(scale: str = Query("24h", alias="range")) -> JSONResponse:
    """Une plage inconnue est le seul 400 du contrat : aucune valeur voisine n'aurait de sens."""
    if scale not in metrics.SCALES:
        connues = ", ".join(metrics.SCALES)
        return JSONResponse(
            {"error": f"range inconnu : {scale} (attendu : {connues})"}, status_code=400
        )
    try:
        current = identity.epoch(cfg.DB_PATH)
        data = metrics.series(cfg.DB_PATH, scale)
    except (sqlite3.Error, OSError) as exc:
        log.warning("métriques v1 indisponibles : %s", exc)
        return JSONResponse(_V1_UNAVAILABLE, status_code=503)
    return JSONResponse({"epoch": current, **data})


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "version": __version__}
