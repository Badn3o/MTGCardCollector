from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote_plus

import requests

# Top 50 cEDH combos (legal en Commander) actualizado para excluir cartas baneadas.
COMBOS = [
    ("Thassa's Oracle + Demonic Consultation", ["Thassa's Oracle", "Demonic Consultation"]),
    ("Thassa's Oracle + Tainted Pact", ["Thassa's Oracle", "Tainted Pact"]),
    ("Underworld Breach + Lion's Eye Diamond + Brain Freeze", ["Underworld Breach", "Lion's Eye Diamond", "Brain Freeze"]),
    ("Kiki-Jiki, Mirror Breaker + Zealous Conscripts", ["Kiki-Jiki, Mirror Breaker", "Zealous Conscripts"]),
    ("Kiki-Jiki, Mirror Breaker + Felidar Guardian", ["Kiki-Jiki, Mirror Breaker", "Felidar Guardian"]),
    ("Kiki-Jiki, Mirror Breaker + Village Bell-Ringer", ["Kiki-Jiki, Mirror Breaker", "Village Bell-Ringer"]),
    ("Splinter Twin + Deceiver Exarch", ["Splinter Twin", "Deceiver Exarch"]),
    ("Splinter Twin + Pestermite", ["Splinter Twin", "Pestermite"]),
    ("Heliod, Sun-Crowned + Walking Ballista", ["Heliod, Sun-Crowned", "Walking Ballista"]),
    ("Mikaeus, the Unhallowed + Walking Ballista", ["Mikaeus, the Unhallowed", "Walking Ballista"]),
    ("Mikaeus, the Unhallowed + Triskelion", ["Mikaeus, the Unhallowed", "Triskelion"]),
    ("Sanguine Bond + Exquisite Blood", ["Sanguine Bond", "Exquisite Blood"]),
    ("Painter's Servant + Grindstone", ["Painter's Servant", "Grindstone"]),
    ("Food Chain + Misthollow Griffin", ["Food Chain", "Misthollow Griffin"]),
    ("Food Chain + Eternal Scourge", ["Food Chain", "Eternal Scourge"]),
    ("Food Chain + Squee, the Immortal", ["Food Chain", "Squee, the Immortal"]),
    ("Isochron Scepter + Dramatic Reversal", ["Isochron Scepter", "Dramatic Reversal"]),
    ("Basalt Monolith + Rings of Brighthearth", ["Basalt Monolith", "Rings of Brighthearth"]),
    ("Grim Monolith + Power Artifact", ["Grim Monolith", "Power Artifact"]),
    ("Basalt Monolith + Power Artifact", ["Basalt Monolith", "Power Artifact"]),
    ("Palinchron + High Tide", ["Palinchron", "High Tide"]),
    ("Peregrine Drake + Deadeye Navigator", ["Peregrine Drake", "Deadeye Navigator"]),
    ("Freed from the Real + Bloom Tender", ["Freed from the Real", "Bloom Tender"]),
    ("Freed from the Real + Faeburrow Elder", ["Freed from the Real", "Faeburrow Elder"]),
    ("Devoted Druid + Vizier of Remedies", ["Devoted Druid", "Vizier of Remedies"]),
    ("Devoted Druid + Swift Reconfiguration", ["Devoted Druid", "Swift Reconfiguration"]),
    ("Hermit Druid + Dread Return + Thassa's Oracle", ["Hermit Druid", "Dread Return", "Thassa's Oracle"]),
    ("Cephalid Illusionist + Nomads en-Kor", ["Cephalid Illusionist", "Nomads en-Kor"]),
    ("Necrotic Ooze + Phyrexian Devourer + Walking Ballista", ["Necrotic Ooze", "Phyrexian Devourer", "Walking Ballista"]),
    ("Razaketh, the Foulblooded + Reanimate loop", ["Razaketh, the Foulblooded", "Reanimate"]),
    ("Protean Hulk pile", ["Protean Hulk"]),
    ("Boonweaver Giant + Pattern of Rebirth", ["Boonweaver Giant", "Pattern of Rebirth"]),
    ("Karmic Guide + Reveillark + Sac outlet", ["Karmic Guide", "Reveillark"]),
    ("Niv-Mizzet, Parun + Curiosity", ["Niv-Mizzet, Parun", "Curiosity"]),
    ("Niv-Mizzet, Parun + Ophidian Eye", ["Niv-Mizzet, Parun", "Ophidian Eye"]),
    ("Niv-Mizzet, Parun + Tandem Lookout", ["Niv-Mizzet, Parun", "Tandem Lookout"]),
    ("Malcolm, Keen-Eyed Navigator + Glint-Horn Buccaneer", ["Malcolm, Keen-Eyed Navigator", "Glint-Horn Buccaneer"]),
    ("Magda, Brazen Outlaw + Clock of Omens", ["Magda, Brazen Outlaw", "Clock of Omens"]),
    ("Godo, Bandit Warlord + Helm of the Host", ["Godo, Bandit Warlord", "Helm of the Host"]),
    ("Winota combo lines", ["Winota, Joiner of Forces", "Kiki-Jiki, Mirror Breaker"]),
    ("Emry + Mirran Spy + 0-mana artifact", ["Emry, Lurker of the Loch", "Mirran Spy", "Mox Amber"]),
    ("Hullbreaker Horror + mana rocks", ["Hullbreaker Horror", "Sol Ring"]),
    ("Displacer Kitten + The One Ring", ["Displacer Kitten", "The One Ring"]),
    ("Teferi, Time Raveler + Knowledge Pool", ["Teferi, Time Raveler", "Knowledge Pool"]),
    ("Possibility Storm + Drannith Magistrate", ["Possibility Storm", "Drannith Magistrate"]),
    ("Lavinia, Azorius Renegade + Knowledge Pool", ["Lavinia, Azorius Renegade", "Knowledge Pool"]),
    ("Worldgorger Dragon + Animate Dead", ["Worldgorger Dragon", "Animate Dead"]),
    ("Auriok Salvagers + Lion's Eye Diamond", ["Auriok Salvagers", "Lion's Eye Diamond"]),
    ("Abdel Adrian, Gorion's Ward + Animate Dead", ["Abdel Adrian, Gorion's Ward", "Animate Dead"]),
    ("Bolas's Citadel + Sensei's Divining Top + Aetherflux Reservoir", ["Bolas's Citadel", "Sensei's Divining Top", "Aetherflux Reservoir"]),
]

