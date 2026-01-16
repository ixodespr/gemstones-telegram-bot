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
# ЛОГИ
# -------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# -------------------------
# ENV ПЕРЕМЕННЫЕ (КАК БЫЛО)
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

creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=SCOPES,
)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1


def normalize(text: str) -> str:
    return text.strip().lower()


# -------------------------
# HANDLERS
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я бот каталога камней.\n"
        "Напиши название камня, например:\n"
        "Pink Spinel"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = normalize(update.message.text)

    rows = sheet.get_all_records()

    for row in rows:
        name = normalize(str(row.get("name", "")))

        if name == query:
            reply = (
                f"Название: {row.get('name')}\n"
                f"Цвет: {row.get('color')}\n"
                f"Форма: {row.get('shape')}\n"
                f"Размер: {row.get('size ct')} ct\n"
                f"Происхождение: {row.get('origin')}\n"
                f"Чистота: {row.get('clarity')}\n"
                f"Цена: {row.get('price')}"
            )

            image_url = row.get("image_url")

            if image_url:
                await update.message.reply_photo(
                    photo=image_url,
                    caption=reply
                )
            else:
                await update.message.reply_text(reply)

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
