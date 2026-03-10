#!/usr/bin/env bash
set -euo pipefail

APP_DIR=""
DOMAIN=""
APP_NAME="pdftoword"
APP_USER="www-data"
APP_GROUP="www-data"
APP_PORT="8000"
PYTHON_BIN="python3"

print_help() {
  cat <<'EOF'
Uso:
  sudo bash install_linux_apache.sh --domain SEU_DOMINIO

Opcoes:
  --app-dir DIR        Diretoria da app (default: diretoria do script chamador)
  --domain DOMINIO     Dominio (ex: app.exemplo.com). Use "_" para acesso por IP.
  --app-name NOME      Nome do servico systemd e ficheiros Apache (default: pdftoword)
  --app-user USER      Utilizador para correr Gunicorn (default: www-data)
  --app-group GROUP    Grupo para correr Gunicorn (default: www-data)
  --port PORT          Porta local do Gunicorn (default: 8000)
  --python-bin BIN     Binario Python (default: python3)
  -h, --help           Mostrar ajuda
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-dir) APP_DIR="${2:-}"; shift 2 ;;
    --domain) DOMAIN="${2:-}"; shift 2 ;;
    --app-name) APP_NAME="${2:-}"; shift 2 ;;
    --app-user) APP_USER="${2:-}"; shift 2 ;;
    --app-group) APP_GROUP="${2:-}"; shift 2 ;;
    --port) APP_PORT="${2:-}"; shift 2 ;;
    --python-bin) PYTHON_BIN="${2:-}"; shift 2 ;;
    -h|--help) print_help; exit 0 ;;
    *) echo "Opcao desconhecida: $1"; print_help; exit 1 ;;
  esac
done

if [[ -z "$APP_DIR" ]]; then
  APP_DIR="$(pwd)"
fi

if [[ -z "$DOMAIN" ]]; then
  echo "Erro: informe --domain (ou use --domain _ para acesso por IP)."
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Erro: execute como root (sudo)."
  exit 1
fi

if [[ ! -f "$APP_DIR/web_app.py" ]]; then
  echo "Erro: web_app.py nao encontrado em $APP_DIR"
  exit 1
fi

if [[ ! -f "$APP_DIR/requirements-server.txt" ]]; then
  echo "Erro: requirements-server.txt nao encontrado em $APP_DIR"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y apache2 python3 python3-venv python3-pip

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  echo "Erro: utilizador '$APP_USER' nao existe."
  exit 1
fi

chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

sudo -u "$APP_USER" "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements-server.txt"

SERVICE_PATH="/etc/systemd/system/${APP_NAME}.service"
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=${APP_NAME} Flask App (Gunicorn)
After=network.target

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=PORT=${APP_PORT}
ExecStart=${APP_DIR}/.venv/bin/gunicorn -w 2 -b 127.0.0.1:${APP_PORT} web_app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

APACHE_CONF="/etc/apache2/sites-available/${APP_NAME}.conf"
cat > "$APACHE_CONF" <<EOF
<VirtualHost *:80>
    ServerName ${DOMAIN}

    ProxyPreserveHost On
    ProxyRequests Off
    ProxyPass / http://127.0.0.1:${APP_PORT}/
    ProxyPassReverse / http://127.0.0.1:${APP_PORT}/

    ErrorLog \${APACHE_LOG_DIR}/${APP_NAME}_error.log
    CustomLog \${APACHE_LOG_DIR}/${APP_NAME}_access.log combined
</VirtualHost>
EOF

a2enmod proxy proxy_http headers rewrite
a2dissite 000-default.conf || true
a2ensite "${APP_NAME}.conf"

systemctl daemon-reload
systemctl enable "${APP_NAME}"
systemctl restart "${APP_NAME}"
systemctl reload apache2

echo ""
echo "Instalacao concluida."
echo "Servico: systemctl status ${APP_NAME} --no-pager"
echo "Logs app: journalctl -u ${APP_NAME} -n 100 --no-pager"
echo "Logs apache: tail -n 100 /var/log/apache2/${APP_NAME}_error.log"
