"""
WordPress REST API istemcisi — JWT + Application Password (Basic Auth)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

from app import config
from .modul_base import simdi

logger = logging.getLogger("hive.wordpress")

DATA_DIR = Path(__file__).resolve().parent.parent
SESSION_FILE = DATA_DIR / "wp_sessions.json"

PROFILE_META_KEYS = [
    "yas", "telefon", "telegram", "lokasyon", "fiyat",
    "odeme_sekli", "ozellikler", "vip", "hizmetler",
]


def _load_sessions() -> dict:
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_sessions(data: dict) -> None:
    SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_session(domain_id: int = 0) -> dict | None:
    data = _load_sessions()
    key = str(domain_id)
    if key in data:
        return data[key]
    if "0" in data:
        return data["0"]
    return None


def _env_credentials() -> tuple[str, str, str]:
    url = (config.get("WP_URL") or "").strip().rstrip("/")
    user = (config.get("WP_USERNAME") or "").strip()
    password = (config.get("WP_APP_PASSWORD") or config.get("WP_PASSWORD") or "").strip()
    return url, user, password


def _ping_session(session: dict) -> bool:
    if not session or not session.get("url"):
        return False
    try:
        api = WordPressAPI.__new__(WordPressAPI)
        api.domain_id = 0
        api._session = session
        res = api._request("GET", "/wp-json/hive/v1/test")
        return bool(res.get("success"))
    except Exception:
        return False


def ensure_wp_connected(domain_id: int = 0, verify: bool = False) -> dict[str, Any]:
    """
    WP oturumu yoksa veya ölüyse .env'deki WP_URL / WP_USERNAME / WP_APP_PASSWORD ile bağlan.
    verify=True ise mevcut oturumu test endpoint ile doğrular; ölü oturumu temizler.
    """
    from app import config
    config.reload_env()

    api = WordPressAPI(domain_id)
    if api.connected:
        if not verify or _ping_session(api._session):
            st = api.status()
            st["auto_connected"] = False
            return st
        logger.warning("WP oturumu geçersiz — yeniden bağlanılıyor (%s)", api._session.get("url"))
        api.disconnect()
        api = WordPressAPI(domain_id)

    url, user, password = _env_credentials()
    if not url or not user or not password:
        return {
            "connected": False,
            "auto_connected": False,
            "error": ".env'de WP_URL, WP_USERNAME ve WP_APP_PASSWORD tanımlı değil",
        }

    logger.info("WP otomatik bağlanıyor: %s (%s)", url, user)
    result = api.login(url, user, password)
    if result.get("success"):
        st = api.status()
        st["auto_connected"] = True
        st["message"] = "Otomatik bağlandı (.env)"
        return st

    return {
        "connected": False,
        "auto_connected": False,
        "error": result.get("error", "Otomatik bağlantı başarısız"),
    }


class WordPressAPI:
  """HIVE ↔ WordPress REST köprüsü."""

  def __init__(self, domain_id: int = 0):
      self.domain_id = domain_id
      self._session: dict | None = get_session(domain_id)

  @property
  def connected(self) -> bool:
      return bool(self._session and self._session.get("url"))

  def _base(self) -> str:
      if not self._session:
          raise ValueError("WordPress bağlantısı yok")
      return self._session["url"].rstrip("/")

  def _auth_headers(self) -> dict[str, str]:
      if not self._session:
          return {}
      token = self._session.get("jwt_token")
      if token and self._session.get("jwt_expires", 0) > time.time():
          return {"Authorization": f"Bearer {token}"}
      return {}

  def _auth(self) -> HTTPBasicAuth | None:
      if not self._session:
          return None
      if self._auth_headers():
          return None
      return HTTPBasicAuth(
          self._session["username"],
          self._session["password"],
      )

  def login(self, url: str, username: str, password: str) -> dict[str, Any]:
      """JWT veya Application Password ile bağlan."""
      url = url.rstrip("/")
      jwt = self._fetch_jwt(url, username, password)
      auth_mode = "jwt" if jwt else "basic"

      test = self._raw_request(
          "GET",
          f"{url}/wp-json/hive/v1/test",
          username=username,
          password=password,
          jwt_token=jwt.get("token") if jwt else None,
      )
      if test.status_code == 401:
          return {"success": False, "error": "Yetkilendirme hatası: kullanıcı adı veya şifre yanlış"}
      if test.status_code == 404:
          return {
              "success": False,
              "error": "HIVE WP Bridge plugin bulunamadı. sites/setup-wp-hive-bridge.sh çalıştırın.",
          }
      if test.status_code >= 400:
          return {"success": False, "error": f"Bağlantı hatası: HTTP {test.status_code}"}

      data = test.json()
      session = {
          "url": url,
          "username": username,
          "password": password,
          "auth_mode": auth_mode,
          "connected_at": simdi(),
          "is_multisite": data.get("is_multisite", False),
          "site_count": data.get("site_count", 0),
          "jwt_token": jwt.get("token") if jwt else None,
          "jwt_expires": time.time() + int(jwt.get("expires_in", 3600)) if jwt else 0,
      }
      sessions = _load_sessions()
      sessions[str(self.domain_id)] = session
      _save_sessions(sessions)
      self._session = session
      return {
          "success": True,
          "message": "Bağlantı başarılı",
          "auth_mode": auth_mode,
          "is_multisite": session["is_multisite"],
          "site_count": session["site_count"],
          "current_user": data.get("current_user", username),
      }

  def disconnect(self) -> dict:
      sessions = _load_sessions()
      sessions.pop(str(self.domain_id), None)
      _save_sessions(sessions)
      self._session = None
      return {"success": True, "message": "Bağlantı kesildi"}

  def status(self) -> dict:
      if not self.connected:
          return {"connected": False}
      return {
          "connected": True,
          "url": self._session["url"],
          "username": self._session["username"],
          "auth_mode": self._session.get("auth_mode", "basic"),
          "connected_at": self._session.get("connected_at"),
          "is_multisite": self._session.get("is_multisite", False),
          "site_count": self._session.get("site_count", 0),
      }

  def refresh_token(self) -> bool:
      if not self._session:
          return False
      jwt = self._fetch_jwt(
          self._session["url"],
          self._session["username"],
          self._session["password"],
      )
      if jwt:
          self._session["jwt_token"] = jwt.get("token")
          self._session["jwt_expires"] = time.time() + int(jwt.get("expires_in", 3600))
          sessions = _load_sessions()
          sessions[str(self.domain_id)] = self._session
          _save_sessions(sessions)
          return True
      return False

  def _fetch_jwt(self, url: str, username: str, password: str) -> dict | None:
      try:
          r = requests.post(
              f"{url.rstrip('/')}/wp-json/jwt-auth/v1/token",
              json={"username": username, "password": password},
              timeout=15,
              verify=False,
          )
          if r.status_code == 200:
              return r.json()
      except requests.RequestException:
          pass
      return None

  def _raw_request(
      self,
      method: str,
      url: str,
      *,
      username: str | None = None,
      password: str | None = None,
      jwt_token: str | None = None,
      **kwargs,
  ) -> requests.Response:
      headers = kwargs.pop("headers", {}) or {}
      if jwt_token:
          headers["Authorization"] = f"Bearer {jwt_token}"
      auth = None
      if not jwt_token and username and password:
          auth = HTTPBasicAuth(username, password)
      return requests.request(
          method, url, headers=headers, auth=auth, timeout=30, verify=False, **kwargs
      )

  def _request(
      self,
      method: str,
      path: str,
      *,
      json_body: dict | None = None,
      params: dict | None = None,
      files: Any = None,
      data: Any = None,
  ) -> dict[str, Any]:
      if not self.connected:
          return {"success": False, "error": "Önce WordPress'e bağlanın"}

      if self._session.get("jwt_expires", 0) < time.time() and self._session.get("auth_mode") == "jwt":
          self.refresh_token()

      url = f"{self._base()}{path}"
      headers = {**self._auth_headers(), "Accept": "application/json"}
      if json_body is not None and files is None:
          headers["Content-Type"] = "application/json"

      try:
          r = requests.request(
              method,
              url,
              headers=headers,
              auth=self._auth(),
              json=json_body if files is None else None,
              params=params,
              files=files,
              data=data,
              timeout=60,
              verify=False,
          )
      except requests.exceptions.ConnectionError:
          return {"success": False, "error": f"Sunucuya bağlanılamadı: {self._base()}"}
      except requests.exceptions.Timeout:
          return {"success": False, "error": "İstek zaman aşımına uğradı"}

      if r.status_code == 401:
          if self.refresh_token():
              return self._request(method, path, json_body=json_body, params=params, files=files, data=data)
          return {"success": False, "error": "Yetkilendirme süresi doldu — tekrar giriş yapın"}

      if r.status_code >= 400:
          try:
              err = r.json()
              msg = err.get("message") or err.get("code") or r.text[:200]
          except Exception:
              msg = r.text[:200] or f"HTTP {r.status_code}"
          return {"success": False, "error": msg, "status_code": r.status_code}

      if r.status_code == 204 or not r.text:
          return {"success": True}
      try:
          body = r.json()
      except Exception:
          body = {"raw": r.text}
      if isinstance(body, dict) and "success" not in body:
          return {"success": True, **body}
      return body if isinstance(body, dict) else {"success": True, "data": body}

  # ── Posts ──
  def get_posts(self, page: int = 1, per_page: int = 20, search: str = "") -> dict:
      params = {"page": page, "per_page": per_page}
      if search:
          params["search"] = search
      return self._request("GET", "/wp-json/wp/v2/posts", params=params)

  def create_post(self, title: str, content: str = "", status: str = "draft", **extra) -> dict:
      return self._request("POST", "/wp-json/wp/v2/posts", json_body={"title": title, "content": content, "status": status, **extra})

  def update_post(self, post_id: int, **fields) -> dict:
      return self._request("POST", f"/wp-json/wp/v2/posts/{post_id}", json_body=fields)

  def delete_post(self, post_id: int, force: bool = True) -> dict:
      return self._request("DELETE", f"/wp-json/wp/v2/posts/{post_id}", params={"force": force})

  # ── Pages ──
  def get_pages(self, page: int = 1, per_page: int = 20) -> dict:
      return self._request("GET", "/wp-json/wp/v2/pages", params={"page": page, "per_page": per_page})

  def create_page(self, title: str, content: str = "", status: str = "draft", **extra) -> dict:
      return self._request("POST", "/wp-json/wp/v2/pages", json_body={"title": title, "content": content, "status": status, **extra})

  def update_page(self, page_id: int, **fields) -> dict:
      return self._request("POST", f"/wp-json/wp/v2/pages/{page_id}", json_body=fields)

  def delete_page(self, page_id: int, force: bool = True) -> dict:
      return self._request("DELETE", f"/wp-json/wp/v2/pages/{page_id}", params={"force": force})

  def _list_rest_items(self, rest: str, **params: Any) -> list[dict[str, Any]]:
      raw = self._request("GET", f"/wp-json/wp/v2/{rest}", params=params)
      if not raw.get("success"):
          return []
      data = raw.get("data")
      if isinstance(data, list):
          return [x for x in data if isinstance(x, dict)]
      if raw.get("id"):
          return [raw]
      return []

  def find_by_slug(self, rest: str, slug: str) -> dict[str, Any] | None:
      slug = (slug or "").strip().strip("/")
      if not slug:
          return None
      items = self._list_rest_items(
          rest,
          slug=slug,
          per_page=1,
          status="publish,draft,pending,private",
      )
      return items[0] if items else None

  def upsert_page(
      self,
      title: str,
      content: str,
      slug: str = "",
      status: str = "publish",
      **extra: Any,
  ) -> dict[str, Any]:
      slug = (slug or "").strip().strip("/")
      body: dict[str, Any] = {"title": title, "content": content, "status": status, **extra}
      if slug:
          body["slug"] = slug
      existing = self.find_by_slug("pages", slug) if slug else None
      if existing and existing.get("id"):
          res = self.update_page(int(existing["id"]), **body)
          page_id = res.get("id") or existing.get("id")
          if res.get("success") or page_id:
              return {
                  **res,
                  "success": True,
                  "id": page_id,
                  "link": res.get("link") or existing.get("link", ""),
                  "updated": True,
              }
          return res
      res = self.create_page(title, content, status=status, slug=slug or None, **extra)
      if res.get("success") or res.get("id"):
          return {**res, "success": True, "created": True}
      return res

  def trash_conflicting_post(self, slug: str) -> dict[str, Any] | None:
      """Aynı slug'lı yazı varsa çöp kutusuna taşır (sayfa önceliği için)."""
      post = self.find_by_slug("posts", slug)
      if post and post.get("id"):
          return self.delete_post(int(post["id"]), force=False)
      return None

  # ── Profiles (companion_profile) ──
  def get_profiles(self, page: int = 1, per_page: int = 20, search: str = "") -> dict:
      params = {"page": page, "per_page": per_page}
      if search:
          params["search"] = search
      return self._request("GET", "/wp-json/wp/v2/companion_profile", params=params)

  def get_profile(self, profile_id: int) -> dict:
      return self._request("GET", f"/wp-json/wp/v2/companion_profile/{profile_id}")

  def create_profile(
      self,
      title: str,
      content: str = "",
      status: str = "publish",
      meta: dict | None = None,
      categories: list | None = None,
      featured_media: int | None = None,
      excerpt: str = "",
      slug: str = "",
  ) -> dict:
      body: dict[str, Any] = {"title": title, "content": content, "status": status}
      if meta:
          body["meta"] = meta
      if categories:
          body["companion_category"] = categories
      if featured_media:
          body["featured_media"] = featured_media
      if excerpt:
          body["excerpt"] = excerpt
      if slug:
          body["slug"] = slug
      return self._request("POST", "/wp-json/wp/v2/companion_profile", json_body=body)

  def resolve_companion_category_ids(self, categories: list | None) -> list[int]:
      if not categories:
          return []
      listed = self.get_categories("companion_category", per_page=100)
      slug_map: dict[str, int] = {}
      rows = listed.get("data") if isinstance(listed.get("data"), list) else []
      if not rows and listed.get("id"):
          rows = [listed]
      for t in rows:
          if isinstance(t, dict) and t.get("id"):
              slug_map[t.get("slug", "")] = int(t["id"])
      ids: list[int] = []
      for item in categories:
          if isinstance(item, int):
              ids.append(item)
              continue
          s = str(item).strip()
          if s.isdigit():
              ids.append(int(s))
          elif s in slug_map:
              ids.append(slug_map[s])
      return ids

  def update_profile(self, profile_id: int, **fields) -> dict:
      return self._request("POST", f"/wp-json/wp/v2/companion_profile/{profile_id}", json_body=fields)

  def delete_profile(self, profile_id: int, force: bool = True) -> dict:
      return self._request("DELETE", f"/wp-json/wp/v2/companion_profile/{profile_id}", params={"force": force})

  # ── Erotic stories ──
  def list_story_categories(self) -> dict[str, Any]:
      raw = self._request("GET", "/wp-json/wp/v2/story_category", params={"per_page": 100})
      if not raw.get("success"):
          return raw
      rows = raw.get("data") if isinstance(raw.get("data"), list) else []
      terms = [
          {"id": int(t["id"]), "slug": t.get("slug", ""), "name": t.get("name", ""), "parent": int(t.get("parent") or 0)}
          for t in rows
          if isinstance(t, dict) and t.get("id")
      ]
      return {"success": True, "terms": terms, "count": len(terms)}

  def create_story_category(self, name: str, slug: str, parent: int = 0) -> dict[str, Any]:
      body: dict[str, Any] = {"name": name, "slug": slug}
      if parent:
          body["parent"] = parent
      raw = self._request("POST", "/wp-json/wp/v2/story_category", json_body=body)
      if raw.get("success") and raw.get("id"):
          return {"success": True, "id": int(raw["id"]), "slug": raw.get("slug", slug), "name": raw.get("name", name)}
      return raw

  def resolve_story_category_ids(self, categories: list | None) -> list[int]:
      """Slug veya ID listesini WP term ID'lerine çevirir (REST slug kabul etmez)."""
      if not categories:
          return []
      listed = self.list_story_categories()
      slug_map: dict[str, int] = {}
      if listed.get("success"):
          for t in listed.get("terms", []):
              slug_map[t["slug"]] = t["id"]

      ids: list[int] = []
      for item in categories:
          if isinstance(item, int):
              ids.append(item)
              continue
          s = str(item).strip()
          if s.isdigit():
              ids.append(int(s))
              continue
          if s in slug_map:
              ids.append(slug_map[s])
      return ids

  def create_erotic_story(
      self,
      title: str,
      content: str = "",
      status: str = "publish",
      excerpt: str = "",
      meta: dict | None = None,
      categories: list | None = None,
      featured_media: int | None = None,
  ) -> dict:
      body: dict[str, Any] = {"title": title, "content": content, "status": status}
      if excerpt:
          body["excerpt"] = excerpt
      if meta:
          body["meta"] = meta
      if categories:
          term_ids = self.resolve_story_category_ids(categories)
          if term_ids:
              body["story_category"] = term_ids
      if featured_media:
          body["featured_media"] = featured_media
      return self._request("POST", "/wp-json/wp/v2/erotic_story", json_body=body)

  def update_erotic_story(self, post_id: int, **fields) -> dict:
      return self._request("POST", f"/wp-json/wp/v2/erotic_story/{post_id}", json_body=fields)

  def get_erotic_stories(self, page: int = 1, per_page: int = 20) -> dict:
      return self._request(
          "GET",
          "/wp-json/wp/v2/erotic_story",
          params={"page": page, "per_page": per_page, "status": "publish"},
      )

  def count_post_type(self, post_type: str = "erotic_story", status: str = "publish") -> dict:
      if not self.connected:
          return {"success": False, "error": "Önce WordPress'e bağlanın"}
      url = f"{self._base()}/wp-json/wp/v2/{post_type}"
      headers = {**self._auth_headers(), "Accept": "application/json"}
      try:
          r = requests.get(
              url,
              headers=headers,
              auth=self._auth(),
              params={"per_page": 1, "page": 1, "status": status},
              timeout=30,
              verify=False,
          )
      except requests.exceptions.RequestException as e:
          return {"success": False, "error": str(e)}
      if r.status_code >= 400:
          return {"success": False, "error": f"HTTP {r.status_code}"}
      return {
          "success": True,
          "total": int(r.headers.get("X-WP-Total", 0)),
          "post_type": post_type,
          "status": status,
      }

  # ── Categories (companion_category + post categories) ──
  def get_categories(self, taxonomy: str = "companion_category", per_page: int = 100) -> dict:
      return self._request("GET", f"/wp-json/wp/v2/{taxonomy}", params={"per_page": per_page})

  def create_category(self, name: str, taxonomy: str = "companion_category", parent: int = 0, slug: str = "") -> dict:
      body = {"name": name, "parent": parent}
      if slug:
          body["slug"] = slug
      return self._request("POST", f"/wp-json/wp/v2/{taxonomy}", json_body=body)

  def update_category(self, term_id: int, taxonomy: str = "companion_category", **fields) -> dict:
      return self._request("POST", f"/wp-json/wp/v2/{taxonomy}/{term_id}", json_body=fields)

  def delete_category(self, term_id: int, taxonomy: str = "companion_category", force: bool = True) -> dict:
      return self._request("DELETE", f"/wp-json/wp/v2/{taxonomy}/{term_id}", params={"force": force})

  # ── Tags ──
  def get_tags(self, per_page: int = 100) -> dict:
      return self._request("GET", "/wp-json/wp/v2/tags", params={"per_page": per_page})

  def create_tag(self, name: str) -> dict:
      return self._request("POST", "/wp-json/wp/v2/tags", json_body={"name": name})

  # ── Media ──
  def get_media(self, page: int = 1, per_page: int = 24) -> dict:
      return self._request("GET", "/wp-json/wp/v2/media", params={"page": page, "per_page": per_page})

  def upload_media(self, filename: str, file_bytes: bytes, mime: str = "image/jpeg") -> dict:
      if not self.connected:
          return {"success": False, "error": "Önce WordPress'e bağlanın"}
      url = f"{self._base()}/wp-json/wp/v2/media"
      headers = {
          **self._auth_headers(),
          "Content-Disposition": f'attachment; filename="{filename}"',
          "Content-Type": mime,
      }
      try:
          r = requests.post(
              url,
              headers=headers,
              auth=self._auth(),
              data=file_bytes,
              timeout=120,
              verify=False,
          )
      except requests.RequestException as e:
          return {"success": False, "error": str(e)}
      if r.status_code >= 400:
          return {"success": False, "error": r.text[:300]}
      return {"success": True, **r.json()}

  def delete_media(self, media_id: int, force: bool = True) -> dict:
      return self._request("DELETE", f"/wp-json/wp/v2/media/{media_id}", params={"force": force})

  # ── Users ──
  def get_users(self, per_page: int = 50) -> dict:
      return self._request("GET", "/wp-json/wp/v2/users", params={"per_page": per_page})

  def create_user(self, username: str, email: str, password: str, roles: list | None = None) -> dict:
      body = {"username": username, "email": email, "password": password}
      if roles:
          body["roles"] = roles
      return self._request("POST", "/wp-json/wp/v2/users", json_body=body)

  def update_user(self, user_id: int, **fields) -> dict:
      return self._request("POST", f"/wp-json/wp/v2/users/{user_id}", json_body=fields)

  def delete_user(self, user_id: int, reassign: int = 1) -> dict:
      return self._request("DELETE", f"/wp-json/wp/v2/users/{user_id}", params={"force": True, "reassign": reassign})

  # ── Comments ──
  def get_comments(self, page: int = 1, status: str = "hold") -> dict:
      return self._request("GET", "/wp-json/wp/v2/comments", params={"page": page, "status": status})

  def approve_comment(self, comment_id: int) -> dict:
      return self._request("POST", f"/wp-json/wp/v2/comments/{comment_id}", json_body={"status": "approved"})

  def delete_comment(self, comment_id: int, force: bool = True) -> dict:
      return self._request("DELETE", f"/wp-json/wp/v2/comments/{comment_id}", params={"force": force})

  # ── Bridge: plugins, themes, settings, multisite ──
  def get_plugins(self) -> dict:
      return self._request("GET", "/wp-json/hive/v1/plugins")

  def activate_plugin(self, plugin_file: str) -> dict:
      return self._request("POST", f"/wp-json/hive/v1/plugins/{quote(plugin_file, safe='')}/activate")

  def deactivate_plugin(self, plugin_file: str) -> dict:
      return self._request("POST", f"/wp-json/hive/v1/plugins/{quote(plugin_file, safe='')}/deactivate")

  def get_themes(self) -> dict:
      return self._request("GET", "/wp-json/hive/v1/themes")

  def activate_theme(self, stylesheet: str) -> dict:
      return self._request("POST", f"/wp-json/hive/v1/themes/{quote(stylesheet, safe='')}/activate")

  def get_settings(self) -> dict:
      return self._request("GET", "/wp-json/hive/v1/settings")

  def update_settings(self, **fields) -> dict:
      return self._request("PUT", "/wp-json/hive/v1/settings", json_body=fields)

  def get_head_injections(self) -> dict:
      return self._request("GET", "/wp-json/hive/v1/head-injections")

  def update_head_injections(self, injections: list) -> dict:
      return self._request("PUT", "/wp-json/hive/v1/head-injections", json_body={"injections": injections})

  def get_sites(self) -> dict:
      return self._request("GET", "/wp-json/hive/v1/sites")

  def create_site(self, domain: str, title: str, email: str, path: str = "/") -> dict:
      return self._request("POST", "/wp-json/hive/v1/sites", json_body={"domain": domain, "title": title, "email": email, "path": path})

  def delete_site(self, blog_id: int) -> dict:
      return self._request("DELETE", f"/wp-json/hive/v1/sites/{blog_id}")


def wp_api(domain_id: int = 0, auto_connect: bool = True) -> WordPressAPI:
      api = WordPressAPI(domain_id)
      if auto_connect and not api.connected:
          ensure_wp_connected(domain_id)
          api._session = get_session(domain_id)
      return api
