import os
import json
import logging
from typing import List, Dict

import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not all([TELEGRAM_TOKEN, SPREADSHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON, GEMINI_API_KEY]):
    raise RuntimeError("Missing ENV variables")

# -------------------------
# GEMINI CONFIG
# -------------------------
genai.configure(api_key=GEMINI_API_KEY)

gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash"
)

def gemini_call(prompt: str) -> str | None:
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 300,
            },
            request_options={"timeout": 8},
        )
        return response.text
    except Exception as e:
        logging.warning(f"Gemini failed: {e}")
        return None

# -------------------------
# GOOGLE SHEETS
# -------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = Credentials.from_service_account_info(
    json.loads(GOOGLE_SERVICE_ACCOUNT_JSON),
    scopes=SCOPES,
)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

ROWS_CACHE: List[Dict] = sheet.get_all_records()

# -------------------------
# UTILS
# -------------------------
def normalize(text: str) -> str:
    return text.strip().lower()

# -------------------------
# AI LOGIC
# -------------------------
def parse_intent(user_text: str) -> Dict:
    prompt = f"""
Ты аналитический модуль каталога камней.
Верни ТОЛЬКО JSON строго по схеме:

{{
  "stone": string|null,
  "color": string|null,
  "budget_max": number|null,
  "intent": "buy"|"compare"|"ask"
}}

Запрос пользователя:
{user_text}
"""
    raw = gemini_call(prompt)
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def filter_rows(intent: Dict) -> List[Dict]:
    results = []

    for row in ROWS_CACHE:
        if intent.get("stone"):
            if intent["stone"] not in normalize(str(row.get("name", ""))):
                continue

        if intent.get("color"):
            if intent["color"] not in normalize(str(row.get("color", ""))):
                continue

        if intent.get("budget_max"):
            try:
                if float(row.get("price", 0)) > intent["budget_max"]:
                    continue
            except ValueError:
                continue

        results.append(row)

    return results

def build_sales_reply(intent: Dict, rows: List[Dict]) -> str:
    if not rows:
        return "Подходящих вариантов не нашёл. Можем расширить критерии."

    top = rows[:3]

    prompt = f"""
Пользователь хочет: {intent}

Вот подходящие варианты:
{json.dumps(top, ensure_ascii=False)}

Сформулируй короткий продающий ответ:
- без воды
- максимум 5 строк
- акцент на выгоду
"""

    text = gemini_call(prompt)
    return text or "Нашёл несколько подходящих вариантов. Могу показать детали."

# -------------------------
# HANDLERS
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я бот каталога камней.\n"
        "Опиши, что ты ищешь:\n"
        "например: pink spinel до 3000"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    await update.message.reply_text("Подбираю варианты…")

    intent = parse_intent(user_text)
    rows = filter_rows(intent)

    reply = build_sales_reply(intent, rows)
    await update.message.reply_text(reply)

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
