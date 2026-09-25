# DMobileMart Hostinger Ubuntu 24.04 Runbook

## 0. Change-control gate

1. Record the production domain, VPS IPv4, Atlas cluster name, exact DB name, and current Atlas backup timestamp.
2. Create an Atlas on-demand snapshot and verify it reports `completed`.
3. Export **metadata only** (collection names, document counts, indexes) with read-only credentials. Do not export/import data as part of routine deployment.
4. Set a maintenance window and keep the current deployment available for rollback.

## 1. VPS baseline

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install nginx certbot python3-certbot-nginx python3.12-venv git curl ufw logrotate
sudo adduser --system --group --home /opt/dmobilemart dmobilemart
sudo mkdir -p /opt/dmobilemart/{app,releases,shared,logs} /var/lib/dmobilemart/uploads
sudo chown -R dmobilemart:dmobilemart /opt/dmobilemart /var/lib/dmobilemart
sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
```

Install a supported Node LTS release (Node 20+) from the owner-controlled NodeSource/official source and Python 3.12.

## 2. Release build

```bash
git clone <OWNER_REPOSITORY_URL> /opt/dmobilemart/app
cd /opt/dmobilemart/app/frontend && yarn install --frozen-lockfile && yarn build
cd /opt/dmobilemart/app/backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Phase 2 must replace Emergent-dependent dependencies before this release is treated as independent.

## 3. Production secrets

Create `/etc/dmobilemart/dmobilemart.env`, owned by `root:dmobilemart`, mode `640`. Populate from `hostinger-secrets.template.env`; never commit it.

```bash
sudo install -d -m 750 -o root -g dmobilemart /etc/dmobilemart
sudo install -m 640 -o root -g dmobilemart /dev/null /etc/dmobilemart/dmobilemart.env
```

## 4. Systemd API service

Create `/etc/systemd/system/dmobilemart-api.service`:

```ini
[Unit]
Description=DMobileMart FastAPI
After=network-online.target
Wants=network-online.target

[Service]
User=dmobilemart
Group=dmobilemart
WorkingDirectory=/opt/dmobilemart/app/backend
EnvironmentFile=/etc/dmobilemart/dmobilemart.env
ExecStart=/opt/dmobilemart/app/backend/.venv/bin/gunicorn server:app -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8001 --access-logfile - --error-logfile -
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable only after Phase 2 code is complete:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dmobilemart-api
sudo systemctl status dmobilemart-api
```

## 5. Nginx and HTTPS

Serve `frontend/build` as static files. Proxy `/api/` to `127.0.0.1:8001`; do not expose port 8001 publicly. Configure SPA fallback to `/index.html`, maximum upload size, gzip/Brotli if available, security headers, and `X-Forwarded-Proto`.

```nginx
server {
  listen 80;
  server_name <domain> www.<domain>;
  root /opt/dmobilemart/app/frontend/build;
  client_max_body_size 25m;

  location /api/ { proxy_pass http://127.0.0.1:8001; proxy_set_header Host $host; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme; }
  location / { try_files $uri $uri/ /index.html; }
}
```

After DNS A/AAAA records point to the VPS:

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d <domain> -d www.<domain>
```

## 6. Operational checks

- `curl -f https://<domain>/api/health` (add a health endpoint in Phase 2).
- Verify API cannot be reached directly on port 8001 from the internet.
- Test customer/admin login, Google callback, product upload/retrieval, checkout, Razorpay callback, UPI proof, wallet, order flow, auction bid, QC report, and admin actions.
- Check `journalctl -u dmobilemart-api`, `/var/log/nginx`, Atlas connections, disk free space, and media backup status.

## 7. Backups, logs, and rollback

- Atlas: retain Atlas snapshots; test point-in-time restore in a separate staging project, never in production.
- Media: nightly `restic`/`rclone` encrypted backup of `/var/lib/dmobilemart/uploads` to owner-controlled storage; retain 30 daily snapshots.
- Logs: use journald limits and Nginx logrotate; alert on API restarts, 5xx rate, disk usage, and backup failure.
- Rollback: retain the previous release directory, run `systemctl stop dmobilemart-api`, atomically switch the release symlink, rebuild static assets if required, then restart. Do not alter Atlas during rollback.