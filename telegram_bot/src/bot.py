"""Bot de Telegram mínimo para validar un entorno independiente."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start para confirmar que el bot está activo."""
    default_reply = os.getenv("TELEGRAM_DEFAULT_REPLY", "¡Bot activo!")
    user_name = update.effective_user.first_name if update.effective_user else "usuario"
    await update.message.reply_text(f"Hola {user_name}. {default_reply}")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Repite el texto recibido."""
    if not update.message or not update.message.text:
        return
    await update.message.reply_text(f"Echo: {update.message.text}")


def main() -> None:
    """Inicia el bot usando TELEGRAM_BOT_TOKEN de variables de entorno."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Falta TELEGRAM_BOT_TOKEN. Crea un .env basado en telegram_bot/.env.example"
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Bot iniciado. Esperando mensajes...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
