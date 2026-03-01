# MTGCardCollector

Herramienta para sincronizar cartas de Magic desde MTGJSON hacia MySQL, incluyendo la URL de imagen por carta.

## Qué hace

- Descarga diariamente `AtomicCards.json.gz` desde MTGJSON.
- Calcula un checksum SHA-256 para evitar reprocesar la misma versión.
- Recorre todas las cartas y realiza `upsert` en MySQL usando `uuid` como clave primaria.
- Genera la URL de imagen siguiendo identificadores de MTGJSON:
  - Prioridad 1: `identifiers.scryfallId` → `cards.scryfall.io`.
  - Prioridad 2: `identifiers.multiverseId` → `gatherer.wizards.com`.
- Guarda el JSON completo de la carta en la columna `raw_card` para trazabilidad.
- Registra cada ejecución en `sync_runs`.

## Requisitos

- Python 3.10+
- MySQL 8+

## Configuración

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

2. Crea tu `.env` desde el ejemplo:

```bash
cp .env.example .env
```

3. Define credenciales:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

## Ejecución manual

```bash
python -m src.sync_atomic_cards
```

## Ejecución diaria

Se incluye el workflow de GitHub Actions:

- `.github/workflows/daily-sync.yml`

Configura en los secrets del repositorio:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

## Tablas creadas automáticamente

- `cards`: catálogo consolidado de cartas con URL de imagen y payload JSON.
- `sync_runs`: historial de sincronizaciones por checksum.


## Entorno adicional: bot de Telegram

Se añadió un entorno independiente en `telegram_bot/` para crear una app conectada a Telegram.

```bash
bash telegram_bot/scripts/setup_telegram_env.sh
```

Documentación completa: `telegram_bot/README.md`.
