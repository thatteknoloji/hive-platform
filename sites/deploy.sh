#!/bin/bash
# ============================================
# BALKUTUSU.COM - VPS DEPLOY SCRIPT
# Çalıştır: bash deploy.sh
# ============================================

set -e

echo "🚀 Balkutusu.com WordPress Multisite Kurulumu"
echo "============================================="

# 1. Dizin oluştur
echo "[1/7] Dizin oluşturuluyor..."
mkdir -p /opt/thiqos/apps/hive/sites/nginx/ssl
cd /opt/thiqos/apps/hive/sites

# 2. Docker kontrol
echo "[2/7] Docker kontrol ediliyor..."
if ! command -v docker &> /dev/null; then
    echo "Docker bulunamadı, kuruluyor..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose kuruluyor..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 3. Dosyaları kopyala (lokalden scp ile gönderildiğini varsayıyoruz)
echo "[3/7] Dosyalar kontrol ediliyor..."
if [ ! -f docker-compose.yml ]; then
    echo "❌ docker-compose.yml bulunamadı! Önce dosyaları scp ile gönder."
    echo "   scp -r ./sites/* root@13.140.138.135:/opt/thiqos/apps/hive/sites/"
    exit 1
fi

# 4. Self-signed SSL oluştur (Cloudflare proxy kullanıyorsan gerekmez ama nginx için)
echo "[4/7] SSL sertifikası oluşturuluyor..."
if [ ! -f nginx/ssl/cert.pem ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/CN=balkutusu.com" \
        -addext "subjectAltName=DNS:balkutusu.com,DNS:*.balkutusu.com"
    echo "✅ Self-signed SSL oluşturuldu"
fi

# 5. Docker Compose başlat
echo "[5/7] Docker container'lar başlatılıyor..."
docker-compose down 2>/dev/null || true
docker-compose up -d

# 6. WordPress'in hazır olmasını bekle
echo "[6/7] WordPress bekleniyor..."
sleep 15

# 7. WordPress CLI ile Multisite kur
echo "[7/7] WordPress Multisite kuruluyor..."

# WP-CLI ile WordPress'i kur (eğer ilk kurulumsa)
docker exec hive_wordpress bash -c '
if [ ! -f /var/www/html/wp-config.php ]; then
    echo "WordPress ilk kurulum modu..."
    # wp-cli yoksa kur
    curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
    chmod +x wp-cli.phar
    mv wp-cli.phar /usr/local/bin/wp
    
    # WordPress kur
    wp core install \
        --url="https://balkutusu.com" \
        --title="Balkutusu" \
        --admin_user="admin" \
        --admin_password="Balkut2026!" \
        --admin_email="admin@balkutusu.com" \
        --allow-root || echo "WP zaten kurulu olabilir"
fi
'

# Multisite aktivasyonu için wp-config.php'yi düzenle
docker exec hive_wordpress bash -c '
if ! grep -q "MULTISITE" /var/www/html/wp-config.php; then
    echo "Multisite satırları ekleniyor..."
    cat >> /var/www/html/wp-config.php << "EOF"

// Multisite Configuration
define("WP_ALLOW_MULTISITE", true);
define("MULTISITE", true);
define("SUBDOMAIN_INSTALL", true);
define("DOMAIN_CURRENT_SITE", "balkutusu.com");
define("PATH_CURRENT_SITE", "/");
define("SITE_ID_CURRENT_SITE", 1);
define("BLOG_ID_CURRENT_SITE", 1);
EOF
    echo "✅ Multisite config eklendi"
else
    echo "ℹ️  Multisite zaten aktif"
fi
'

# Container'ları yeniden başlat
docker-compose restart wordpress nginx

echo ""
echo "============================================="
echo "✅ KURULUM TAMAMLANDI!"
echo "============================================="
echo ""
echo "🌐 WordPress: https://balkutusu.com"
echo "🔐 Admin:     https://balkutusu.com/wp-admin"
echo "👤 Kullanıcı: admin"
echo "🔑 Şifre:     Balkut2026!"
echo ""
echo "⚠️  ÖNEMLİ: İlk girişte Multisite kurulumunu"
echo "   wp-admin > Araçlar > Ağ Kurulumu'ndan tamamla."
echo ""
echo "📋 Subdomain'ler (Multisite'den eklenecek):"
echo "   - vip-model.balkutusu.com"
echo "   - anal.balkutusu.com"
echo "   - oral.balkutusu.com"
echo "   - otel.balkutusu.com"
echo "   - gece.balkutusu.com"
echo ""
