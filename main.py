import os
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# -------------------------
# ЛОГИ
# -------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# -------------------------
# ENV
# -------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN not set")

# -------------------------
# HANDLERS
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет. Я жив. Render не упал, GitHub не соврал."
    )

# -------------------------
# MAIN
# -------------------------
def main():
    logging.info("BOT STARTING")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    logging.info("BOT POLLING")
    app.run_polling()

if __name__ == "__main__":
    main()
