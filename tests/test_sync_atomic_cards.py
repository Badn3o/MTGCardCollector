from src.sync_atomic_cards import AtomicCardsSync


def test_build_image_url_with_scryfall_id() -> None:
    card = {"identifiers": {"scryfallId": "12345678-aaaa-bbbb-cccc-1234567890ab"}}
    url = AtomicCardsSync._build_image_url(card)
    assert url == "https://cards.scryfall.io/normal/front/1/2/12345678-aaaa-bbbb-cccc-1234567890ab.jpg"


def test_build_image_url_with_multiverse_fallback() -> None:
    card = {"identifiers": {"multiverseId": "9001"}}
    url = AtomicCardsSync._build_image_url(card)
    assert url == "https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=9001&type=card"


def test_build_image_url_none_when_missing_identifiers() -> None:
    card = {"name": "Black Lotus"}
    assert AtomicCardsSync._build_image_url(card) is None
