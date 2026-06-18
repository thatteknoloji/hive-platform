#!/bin/bash
# VPS Recovery Script - balkutusu.com
set -e
OUT="/opt/thiqos/apps/hive/sites/wp-content/recovery-log.txt"
exec > >(tee -a "$OUT") 2>&1
echo "=== RECOVERY START $(date) ==="

# 1. Docker containers
CONTAINERS="twitter-redis twitter-postgres postgres redis qdrant ollama hive_wordpress hive_db"
for c in $CONTAINERS; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    echo "[OK] $c running"
  elif docker ps -a --format '{{.Names}}' | grep -qx "$c"; then
    echo "[START] $c"
    docker start "$c"
  else
    echo "[MISSING] $c not found"
  fi
done

echo "--- docker ps ---"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Ensure wordpress on 8080 (fix docker-compose if needed)
cd /opt/thiqos/apps/hive/sites
if ! docker ps --format '{{.Ports}}' --filter name=hive_wordpress | grep -q 8080; then
  echo "[FIX] Remapping hive_wordpress to port 8080..."
  if grep -q '"80:80"' docker-compose.yml 2>/dev/null; then
    sed -i 's/"80:80"/"8080:80"/' docker-compose.yml
    docker-compose up -d wordpress
    sleep 5
  fi
fi

# 2. WP-CLI install
echo "[STEP 2] Installing WP-CLI..."
docker exec hive_wordpress bash -c "curl -sO https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && chmod +x wp-cli.phar && mv -f wp-cli.phar /usr/local/bin/wp"
docker exec hive_wordpress wp --info --allow-root | head -3

# 3. Temp URLs to IP:8080
echo "[STEP 3] Setting temp URLs..."
docker exec hive_wordpress wp option update siteurl "http://13.140.138.135:8080" --allow-root
docker exec hive_wordpress wp option update home "http://13.140.138.135:8080" --allow-root

# 4. Nginx config
echo "[STEP 4] Configuring Nginx..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-available/default

sudo tee /etc/nginx/sites-available/wordpress > /dev/null <<'NGINX'
server {
    listen 80;
    server_name balkutusu.com;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/wordpress /etc/nginx/sites-enabled/wordpress
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
echo "[OK] Nginx status: $(systemctl is-active nginx)"

# 5. WordPress URLs to domain
echo "[STEP 5] Setting domain URLs..."
docker exec hive_wordpress wp option update siteurl "http://balkutusu.com" --allow-root
docker exec hive_wordpress wp option update home "http://balkutusu.com" --allow-root
docker exec hive_wordpress wp rewrite flush --allow-root

echo "--- Final WP options ---"
docker exec hive_wordpress wp option get siteurl --allow-root
docker exec hive_wordpress wp option get home --allow-root

echo "--- curl test ---"
curl -sI http://127.0.0.1/ -H "Host: balkutusu.com" | head -10

echo "=== RECOVERY DONE $(date) ==="
