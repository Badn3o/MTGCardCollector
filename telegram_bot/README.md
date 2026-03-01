# Entorno aislado para bot de Telegram

Este módulo crea un entorno nuevo e independiente para desarrollar una aplicación que se comunique con Telegram.

## 1) Crear el entorno

```bash
bash telegram_bot/scripts/setup_telegram_env.sh
```

El script:
- Crea un virtualenv en `telegram_bot/.venv`
- Instala dependencias de `telegram_bot/requirements.txt`
- Crea `telegram_bot/.env` desde `telegram_bot/.env.example` si no existe

## 2) Configurar token

Edita `telegram_bot/.env` y coloca el token generado por BotFather:

```env
TELEGRAM_BOT_TOKEN=<tu_token>
```

## 3) Ejecutar el bot

```bash
source telegram_bot/.venv/bin/activate
python -m src.bot
```

> Ejecuta el comando desde la carpeta `telegram_bot`.

## Comportamiento inicial

- `/start`: responde confirmando que el bot está activo.
- Cualquier mensaje de texto: devuelve un `echo` del mensaje recibido.
