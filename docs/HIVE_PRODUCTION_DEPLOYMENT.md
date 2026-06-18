# HIVE Private Production Deployment — hive.thiqos.com

HIVE panel runs on **https://hive.thiqos.com** (Thiqos product domain).  
Customer/project sites (e.g. **balkutusu.com**) stay separate in `WP_URL` and campaign targets.

## 1. Cloudflare DNS

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | hive | `<VPS_IP>` | Proxied (recommended) |

Optional: Cloudflare Access on `hive.thiqos.com` for extra layer.

## 2. VPS bootstrap

```bash
ssh root@<VPS_IP>
git clone <repo> /opt/hive   # or rsync from Mac (step 3)
bash /opt/hive/scripts/deploy/install-server.sh
```

## 3. Mac → VPS rsync

```bash
bash scripts/deploy/rsync-to-vps.sh hive@<VPS_IP>
scp backend/.env hive@<VPS_IP>:/opt/hive/backend/.env
```

State to copy manually on first deploy:

- `backend/app/*_state.json`
- `backend/talon_data/`
- `backend/reports/`
- `backend/browser_profiles/`

## 4. Production `.env`

Copy `backend/.env.example` → `backend/.env` on VPS. Set at minimum:

```env
HIVE_API_KEY=<strong-random>
HIVE_PANEL_URL=https://hive.thiqos.com
HIVE_CORS_ORIGINS=https://hive.thiqos.com,http://localhost:4000
HIVE_DISABLE_DOCS=true
HIVE_ADMIN_EMAIL=admin@thiqos.com
HIVE_ADMIN_PASSWORD_HASH=<bcrypt>
HIVE_JWT_SECRET=<strong-random>
```

Generate password hash:

```bash
cd backend && ./venv/bin/python ../scripts/deploy/generate-admin-password-hash.py
```

## 5. App setup

```bash
sudo bash /opt/hive/scripts/deploy/setup-app.sh
```

Creates venv, `npm run build`, systemd, nginx.

## 6. SSL

```bash
sudo certbot --nginx -d hive.thiqos.com
```

## 7. Services

```bash
sudo systemctl status hive-backend
sudo journalctl -u hive-backend -f
sudo nginx -t && sudo systemctl reload nginx
```

## 8. Backup (daily cron)

```bash
sudo crontab -e
# 0 3 * * * /opt/hive/scripts/deploy/backup-hive.sh
```

Retention: 14 days in `/opt/hive/backups/`.

## 9. Health check

```bash
HIVE_API_KEY=... HIVE_ADMIN_EMAIL=... HIVE_ADMIN_PASSWORD=... \
  bash /opt/hive/scripts/deploy/check-production.sh
```

## 10. Rollback

1. Stop service: `sudo systemctl stop hive-backend`
2. Restore backup: `tar -xzf /opt/hive/backups/hive-YYYY-MM-DD.tar.gz -C /tmp/hive-restore`
3. Copy state + `.env` back
4. `sudo systemctl start hive-backend`

## Architecture

```
Browser → https://hive.thiqos.com (Nginx)
           ├─ /          → /opt/hive/frontend/build (static)
           └─ /api/*     → 127.0.0.1:4001 (FastAPI systemd)
```

## Security checklist

- [ ] `.env` never committed
- [ ] `HIVE_DISABLE_DOCS=true` in production
- [ ] `X-Robots-Tag: noindex, nofollow` (nginx)
- [ ] `robots.txt` Disallow: /
- [ ] Panel login enabled (`HIVE_ADMIN_*`)
- [ ] API key for automation/scripts only
- [ ] Cloudflare Access (optional)

## Local dev

Without `HIVE_ADMIN_EMAIL` / `HIVE_ADMIN_PASSWORD_HASH`, panel falls back to API-key-only mode.  
Set `REACT_APP_HIVE_API_KEY` in `frontend/.env.local` matching `backend/.env` for dev proxy.
