# Alert App

Panel webowy (serwer, Docker) → okienko z dowolnym tekstem na komputerze (klient `.exe`, autostart).

## Serwer
```bash
cp .env.example .env     # ustaw PANEL_PASSWORD i CLIENT_TOKEN
docker compose up -d --build
```
Panel: `http://SERWER:8023/alertapp/` (logowanie Basic: `PANEL_USER` / `PANEL_PASSWORD`).

**Produkcja:** wystaw za reverse proxy z TLS (klienci łączą się po `wss://`). Przykład Caddy:
```
alerty.twojadomena.pl {
    reverse_proxy /alertapp/* localhost:8023
}
```
(Caddy sam obsługuje WebSocket i certyfikaty.) Prefiks zmienisz zmienną `BASE_PATH` w `.env` (a port w `Dockerfile` i `docker-compose.yml`). Adres w configu klienta: `wss://alerty.twojadomena.pl/alertapp/ws` (lub `ws://SERWER:8023/alertapp/ws` bez TLS). Bez TLS hasło i token idą jawnym tekstem.

## Klient (budowanie na Windowsie)
```bat
cd client
copy config.example.json config.json   & rem uzupelnij server_url, token, name
build.bat
```
Wynik: `client\dist\AlertClient.exe` (config jest wbudowany w exe; można go nadpisać plikiem
`config.json` leżącym obok exe).

Uruchom exe raz na docelowym komputerze – dopisze się do autostartu
(`HKCU\...\Run`) i działa w tle bez okna. Wyłączenie autostartu: `AlertClient.exe --uninstall`.
Log: `%LOCALAPPDATA%\AlertClient\client.log`.

## Uwagi
- Klient łączy się sam i ponawia połączenie (backoff do 30 s).
- Alert trafia tylko do aktualnie podłączonych komputerów (brak kolejki offline).
- `name` w configu = nazwa widoczna na liście odbiorców w panelu.
