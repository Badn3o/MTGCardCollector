"""Monitor de TicketSwap para detectar nuevas entradas y notificar por Telegram."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

NEXT_DATA_PATTERN = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


@dataclass(frozen=True)
class Listing:
    listing_id: str
    title: str
    price: str
    quantity: str
    url: str


def _extract_next_data_json(html: str) -> dict[str, Any]:
    match = NEXT_DATA_PATTERN.search(html)
    if not match:
        raise ValueError("No se encontró __NEXT_DATA__ en la página de TicketSwap")
    payload = match.group(1).strip()
    return json.loads(payload)


def _iter_nodes(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _iter_nodes(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_nodes(value)


def _looks_like_listing(node: dict[str, Any]) -> bool:
    keys = set(node.keys())
    return (
        ("url" in keys or "href" in keys)
        and ("price" in keys or "formatted_price" in keys)
        and ("id" in keys or "listing_id" in keys)
    )


def _to_listing(node: dict[str, Any], event_url: str) -> Listing:
    listing_id = str(node.get("id") or node.get("listing_id") or "")
    title = str(node.get("title") or node.get("name") or "Entrada")

    price_value = node.get("formatted_price")
    if not price_value:
        raw_price = node.get("price")
        currency = node.get("currency") or "EUR"
        price_value = f"{raw_price} {currency}" if raw_price is not None else "N/D"

    quantity_value = node.get("number_of_tickets") or node.get("quantity") or "N/D"

    raw_url = node.get("url") or node.get("href") or ""
    if raw_url.startswith("http"):
        listing_url = raw_url
    elif raw_url.startswith("/"):
        listing_url = f"https://www.ticketswap.com{raw_url}"
    else:
        listing_url = event_url

    return Listing(
        listing_id=listing_id or f"fallback-{hash(listing_url)}",
        title=title,
        price=str(price_value),
        quantity=str(quantity_value),
        url=listing_url,
    )


def fetch_listings(event_url: str, timeout_seconds: int = 20) -> list[Listing]:
    response = requests.get(event_url, timeout=timeout_seconds)
    response.raise_for_status()

    next_data = _extract_next_data_json(response.text)

    listings: list[Listing] = []
    seen: set[str] = set()

    for node in _iter_nodes(next_data):
        if not isinstance(node, dict) or not _looks_like_listing(node):
            continue
        listing = _to_listing(node, event_url)
        if listing.listing_id in seen:
            continue
        seen.add(listing.listing_id)
        listings.append(listing)

    return listings


def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        endpoint,
        json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
        timeout=15,
    )
    resp.raise_for_status()


def _format_listing_message(listing: Listing) -> str:
    return (
        "🎟️ Nueva entrada detectada en TicketSwap\n"
        f"- Título: {listing.title}\n"
        f"- Precio: {listing.price}\n"
        f"- Cantidad: {listing.quantity}\n"
        f"- Link: {listing.url}"
    )


def monitor_loop() -> None:
    event_url = os.getenv("TICKETSWAP_EVENT_URL", "").strip()
    poll_seconds = int(os.getenv("TICKETSWAP_POLL_SECONDS", "15"))
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not event_url:
        raise RuntimeError("Falta TICKETSWAP_EVENT_URL en el archivo .env")
    if not bot_token or not chat_id:
        raise RuntimeError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en el archivo .env")

    logger.info("Iniciando monitor para: %s", event_url)
    logger.info("Intervalo de consulta: %s segundos", poll_seconds)

    known_ids: set[str] = set()

    while True:
        try:
            listings = fetch_listings(event_url)
            if not known_ids:
                known_ids = {item.listing_id for item in listings}
                logger.info("Estado inicial: %s entradas actuales", len(known_ids))
            else:
                fresh = [item for item in listings if item.listing_id not in known_ids]
                for item in fresh:
                    send_telegram_message(bot_token, chat_id, _format_listing_message(item))
                    logger.info("Notificada nueva entrada: %s", item.url)
                known_ids.update(item.listing_id for item in fresh)
                logger.info("Consulta OK. Nuevas: %s | Total vistas: %s", len(fresh), len(known_ids))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error monitorizando TicketSwap: %s", exc)

        time.sleep(poll_seconds)


if __name__ == "__main__":
    monitor_loop()
