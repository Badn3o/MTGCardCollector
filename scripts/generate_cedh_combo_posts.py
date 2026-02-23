from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote_plus

import requests

COMBOS = [
    {"name": "Thassa's Oracle + Demonic Consultation", "cards": ["Thassa's Oracle", "Demonic Consultation"], "win_condition": "Victoria inmediata por biblioteca vacía.", "how": "Con el trigger de Thassa's Oracle en la pila, se lanza Demonic Consultation nombrando una carta ausente para exiliar casi toda la biblioteca. Al resolver el trigger, la devoción azul supera las cartas en biblioteca (0), ganando la partida.", "interaction": ["Counter al Oracle o al Consultation.", "Stifle/Disallow al trigger de Oracle.", "Silence effects y Rule of Law dificultan la ventana de combo."]},
    {"name": "Thassa's Oracle + Tainted Pact", "cards": ["Thassa's Oracle", "Tainted Pact"], "win_condition": "Victoria inmediata por biblioteca vacía.", "how": "Con base de maná singleton, Tainted Pact exilia la biblioteca hasta dejar 0-1 cartas con el trigger de Oracle en pila. Oracle resuelve y cumple la condición de victoria.", "interaction": ["Counter al Oracle/Pact.", "Stifle al trigger de Oracle.", "Opposition Agent o Drannith pueden frenar líneas de tutor previas."]},
    {"name": "Underworld Breach + Lion's Eye Diamond + Brain Freeze", "cards": ["Underworld Breach", "Lion's Eye Diamond", "Brain Freeze"], "win_condition": "Storm letal o auto-mill infinito hacia win determinista.", "how": "Con Breach en mesa, se castea LED del cementerio, se sacrifica para mana y se relanza Brain Freeze objetivo a uno mismo para recargar cementerio. Repetición genera storm infinito y permite deckear rivales o transicionar a Oracle.", "interaction": ["Hate de cementerio (Endurance, Dauthi, RIP).", "Counter a Breach/Brain Freeze.", "Stony Silence/Collector Ouphe limita LED."]},
    {"name": "Kiki-Jiki, Mirror Breaker + Zealous Conscripts", "cards": ["Kiki-Jiki, Mirror Breaker", "Zealous Conscripts"], "win_condition": "Infinitas criaturas con prisa para daño letal en combate.", "how": "Kiki copia Zealous; el token endereza Kiki al entrar. Se repite para crear infinitos Conscripts con prisa y atacar letal.", "interaction": ["Removal instantáneo a Kiki en respuesta al primer activado.", "Cursed Totem/Torpor Orb apagan la línea.", "Fog effects fuerzan pase de turno."]},
    {"name": "Kiki-Jiki, Mirror Breaker + Felidar Guardian", "cards": ["Kiki-Jiki, Mirror Breaker", "Felidar Guardian"], "win_condition": "Infinitos tokens con prisa y kill por combate.", "how": "Kiki copia a Felidar; el token blinkea a Kiki y vuelve enderezado como nuevo objeto. Se itera para infinitos Felidar token.", "interaction": ["Removal instantáneo a Kiki o Felidar.", "Torpor Orb anula ETB de Felidar.", "Linvala/Cursed Totem corta activaciones."]},
    {"name": "Kiki-Jiki, Mirror Breaker + Village Bell-Ringer", "cards": ["Kiki-Jiki, Mirror Breaker", "Village Bell-Ringer"], "win_condition": "Infinitas copias con prisa para letal de combate.", "how": "Kiki copia Bell-Ringer; el token endereza todas tus criaturas, incluido Kiki. Repetición infinita = ejército letal.", "interaction": ["Removal sobre Kiki.", "Torpor Orb evita el enderezar.", "Ensnaring Bridge puede frenar daño."]},
    {"name": "Splinter Twin + Deceiver Exarch", "cards": ["Splinter Twin", "Deceiver Exarch"], "win_condition": "Tokens infinitos con prisa.", "how": "Twin encantando Exarch crea token copia con prisa; ETB del token endereza el Exarch encantado. Se repite para infinitos atacantes.", "interaction": ["Removal al objetivo de Twin en respuesta al aura.", "Disenchant sobre Splinter Twin.", "Torpor Orb corta ETB."]},
    {"name": "Splinter Twin + Pestermite", "cards": ["Splinter Twin", "Pestermite"], "win_condition": "Infinitos tokens con prisa y daño de combate.", "how": "Twin sobre Pestermite genera token; ETB del token endereza la criatura encantada y habilita nuevo activado.", "interaction": ["Removal en respuesta al primer activado.", "Counter a Splinter Twin.", "Torpor Orb/Hushbringer."]},
    {"name": "Heliod, Sun-Crowned + Walking Ballista", "cards": ["Heliod, Sun-Crowned", "Walking Ballista"], "win_condition": "Daño infinito a mesa/rivales.", "how": "Con Ballista al menos de 2 contadores y lifelink por Heliod, quitas contador para hacer daño, ganas vida y Heliod repone contador +1/+1, habilitando loop infinito.", "interaction": ["Removal a Ballista en respuesta a lifelink trigger.", "Stifle al trigger de Heliod.", "Pithing Needle sobre Ballista."]},
    {"name": "Mikaeus, the Unhallowed + Walking Ballista", "cards": ["Mikaeus, the Unhallowed", "Walking Ballista"], "win_condition": "Daño infinito.", "how": "Ballista sin contadores muere y vuelve con undying por Mikaeus con un contador +1/+1; se remueve contador para dañar y repetir sacrificando/descargando Ballista.", "interaction": ["Exilio al morir (Swords, Path).", "Hate anti-graveyard.", "Removal sobre Mikaeus."]},
    {"name": "Mikaeus, the Unhallowed + Triskelion", "cards": ["Mikaeus, the Unhallowed", "Triskelion"], "win_condition": "Daño infinito repartido.", "how": "Triskelion entra con contadores, se quitan para dañar y uno a sí mismo para morir; undying lo regresa con contador extra. Repite para daño arbitrario.", "interaction": ["Graveyard hate.", "Stifle al undying trigger.", "Removal a Mikaeus."]},
    {"name": "Sanguine Bond + Exquisite Blood", "cards": ["Sanguine Bond", "Exquisite Blood"], "win_condition": "Loop infinito de pérdida/ganancia de vida.", "how": "Cualquier pérdida de vida del oponente dispara Exquisite Blood y luego Sanguine Bond, creando bucle que reduce a todos los rivales a 0.", "interaction": ["Disenchant a cualquiera de los encantamientos en respuesta al primer trigger.", "Narset-like prevention no corta, pero Angel's Grace sí evita morir ese turno.", "Counter a la segunda pieza."]},
    {"name": "Painter's Servant + Grindstone", "cards": ["Painter's Servant", "Grindstone"], "win_condition": "Milling completo de bibliotecas.", "how": "Painter hace todas las cartas del mismo color; Grindstone repite molienda mientras comparten color, deckeando por completo al objetivo.", "interaction": ["Removal a Painter en respuesta a activación.", "Stony Silence/Ouphe sobre Grindstone.", "Shuffle titan effects pueden retrasar kill."]},
    {"name": "Food Chain + Misthollow Griffin", "cards": ["Food Chain", "Misthollow Griffin"], "win_condition": "Maná infinito de criatura para castear wincon.", "how": "Exilias Griffin con Food Chain por más maná del que cuesta y lo casteas desde exilio repetidamente para producir maná neto infinito restringido a criaturas.", "interaction": ["Counter/disenchant a Food Chain.", "Drannith Magistrate evita castear desde exilio.", "Containment Priest complica líneas de ETB posteriores."]},
    {"name": "Food Chain + Eternal Scourge", "cards": ["Food Chain", "Eternal Scourge"], "win_condition": "Maná infinito de criatura.", "how": "Scourge puede castearse desde exilio; con Food Chain se genera maná neto positivo en loop hasta infinito.", "interaction": ["Removal a Food Chain.", "Drannith Magistrate.", "Counter a la pieza criatura."]},
    {"name": "Food Chain + Squee, the Immortal", "cards": ["Food Chain", "Squee, the Immortal"], "win_condition": "Maná infinito de criatura.", "how": "Squee se recastea desde exilio/gy; con Food Chain produce ciclo de maná neto positivo infinito.", "interaction": ["Drannith Magistrate.", "Disenchant a Food Chain.", "Rule of Law limita recasteos."]},
    {"name": "Isochron Scepter + Dramatic Reversal", "cards": ["Isochron Scepter", "Dramatic Reversal"], "win_condition": "Maná infinito y/o activaciones infinitas.", "how": "Con rocas/dorks que produzcan al menos 3 manás, activas Scepter para copiar Dramatic y enderezar permanentes, quedando maná neto positivo por ciclo.", "interaction": ["Artifact removal en respuesta a activación.", "Collector Ouphe/Stony Silence.", "Null Rod corta el combo completo."]},
    {"name": "Basalt Monolith + Rings of Brighthearth", "cards": ["Basalt Monolith", "Rings of Brighthearth"], "win_condition": "Maná incoloro infinito.", "how": "Pagas para enderezar Basalt y copias activación con Rings; resolución correcta deja Basalt enderezado con maná neto positivo. Repite a infinito.", "interaction": ["Artifact removal.", "Null Rod effects.", "Pithing Needle sobre Basalt."]},
    {"name": "Grim Monolith + Power Artifact", "cards": ["Grim Monolith", "Power Artifact"], "win_condition": "Maná incoloro infinito.", "how": "Power Artifact reduce coste de enderezar Grim por debajo de su producción, generando neto positivo infinito al girar/enderezar.", "interaction": ["Disenchant a Power Artifact.", "Null Rod/Ouphe.", "Counter a pieza de aura."]},
    {"name": "Basalt Monolith + Power Artifact", "cards": ["Basalt Monolith", "Power Artifact"], "win_condition": "Maná infinito.", "how": "La reducción de coste permite que Basalt produzca más maná del que requiere para enderezarse, iterando a infinito.", "interaction": ["Removal a artefacto/aura.", "Stony Silence.", "Counter a Power Artifact."]},
    {"name": "Palinchron + High Tide", "cards": ["Palinchron", "High Tide"], "win_condition": "Maná azul infinito y cierre con outlet.", "how": "Con High Tide activo y suficientes islas, Palinchron endereza tierras al entrar; al devolverlo a mano y recastearlo se genera maná neto positivo repetible.", "interaction": ["Counter a High Tide/Palinchron.", "Removal en respuesta al trigger.", "Damping effects en tierras."]},
    {"name": "Peregrine Drake + Deadeye Navigator", "cards": ["Peregrine Drake", "Deadeye Navigator"], "win_condition": "Maná infinito de tierras.", "how": "Soulbond permite blinkear Drake por 1U; al reentrar endereza 5 tierras. Si esas tierras producen >2, hay maná neto positivo infinito.", "interaction": ["Removal a Deadeye en respuesta a soulbond/activación.", "Torpor Orb.", "Cursed Totem no afecta aquí, pero Hushbringer sí."]},
    {"name": "Freed from the Real + Bloom Tender", "cards": ["Freed from the Real", "Bloom Tender"], "win_condition": "Maná infinito de colores presentes en permanentes.", "how": "Bloom Tender produce múltiples colores; Freed permite pagar U para enderezarlo. Si produce al menos UG (u otro neto >1), se obtiene infinito.", "interaction": ["Removal a Bloom Tender.", "Disenchant a Freed.", "Cursed Totem."]},
    {"name": "Freed from the Real + Faeburrow Elder", "cards": ["Freed from the Real", "Faeburrow Elder"], "win_condition": "Maná infinito.", "how": "Faeburrow con suficientes colores produce >=2 manás; Freed lo endereza por U y deja neto positivo por ciclo.", "interaction": ["Removal a Elder.", "Disenchant a aura.", "Cursed Totem."]},
    {"name": "Devoted Druid + Vizier of Remedies", "cards": ["Devoted Druid", "Vizier of Remedies"], "win_condition": "Maná verde infinito.", "how": "Druid intenta ponerse contador -1/-1 para enderezarse; Vizier reduce el contador que recibiría, permitiendo enderezar sin coste real y generar G infinito.", "interaction": ["Removal a cualquiera de las criaturas.", "Cursed Totem.", "Grafdigger no afecta, pero Linvala sí."]},
    {"name": "Devoted Druid + Swift Reconfiguration", "cards": ["Devoted Druid", "Swift Reconfiguration"], "win_condition": "Maná verde infinito.", "how": "Al volverse Vehículo, Devoted Druid ya no es criatura y no puede recibir -1/-1 counters; aun así conserva habilidad de enderezar, habilitando loop infinito de G.", "interaction": ["Removal al aura o al Druid.", "Pithing Needle en Druid.", "Counter al aura."]},
    {"name": "Hermit Druid + Dread Return + Thassa's Oracle", "cards": ["Hermit Druid", "Dread Return", "Thassa's Oracle"], "win_condition": "Auto-mill total y victoria por Oracle.", "how": "Hermit Druid muele toda la biblioteca en listas sin básicas; luego Dread Return reanima Oracle desde cementerio para ganar con biblioteca vacía.", "interaction": ["Graveyard hate instantáneo.", "Removal al Druid antes de activar.", "Stifle al trigger de Oracle."]},
    {"name": "Cephalid Illusionist + Nomads en-Kor", "cards": ["Cephalid Illusionist", "Nomads en-Kor"], "win_condition": "Auto-mill completo hacia línea de reanimación/Oracle.", "how": "Nomads puede redirigir daño infinitas veces al Illusionist, disparando su habilidad de moler 3 por objetivo. Se muele toda la biblioteca y se cierra con payoff de cementerio.", "interaction": ["Removal a Illusionist en respuesta a primeras activaciones.", "Hate de cementerio.", "Cursed Totem limita activaciones de criaturas."]},
    {"name": "Necrotic Ooze + Phyrexian Devourer + Walking Ballista", "cards": ["Necrotic Ooze", "Phyrexian Devourer", "Walking Ballista"], "win_condition": "Daño letal desde cementerio con Ooze.", "how": "Con Devourer y Ballista en cementerio, Ooze gana ambas habilidades: exilia cartas para ganar poder/contadores y convierte esos contadores en daño directo.", "interaction": ["Graveyard hate antes de resolver Ooze.", "Removal al Ooze.", "Stifle a habilidad crítica."]},
    {"name": "Razaketh, the Foulblooded + Reanimate loop", "cards": ["Razaketh, the Foulblooded", "Reanimate"], "win_condition": "Cadena de tutores hasta win determinista.", "how": "Reanimate acelera Razaketh; sacrificando criaturas/tokens se tutorean piezas exactas (rituales, protección, Oracle/Breach) para cerrar en el mismo turno.", "interaction": ["Grave hate para frenar reanimación.", "Removal a Razaketh en respuesta a primer tutor.", "Opposition Agent castiga tutores."]},
    {"name": "Protean Hulk pile", "cards": ["Protean Hulk"], "win_condition": "Tutor en cadena hacia kill inmediata (Oracle/Kiki/Ballista según pile).", "how": "Al morir Hulk busca criaturas por CMC total 6 o menos; piles optimizadas ensamblan un loop de daño, maná o Oracle en resolución encadenada.", "interaction": ["Exilio en lugar de morir (Swords, Endurance).", "Hate de cementerio.", "Stifle al trigger de Hulk."]},
    {"name": "Boonweaver Giant + Pattern of Rebirth", "cards": ["Boonweaver Giant", "Pattern of Rebirth"], "win_condition": "Cadena de reanimación/ETB que termina en kill (Blood Artist/Altar/etc.).", "how": "Boonweaver busca y equipa auras clave desde biblioteca/cementerio; con sac outlet genera loop de ETB/LTB hasta ensamblar condición letal.", "interaction": ["Removal al outlet o al Giant.", "Graveyard hate.", "Disenchant a Pattern/Necromancy."]},
    {"name": "Karmic Guide + Reveillark + Sac outlet", "cards": ["Karmic Guide", "Reveillark"], "win_condition": "Loop infinito de ETB/LTB con payoff letal.", "how": "Sacrificando Reveillark vuelven Guide + otra pieza; Guide reanima Reveillark y se repite. Con Blood Artist/Altar/Ballista se convierte en victoria.", "interaction": ["Graveyard hate en respuesta al trigger.", "Removal al sac outlet.", "Torpor Orb."]},
    {"name": "Niv-Mizzet, Parun + Curiosity", "cards": ["Niv-Mizzet, Parun", "Curiosity"], "win_condition": "Daño infinito por robo de cartas.", "how": "Niv hace daño al robar; Curiosity roba al hacer daño. Se crea bucle de robo-daño hasta matar a la mesa.", "interaction": ["Removal a Niv en respuesta al aura/primer trigger.", "Counter al encantamiento.", "Narset-like draw prevention corta loop."]},
    {"name": "Niv-Mizzet, Parun + Ophidian Eye", "cards": ["Niv-Mizzet, Parun", "Ophidian Eye"], "win_condition": "Bucle infinito de daño/robo.", "how": "Misma lógica que Curiosity: cada ping roba carta y cada carta dispara nuevo ping.", "interaction": ["Removal/counter en ventana de resolver aura.", "Hushbringer no aplica; draw-hate sí.", "Stifle a trigger puntual puede comprar turno."]},
    {"name": "Niv-Mizzet, Parun + Tandem Lookout", "cards": ["Niv-Mizzet, Parun", "Tandem Lookout"], "win_condition": "Daño infinito por soulbond.", "how": "Con soulbond activo, daño de Niv roba cartas y cada carta vuelve a disparar daño, cerrando partida.", "interaction": ["Removal a cualquiera antes de conectar soulbond.", "Counter al Lookout.", "Effects que impidan robo."]},
    {"name": "Malcolm, Keen-Eyed Navigator + Glint-Horn Buccaneer", "cards": ["Malcolm, Keen-Eyed Navigator", "Glint-Horn Buccaneer"], "win_condition": "Loop de daño y tesoros infinitos en combate.", "how": "Al hacer daño y descartar con Buccaneer, Malcolm crea tesoros; esos tesoros pagan nuevos activados de Buccaneer para repetir daño/discard hasta matar mesa.", "interaction": ["Removal en combate a Buccaneer.", "Stony Silence limita uso de tesoros.", "Ghostly Prison puede frenar fase de combate."]},
    {"name": "Magda, Brazen Outlaw + Clock of Omens", "cards": ["Magda, Brazen Outlaw", "Clock of Omens"], "win_condition": "Tesoros infinitos y tutor repetido de artefacto/dragón hacia win.", "how": "Con suficientes artefactos en mesa, Clock endereza fuentes para generar más tesoros con Magda; al acumular 5 repetidamente, Magda tutoriza piezas de cierre.", "interaction": ["Artifact hate sobre Clock.", "Cursed Totem impide activar Magda.", "Null Rod reduce conversión de tesoros."]},
    {"name": "Godo, Bandit Warlord + Helm of the Host", "cards": ["Godo, Bandit Warlord", "Helm of the Host"], "win_condition": "Fases de combate infinitas.", "how": "Helm crea token no legendario de Godo al comienzo de combate; cada Godo nuevo da fase de combate adicional, repitiendo indefinidamente para letal.", "interaction": ["Removal a Helm antes del combate.", "Artifact hate/counter al equipar.", "Fog effects fuerzan turno extra de intento."]},
    {"name": "Winota combo lines", "cards": ["Winota, Joiner of Forces", "Kiki-Jiki, Mirror Breaker"], "win_condition": "Snowball de triggers de Winota hacia lock/combo de combate.", "how": "Ataques con no-humanos disparan Winota y colocan humanos clave gratis (hatebears o piezas combo), construyendo ventaja explosiva que deriva en kill por combate o lock irreversible.", "interaction": ["Removal a Winota antes de declarar atacantes.", "Blind Obedience/Propaganda reducen presión.", "Board wipes tempranos."]},
    {"name": "Emry + Mirran Spy + 0-mana artifact", "cards": ["Emry, Lurker of the Loch", "Mirran Spy", "Mox Amber"], "win_condition": "Cast infinito de artefacto para storm/ETB/outlet.", "how": "Emry recastea artefacto de coste 0 desde cementerio; Mirran Spy endereza Emry al lanzar artefacto. Con fuente de maná/beneficio, se repite infinito para Brain Freeze, Aetherflux o similares.", "interaction": ["Grave hate.", "Removal a Emry/Spy.", "Null Rod limita el artefacto de maná."]},
    {"name": "Hullbreaker Horror + mana rocks", "cards": ["Hullbreaker Horror", "Sol Ring"], "win_condition": "Maná/valor infinito y eventual lock total de mesa.", "how": "Con dos rocas y suficiente maná inicial, cada hechizo permite rebotar otra roca/permanente, creando cadena de recasteo que genera ventaja infinita y limpia permanentes rivales.", "interaction": ["Counter o removal a Hullbreaker antes de priority loop.", "Null Rod/Ouphe limitan rocas.", "Rule of Law corta secuencia."]},
    {"name": "Displacer Kitten + The One Ring", "cards": ["Displacer Kitten", "The One Ring"], "win_condition": "Motor de ventaja masiva que deriva en win por recursos/combo secundario.", "how": "Cada hechizo no criatura blinkea permanentes no tierra; con The One Ring se reinicia contador burden y se roba gran volumen de cartas, encontrando wincon protegida.", "interaction": ["Removal a Kitten en respuesta a primer trigger.", "Stifle al trigger de blink.", "Rule of Law reduce explosividad."]},
    {"name": "Teferi, Time Raveler + Knowledge Pool", "cards": ["Teferi, Time Raveler", "Knowledge Pool"], "win_condition": "Hard lock: oponentes no pueden resolver hechizos.", "how": "Knowledge Pool exilia hechizo y permite castear otro gratis, pero Teferi impide a rivales castear a velocidad instantánea fuera de sus ventanas; el resultado práctico es lock de casteo rival.", "interaction": ["Removal a Teferi o Pool antes de ensamblar lock.", "Counter a la segunda pieza.", "Habilidades activadas/ataques aún rompen estancamiento."]},
    {"name": "Possibility Storm + Drannith Magistrate", "cards": ["Possibility Storm", "Drannith Magistrate"], "win_condition": "Soft lock: rivales casi no pueden castear hechizos desde mano.", "how": "Storm exilia hechizo y obliga a castear otro desde biblioteca; Drannith impide lanzar hechizos desde zonas no mano, por lo que la resolución deja a rivales sin spell efectivo.", "interaction": ["Removal a Drannith en respuesta al primer hechizo.", "Disenchant a Storm.", "Habilidades de permanentes siguen funcionando."]},
    {"name": "Lavinia, Azorius Renegade + Knowledge Pool", "cards": ["Lavinia, Azorius Renegade", "Knowledge Pool"], "win_condition": "Lock de casteo para oponentes.", "how": "Knowledge Pool intenta permitir lanzamiento gratis del exilio; Lavinia contrarresta hechizos lanzados sin pagar maná, cerrando la capacidad de castear de rivales.", "interaction": ["Removal puntual a Lavinia.", "Artifact removal a Pool.", "Counter a la pieza final."]},
    {"name": "Worldgorger Dragon + Animate Dead", "cards": ["Worldgorger Dragon", "Animate Dead"], "win_condition": "Maná infinito de permanentes no tierra + outlet letal.", "how": "Animate Dead reanima Worldgorger; ETB del dragón exilia tus permanentes (incluido Animate Dead), lo que sacrifica dragón y devuelve todo enderezado. Repite para maná infinito con tierras/rocas y finaliza con outlet (Comet Storm/Oracle/etc.).", "interaction": ["Removal al dragón en momento incorrecto puede forzar empate/board exile temporal.", "Grave hate corta reanimación.", "Stifle a trigger crítico."]},
    {"name": "Auriok Salvagers + Lion's Eye Diamond", "cards": ["Auriok Salvagers", "Lion's Eye Diamond"], "win_condition": "Maná blanco infinito + storm.", "how": "LED se sacrifica por 3 manás; Salvagers lo regresa por 1W. Si eliges blanco y repites, generas maná neto positivo infinito para cerrar con Walking Ballista/Breach/Oracle lines.", "interaction": ["Artifact hate sobre LED.", "Removal a Salvagers.", "Drannith no afecta, pero Rule of Law complica cierre."]},
    {"name": "Abdel Adrian, Gorion's Ward + Animate Dead", "cards": ["Abdel Adrian, Gorion's Ward", "Animate Dead"], "win_condition": "ETB/LTB loop infinito con tokens/valor y outlet letal.", "how": "Animate Dead reanima Abdel, que exilia otros permanentes propios (incluido Animate bajo ciertas líneas), forzando su salida/entrada repetida. Con Blood Artist/Altar genera win determinista.", "interaction": ["Removal en respuesta al trigger de Abdel.", "Graveyard hate.", "Torpor Orb corta ETB."]},
    {"name": "Bolas's Citadel + Sensei's Divining Top + Aetherflux Reservoir", "cards": ["Bolas's Citadel", "Sensei's Divining Top", "Aetherflux Reservoir"], "win_condition": "Vida infinita efectiva + disparos de 50 de Aetherflux.", "how": "Con Citadel puedes lanzar Top desde biblioteca pagando vida; Top roba y se recoloca arriba, permitiendo casteos repetidos que incrementan storm y vida vía Reservoir hasta activar 50 daño a cada rival.", "interaction": ["Artifact/enchantment removal a cualquiera de las tres piezas.", "Stony Silence limita Top.", "Counter a Citadel/Reservoir antes de estabilizar."]},
]

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

