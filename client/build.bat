@echo off
REM Uruchom na Windowsie (PyInstaller nie buduje .exe z Linuksa).
REM Najpierw skopiuj config.example.json -> config.json i uzupelnij.
if not exist config.json (
  echo Brak config.json - skopiuj config.example.json i uzupelnij.
  exit /b 1
)
python -m pip install -r requirements.txt
python -m PyInstaller --onefile --noconsole --name AlertClient --add-data "config.json;." client.py
echo.
echo Gotowe: dist\AlertClient.exe
