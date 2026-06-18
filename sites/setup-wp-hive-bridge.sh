#!/bin/bash
# HIVE WordPress Bridge + JWT kurulumu (VPS Docker)
set -euo pipefail

WP="docker exec hive_wordpress wp --allow-root"
URL="${WP_URL:-https://balkutusu.com}"

echo "=== 1) HIVE WP Bridge plugin aktif ==="
$WP plugin activate hive-multisite-bridge/hive-multisite-bridge.php --url="$URL" 2>/dev/null || true

echo "=== 2) JWT Authentication plugin ==="
$WP plugin install jwt-authentication-for-wp-rest-api --activate --url="$URL" 2>/dev/null || \
$WP plugin activate jwt-authentication-for-wp-rest-api --url="$URL" 2>/dev/null || true

echo "=== 3) JWT secret + CORS (wp-config) ==="
SECRET=$(openssl rand -base64 48 | tr -d '\n')
docker exec hive_wordpress bash -c "
grep -q JWT_AUTH_SECRET_KEY /var/www/html/wp-config.php || echo \"define('JWT_AUTH_SECRET_KEY', '${SECRET}');\" >> /var/www/html/wp-config.php
grep -q JWT_AUTH_CORS_ENABLE /var/www/html/wp-config.php || echo \"define('JWT_AUTH_CORS_ENABLE', true);\" >> /var/www/html/wp-config.php
grep -q WP_ENVIRONMENT_TYPE /var/www/html/wp-config.php || echo \"define('WP_ENVIRONMENT_TYPE', 'production');\" >> /var/www/html/wp-config.php
"

echo "=== 4) Permalink + flush ==="
$WP rewrite structure '/%postname%/' --url="$URL"
$WP rewrite flush --url="$URL"

echo "=== 5) REST test ==="
curl -sk "${URL}/wp-json/" | head -c 200
echo ""
echo "=== Bitti ==="
echo "Application Password: WP Admin > Kullanıcılar > Profil > Uygulama Parolaları"
echo "HIVE Panel > WordPress Manager ile bağlanın."
