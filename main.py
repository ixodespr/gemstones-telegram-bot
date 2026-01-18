import os
import json
import logging
from typing import List, Dict, Optional

import gspread
from google.oauth2.service_account import Credentials
from google import genai

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# LOGGING
# =========================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# =========================
# ENV
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not all([TELEGRAM_TOKEN, SPREADSHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON, GEMINI_API_KEY]):
    raise RuntimeError("Missing required ENV variables")

# =========================
# GEMINI (NEW SDK)
# =========================
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def gemini_call(prompt: str) -> Optional[str]:
    try:
        response = gemini_client.models.generate_content(
            model="models/gemini-1.5-flash",
            contents=prompt,
            config={
                "temperature": 0.2,
                "max_output_tokens": 300,
            },
        )
        if not response.text:
            return None
        return response.text.strip()
    except Exception as e:
        logging.warning(f"Gemini failed: {e}")
        return None

# =========================
# GOOGLE SHEETS
# =========================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = Credentials.from_service_account_info(
    json.loads(GOOGLE_SERVICE_ACCOUNT_JSON),
    scopes=SCOPES,
)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

ROWS_CACHE: List[Dict] = sheet.get_all_records()
logging.info(f"Loaded {len(ROWS_CACHE)} rows from sheet")

# =========================
# UTILS
# =========================
def normalize(text: str) -> str:
    return text.strip().lower()

def safe_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0

# =========================
# AI LOGIC
# =========================
def parse_intent(user_text: str) -> Dict:
    prompt = f"""
Ты аналитический модуль каталога драгоценных камней.
Верни ТОЛЬКО валидный JSON строго по схеме:

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
        logging.warning(f"Invalid JSON from Gemini: {raw}")
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
            price = safe_float(row.get("price"))
            if price <= 0 or price > intent["budget_max"]:
                continue

        results.append(row)

    return results

def build_sales_reply(intent: Dict, rows: List[Dict]) -> str:
    if not rows:
        return "Подходящих вариантов не нашёл. Можно расширить критерии или увеличить бюджет."

    top = sorted(
        rows,
        key=lambda r: safe_float(r.get("price")),
    )[:3]

    prompt = f"""
Пользователь ищет камень с параметрами:
{json.dumps(intent, ensure_ascii=False)}

Подходящие варианты (JSON):
{json.dumps(top, ensure_ascii=False)}

Сформулируй короткий продающий ответ:
- 3–5 строк
- без воды
- подчеркни ценность и отличие
"""

    text = gemini_call(prompt)
    if text:
        return text

    # fallback без ИИ
    lines = []
    for r in top:
        lines.append(
            f"{r.get('name')} | {r.get('color')} | {r.get('size ct')} ct | ${r.get('price')}"
        )

    return "Нашёл подходящие варианты:\n" + "\n".join(lines)

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я бот каталога камней.\n"
        "Опиши, что ты ищешь.\n"
        "Например: pink spinel до 3000"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    await update.message.reply_text("Подбираю варианты…")

    intent = parse_intent(user_text)
    logging.info(f"INTENT: {intent}")

    rows = filter_rows(intent)
    logging.info(f"FOUND ROWS: {len(rows)}")

    reply = build_sales_reply(intent, rows)
    await update.message.reply_text(reply)

# =========================
# MAIN
# =========================
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
