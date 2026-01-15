import os
import json

import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


# ---------- CONFIG ----------

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # может не использоваться
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set")

if not SPREADSHEET_ID:
    raise ValueError("SPREADSHEET_ID is not set")

if not GOOGLE_SERVICE_ACCOUNT_JSON:
    raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not set")


# ---------- GOOGLE SHEETS ----------

service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)

creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=SCOPES
)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1


# ---------- TELEGRAM HANDLERS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напишите параметры камня, например:\nкрасный камень из Бирмы"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()

    rows = sheet.get_all_records()

    for row in rows:
        name = str(row.get("название камня", "")).lower()
        color = str(row.get("цвет", "")).lower()
        origin = str(row.get("происхождение", "")).lower()
        image_url = row.get("image_url", "")

        if (
            (not name or name in query)
            and (not color or color in query)
            and (not origin or origin in query)
        ):
            text = (
                f"Камень: {row.get('название камня')}\n"
                f"Цвет: {row.get('цвет')}\n"
                f"Размер: {row.get('размер')}\n"
                f"Происхождение: {row.get('происхождение')}\n"
                f"Чистота: {row.get('чистота')}\n"
                f"Стоимость: {row.get('стоимость')}"
            )

            if image_url:
                await update.message.reply_photo(photo=image_url, caption=text)
            else:
                await update.message.reply_text(text)

            return

    await update.message.reply_text("Подходящих камней не найдено.")


# ---------- APP ----------

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()

