import os
import json
import logging

import gspread
from google.oauth2.service_account import Credentials

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -------------------------
# LOGGING
# -------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# -------------------------
# ENV VARIABLES (Render)
# -------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN not set")

if not SPREADSHEET_ID:
    raise RuntimeError("SPREADSHEET_ID not set")

if not GOOGLE_SERVICE_ACCOUNT_JSON:
    raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set")

# -------------------------
# GOOGLE SHEETS
# -------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)

credentials = Credentials.from_service_account_info(
    service_account_info,
    scopes=SCOPES,
)

gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# -------------------------
# HANDLERS
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет.\n\n"
        "Как пользоваться ботом:\n"
        "1. Напиши название камня.\n"
        "2. Название должно совпадать с таблицей.\n"
        "3. Бот пришлёт описание и фото.\n\n"
        "Просто текст. Всё."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lower()

    rows = sheet.get_all_records()

    for row in rows:
        stone_name = str(row.get("название каменя", "")).strip().lower()

        if stone_name == query:
            reply_text = (
                f"Название: {row.get('название каменя')}\n"
                f"Цвет: {row.get('цвет')}\n"
                f"Размер: {row.get('размер')}\n"
                f"Происхождение: {row.get('происхождение')}\n"
                f"Чистота: {row.get('чистота')}\n"
                f"Стоимость: {row.get('стоимость')}"
            )

            image_url = row.get("картинка")

            if image_url:
                await update.message.reply_photo(
                    photo=image_url,
                    caption=reply_text,
                )
            else:
                await update.message.reply_text(reply_text)

            return

    await update.message.reply_text("Камень не найден.")

# -------------------------
# MAIN
# -------------------------
def main():
    logging.info("BOT STARTING")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logging.info("BOT POLLING")
    app.run_polling()

if __name__ == "__main__":
    main()
