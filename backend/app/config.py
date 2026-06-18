import os

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def reload_env() -> None:
    """backend/.env dosyasını oku — boş ortam değişkenlerini de güncelle."""
    if not os.path.exists(_env_path):
        return
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip("\"'")
            if not val:
                continue
            current = os.environ.get(key, "")
            if key not in os.environ or not str(current).strip():
                os.environ[key] = val


reload_env()


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def has(key: str) -> bool:
    return bool(os.environ.get(key, "").strip())
