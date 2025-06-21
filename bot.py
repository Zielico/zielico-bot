import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
import os

    # --- Запуск Telegram-бота (без ошибок asyncio)
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

    async def runner():
        await main()


# --- Загрузка токена и переменных окружения
load_dotenv()
TOKEN = os.getenv("TOKEN") or "ТВОЙ_ТОКЕН_ЗДЕСЬ"

# --- Эмодзи
EMOJI_MAP = {
    "Słonecznik": "🌻",
    "Groszek": "🫛",
    'Rzodkiewka "Sango"': "🟣",
    'Rzodkiewka "China Rose"': "🌸",
    "Soczewica": "🥣",
    "Rukola": "🌿",
    "Kolendra": "🪴",
    "Gorczyca": "🍀",
    "Pszenica": "🌾",
    "Brokuł": "🥦",
    "Burak": "🍠",
    "Rzeżucha": "🌱",
    "Bazylia": "🥬",
    "Lucerna": "🎋",
    "Fasola Mung": "🫘",
    "Szczaw Krwisty": "🩸",
    "Mangold": "🍂",
    "Amarantus": "🔥",
    "Kapusta Mizuna": "🥬"
}

import json

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
GOOGLE_SHEET_NAME = "Zielico_Заказы"

creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)

client = gspread.authorize(creds)
sheet_cennik = client.open(GOOGLE_SHEET_NAME).worksheet("Cennik")
sheet_zamowienia = client.open(GOOGLE_SHEET_NAME).worksheet("Zamówienia")

# --- Данные
WEIGHTS = [50, 100, 500, 1000]
USER_CART = {}
USER_STAGE = {}
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID") or "8021830147")  # Замени на свой ID
USER_STAGE_QUESTION = {}

MAIN_MENU = ReplyKeyboardMarkup(
    [['📋 Cennik', '🧾 Złóż zamówienie'], ['❓ Zadaj pytanie', '🛒 Koszyk']],
    resize_keyboard=True
)

def get_cennik():
    records = sheet_cennik.get_all_records()
    cleaned = {}
    for row in records:
        kultura = row.get("Kultura")
        price_str = row.get("Cena za 100g")
        if kultura and price_str:
            try:
                cleaned_price = float(price_str.replace('zł', '').replace(',', '.').strip())
                cleaned[kultura] = cleaned_price
            except ValueError:
                print(f"⚠️ Błąd konwersji ceny: {price_str} (dla: {kultura})")
    return cleaned

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cześć! 👋 Witaj w Zielico! Wybierz opcję z menu poniżej.", reply_markup=MAIN_MENU)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    if text == "📋 Cennik":
        cennik = get_cennik()
        msg = "📋 *Aktualny cennik Zielico:*\n"
        for k, price in cennik.items():
            emoji = EMOJI_MAP.get(k, "")
            msg += f"{emoji} *{k}* — {price:.2f} zł / 100g\n"
        await update.message.reply_text(msg, parse_mode='Markdown')

    elif text == "🧾 Złóż zamówienie":
        USER_CART[chat_id] = []
        await show_products(update, context)

    elif text == "🛒 Koszyk":
        await cart_command(update, context)

    elif text == "❓ Zadaj pytanie":
        USER_STAGE[chat_id] = "ASK_QUESTION"
        await update.message.reply_text("✍️ Napisz swoje pytanie, a my odpowiemy tak szybko, jak to możliwe!")

    elif chat_id in USER_STAGE and USER_STAGE[chat_id] == "GET_PHONE":
        context.user_data["phone"] = text
        USER_STAGE[chat_id] = "GET_ADDRESS"
        await update.message.reply_text("📍 Podaj adres dostawy lub uwagi:")

    elif chat_id in USER_STAGE and USER_STAGE[chat_id] == "GET_ADDRESS":
        context.user_data["address"] = text
        await finalize_order(update, context)

    elif chat_id in USER_STAGE and USER_STAGE[chat_id] == "ASK_QUESTION":
        USER_STAGE.pop(chat_id)

        await update.message.reply_text("📩 Dziękujemy! Odpowiemy na Twoje pytanie tak szybko, jak to możliwe.")

        # Уведомление админу
        question = update.message.text
        user = update.effective_user
        msg = f"❓ *Nowe pytanie od klienta:*\n\n"
        msg += f"👤 {user.full_name} (@{user.username or 'brak'})\n"
        msg += f"📝 {question}"
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="None")
        return

    else:
        await update.message.reply_text("Nie rozumiem... Wybierz opcję z menu 👇")

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cennik = get_cennik()
    keyboard = []
    for culture, price_per_100 in cennik.items():
        emoji = EMOJI_MAP.get(culture, "")
        keyboard.append([InlineKeyboardButton(f"{emoji} {culture}", callback_data="ignore")])
        weight_buttons = [
            InlineKeyboardButton(f"{w}g", callback_data=f"add:{culture}:{w}")
            for w in WEIGHTS
        ]
        price_buttons = [
            InlineKeyboardButton(f"{(price_per_100 * w / 100):.2f} zł", callback_data=f"add:{culture}:{w}")
            for w in WEIGHTS
        ]
        keyboard.append(weight_buttons)
        keyboard.append(price_buttons)
    await update.message.reply_text("🛍 Wybierz ilość:", reply_markup=InlineKeyboardMarkup(keyboard))

