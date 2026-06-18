#!/usr/bin/env python3
import pexpect
import shlex
import sys

HOST = "13.140.138.135"
USER = "root"
PASS = ""  # set via env VPS_SSH_PASS or prompt

def ssh(cmd, timeout=120):
    child = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no {USER}@{HOST} {shlex.quote(cmd)}",
        timeout=timeout,
        encoding="utf-8",
    )
    idx = child.expect(["password:", pexpect.EOF, pexpect.TIMEOUT], timeout=30)
    if idx == 0:
        child.sendline(PASS)
        child.expect(pexpect.EOF, timeout=timeout)
    return child.before or "", child.exitstatus

steps = [
    ("ADIM 1 - Docker kontrol",
     """for c in twitter-redis twitter-postgres postgres redis qdrant ollama hive_wordpress hive_db; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then echo "[OK] $c"; 
  elif docker ps -a --format '{{.Names}}' | grep -qx "$c"; then echo "[START] $c"; docker start "$c";
  else echo "[MISSING] $c"; fi; done && docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'"""),
    ("ADIM 2 - Port 8080",
     """cd /opt/thiqos/apps/hive/sites && (grep -q '8080:80' docker-compose.yml || sed -i 's/"80:80"/"8080:80"/' docker-compose.yml) && docker-compose up -d && sleep 8 && docker ps --filter name=hive_wordpress --format '{{.Ports}}'"""),
    ("ADIM 3 - WP-CLI",
     """docker exec hive_wordpress bash -c 'curl -sO https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && chmod +x wp-cli.phar && mv -f wp-cli.phar /usr/local/bin/wp' && docker exec hive_wordpress wp --info --allow-root | head -2"""),
    ("ADIM 4 - Gecici URL",
     """docker exec hive_wordpress wp option update siteurl 'http://13.140.138.135:8080' --allow-root && docker exec hive_wordpress wp option update home 'http://13.140.138.135:8080' --allow-root"""),
    ("ADIM 5 - Nginx",
     """sudo rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default && printf '%s\\n' 'server {' '    listen 80;' '    server_name balkutusu.com;' '    location / {' '        proxy_pass http://127.0.0.1:8080;' '        proxy_set_header Host \\$host;' '        proxy_set_header X-Real-IP \\$remote_addr;' '    }' '}' | sudo tee /etc/nginx/sites-available/wordpress > /dev/null && sudo ln -sf /etc/nginx/sites-available/wordpress /etc/nginx/sites-enabled/wordpress && sudo nginx -t && sudo systemctl enable nginx && sudo systemctl restart nginx && systemctl is-active nginx"""),
    ("ADIM 6 - Domain URL",
     """docker exec hive_wordpress wp option update siteurl 'http://balkutusu.com' --allow-root && docker exec hive_wordpress wp option update home 'http://balkutusu.com' --allow-root && docker exec hive_wordpress wp rewrite flush --allow-root && echo siteurl=$(docker exec hive_wordpress wp option get siteurl --allow-root) && echo home=$(docker exec hive_wordpress wp option get home --allow-root)"""),
    ("ADIM 7 - Test",
     """curl -sI http://127.0.0.1/ -H 'Host: balkutusu.com' | head -8"""),
]

for title, cmd in steps:
    print(f"\n{'='*50}\n{title}\n{'='*50}")
    out, code = ssh(cmd)
    print(out)
    print(f"exit: {code}")
    if code not in (0, None) and title != "ADIM 1 - Docker kontrol":
        print("HATA - devam ediliyor...", file=sys.stderr)

print("\n=== BITTI ===")
