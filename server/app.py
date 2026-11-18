import json
import os
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

PANEL_USER = os.getenv("PANEL_USER", "admin")
PANEL_PASSWORD = os.getenv("PANEL_PASSWORD")
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")
if not PANEL_PASSWORD or not CLIENT_TOKEN:
    raise RuntimeError("Ustaw zmienne PANEL_PASSWORD i CLIENT_TOKEN")

BASE_PATH = "/" + os.getenv("BASE_PATH", "/alertapp").strip("/")
STATIC = Path(__file__).parent / "static"
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
router = APIRouter(prefix=BASE_PATH)
basic = HTTPBasic()


def eq(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode(), b.encode())


def require_panel(creds: HTTPBasicCredentials = Depends(basic)):
    if not (eq(creds.username, PANEL_USER) and eq(creds.password, PANEL_PASSWORD)):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )


@dataclass
class Client:
    ws: WebSocket
    name: str


clients: dict[str, Client] = {}


class AlertIn(BaseModel):
    title: str = Field("Alert", max_length=100)
    text: str = Field(..., min_length=1, max_length=2000)
    target: str = "all"  # "all" albo nazwa komputera


@router.get("/", dependencies=[Depends(require_panel)])
async def index():
    return FileResponse(STATIC / "index.html")


@router.get("/api/clients", dependencies=[Depends(require_panel)])
async def list_clients():
    return sorted({c.name for c in clients.values()})


@router.post("/api/send", dependencies=[Depends(require_panel)])
async def send_alert(alert: AlertIn):
    payload = json.dumps(
        {"type": "alert", "title": alert.title.strip() or "Alert", "text": alert.text}
    )
    targets = [
        (cid, c)
        for cid, c in list(clients.items())
        if alert.target == "all" or c.name == alert.target
    ]
    delivered = 0
    for cid, c in targets:
        try:
            await c.ws.send_text(payload)
            delivered += 1
        except Exception:
            clients.pop(cid, None)
    return {"delivered": delivered, "matched": len(targets)}


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    auth = ws.headers.get("authorization", "")
    if not (auth.startswith("Bearer ") and eq(auth[7:], CLIENT_TOKEN)):
        await ws.close(code=4401)
        return
    await ws.accept()
    name = (ws.query_params.get("name") or "unknown")[:64]
    cid = uuid.uuid4().hex
    clients[cid] = Client(ws, name)
    try:
        while True:
            await ws.receive_text()  # klient nic nie musi wysyłać; trzymamy połączenie
    except WebSocketDisconnect:
        pass
    finally:
        clients.pop(cid, None)


app.include_router(router)
