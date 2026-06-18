#!/usr/bin/env bash
# HIVE panel kullanıcı yönetimi (şifre sıfırlama / oluşturma)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

usage() {
  echo "Kullanım:"
  echo "  bash scripts/panel-user.sh reset  EMAIL  NEW_PASSWORD"
  echo "  bash scripts/panel-user.sh create EMAIL  PASSWORD [role]"
  echo ""
  echo "Örnek:"
  echo "  bash scripts/panel-user.sh reset admin@thiqos.com admin12345"
  exit 1
}

[[ $# -ge 3 ]] || usage

ACTION="$1"
EMAIL="$2"
PASSWORD="$3"
ROLE="${4:-admin}"

./venv/bin/python - "$ACTION" "$EMAIL" "$PASSWORD" "$ROLE" <<'PY'
import sys
from app import panel_identity

action, email, password, role = sys.argv[1:5]
if action == "reset":
    result = panel_identity.reset_user_password(email, password)
elif action == "create":
    result = panel_identity.create_user(email=email, password=password, role=role)
else:
    print(f"Bilinmeyen komut: {action}", file=sys.stderr)
    sys.exit(1)

if not result.get("success"):
    print(f"HATA: {result.get('error', 'unknown')}", file=sys.stderr)
    sys.exit(1)

print(f"OK: {action} {email}")
PY
