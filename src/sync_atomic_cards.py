import gzip
import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv() -> None:
        return None

try:
    import mysql.connector
    from mysql.connector import MySQLConnection
except ModuleNotFoundError:  # pragma: no cover
    mysql = None
    MySQLConnection = Any

ATOMIC_CARDS_URL = "https://mtgjson.com/api/v5/AtomicCards.json.gz"


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


class AtomicCardsSync:
    def __init__(self, db_config: DbConfig, download_url: str = ATOMIC_CARDS_URL) -> None:
        self.db_config = db_config
        self.download_url = download_url

    def run(self) -> None:
        logging.info("Starting MTGJSON AtomicCards sync")
        with self._connect_db() as conn:
            self._ensure_schema(conn)
            with tempfile.TemporaryDirectory(prefix="mtgjson-sync-") as tmp_dir:
                archive_path = Path(tmp_dir) / "AtomicCards.json.gz"
                self._download_file(archive_path)
                checksum = self._sha256sum(archive_path)

                if self._already_processed(conn, checksum):
                    logging.info("No new AtomicCards version detected. Checksum: %s", checksum)
                    return

                counters = self._process_atomic_cards(conn, archive_path)
                self._record_sync(conn, checksum, counters)

                logging.info(
                    "Sync finished. Processed=%s, Inserted=%s, Updated=%s",
                    counters["processed"],
                    counters["inserted"],
                    counters["updated"],
                )

    def _connect_db(self) -> MySQLConnection:
        if mysql is None:
            raise RuntimeError("mysql-connector-python is required. Install dependencies with pip install -r requirements.txt")

        return mysql.connector.connect(
            host=self.db_config.host,
            port=self.db_config.port,
            user=self.db_config.user,
            password=self.db_config.password,
            database=self.db_config.database,
            autocommit=False,
        )

    def _ensure_schema(self, conn: MySQLConnection) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cards (
                    uuid VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    set_code VARCHAR(32),
                    number VARCHAR(32),
                    language VARCHAR(32),
                    layout_name VARCHAR(64),
                    mana_value DECIMAL(5,2),
                    types JSON,
                    colors JSON,
                    identifiers JSON,
                    image_url TEXT,
                    last_printed VARCHAR(32),
                    raw_card JSON NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_runs (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    source_checksum CHAR(64) NOT NULL,
                    processed_count INT NOT NULL,
                    inserted_count INT NOT NULL,
                    updated_count INT NOT NULL,
                    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uniq_source_checksum (source_checksum)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
        conn.commit()

    def _download_file(self, target_path: Path) -> None:
        if requests is None:
            raise RuntimeError("requests is required. Install dependencies with pip install -r requirements.txt")

        logging.info("Downloading %s", self.download_url)
        response = requests.get(self.download_url, stream=True, timeout=120)
        response.raise_for_status()

        with target_path.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 512):
                if chunk:
                    output.write(chunk)

    def _sha256sum(self, file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _already_processed(self, conn: MySQLConnection, checksum: str) -> bool:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM sync_runs WHERE source_checksum = %s LIMIT 1", (checksum,))
            return cursor.fetchone() is not None

    def _iter_atomic_cards(self, archive_path: Path) -> Iterable[Dict[str, Any]]:
        with gzip.open(archive_path, "rb") as gz_file:
            payload = json.load(gz_file)
            for card_printings in payload.get("data", {}).values():
                for card in card_printings:
                    yield card

    @staticmethod
    def _build_image_url(card: Dict[str, Any]) -> Optional[str]:
        identifiers = card.get("identifiers") or {}
        scryfall_id = identifiers.get("scryfallId")
        if scryfall_id:
            compact = scryfall_id.replace("-", "")
            return f"https://cards.scryfall.io/normal/front/{compact[0]}/{compact[1]}/{scryfall_id}.jpg"

        multiverse_id = identifiers.get("multiverseId")
        if multiverse_id:
            return f"https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid={multiverse_id}&type=card"

        return None

    def _upsert_card(self, conn: MySQLConnection, card: Dict[str, Any]) -> str:
        payload = {
            "uuid": card["uuid"],
            "name": card.get("name"),
            "set_code": card.get("setCode"),
            "number": card.get("number"),
            "language": card.get("language"),
            "layout_name": card.get("layout"),
            "mana_value": card.get("manaValue"),
            "types": json.dumps(card.get("types") or []),
            "colors": json.dumps(card.get("colors") or []),
            "identifiers": json.dumps(card.get("identifiers") or {}),
            "image_url": self._build_image_url(card),
            "last_printed": card.get("lastPrint"),
            "raw_card": json.dumps(card),
        }

        query = """
            INSERT INTO cards (
                uuid, name, set_code, number, language, layout_name, mana_value,
                types, colors, identifiers, image_url, last_printed, raw_card
            ) VALUES (
                %(uuid)s, %(name)s, %(set_code)s, %(number)s, %(language)s, %(layout_name)s, %(mana_value)s,
                %(types)s, %(colors)s, %(identifiers)s, %(image_url)s, %(last_printed)s, %(raw_card)s
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                set_code = VALUES(set_code),
                number = VALUES(number),
                language = VALUES(language),
                layout_name = VALUES(layout_name),
                mana_value = VALUES(mana_value),
                types = VALUES(types),
                colors = VALUES(colors),
                identifiers = VALUES(identifiers),
                image_url = VALUES(image_url),
                last_printed = VALUES(last_printed),
                raw_card = VALUES(raw_card);
        """

        with conn.cursor() as cursor:
            cursor.execute(query, payload)
            if cursor.rowcount == 1:
                return "inserted"
            if cursor.rowcount == 2:
                return "updated"
            return "unchanged"

    def _process_atomic_cards(self, conn: MySQLConnection, archive_path: Path) -> Dict[str, int]:
        counters = {"processed": 0, "inserted": 0, "updated": 0}

        for card in self._iter_atomic_cards(archive_path):
            status = self._upsert_card(conn, card)
            counters["processed"] += 1
            if status in ("inserted", "updated"):
                counters[status] += 1

            if counters["processed"] % 2000 == 0:
                conn.commit()
                logging.info(
                    "Progress: processed=%s inserted=%s updated=%s",
                    counters["processed"],
                    counters["inserted"],
                    counters["updated"],
                )

        conn.commit()
        return counters

    def _record_sync(self, conn: MySQLConnection, checksum: str, counters: Dict[str, int]) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sync_runs (source_checksum, processed_count, inserted_count, updated_count)
                VALUES (%s, %s, %s, %s)
                """,
                (checksum, counters["processed"], counters["inserted"], counters["updated"]),
            )
        conn.commit()


def _load_db_config() -> DbConfig:
    load_dotenv()
    return DbConfig(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
    )


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    started_at = datetime.now(timezone.utc)
    try:
        sync = AtomicCardsSync(_load_db_config())
        sync.run()
    except Exception:
        logging.exception("AtomicCards sync failed")
        raise
    finally:
        logging.info("Execution finished in %s", datetime.now(timezone.utc) - started_at)


if __name__ == "__main__":
    main()
