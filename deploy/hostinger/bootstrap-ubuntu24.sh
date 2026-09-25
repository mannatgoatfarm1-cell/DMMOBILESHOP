#!/usr/bin/env bash
set -euo pipefail
sudo apt update && sudo apt -y upgrade
sudo apt -y install nginx certbot python3-certbot-nginx python3.12-venv git curl ufw logrotate
sudo adduser --system --group --home /opt/dmobilemart dmobilemart || true
sudo install -d -o dmobilemart -g dmobilemart /opt/dmobilemart/{releases,current,logs}
sudo install -d -o dmobilemart -g dmobilemart /var/lib/dmobilemart/uploads /var/backups/dmobilemart/media
sudo install -d -m 750 -o root -g dmobilemart /etc/dmobilemart
sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
echo 'Install Node.js 20 LTS, clone your repository into /opt/dmobilemart/releases, then copy .env.production.example to /etc/dmobilemart/dmobilemart.env and fill placeholders.'