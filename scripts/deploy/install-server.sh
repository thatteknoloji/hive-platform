#!/usr/bin/env bash
# HIVE VPS bootstrap — Ubuntu 22.04/24.04
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash scripts/deploy/install-server.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  python3 python3-venv python3-pip \
  nodejs npm \
  nginx git curl rsync tar \
  certbot python3-certbot-nginx \
  libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 libasound2t64 libxshmfence1 \
  fonts-liberation libappindicator3-1 xdg-utils

id -u hive &>/dev/null || useradd -r -m -d /opt/hive -s /bin/bash hive
mkdir -p /opt/hive/{backend,frontend,logs,backups,shared}
chown -R hive:hive /opt/hive

echo "✅ Base packages installed."
echo "Next: deploy code to /opt/hive, create /opt/hive/backend/.env, then:"
echo "  sudo bash scripts/deploy/setup-app.sh"
