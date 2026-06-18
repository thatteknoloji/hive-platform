#!/usr/bin/env python3
"""Generate bcrypt hash for HIVE_ADMIN_PASSWORD_HASH in backend/.env"""
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.auth import hash_password  # noqa: E402


def main() -> None:
    pwd = getpass.getpass("Admin password: ")
    if len(pwd) < 10:
        print("Password must be at least 10 characters.", file=sys.stderr)
        sys.exit(1)
    print(hash_password(pwd))


if __name__ == "__main__":
    main()
