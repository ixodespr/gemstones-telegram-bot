import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import gspread
from google.oauth2.service_account import Credentials

import openai

# ---------- НАСТРОЙКИ ----------

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

SHEET_NAME = "Gemstones"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)

gc = gspread.authorize(creds)
sheet = gc.open(SHEET_NAME).sheet1

# ---------- ЛОГИ ----------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ---------- КОМАНДЫ ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напиши запрос, например:\n"
        "• красный камень\n"
        "• зелёный для подарка\n"
        "• прозрачный дорогой"
    )

# ---------- ОСНОВНАЯ ЛОГИКА ----------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.lower()

    rows = sheet.get_all_records()

    matched = None
    for row in rows:
        if row["цвет"].lower() in user_text:
            matched = row
            break

    if not matched:
        await update.message.reply_text("Подходящий камень не найден.")
        return

    prompt = f"""
Опиши камень для клиента красиво и кратко.

Название: {matched['название']}
Цвет: {matched['цвет']}
Размер: {matched['размер']}
Происхождение: {matched['происхождение']}
Чистота: {matched['чистота']}
Стоимость: {matched['стоимость']}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты ювелирный консультант."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    description = response.choices[0].message.content

    image_url = matched["image_url"]

    await update.message.reply_photo(
        photo=image_url,
        caption=description
    )

# ---------- ЗАПУСК ----------

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
