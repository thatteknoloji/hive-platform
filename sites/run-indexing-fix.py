#!/usr/bin/env python3
"""VPS üzerinde WordPress indeksleme düzeltmeleri."""
import os
import pexpect
import shlex
import sys

HOST = os.environ.get("VPS_HOST", "13.140.138.135")
USER = os.environ.get("VPS_SSH_USER", "root")
PASS = os.environ.get("VPS_SSH_PASS", "")
SITE = "https://www.balkutusu.com"


def ssh(cmd, timeout=180):
    child = pexpect.spawn(
        f"ssh -o StrictHostKeyChecking=no {USER}@{HOST} {shlex.quote(cmd)}",
        timeout=timeout,
        encoding="utf-8",
    )
    idx = child.expect(["password:", pexpect.EOF, pexpect.TIMEOUT], timeout=30)
    if idx == 0:
        if not PASS:
            print("VPS_SSH_PASS gerekli", file=sys.stderr)
            sys.exit(1)
        child.sendline(PASS)
        child.expect(pexpect.EOF, timeout=timeout)
    out = (child.before or "").strip()
    return out, child.exitstatus


steps = [
    ("WP-CLI kontrol", "docker exec hive_wordpress wp --info --allow-root 2>&1 | head -3"),
    (
        "Site URL (www + https)",
        f"""docker exec hive_wordpress wp option update siteurl '{SITE}' --allow-root && \
docker exec hive_wordpress wp option update home '{SITE}' --allow-root && \
echo siteurl=$(docker exec hive_wordpress wp option get siteurl --allow-root) && \
echo home=$(docker exec hive_wordpress wp option get home --allow-root)""",
    ),
    (
        "Arama motoru görünürlüğü (blog_public=1)",
        """docker exec hive_wordpress wp option update blog_public 1 --allow-root && \
echo blog_public=$(docker exec hive_wordpress wp option get blog_public --allow-root)""",
    ),
    (
        "Permalink Post name",
        """docker exec hive_wordpress wp rewrite structure '/%postname%/' --allow-root && \
docker exec hive_wordpress wp rewrite flush --allow-root && \
echo permalink=$(docker exec hive_wordpress wp option get permalink_structure --allow-root)""",
    ),
    (
        "Rank Math noindex kapat",
        """docker exec hive_wordpress wp plugin is-active seo-by-rank-math --allow-root 2>/dev/null && \
docker exec hive_wordpress wp option patch update rank-math-options-titles homepage_robots '["index","follow"]' --allow-root 2>/dev/null || true && \
docker exec hive_wordpress wp option patch update rank-math-options-titles noindex_empty_taxonomies off --allow-root 2>/dev/null || true && \
echo rank_math_ok=1 || echo rank_math_skip=1""",
    ),
    (
        ".htaccess rewrite",
        """docker exec hive_wordpress bash -c 'test -f /var/www/html/.htaccess && head -20 /var/www/html/.htaccess || echo NO_HTACCESS'""",
    ),
    (
        "REST API test",
        f"""docker exec hive_wordpress wp eval 'echo wp_remote_retrieve_response_code(wp_remote_get("{SITE}/wp-json/"));' --allow-root""",
    ),
    (
        "IndexNow key dosyası",
        """KEY=hive-indexnow-balkutusu
docker exec hive_wordpress bash -c "echo -n $KEY > /var/www/html/$KEY.txt && chmod 644 /var/www/html/$KEY.txt"
echo indexnow_key=$KEY""",
    ),
]

if __name__ == "__main__":
    for title, cmd in steps:
        print(f"\n{'=' * 50}\n{title}\n{'=' * 50}")
        out, code = ssh(cmd)
        print(out)
        print(f"exit: {code}")
