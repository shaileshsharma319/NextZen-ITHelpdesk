#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/shaileshsharma319/NextZen-ITHelpdesk.git}"
APP_DIR="${APP_DIR:-/opt/helpdesk}"
ENV_DIR="${ENV_DIR:-/etc/helpdesk}"
ENV_FILE="${ENV_FILE:-/etc/helpdesk/helpdesk.env}"
APP_USER="${APP_USER:-www-data}"
APP_GROUP="${APP_GROUP:-www-data}"

echo "== NextZen IT Helpdesk Ubuntu installer =="
echo "Repository: ${REPO_URL}"
echo "App path:   ${APP_DIR}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Please run with sudo:"
  echo "sudo bash deploy/ubuntu/install.sh"
  exit 1
fi

echo "== Installing Ubuntu packages =="
apt update
apt install -y git python3 python3-venv python3-pip mysql-server nginx

echo "== Starting MySQL =="
systemctl enable mysql
systemctl start mysql

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "== Cloning project =="
  rm -rf "${APP_DIR}"
  git clone "${REPO_URL}" "${APP_DIR}"
else
  echo "== Project already exists, pulling latest code =="
  git -C "${APP_DIR}" pull
fi

echo "== Creating Python virtual environment =="
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "== Creating upload folders =="
mkdir -p "${APP_DIR}/app/static/uploads"
chown -R "${APP_USER}:${APP_GROUP}" "${APP_DIR}/app/static/uploads"

echo "== Creating production env file =="
mkdir -p "${ENV_DIR}"
if [[ ! -f "${ENV_FILE}" ]]; then
  if [[ ! -f "${APP_DIR}/.env.example" ]]; then
    echo "Missing ${APP_DIR}/.env.example. Check that the Git clone completed."
    exit 1
  fi
  cp "${APP_DIR}/.env.example" "${ENV_FILE}"
  SECRET_KEY="$("${APP_DIR}/venv/bin/python" -c "import secrets; print(secrets.token_urlsafe(48))")"
  sed -i "s|replace-with-a-long-random-secret|${SECRET_KEY}|g" "${ENV_FILE}"
  sed -i "s|replace-with-strong-secret|${SECRET_KEY}|g" "${ENV_FILE}"
  echo "Created ${ENV_FILE}"
  echo "IMPORTANT: Edit DATABASE_URL and mail settings before starting production."
else
  echo "${ENV_FILE} already exists. Keeping existing file."
fi
chown root:"${APP_GROUP}" "${ENV_FILE}"
chmod 640 "${ENV_FILE}"

echo "== Installing systemd services =="
cp "${APP_DIR}/deploy/ubuntu/helpdesk.service" /etc/systemd/system/helpdesk.service
cp "${APP_DIR}/deploy/ubuntu/helpdesk-email-fetch.service" /etc/systemd/system/helpdesk-email-fetch.service
systemctl daemon-reload
systemctl enable helpdesk
systemctl enable helpdesk-email-fetch

echo
echo "Installer completed."
echo
echo "Next required steps:"
echo "1. Create MySQL database/user from DB_SETUP.md"
echo "2. Edit env file: sudo nano ${ENV_FILE}"
echo "3. Run: sudo -u ${APP_USER} ${APP_DIR}/venv/bin/flask --app wsgi:app init-defaults"
echo "4. Run: sudo -u ${APP_USER} ${APP_DIR}/venv/bin/flask --app wsgi:app init-admin"
echo "5. Start: sudo systemctl start helpdesk helpdesk-email-fetch"