async def cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cart = USER_CART.get(chat_id, [])
    if not cart:
        if update.callback_query:
            await update.callback_query.message.edit_text("🛒 Twój koszyk jest pusty.")
        else:
            await update.message.reply_text("🛒 Twój koszyk jest pusty.")
        return

    msg = "🛒 *Zawartość koszyka:*\n"
    total = 0
    keyboard = []
    for item in cart:
        msg += f"\n• {item['culture']} {item['weight']}g – {item['price']:.2f} zł"
        total += item['price']

    for idx, item in enumerate(cart):
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Usuń {item['culture']} {item['weight']}g", 
                callback_data=f"remove:{idx}")])
    msg += f"\n💰 *Razem:* {total:.2f} zł"
    keyboard.append([InlineKeyboardButton("✅ Potwierdź zamówienie", callback_data="confirm_order")])
   
    if update.callback_query:
        await update.callback_query.message.edit_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.from_user.id

    if data.startswith("add:"):
        try:
            _, culture, weight = data.split(":", 2)
            price = get_cennik().get(culture)
            if not price:
                await query.message.reply_text("❌ Błąd: brak ceny")
                return
            total = price * (int(weight) / 100)
            USER_CART.setdefault(chat_id, []).append({"culture": culture, "weight": int(weight), "price": total})
            await query.message.reply_text(f"✅ Dodano: {culture} {weight}g – {total:.2f} zł")
        except Exception as e:
            await query.message.reply_text(f"❌ Błąd przy dodawaniu: {e}")
        return

    elif data.startswith("remove:"):
        try:
            idx = int(data.split(":")[1])
            cart = USER_CART.get(chat_id, [])
            if 0 <= idx < len(cart):
                removed = cart.pop(idx)
                await query.answer(f"🗑 Usunięto {removed['culture']} {removed['weight']}g")
                await cart_command(update, context)
            else:
                await query.answer("❌ Nieprawidłowy indeks.")
        except (IndexError, ValueError):
            await query.answer("❌ Błąd przy usuwaniu.")
        return

    elif data == "ask_question":
        USER_STAGE_QUESTION[chat_id] = True
        await query.message.reply_text("✍️ Napisz swoje pytanie:")
        return


    elif data == "confirm_order":
        USER_STAGE[chat_id] = "GET_PHONE"
        await query.message.reply_text("📞 Podaj swój numer telefonu:")
        return

async def finalize_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    user = update.effective_user
    cart = USER_CART.get(chat_id, [])
    total = sum(item["price"] for item in cart)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    sheet_zamowienia.append_row([
        user.full_name,
        f"@{user.username}" if user.username else "brak",
        context.user_data.get("phone", ""),
        "\n".join([f'{i["culture"]} {i["weight"]}g – {i["price"]:.2f} zł' for i in cart]),
        f"{total:.2f} zł",
        context.user_data.get("address", ""),
        now
    ])

    summary = "🧾 Twoje zamówienie:"
    for item in cart:
        summary += f"\n• {item['culture']} {item['weight']}g – {item['price']:.2f} zł"
    summary += f"\n\n💰 Razem: {total:.2f} zł"
    summary += f"\n📞 Telefon: {context.user_data.get('phone')}"
    summary += f"\n📍 Adres/Uwagi: {context.user_data.get('address')}"
    summary += "\n✅ Zamówienie zostało zapisane. Dziękujemy!"

    await update.message.reply_text(summary)
    USER_CART.pop(chat_id, None)
    USER_STAGE.pop(chat_id, None)
    context.user_data.clear()

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ Bot działa...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    import threading
    import http.server
    import socketserver

    # Заглушка для Render
    def fake_server():
        PORT = 10000
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Fake server running on port {PORT}")
            httpd.serve_forever()

    threading.Thread(target=fake_server, daemon=True).start()

    # Применяем патч для Render
    nest_asyncio.apply()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("🛑 Bot zatrzymany przez użytkownika.")


