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
# ENV
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


def format_reply(row: dict) -> str:
    return (
        f"Название: {row.get('name')}\n"
        f"Цвет: {row.get('color')}\n"
        f"Форма: {row.get('shape')}\n"
        f"Размер: {row.get('size ct')} ct\n"
        f"Происхождение: {row.get('origin')}\n"
        f"Чистота: {row.get('clarity')}\n"
        f"Цена: {row.get('price')}"
    )


# -------------------------
# HANDLERS
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Каталог камней.\n"
        "Просто напиши запрос. Я сразу покажу лучший вариант."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = normalize(update.message.text)
    rows = sheet.get_all_records()

    if not rows:
        await update.message.reply_text("Каталог пуст.")
        return

    exact_match = None
    partial_match = None

    for row in rows:
        name = normalize(str(row.get("name", "")))

        if name == query:
            exact_match = row
            break

        if query in name and not partial_match:
            partial_match = row

    result = exact_match or partial_match or rows[0]

    reply_text = format_reply(result)
    image_url = result.get("image_url")

    if image_url:
        await update.message.reply_photo(
            photo=image_url,
            caption=reply_text
        )
    else:
        await update.message.reply_text(reply_text)


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
