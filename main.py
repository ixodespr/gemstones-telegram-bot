import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import gspread
from google.oauth2.service_account import Credentials

# --------------------
# НАСТРОЙКИ (ты подставляешь значения)
# --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

GOOGLE_CREDS_JSON = {
    # сюда ты подставляешь JSON сервис-аккаунта
}

# --------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# --------------------
# Google Sheets
# --------------------
def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        GOOGLE_CREDS_JSON, scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet.get_all_records()

# --------------------
# Handlers
# --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет.\n"
        "Напиши название камня, например:\n"
        "Pink Spinel\n\n"
        "Я ищу по таблице и верну все совпадения."
    )

async def search_stone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lower()

    try:
        rows = get_sheet()
    except Exception as e:
        logging.exception("Google Sheets error")
        await update.message.reply_text("Ошибка доступа к таблице.")
        return

    results = []

    for row in rows:
        name = str(row.get("name", "")).strip().lower()

        if query in name:
            results.append(row)

    if not results:
        await update.message.reply_text("Камень не найден.")
        return

    for r in results:
        text = (
            f"💎 {r['name']}\n"
            f"Color: {r['color']}\n"
            f"Shape: {r['shape']}\n"
            f"Size: {r['size ct']} ct\n"
            f"Origin: {r['origin']}\n"
            f"Clarity: {r['clarity']}\n"
            f"Price: ${r['price']}"
        )

        if r.get("image_url"):
            await update.message.reply_photo(
                photo=r["image_url"],
                caption=text
            )
        else:
            await update.message.reply_text(text)

# --------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_stone))

    app.run_polling()

# --------------------
if __name__ == "__main__":
    main()
