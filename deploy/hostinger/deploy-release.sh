#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="${1:?Usage: deploy-release.sh <repository-directory>}"
RELEASE="/opt/dmobilemart/releases/$(date -u +%Y%m%dT%H%M%SZ)"
sudo rsync -a --delete --exclude .git --exclude node_modules --exclude build "$REPO_DIR/" "$RELEASE/"
sudo chown -R dmobilemart:dmobilemart "$RELEASE"
sudo -u dmobilemart bash -lc "cd '$RELEASE/frontend' && yarn install --frozen-lockfile && yarn build"
sudo -u dmobilemart bash -lc "cd '$RELEASE/backend' && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"
sudo ln -sfn "$RELEASE" /opt/dmobilemart/current
sudo systemctl daemon-reload && sudo systemctl restart dmobilemart-api && sudo systemctl reload nginx