# Commander ban list snapshot (incluye actualizaciones Sept 2024: Dockside, Jeweled Lotus, Mana Crypt, Nadu).
BANNED = {
    "Ancestral Recall", "Balance", "Biorhythm", "Black Lotus", "Braids, Cabal Minion", "Chaos Orb",
    "Channel", "Coalition Victory", "Dockside Extortionist", "Emrakul, the Aeons Torn", "Erayo, Soratami Ascendant",
    "Falling Star", "Fastbond", "Flash", "Gifts Ungiven", "Griselbrand", "Hullbreacher", "Iona, Shield of Emeria",
    "Jeweled Lotus", "Karakas", "Leovold, Emissary of Trest", "Library of Alexandria", "Limited Resources",
    "Lutri, the Spellchaser", "Mana Crypt", "Mox Emerald", "Mox Jet", "Mox Pearl", "Mox Ruby", "Mox Sapphire",
    "Nadu, Winged Wisdom", "Panoptic Mirror", "Paradox Engine", "Primeval Titan", "Prophet of Kruphix",
    "Recurring Nightmare", "Rofellos, Llanowar Emissary", "Shahrazad", "Sundering Titan", "Sway of the Stars",
    "Sylvan Primordial", "Time Vault", "Time Walk", "Tinker", "Tolarian Academy", "Trade Secrets", "Upheaval",
    "Yawgmoth's Bargain",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def fetch_spellbook_snippet(cards: list[str]) -> tuple[str, str]:
    query = quote_plus(" + ".join(cards))
    url = f"https://commanderspellbook.com/search/?q={query}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        snippet = re.sub(r"\s+", " ", response.text[:320])
        return url, snippet
    except Exception as exc:
        return url, f"No disponible por limitación de red/proxy: {exc}"


def build_post(rank: int, combo_name: str, cards: list[str], banned_cards: list[str], source_url: str, source_excerpt: str) -> str:
    banned_text = "Ninguna" if not banned_cards else ", ".join(banned_cards)
    status = "✅ Válido en Commander" if not banned_cards else "❌ Inválido para Commander"
    return f"""<!-- wp:heading -->
<h2>Top {rank} cEDH: {combo_name}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p><strong>Estado de legalidad:</strong> {status}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Cartas en ban list detectadas:</strong> {banned_text}</p>
<!-- /wp:paragraph -->

<!-- wp:heading {{\"level\":3}} -->
<h3>Cartas del combo</h3>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>
{''.join([f'<li>{card}</li>' for card in cards])}
</ul>
<!-- /wp:list -->

<!-- wp:heading {{\"level\":3}} -->
<h3>Cómo funciona</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Este paquete busca ensamblar {combo_name} para producir una condición de victoria inmediata, maná infinito o control de mesa suficiente para cerrar la partida en una mesa cEDH.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {{\"level\":3}} -->
<h3>Puntos de interacción</h3>
<!-- /wp:heading -->

<!-- wp:list -->
<ul><li>Countermagic al hechizo crítico.</li><li>Removal instantáneo sobre la pieza criatura/artefacto clave.</li><li>Hate pieces de cementerio o de lanzamiento según la línea.</li></ul>
<!-- /wp:list -->

<!-- wp:heading {{\"level\":3}} -->
<h3>Fuente scrapeada</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p><strong>URL:</strong> {source_url}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Extracto:</strong> {source_excerpt}</p>
<!-- /wp:paragraph -->
"""


def main() -> None:
    out_dir = Path("wordpress/combos")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old_file in out_dir.glob("*.md"):
        old_file.unlink()

    report = []
    for idx, (name, cards) in enumerate(COMBOS, start=1):
        banned_cards = sorted([card for card in cards if card in BANNED])
        source_url, source_excerpt = fetch_spellbook_snippet(cards)
        post_path = out_dir / f"{idx:02d}-{slugify(name)}.md"
        post_path.write_text(build_post(idx, name, cards, banned_cards, source_url, source_excerpt), encoding="utf-8")
        report.append(
            {
                "rank": idx,
                "combo": name,
                "cards": cards,
                "banned_cards": banned_cards,
                "valid": len(banned_cards) == 0,
                "post_file": str(post_path),
                "source_url": source_url,
            }
        )

    Path("data/cedh_combo_validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    valid = sum(1 for r in report if r["valid"])
    invalid = len(report) - valid
    summary = [
        "# Validación de combos cEDH vs ban list de Commander",
        "",
        "- Nota: se excluyeron líneas con cartas baneadas (incluyendo Dockside Extortionist).",
        f"- Total combos analizados: {len(report)}",
        f"- Válidos: {valid}",
        f"- Inválidos: {invalid}",
        "",
        "## Resultado por combo",
        "",
    ]
    for r in report:
        status = "✅" if r["valid"] else "❌"
        banned = ", ".join(r["banned_cards"]) if r["banned_cards"] else "Ninguna"
        summary.append(f"- {status} #{r['rank']:02d} {r['combo']} — Ban list: {banned} — Post: `{r['post_file']}`")

    Path("docs_cedh_combo_validation.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
