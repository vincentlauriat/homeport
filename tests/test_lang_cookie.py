"""Sélection de langue par navigateur : le cookie `homeport_lang` gagne quand il est
connu, sinon la config serveur — chacun sa langue, y compris la tablette murale."""
from fastapi.testclient import TestClient

from homeport import main


def client() -> TestClient:
    # Pas de lifespan : ni jobs de fond ni MQTT dans les tests.
    return TestClient(main.app)


def test_cookie_fr_rend_la_page_en_francais():
    http = client()
    http.cookies.set("homeport_lang", "fr")
    text = http.get("/livre-de-bord").text
    assert "Livre de bord" in text
    assert 'lang="fr"' in text


def test_cookie_zh_retire_est_ignore():
    # `zh` n'est plus offert : un cookie posé avant le retrait doit être ignoré comme
    # n'importe quelle langue inconnue, pas rendre une page à moitié traduite.
    http = client()
    http.cookies.set("homeport_lang", "zh")
    text = http.get("/livre-de-bord").text
    assert 'lang="zh"' not in text


def test_cookie_inconnu_ignore():
    http = client()
    http.cookies.set("homeport_lang", "klingon")
    text = http.get("/livre-de-bord").text
    assert 'lang="klingon"' not in text  # repli sur la config serveur


VUES = ("/", "/controle", "/journal", "/mur", "/reseau", "/historique", "/starlink", "/livebox", "/livre-de-bord")


def test_selecteurs_presents_sur_toutes_les_pages():
    http = client()
    for path in VUES:
        text = http.get(path).text
        assert 'id="pref-lang"' in text, path
        assert 'id="pref-theme"' in text, path
        assert "homeport_theme" in text, path  # script anti-flash dans le <head>


def test_lien_d_evitement_sur_toutes_les_pages():
    """Sans lui, le clavier retraverse les neuf onglets de nav avant d'atteindre le
    contenu, sur chaque page (WCAG 2.4.1). Il doit précéder la nav et viser un <main>
    qui existe — un lien d'évitement pointant dans le vide est pire que pas de lien."""
    http = client()
    for path in VUES:
        text = http.get(path).text
        assert 'class="skip-link" href="#main"' in text, path
        assert '<main id="main"' in text, path
        assert text.index("skip-link") < text.index("view-switch"), path


def test_le_mur_n_affiche_plus_l_ip_publique():
    """Le Mur est l'écran le plus exposé du produit : allumé en permanence dans une pièce
    partagée, visible des invités. Il était le seul à afficher l'IP publique en clair alors
    que le produit masque par ailleurs l'identité LAN. Elle reste sur Contrôle et Réseau."""
    http = client()
    mur = http.get("/mur").text
    assert 'id="wf-ip"' not in mur
    assert 'id="wf-starlink"' not in mur
    assert 'id="wf-livebox"' not in mur
    # Toujours disponible là où l'écran n'est pas permanent et le texte se lit de près.
    assert "public_ip" in http.get("/controle").text


def test_le_mur_porte_un_mot_d_etat_par_tuile():
    """L'état ne peut pas tenir à la seule couleur du chiffre (WCAG 1.4.1) : chaque tuile
    porteuse d'état a un emplacement pour le mot, que `mur.js` remplit en `warn`/`down`."""
    http = client()
    mur = http.get("/mur").text
    assert mur.count('class="cell-state"') == 5, "5 tuiles portent un état (la 6e est la sparkline CPU)"


def test_le_mur_annonce_le_verdict_et_lui_seul():
    """`aria-live` restreint à la ligne de verdict : le porter sur les tuiles ferait
    réannoncer les six à chaque sondage de 5 s."""
    http = client()
    mur = http.get("/mur").text
    assert 'id="w-state-text" aria-live="polite"' in mur
    assert mur.count('aria-live') == 1


def test_le_journal_ne_saute_aucun_niveau_de_titre():
    """Le bloc « À regarder » émet des `h3` ; sans titre de section il les glissait entre le
    `h1` de la page et son premier `h2` (WCAG 1.3.1). Y injecter les services en panne
    aggravait le saut au lieu de le corriger — d'où le `h2` propre au bloc."""
    http = client()
    journal = http.get("/journal").text
    section = journal.index('id="j-attention-section"')
    machine = journal.index('journal.machine') if 'journal.machine' in journal else None
    assert '<h2 class="edit-h2">' in journal[section:section + 400], (
        "le bloc attention doit porter son propre h2 avant ses cartes h3"
    )
    assert machine is None or section < machine


def test_le_journal_n_a_qu_une_zone_vive():
    """`role="status"` sur le seul verdict. Le bloc attention se reconstruit entièrement à
    chaque sondage : l'y poser ferait réannoncer toutes ses cartes toutes les 5 s."""
    http = client()
    journal = http.get("/journal").text
    assert journal.count('role="status"') == 1
    assert 'aria-live' not in journal


def test_le_journal_replie_les_services_mais_dit_le_lien_rompu():
    """Deux décisions liées : la liste des quinze services se replie quand elle ne fait que
    confirmer le titre, et le démenti du lien vit sous le verdict — au pied de page, une
    tablette figée sur « Tout va bien » mentirait hors du regard."""
    http = client()
    journal = http.get("/journal").text
    assert '<details class="edit-services"' in journal
    assert 'id="j-services-summary"' in journal
    lien = journal.index('id="j-link"')
    pied = journal.index("<footer>")
    assert lien < pied, "la ligne de lien appartient au verdict, pas au pied de page"
