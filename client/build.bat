@echo off
if not exist config.json (
  echo Brak config.json - skopiuj config.example.json i uzupelnij.
  exit /b 1
)
if exist .venv rmdir /s /q .venv
python -m venv .venv || exit /b 1
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || exit /b 1
python -c "import websockets; print('websockets', websockets.__version__)" || exit /b 1
python -m PyInstaller --clean --onefile --noconsole --name AlertClient ^
  --collect-submodules websockets --add-data "config.json;." client.py
echo.
echo Gotowe: dist\AlertClient.exe