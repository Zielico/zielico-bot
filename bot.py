import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
import os


if __name__ == "__main__":
    import nest_asyncio
    import asyncio
    import threading
    import http.server
    import socketserver
    import os

    # Костыль для Render (Web Service требует открытый порт)
    def fake_server():
        PORT = int(os.getenv("PORT", 10000))
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Fake HTTP server on port {PORT}")
            httpd.serve_forever()

    threading.Thread(target=fake_server, daemon=True).start()

    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    
    # --- Запуск Telegram-бота
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

    async def runner():
        await main()

    asyncio.run(runner())
