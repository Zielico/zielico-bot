
@echo off
echo Tworzenie wirtualnego środowiska...
python -m venv venv

echo Aktywacja środowiska...
call venv\Scripts\activate

echo Instalacja python-telegram-bot 20.8...
pip install --upgrade pip
pip install python-telegram-bot==20.8
pip install gspread oauth2client

echo Gotowe. Aby uruchomić bota:
echo.
echo call venv\Scripts\activate
echo python bot.py
pause
