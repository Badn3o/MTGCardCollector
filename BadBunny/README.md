# Entorno aislado para bot de Telegram + monitor TicketSwap

Este módulo crea un entorno independiente para desarrollar una aplicación que:
- se comunique con Telegram,
- y monitorice TicketSwap en busca de nuevas entradas en venta para conciertos de Bad Bunny en Madrid.

## 1) Crear el entorno

```bash
bash BadBunny/scripts/setup_telegram_env.sh
```

## 2) Configurar variables en `BadBunny/.env`

```env
TELEGRAM_BOT_TOKEN=<token de BotFather>
TELEGRAM_CHAT_ID=<tu chat id>
TICKETSWAP_EVENT_URL=https://www.ticketswap.com/event/bad-bunny-madrid
TICKETSWAP_POLL_SECONDS=15
```

## 3) Ejecutar bot básico (opcional)

```bash
cd BadBunny
source .venv/bin/activate
python -m src.bot
```

## 4) Ejecutar monitor TicketSwap (tiempo real por polling)

```bash
cd BadBunny
source .venv/bin/activate
python -m src.ticketswap_monitor
```

Cuando detecta nuevas entradas, envía un mensaje a Telegram con precio, cantidad y enlace.

## Nota importante

TicketSwap puede cambiar la estructura interna de su web en cualquier momento. Este monitor usa scraping del payload `__NEXT_DATA__` de la página del evento y puede requerir ajustes futuros.
