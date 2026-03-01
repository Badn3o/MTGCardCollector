# Entorno aislado para bot de Telegram

Este módulo crea un entorno nuevo e independiente para desarrollar una aplicación que se comunique con Telegram.

## 1) Crear el entorno

```bash
bash BadBunny/scripts/setup_telegram_env.sh
```

El script:
- Crea un virtualenv en `BadBunny/.venv`
- Instala dependencias de `BadBunny/requirements.txt`
- Crea `BadBunny/.env` desde `BadBunny/.env.example` si no existe

## 2) Configurar token

Edita `BadBunny/.env` y coloca el token generado por BotFather:

```env
TELEGRAM_BOT_TOKEN=<tu_token>
```

## 3) Ejecutar el bot

```bash
source BadBunny/.venv/bin/activate
python -m src.bot
```

> Ejecuta el comando desde la carpeta `BadBunny`.

## Comportamiento inicial

- `/start`: responde confirmando que el bot está activo.
- Cualquier mensaje de texto: devuelve un `echo` del mensaje recibido.
