import asyncio
import json
import logging
import os
import queue
import socket
import sys
import threading
import tkinter as tk
from pathlib import Path
from urllib.parse import quote

import websockets

APP_NAME = "AlertClient"
FROZEN = getattr(sys, "frozen", False)


def app_dir() -> Path:
    return Path(sys.executable).parent if FROZEN else Path(__file__).parent


def setup_logging():
    log_dir = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / APP_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "client.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def load_config() -> dict:
    path = app_dir() / "config.json"
    if not path.exists() and FROZEN:
        path = Path(sys._MEIPASS) / "config.json"  # wersja wbudowana w exe
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg.setdefault("name", socket.gethostname())
    cfg.setdefault("autostart", True)
    return cfg


# ---------- Windows: autostart + pojedyncza instancja ----------
_mutex = None


def single_instance() -> bool:
    global _mutex
    if os.name != "nt":
        return True
    import ctypes

    k32 = ctypes.windll.kernel32
    _mutex = k32.CreateMutexW(None, False, f"{APP_NAME}Mutex")
    return k32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def set_autostart(enable: bool):
    if os.name != "nt":
        return
    import winreg

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    try:
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{sys.executable}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


# ---------- sieć (wątek w tle) ----------
async def listen(cfg: dict, q: "queue.Queue[dict]"):
    url = f"{cfg['server_url']}?name={quote(cfg['name'])}"
    headers = {"Authorization": f"Bearer {cfg['token']}"}
    delay = 1
    while True:
        try:
            async with websockets.connect(url, additional_headers=headers) as ws:
                logging.info("Połączono z %s", cfg["server_url"])
                delay = 1
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except ValueError:
                        continue
                    if msg.get("type") == "alert":
                        q.put(msg)
        except Exception as e:
            logging.warning("Rozłączono: %s", e)
        await asyncio.sleep(delay)
        delay = min(delay * 2, 30)


def network_thread(cfg, q):
    asyncio.run(listen(cfg, q))


# ---------- UI (główny wątek) ----------
class App:
    def __init__(self, q):
        self.q = q
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.after(200, self.poll)

    def poll(self):
        try:
            while True:
                self.show(self.q.get_nowait())
        except queue.Empty:
            pass
        self.root.after(200, self.poll)

    def show(self, msg: dict):
        win = tk.Toplevel(self.root)
        win.title(msg.get("title") or "Alert")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        frame = tk.Frame(win, padx=24, pady=20)
        frame.pack()
        tk.Label(
            frame,
            text=msg.get("text", ""),
            wraplength=440,
            justify="left",
            font=("Segoe UI", 12),
        ).pack()
        btn = tk.Button(frame, text="OK", width=14, command=win.destroy)
        btn.pack(pady=(16, 0))
        win.bind("<Return>", lambda e: win.destroy())
        win.bind("<Escape>", lambda e: win.destroy())

        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        x = (win.winfo_screenwidth() - w) // 2
        y = (win.winfo_screenheight() - h) // 2
        win.geometry(f"+{x}+{y}")
        win.lift()
        win.focus_force()
        btn.focus_set()
        if os.name == "nt":
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

    def run(self):
        self.root.mainloop()


def main():
    setup_logging()
    if "--uninstall" in sys.argv:
        set_autostart(False)
        return
    if not single_instance():
        return
    cfg = load_config()
    if FROZEN and cfg["autostart"]:
        try:
            set_autostart(True)
        except Exception as e:
            logging.warning("Autostart nieudany: %s", e)

    q: "queue.Queue[dict]" = queue.Queue()
    threading.Thread(target=network_thread, args=(cfg, q), daemon=True).start()
    App(q).run()


if __name__ == "__main__":
    main()