SOURCES = {
    "EDHTop16": "https://edhtop16.com/search?cards={query}",
    "Moxfield": "https://www.moxfield.com/decks/public?q={query}",
    "MTGTop8": "https://mtgtop8.com/search?MD_check=1&SB_check=1&cards={query}",
    "cEDH Decklist Database": "https://cedh-decklist-database.com/",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def fetch_url_excerpt(url: str) -> str:
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        return re.sub(r"\s+", " ", response.text[:240])
    except Exception as exc:
        return f"No disponible por limitación de red/proxy: {exc}"


def build_sources(cards: list[str]) -> list[dict[str, str]]:
    query = quote_plus(" ".join(cards))
    rows = []
    for source_name, template in SOURCES.items():
        url = template.format(query=query)
        rows.append({"name": source_name, "url": url, "excerpt": fetch_url_excerpt(url)})
    return rows


def build_post(rank: int, combo: dict, banned_cards: list[str], sources: list[dict[str, str]]) -> str:
    banned_text = "Ninguna" if not banned_cards else ", ".join(banned_cards)
    status = "✅ Válido en Commander" if not banned_cards else "❌ Inválido para Commander"
    source_list = "".join([
        f"<li><strong>{s['name']}:</strong> {s['url']}<br/><em>{s['excerpt']}</em></li>" for s in sources
    ])
    interactions = "".join([f"<li>{item}</li>" for item in combo["interaction"]])
    cards = "".join([f"<li>{card}</li>" for card in combo["cards"]])
    return f"""<!-- wp:heading -->
<h2>Top {rank} cEDH: {combo['name']}</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p><strong>Estado de legalidad:</strong> {status}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Cartas en ban list detectadas:</strong> {banned_text}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Condición de victoria:</strong> {combo['win_condition']}</p>
<!-- /wp:paragraph -->

<!-- wp:heading {{"level":3}} -->
<h3>Cartas del combo</h3>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>{cards}</ul>
<!-- /wp:list -->

<!-- wp:heading {{"level":3}} -->
<h3>Línea exacta de ejecución</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{combo['how']}</p>
<!-- /wp:paragraph -->

<!-- wp:heading {{"level":3}} -->
<h3>Puntos de interacción específicos</h3>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>{interactions}</ul>
<!-- /wp:list -->

<!-- wp:heading {{"level":3}} -->
<h3>Fuentes especializadas consultadas (scraping)</h3>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>{source_list}</ul>
<!-- /wp:list -->
"""


def main() -> None:
    out_dir = Path("wordpress/combos")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old_file in out_dir.glob("*.md"):
        old_file.unlink()

    report = []
    for idx, combo in enumerate(COMBOS, start=1):
        cards = combo["cards"]
        banned_cards = sorted([card for card in cards if card in BANNED])
        sources = build_sources(cards)
        post_path = out_dir / f"{idx:02d}-{slugify(combo['name'])}.md"
        post_path.write_text(build_post(idx, combo, banned_cards, sources), encoding="utf-8")
        report.append({
            "rank": idx,
            "combo": combo["name"],
            "cards": cards,
            "win_condition": combo["win_condition"],
            "banned_cards": banned_cards,
            "valid": len(banned_cards) == 0,
            "post_file": str(post_path),
            "sources": [{"name": s["name"], "url": s["url"]} for s in sources],
        })

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
        "## Resultado por combo (con condición de victoria)",
        "",
    ]
    for r in report:
        status = "✅" if r["valid"] else "❌"
        banned = ", ".join(r["banned_cards"]) if r["banned_cards"] else "Ninguna"
        summary.append(f"- {status} #{r['rank']:02d} {r['combo']} — Wincon: {r['win_condition']} — Ban list: {banned} — Post: `{r['post_file']}`")

    Path("docs_cedh_combo_validation.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
