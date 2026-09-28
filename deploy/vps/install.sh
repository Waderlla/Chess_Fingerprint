#!/usr/bin/env bash
# Instalacja / aktualizacja Chess Fingerprint na VPS (Ubuntu, Caddy, Docker).
# Uruchamiane jako użytkownik z sudo:  sudo bash /opt/chess/app/deploy/vps/install.sh
# Skrypt jest idempotentny - można go puszczać ponownie po każdej zmianie w repo.
set -euo pipefail

APP=/opt/chess/app
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "== Pakiety"
DEBIAN_FRONTEND=noninteractive apt-get install -y -q stockfish python3-venv git >/dev/null

echo "== Użytkownik i katalogi"
id chess >/dev/null 2>&1 || useradd --system --home-dir /opt/chess --shell /usr/sbin/nologin chess
install -d -o chess -g chess -m 750 /opt/chess
install -d -o chess -g chess -m 755 /srv/chess
[ -d /opt/chess/venv ] || python3 -m venv /opt/chess/venv
/opt/chess/venv/bin/pip install -q -r "$APP/requirements.txt"
chown -R chess:chess /opt/chess

echo "== Konfiguracja (.env z losowym hasłem do bazy)"
if [ ! -f /opt/chess/.env ]; then
  PW=$(openssl rand -hex 24)
  sed "s/^SUPABASE_DB_PASSWORD=.*/SUPABASE_DB_PASSWORD=$PW/" "$APP/.env.example" > /opt/chess/.env
  chown chess:chess /opt/chess/.env
  chmod 600 /opt/chess/.env
fi

echo "== Baza PostgreSQL (Docker, tylko localhost)"
if ! docker ps -a --format '{{.Names}}' | grep -qx chess-db; then
  PW=$(grep '^SUPABASE_DB_PASSWORD=' /opt/chess/.env | cut -d= -f2)
  docker run -d --name chess-db --restart unless-stopped \
    -e POSTGRES_DB=chess -e POSTGRES_USER=chess -e POSTGRES_PASSWORD="$PW" \
    -v chess-pgdata:/var/lib/postgresql/data -p 127.0.0.1:5433:5432 \
    --memory 384m postgres:17-alpine >/dev/null
fi

echo "== Harmonogram (systemd)"
install -m 644 "$HERE/chess-sync.service" "$HERE/chess-sync.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now chess-sync.timer

echo "== Caddy (main.caddy + sites/chess.caddy)"
install -d -m 755 /etc/caddy/sites /etc/systemd/system/caddy.service.d
install -m 644 "$HERE/chess.caddy" /etc/caddy/sites/chess.caddy
install -m 644 "$HERE/main.caddy" /etc/caddy/main.caddy
caddy validate --config /etc/caddy/main.caddy --adapter caddyfile
install -m 644 "$HERE/caddy-main-config.conf" /etc/systemd/system/caddy.service.d/main-config.conf
systemctl daemon-reload
systemctl reload caddy

echo "Gotowe. Pierwszy sync ręcznie:  sudo systemctl start chess-sync.service"
echo "Postęp:                         journalctl -u chess-sync.service -f"
