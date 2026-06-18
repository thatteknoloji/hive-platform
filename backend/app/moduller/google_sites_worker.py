"""
Google Sites Worker V1 — gerçek browser automation ile Google Sites yayını.

OpenClaw veya Playwright kullanır. Mock/simülasyon yok.
Login/captcha/2FA bypass yok — login_required durumunda kullanıcı müdahalesi beklenir.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("hive.google_sites_worker")

STATE_FILE = Path(__file__).resolve().parent.parent / "google_sites_worker_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

GOOGLE_SITES_NEW_URL = "https://sites.google.com/new"
VIEW_URL_RE = re.compile(r"https?://sites\.google\.com/view/[a-zA-Z0-9][a-zA-Z0-9_-]*", re.I)
EDITOR_URL_RE = re.compile(r"sites\.google\.com/.+/d/[^/?#]+/edit", re.I)
BLANK_SITE_OPEN_TIMEOUT_MS = 30_000
TEMPLATE_GALLERY_SELECTORS = (
    'button:has-text("Şablon galerisi")',
    '[role="button"]:has-text("Şablon galerisi")',
    'div[role="button"]:has-text("Şablon galerisi")',
    "text=Şablon galerisi",
)
BLANK_SITE_JS_CLICK = """
() => {
  const img = document.querySelector('img[src*="sites-blank-googlecolors"]');
  if (!img) return false;
  img.scrollIntoView({ block: "center", inline: "center" });
  const target = img.closest('[role="option"], .docs-homescreen-templates-templateview');
  if (target) {
    target.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    target.click();
    return true;
  }
  img.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
  img.click();
  return true;
}
"""
MAX_PAGES_DEFAULT = 10
ACTIVE_STATUSES = frozenset({"queued", "login_required", "processing", "review_required", "published"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("tasks", [])
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"tasks": [], "history": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _config() -> dict[str, str]:
    return {
        "provider": (os.environ.get("GOOGLE_SITES_PROVIDER") or "playwright").strip().lower(),
        "profile": (os.environ.get("GOOGLE_SITES_PROFILE") or "default").strip(),
        "headless": (os.environ.get("GOOGLE_SITES_HEADLESS") or "false").strip().lower(),
        "user_data_dir": (os.environ.get("GOOGLE_SITES_USER_DATA_DIR") or "browser_profiles/google_sites").strip(),
        "default_template": (os.environ.get("GOOGLE_SITES_DEFAULT_TEMPLATE") or "authority_micro_site").strip(),
        "max_pages": (os.environ.get("GOOGLE_SITES_MAX_PAGES_PER_SITE") or str(MAX_PAGES_DEFAULT)).strip(),
        "openclaw_url": (os.environ.get("OPENCLAW_BROWSER_WORKER_URL") or "").strip(),
    }


def _max_pages() -> int:
    try:
        return max(1, min(50, int(_config()["max_pages"])))
    except ValueError:
        return MAX_PAGES_DEFAULT


def _profile_path(account_profile: str) -> Path:
    base = Path(_config()["user_data_dir"])
    if not base.is_absolute():
        base = Path(__file__).resolve().parent.parent.parent / base
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", (account_profile or "default").strip())[:64] or "default"
    path = base / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def _playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _chromium_executable_path() -> str | None:
    """Runtime Chromium binary yolu — health raporu için."""
    if not _playwright_available():
        return None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            exe = pw.chromium.executable_path
            if exe and Path(exe).exists():
                return str(exe)
    except Exception:
        pass
    return None


def _chromium_installed() -> bool:
    """Playwright Chromium binary kurulu mu — sahte ready engeli."""
    return _chromium_executable_path() is not None


def _browser_profile_dir(account_profile: str = "") -> str:
    return str(_profile_path(account_profile or _config()["profile"]))


def _headless_enabled() -> bool:
    return _config()["headless"] in ("1", "true", "yes")


def _login_error_code(url: str = "", message: str = "") -> str:
    blob = f"{url} {message}".lower()
    if any(x in blob for x in ("captcha", "challenge", "2fa", "twofactor", "two-factor")):
        return "captcha_or_2fa_required"
    return "google_login_required"


def detect_browser_provider() -> dict[str, Any]:
    """Öncelik: OpenClaw > Playwright (+ chromium) > provider_missing."""
    cfg = _config()
    openclaw = bool(cfg["openclaw_url"])
    playwright_pkg = _playwright_available()
    chromium_ok = _chromium_installed()
    preferred = cfg["provider"]

    if openclaw and preferred in ("openclaw", "auto", "playwright"):
        return {
            "ready": True,
            "provider": "openclaw",
            "openclaw": True,
            "playwright": playwright_pkg,
            "chromium_installed": chromium_ok,
            "error": None,
            "reason": "",
        }
    if playwright_pkg and preferred in ("playwright", "auto"):
        if chromium_ok:
            return {
                "ready": True,
                "provider": "playwright",
                "openclaw": openclaw,
                "playwright": True,
                "chromium_installed": True,
                "error": None,
                "reason": "",
            }
        return {
            "ready": False,
            "provider": "playwright",
            "openclaw": openclaw,
            "playwright": True,
            "chromium_installed": False,
            "error": "browser_missing",
            "reason": "Chromium binary eksik — backend venv içinde: python -m playwright install chromium",
        }
    if openclaw:
        return {
            "ready": True,
            "provider": "openclaw",
            "openclaw": True,
            "playwright": playwright_pkg,
            "chromium_installed": chromium_ok,
            "error": None,
            "reason": "",
        }
    if playwright_pkg and not chromium_ok:
        return {
            "ready": False,
            "provider": "playwright",
            "openclaw": openclaw,
            "playwright": True,
            "chromium_installed": False,
            "error": "browser_missing",
            "reason": "Chromium binary eksik — python -m playwright install chromium",
        }
    return {
        "ready": False,
        "provider": "missing",
        "openclaw": openclaw,
        "playwright": playwright_pkg,
        "chromium_installed": False,
        "error": "provider_missing",
        "reason": "OPENCLAW_BROWSER_WORKER_URL veya Playwright+Chromium yapılandırın",
    }


def _provider_ready() -> tuple[bool, str | None, str | None, str | None]:
    info = detect_browser_provider()
    if info.get("ready"):
        return True, None, info.get("provider"), None
    err = info.get("error") or "provider_missing"
    return False, info.get("reason") or err, info.get("provider"), err


def sanitize_slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return s[:60] or f"site-{uuid.uuid4().hex[:8]}"


def _escape(text: str) -> str:
    return html.escape(text or "")


def _apply_link_block(link: dict[str, Any]) -> str:
    if not link or link.get("link_type") == "no_link":
        return ""
    url = (link.get("target_url") or "").strip()
    if not url:
        return ""
    anchor = (link.get("anchor") or url).strip()
    if not anchor:
        return f'<p>Kaynak: {_escape(url)}</p>'
    return f'<p><a href="{_escape(url)}" rel="noopener">{_escape(anchor)}</a></p>'


def apply_link_policies(policies: list[dict[str, Any]], *, max_links: int = 2) -> str:
    """Authority Mesh link policy — anchor tekrarı ve exact-match spam engeli."""
    used_anchors: set[str] = set()
    blocks: list[str] = []
    for lp in policies or []:
        if len(blocks) >= max_links:
            break
        anchor = (lp.get("anchor") or "").strip().lower()
        if anchor and anchor in used_anchors:
            continue
        block = _apply_link_block(lp)
        if block:
            if anchor:
                used_anchors.add(anchor)
            blocks.append(block)
    return "\n".join(blocks)


def build_faq_html(keyword: str, count: int = 4) -> str:
    kw = keyword.strip() or "konu"
    faqs = [
        (f"{kw} nedir?", f"{kw} hakkında güncel ve pratik bilgiler sunan kapsamlı bir rehberdir."),
        (f"{kw} için en iyi kaynak hangisi?", "Bu sayfa temel rehberlik sağlar; detaylı içerik bölümlerde yer alır."),
        (f"{kw} hakkında nelere dikkat edilmeli?", "Güncel bilgiler, güvenilir kaynaklar ve pratik öneriler önemlidir."),
        (f"{kw} ile ilgili sık sorulan konular nelerdir?", "SSS bölümünde en çok merak edilen sorular yanıtlanmıştır."),
        (f"Daha fazla bilgi nerede bulunur?", "İlgili kaynak ve marka mention alanına bakın."),
    ]
    items = faqs[: max(3, min(5, count))]
    return "".join(
        f'<details class="faq-item"><summary>{_escape(q)}</summary><p>{_escape(a)}</p></details>'
        for q, a in items
    )


def build_page_html(
    *,
    site_title: str,
    target_keyword: str,
    page_title: str = "",
    body_html: str = "",
    link_policies: list[dict] | None = None,
    brand: str = "",
) -> str:
    title = page_title or site_title
    kw = target_keyword.strip()
    desc = f"{kw} hakkında güncel rehber, SSS ve pratik bilgiler." if kw else f"{title} — güncel rehber."
    link_html = apply_link_policies(link_policies or [])
    footer_brand = brand or site_title

    return f"""
<section class="answer-box" role="doc-abstract">
  <p><strong>{_escape(kw or title)}</strong> — {_escape(desc)}</p>
</section>
<section class="main-content">
  <h2>{_escape(title)}</h2>
  {body_html or f"<p>{_escape(kw)} hakkında derlenmiş güncel bilgiler ve pratik öneriler.</p>"}
</section>
{link_html}
<section class="faq"><h3>Sık Sorulan Sorular</h3>{build_faq_html(kw)}</section>
<footer><p>© {datetime.now(timezone.utc).year} {_escape(footer_brand)} — destekleyici otorite içeriği</p></footer>
""".strip()


def build_pages_payload(
    *,
    site_title: str,
    target_keyword: str,
    target_money_site: str,
    pages: list[dict] | None = None,
    link_policy: dict | list | None = None,
) -> list[dict[str, Any]]:
    from app.moduller.authority_mesh_engine import generate_link_policy

    policies: list[dict] = []
    if isinstance(link_policy, list):
        policies = link_policy
    elif isinstance(link_policy, dict) and link_policy:
        policies = [link_policy]
    else:
        policies = generate_link_policy(target_keyword, target_money_site)

    brand = "Kaynak"
    m = re.search(r"https?://(?:www\.)?([^/]+)", target_money_site or "")
    if m:
        brand = m.group(1).split(".")[0].capitalize()

    if pages:
        out: list[dict] = []
        for pg in pages[: _max_pages()]:
            lp = pg.get("link_policy")
            pg_policies = [lp] if isinstance(lp, dict) and lp else policies
            out.append({
                "title": pg.get("title") or site_title,
                "slug": pg.get("slug") or sanitize_slug(pg.get("title") or site_title),
                "content_html": pg.get("content_html") or build_page_html(
                    site_title=site_title,
                    target_keyword=target_keyword,
                    page_title=pg.get("title") or site_title,
                    link_policies=pg_policies,
                    brand=brand,
                ),
                "link_policy": lp if isinstance(lp, dict) else (pg_policies[0] if pg_policies else {}),
            })
        return out

    main_html = build_page_html(
        site_title=site_title,
        target_keyword=target_keyword,
        page_title=site_title,
        link_policies=policies,
        brand=brand,
    )
    return [{
        "title": site_title,
        "slug": sanitize_slug(site_title),
        "content_html": main_html,
        "link_policy": policies[0] if policies else {},
    }]


def _task_fingerprint(site_slug: str, account_profile: str, target_keyword: str) -> str:
    return f"{account_profile}:{site_slug}:{target_keyword}".lower()


def _duplicate_task_blocked(site_slug: str, account_profile: str) -> bool:
    st = _load_state()
    for t in st.get("tasks") or []:
        if (
            t.get("site_slug") == site_slug
            and t.get("account_profile") == account_profile
            and t.get("status") in ACTIVE_STATUSES
            and t.get("status") != "failed"
        ):
            return True
    return False


def _task_model(
    *,
    site_title: str,
    site_slug: str,
    target_keyword: str,
    target_money_site: str,
    account_profile: str,
    pages: list[dict],
    status: str = "queued",
) -> dict[str, Any]:
    return {
        "task_id": f"gsw-{uuid.uuid4().hex[:10]}",
        "status": status,
        "account_profile": account_profile,
        "site_title": site_title,
        "site_slug": site_slug,
        "target_keyword": target_keyword,
        "target_money_site": target_money_site,
        "pages": pages,
        "published_url": None,
        "error": None,
        "created_at": _now(),
        "updated_at": _now(),
    }


def create_task(
    *,
    site_title: str = "",
    site_slug: str = "",
    target_keyword: str = "",
    target_money_site: str = "",
    account_profile: str = "",
    pages: list[dict] | None = None,
    link_policy: dict | list | None = None,
) -> dict[str, Any]:
    title = (site_title or target_keyword or "").strip()
    if not title:
        return {"success": False, "error": "validation_error", "message": "site_title gerekli"}

    profile = (account_profile or _config()["profile"] or "default").strip()
    slug = sanitize_slug(site_slug or title)
    money = (target_money_site or "").strip()
    built_pages = build_pages_payload(
        site_title=title,
        target_keyword=target_keyword,
        target_money_site=money,
        pages=pages,
        link_policy=link_policy,
    )

    if _duplicate_task_blocked(slug, profile):
        return {
            "success": False,
            "error": "duplicate_task_blocked",
            "message": "Aynı slug/profile için aktif task mevcut",
        }

    task = _task_model(
        site_title=title,
        site_slug=slug,
        target_keyword=target_keyword.strip(),
        target_money_site=money,
        account_profile=profile,
        pages=built_pages,
    )

    st = _load_state()
    st.setdefault("tasks", []).insert(0, task)
    st.setdefault("history", []).insert(0, {"type": "task_created", "task_id": task["task_id"], "at": _now()})
    _save_state(st)
    _record_brain("google_sites_task_created", keyword=target_keyword, domain=money, result={"task_id": task["task_id"]}, reason=title)
    return {"success": True, "task": task}


def _find_task(task_id: str) -> dict[str, Any] | None:
    st = _load_state()
    return next((t for t in st.get("tasks") or [] if t.get("task_id") == task_id), None)


def _update_task(task: dict[str, Any]) -> None:
    st = _load_state()
    task["updated_at"] = _now()
    for i, t in enumerate(st.get("tasks") or []):
        if t.get("task_id") == task.get("task_id"):
            st["tasks"][i] = task
            _save_state(st)
            return
    st.setdefault("tasks", []).insert(0, task)
    _save_state(st)


def _detect_login_required_url(url: str) -> bool:
    u = (url or "").lower()
    return any(x in u for x in (
        "accounts.google.com",
        "signin",
        "servicelogin",
        "challenge",
        "captcha",
        "twofactor",
        "2fa",
    ))


def _is_sites_new_home_url(url: str) -> bool:
    u = (url or "").strip().lower().rstrip("/")
    if "sites.google.com" not in u:
        return False
    parsed = urlparse(u)
    path = (parsed.path or "").rstrip("/")
    return path.endswith("/new") or path == "/new"


def _is_sites_homescreen_url(url: str) -> bool:
    """sites.google.com ana ekranı — /new, /u/0/ vb.; editör veya view değil."""
    if _is_sites_editor_url(url):
        return False
    u = (url or "").lower()
    if "sites.google.com" not in u:
        return False
    if "/view/" in u:
        return False
    return True


def _is_sites_editor_url(url: str) -> bool:
    u = url or ""
    return "sites.google.com" in u.lower() and "/d/" in u and "/edit" in u


def _page_requires_login(page: Any) -> bool:
    try:
        if _detect_login_required_url(page.url):
            return True
        if page.locator('input[type="email"]').count() and page.locator('input[type="password"]').count():
            return True
    except Exception:
        pass
    return False


def _click_first_visible(page: Any, selectors: tuple[str, ...] | list[str], *, timeout: int = 5000, force_fallback: bool = True) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if not loc.count():
                continue
            if not loc.is_visible(timeout=min(timeout, 3000)):
                continue
            try:
                loc.click(timeout=timeout)
                return True
            except Exception:
                if force_fallback:
                    loc.click(force=True, timeout=timeout)
                    return True
        except Exception:
            continue
    return False


def _wait_for_editor_in_context(context: Any, primary: Any, *, timeout_ms: int = BLANK_SITE_OPEN_TIMEOUT_MS) -> Any | None:
    """Same-tab veya yeni sekme/popup — context içinde /d/.../edit sayfasını bekle."""
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        for pg in context.pages:
            try:
                if _is_sites_editor_url(pg.url):
                    try:
                        pg.wait_for_load_state("domcontentloaded", timeout=3000)
                    except Exception:
                        pass
                    return pg
            except Exception:
                continue
        try:
            primary.wait_for_timeout(400)
        except Exception:
            break
    for pg in context.pages:
        try:
            if _is_sites_editor_url(pg.url):
                return pg
        except Exception:
            continue
    return None


def _maybe_open_template_gallery(page: Any) -> None:
    """Boş site kartı görünmüyorsa Şablon galerisi drawer'ını aç."""
    try:
        if page.locator('img[src*="sites-blank-googlecolors"]').count():
            return
    except Exception:
        pass
    _click_first_visible(page, TEMPLATE_GALLERY_SELECTORS, timeout=6000)
    page.wait_for_timeout(1200)


def _wait_for_blank_site_card(page: Any, *, timeout_ms: int = 12_000) -> bool:
    try:
        page.locator('img[src*="sites-blank-googlecolors"]').first.wait_for(
            state="visible", timeout=timeout_ms,
        )
        return True
    except Exception:
        try:
            return page.locator('div[role="option"]:has-text("Boş site")').first.is_visible(timeout=2000)
        except Exception:
            return False


def _click_blank_site_parent_option(page: Any) -> bool:
    try:
        img = page.locator('img[src*="sites-blank-googlecolors"]').first
        if not img.count():
            return False
        img.scroll_into_view_if_needed(timeout=8000)
        for xpath in (
            'xpath=ancestor::*[@role="option"][1]',
            'xpath=ancestor::*[contains(@class,"docs-homescreen-templates-templateview")][1]',
        ):
            parent = img.locator(xpath)
            if parent.count():
                try:
                    parent.click(timeout=8000)
                    return True
                except Exception:
                    parent.click(force=True, timeout=8000)
                    return True
    except Exception:
        pass
    return False


def _click_blank_site_js(page: Any) -> bool:
    try:
        return bool(page.evaluate(BLANK_SITE_JS_CLICK))
    except Exception:
        return False


def _click_blank_site_card(page: Any) -> bool:
    """Boş site kartına sıralı fallback ile tıkla."""
    strategies = (
        lambda: _click_first_visible(
            page, ['div[role="option"]:has-text("Boş site")'], timeout=8000, force_fallback=True,
        ),
        lambda: _click_first_visible(
            page,
            ['.docs-homescreen-templates-templateview:has-text("Boş site")'],
            timeout=8000,
            force_fallback=True,
        ),
        _click_blank_site_parent_option,
        _click_blank_site_js,
    )
    for strategy in strategies:
        try:
            if strategy():
                page.wait_for_timeout(600)
                return True
        except Exception:
            continue
    return False


def _blank_site_not_opened_error(page: Any, site_slug: str, message: str) -> dict[str, Any]:
    candidate_urls: list[str] = []
    try:
        for pg in page.context.pages:
            u = getattr(pg, "url", "") or ""
            if u and u not in candidate_urls:
                candidate_urls.append(u)
    except Exception:
        pass
    if page.url and page.url not in candidate_urls:
        candidate_urls.insert(0, page.url)
    _write_publish_debug(
        page,
        site_slug,
        candidate_url=" | ".join(candidate_urls),
        error="blank_site_not_opened",
    )
    return {
        "success": False,
        "status": "review_required",
        "error": "blank_site_not_opened",
        "message": message,
    }


def _open_blank_site_editor(page: Any, site_slug: str) -> tuple[dict[str, Any] | None, Any]:
    """sites.google.com homescreen → Boş site → /d/.../edit. (error, active_page) döner."""
    context = page.context

    if _is_sites_editor_url(page.url):
        return None, page

    if not _is_sites_homescreen_url(page.url):
        return _blank_site_not_opened_error(page, site_slug, f"Beklenmeyen Google Sites sayfası: {page.url}"), page

    _maybe_open_template_gallery(page)
    if not _wait_for_blank_site_card(page):
        _maybe_open_template_gallery(page)
        _wait_for_blank_site_card(page, timeout_ms=8000)

    clicked = _click_blank_site_card(page)
    if not clicked:
        return _blank_site_not_opened_error(page, site_slug, "Boş site kartı bulunamadı veya tıklanamadı"), page

    editor_page = _wait_for_editor_in_context(context, page, timeout_ms=BLANK_SITE_OPEN_TIMEOUT_MS)
    if editor_page:
        return None, editor_page

    return _blank_site_not_opened_error(
        page, site_slug, "Boş site editörü açılamadı — /d/.../edit URL bekleniyordu",
    ), page


def _fit_sites_slug(slug: str) -> str:
    s = (slug or "").lower()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:30].strip("-") or "site"


def _slug_with_timestamp(base_slug: str) -> str:
    ts = str(int(time.time()))
    base = _fit_sites_slug(base_slug)
    suffix = f"-{ts}"
    trimmed = base[: max(1, 30 - len(suffix))].rstrip("-")
    return _fit_sites_slug(f"{trimmed}{suffix}")


PUBLISH_SLUG_INPUT_SELECTORS = (
    "input.poFWNe.zHQkBf",
    'input[jsname="YPqjbf"]',
    '[role="dialog"] input.poFWNe.zHQkBf',
    '[role="dialog"] input[jsname="YPqjbf"]',
    '[role="dialog"] [role="textbox"]',
    '[role="textbox"]',
    'input[aria-label*="Web adresi" i]',
    'input[aria-label*="web address" i]',
    'input[aria-label*="Web address" i]',
    'input[aria-label*="URL" i]',
)


def _locate_publish_slug_input(page: Any) -> Any | None:
    for sel in PUBLISH_SLUG_INPUT_SELECTORS:
        try:
            loc = page.locator(sel)
            count = min(loc.count(), 6)
            for i in range(count):
                inp = loc.nth(i)
                if inp.is_visible(timeout=1500):
                    return inp
        except Exception:
            continue
    return None


def _input_contains_slug(inp: Any, slug: str) -> bool:
    slug = (slug or "").strip()
    if not slug:
        return False
    for raw in (
        _read_input_slug_value(inp),
        _safe_input_attr(inp, "value"),
        _safe_input_attr(inp, "data-initial-value"),
    ):
        val = (raw or "").strip()
        if val and (slug in val or val.endswith(slug) or val.split("/")[-1] == slug):
            return True
    return False


def _safe_input_attr(inp: Any, name: str) -> str:
    try:
        return inp.get_attribute(name) or ""
    except Exception:
        return ""


def _read_input_slug_value(inp: Any) -> str:
    try:
        return inp.input_value() or ""
    except Exception:
        return _safe_input_attr(inp, "value")


def _uncheck_review_publish_checkbox(page: Any) -> None:
    """“İncele ve yayınla” — Düzenleyenler tikini kapat."""
    try:
        labels = page.locator('label:has-text("Düzenleyenler")')
        if labels.count():
            labels.first.click(timeout=5000)
            page.wait_for_timeout(1000)
    except Exception:
        pass


def _fill_publish_slug(page: Any, site_slug: str) -> str:
    slug = _fit_sites_slug(site_slug)

    inp = page.locator('input[aria-labelledby], input[type="text"]').filter(has_text="").last
    if not inp.count():
        inp = page.locator('input[type="text"]').last
    if not inp.count():
        located = _locate_publish_slug_input(page)
        if located is not None:
            inp = located

    if inp.count() and _input_contains_slug(inp, slug):
        _uncheck_review_publish_checkbox(page)
        return slug

    inp.click(timeout=10000)
    page.keyboard.press("Meta+A")
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    inp.fill(slug)
    page.wait_for_timeout(3000)

    _uncheck_review_publish_checkbox(page)
    return slug


def _wait_publish_button_enabled(page: Any, *, timeout_s: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        btn = _locate_final_publish_button(page)
        if btn is not None and not _is_final_publish_button_disabled(btn):
            aria_disabled = (btn.get_attribute("aria-disabled") or "").lower()
            if not aria_disabled or aria_disabled == "false":
                return True
        page.wait_for_timeout(400)
    return False


def _write_publish_dialog_debug(page: Any, site_slug: str, *, slug: str = "", error: str = "") -> None:
    """Publish dialog kapanmadan önce screenshot + url + html."""
    try:
        debug_dir = _debug_log_dir()
        safe = sanitize_slug(site_slug) or "unknown"
        stem = f"{safe}_publish_dialog"
        page.screenshot(path=str(debug_dir / f"{stem}_debug.png"), full_page=True)
        (debug_dir / f"{stem}_url.txt").write_text(
            "\n".join([
                f"page.url={getattr(page, 'url', '')}",
                f"slug={slug}",
                f"error={error}",
                f"at={_now()}",
            ]),
            encoding="utf-8",
        )
        (debug_dir / f"{stem}_html.html").write_text(page.content(), encoding="utf-8")
    except Exception as exc:
        logger.warning("publish dialog debug write failed: %s", exc)


def _is_final_publish_button_disabled(btn: Any) -> bool:
    try:
        cls = btn.get_attribute("class") or ""
        if "RDPZE" in cls:
            return True
        aria_disabled = (btn.get_attribute("aria-disabled") or "").lower()
        return aria_disabled == "true"
    except Exception:
        return True


def _locate_final_publish_button(page: Any) -> Any | None:
    locators = (
        page.locator('div[role="button"]:has-text("Yayınla")').filter(has_not_text="").last,
        page.locator('[role="dialog"] div[role="button"]:has-text("Yayınla")').last,
        page.locator('[role="dialog"] button:has-text("Yayınla")').last,
        page.locator('div[role="button"]:has-text("Publish")').last,
        page.locator('[role="dialog"] button:has-text("Publish")').last,
    )
    for loc in locators:
        try:
            if loc.count() and loc.is_visible(timeout=1500):
                return loc
        except Exception:
            continue
    return None


def _click_final_publish_button(page: Any, *, timeout_s: float = 20.0) -> bool:
    """Dialog içindeki son Yayınla — RDPZE/disabled atla, force click + JS fallback."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        btn = _locate_final_publish_button(page)
        if btn is None:
            page.wait_for_timeout(400)
            continue
        if _is_final_publish_button_disabled(btn):
            page.wait_for_timeout(400)
            continue
        aria_disabled = (btn.get_attribute("aria-disabled") or "").lower()
        if aria_disabled and aria_disabled != "false":
            page.wait_for_timeout(400)
            continue
        try:
            btn.scroll_into_view_if_needed(timeout=5000)
            try:
                btn.click(force=True, timeout=8000)
            except Exception:
                handle = btn.element_handle()
                if handle:
                    page.evaluate("(el) => el.click()", handle)
                else:
                    raise
            return True
        except Exception:
            page.wait_for_timeout(400)
    return False


def _publish_success_visible(page: Any, slug: str) -> bool:
    try:
        html_blob = (page.content() or "").lower()
    except Exception:
        html_blob = ""
    if f"sites.google.com/view/{slug.lower()}" in html_blob:
        return True
    success_markers = (
        "yayınlandı",
        "published",
        "site published",
        "view published site",
        "yayınlanan siteyi görüntüle",
    )
    if any(m in html_blob for m in success_markers):
        return True
    try:
        dialog = page.locator('[role="dialog"]').last
        if dialog.count():
            txt = (dialog.inner_text(timeout=2000) or "").lower()
            if any(m in txt for m in success_markers):
                return True
    except Exception:
        pass
    return False


def _infer_published_url_after_click(context: Any, page: Any, slug: str) -> str | None:
    extracted = _extract_published_view_url(context, page)
    if extracted:
        return _normalize_published_view_url(extracted)
    if _publish_success_visible(page, slug):
        return _normalize_published_view_url(f"https://sites.google.com/view/{slug}")
    return None


def _publish_slug_has_error(page: Any, inp: Any) -> bool:
    aria_invalid = (inp.get_attribute("aria-invalid") or "").lower()
    if aria_invalid in ("true", "1"):
        return True
    try:
        dialog = page.locator('[role="dialog"]').last
        if dialog.count():
            text = (dialog.inner_text(timeout=2000) or "").lower()
            if any(x in text for x in ("daha önce alınmış", "already been taken", "already taken", "unavailable")):
                return True
    except Exception:
        pass
    try:
        err_nodes = page.locator('[role="dialog"] [aria-live], [role="alert"]')
        for i in range(min(err_nodes.count(), 4)):
            txt = (err_nodes.nth(i).inner_text(timeout=800) or "").lower()
            if any(x in txt for x in ("daha önce alınmış", "already been taken", "already taken")):
                return True
    except Exception:
        pass
    return False


def _complete_publish_dialog(page: Any, site_slug: str) -> dict[str, Any]:
    """Slug hazırla, final Yayınla tıkla, view URL çıkar."""
    slug = _fill_publish_slug(page, site_slug)
    _write_publish_dialog_debug(page, site_slug, slug=slug)

    if not _wait_publish_button_enabled(page):
        return {"ok": False, "slug": slug, "published_url": None}

    if not _click_final_publish_button(page):
        return {"ok": False, "slug": slug, "published_url": None}

    page.wait_for_timeout(15_000)

    published_url = _infer_published_url_after_click(page.context, page, slug)
    return {
        "ok": bool(published_url),
        "slug": slug,
        "published_url": published_url,
    }


def _debug_log_dir() -> Path:
    path = Path(__file__).resolve().parent.parent / "logs" / "google_sites_debug"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_rejected_published_url(url: str) -> bool:
    """sites.google.com/new veya /view/ olmayan URL'ler published sayılmaz."""
    u = (url or "").strip().rstrip("/").lower()
    if not u.startswith("http"):
        return True
    if "sites.google.com" not in urlparse(u).netloc.lower():
        return True
    if u.endswith("/new") or "/new?" in u or u == "https://sites.google.com/new":
        return True
    if "/view/" not in u:
        return True
    return False


def _normalize_published_view_url(url: str) -> str | None:
    """Yalnızca https://sites.google.com/view/... formatını kabul et."""
    if not url or _is_rejected_published_url(url):
        return None
    match = VIEW_URL_RE.search(url)
    if match:
        return match.group(0).rstrip("/")
    parsed = urlparse(url.strip())
    if "sites.google.com" not in parsed.netloc.lower():
        return None
    path = (parsed.path or "").split("?")[0].rstrip("/")
    if "/view/" not in path or path.endswith("/new"):
        return None
    return f"{parsed.scheme}://{parsed.netloc}{path}".rstrip("/")


def _write_publish_debug(page: Any, site_slug: str, *, candidate_url: str = "", error: str = "") -> None:
    """Hata/review durumunda screenshot + url + html yaz."""
    try:
        debug_dir = _debug_log_dir()
        safe = sanitize_slug(site_slug) or "unknown"
        page.screenshot(path=str(debug_dir / f"{safe}_debug.png"), full_page=True)
        (debug_dir / f"{safe}_url.txt").write_text(
            "\n".join([
                f"page.url={getattr(page, 'url', '')}",
                f"candidate={candidate_url}",
                f"error={error}",
                f"at={_now()}",
            ]),
            encoding="utf-8",
        )
        (debug_dir / f"{safe}_html.html").write_text(page.content(), encoding="utf-8")
    except Exception as exc:
        logger.warning("google_sites debug write failed: %s", exc)


def _collect_view_url_candidates_from_page(page: Any) -> list[str]:
    candidates: list[str] = []
    try:
        candidates.append(page.url or "")
    except Exception:
        pass

    for selector, script in (
        ('a[href*="sites.google.com/view/"]', "els => els.map(e => e.href)"),
        ('a[href*="sites.google.com"]', "els => els.map(e => e.href).filter(h => h.includes('/view/'))"),
    ):
        try:
            hrefs = page.eval_on_selector_all(selector, script)
            candidates.extend(hrefs or [])
        except Exception:
            continue

    dialog_selectors = (
        'input[readonly][value*="sites.google.com/view/"]',
        'input[value*="sites.google.com/view/"]',
        '[data-url*="sites.google.com/view/"]',
        'a[href*="sites.google.com/view/"]',
        'input.poFWNe.zHQkBf',
        'input[jsname="YPqjbf"]',
    )
    for sel in dialog_selectors:
        try:
            loc = page.locator(sel)
            count = min(loc.count(), 8)
            for i in range(count):
                el = loc.nth(i)
                for attr in ("href", "value", "data-url", "data-initial-value"):
                    val = el.get_attribute(attr)
                    if val:
                        candidates.append(val)
                try:
                    val = el.input_value()
                    if val:
                        candidates.append(val)
                except Exception:
                    pass
                try:
                    txt = el.inner_text(timeout=1500)
                    if txt and "sites.google.com/view/" in txt:
                        candidates.append(txt)
                except Exception:
                    pass
        except Exception:
            continue

    try:
        body = page.content()
        candidates.extend(m.group(0) for m in VIEW_URL_RE.finditer(body))
        candidates.extend(re.findall(r"https?://sites\.google\.com/view/[a-zA-Z0-9][a-zA-Z0-9_/-]*", body, re.I))
    except Exception:
        pass
    return candidates


def _extract_published_view_url(context: Any, page: Any) -> str | None:
    """Publish sonrası page + tüm context sekmeleri + HTML içinden /view/ URL yakala."""
    candidates: list[str] = []
    pages_to_scan: list[Any] = []
    try:
        pages_to_scan = list(context.pages)
    except Exception:
        pages_to_scan = [page]
    if page not in pages_to_scan:
        pages_to_scan.insert(0, page)

    for pg in pages_to_scan:
        candidates.extend(_collect_view_url_candidates_from_page(pg))

    seen: set[str] = set()
    for raw in candidates:
        if not raw:
            continue
        for part in re.findall(r"https?://[^\s\"'<>]+", str(raw)):
            norm = _normalize_published_view_url(part)
            if norm and norm not in seen:
                seen.add(norm)
                return norm
    return None


def _extract_published_view_url_from_page(page: Any) -> str | None:
    """Backward-compatible wrapper."""
    try:
        return _extract_published_view_url(page.context, page)
    except Exception:
        candidates = _collect_view_url_candidates_from_page(page)
        for raw in candidates:
            for part in re.findall(r"https?://[^\s\"'<>]+", str(raw)):
                norm = _normalize_published_view_url(part)
                if norm:
                    return norm
        return None


def _verify_published_url(url: str) -> bool:
    """Sahte published_url üretimini engelle — yalnızca /view/ + HTTP doğrulama."""
    norm = _normalize_published_view_url(url)
    if not norm:
        return False
    try:
        import requests
        resp = requests.get(
            norm,
            timeout=45,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HIVE-GoogleSitesWorker/1.0)"},
        )
        if resp.status_code != 200:
            return False
        text = (resp.text or "").lower()
        if len(text) < 80:
            return False
        if "sign in" in text[:2000] and "google" in text[:2000]:
            return False
        final = _normalize_published_view_url(resp.url)
        return final is not None
    except Exception as exc:
        logger.debug("url verify failed: %s", exc)
        return False


def _login_required_result(message: str = "Google login gerekli — kullanıcı müdahalesi bekleniyor", *, url: str = "") -> dict[str, Any]:
    code = _login_error_code(url, message)
    return {
        "success": False,
        "status": "login_required",
        "error": code,
        "message": message,
    }


def _run_openclaw(task: dict[str, Any]) -> dict[str, Any]:
    cfg = _config()
    url = cfg["openclaw_url"].rstrip("/") + "/google-sites/publish"
    payload = {
        "site_title": task.get("site_title"),
        "site_slug": task.get("site_slug"),
        "pages": task.get("pages"),
        "target_money_site": task.get("target_money_site"),
        "target_keyword": task.get("target_keyword"),
        "account_profile": task.get("account_profile"),
    }
    try:
        import requests
        resp = requests.post(url, json=payload, timeout=180)
        data = resp.json() if resp.content else {}
    except Exception as exc:
        err = str(exc)
        if _detect_login_required_url(err) or any(x in err.lower() for x in ("login", "captcha", "2fa", "sign in")):
            return _login_required_result("OpenClaw: login/captcha — kullanıcı müdahalesi bekleniyor (bypass yok)")
        return {"success": False, "error": "browser_worker_error", "message": err}

    if resp.status_code == 401 or data.get("status") == "login_required":
        return _login_required_result(data.get("message") or "OpenClaw: Google login gerekli")

    pub_url = data.get("published_url") or data.get("url")
    norm = _normalize_published_view_url(pub_url or "")
    if norm and _verify_published_url(norm):
        return {"success": True, "status": "published", "published_url": norm}

    if data.get("error"):
        err = data.get("error", "")
        if any(x in str(err).lower() for x in ("login", "captcha", "2fa", "auth")):
            return _login_required_result(data.get("message") or str(err))
        return {"success": False, "error": data.get("error"), "message": data.get("message", "")}

    return {
        "success": False,
        "status": "review_required",
        "message": data.get("message") or "OpenClaw yanıt verdi — URL doğrulama gerekli",
        "worker_result": data,
    }


def _html_to_plain_blocks(content_html: str) -> list[str]:
    text = re.sub(r"<br\s*/?>", "\n", content_html or "", flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    parts = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return parts or [text.strip() or "İçerik"]


def _playwright_publish(task: dict[str, Any]) -> dict[str, Any]:
    """Gerçek Playwright browser automation — login bypass yok."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        return {"success": False, "error": "provider_missing", "message": "Playwright yüklü değil"}

    cfg = _config()
    profile_dir = _profile_path(task.get("account_profile", "default"))
    headless = cfg["headless"] in ("1", "true", "yes")
    site_title = task.get("site_title", "")
    site_slug = task.get("site_slug") or sanitize_slug(site_title)
    pages = task.get("pages") or []

    published_url: str | None = None
    error_msg: str | None = None
    title_set = False
    page = None
    context = None

    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=headless,
                channel="chrome" if _chrome_channel_available() else None,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(GOOGLE_SITES_NEW_URL, wait_until="domcontentloaded", timeout=90000)

            page.wait_for_timeout(1500)
            if _page_requires_login(page):
                context.close()
                return _login_required_result(url=page.url)

            blank_err, page = _open_blank_site_editor(page, site_slug)
            if blank_err:
                context.close()
                return blank_err

            if not _is_sites_editor_url(page.url):
                _write_publish_debug(page, site_slug, candidate_url=page.url, error="blank_site_not_opened")
                context.close()
                return {
                    "success": False,
                    "status": "review_required",
                    "error": "blank_site_not_opened",
                    "message": "Editör açılmadan devam edilemez",
                }

            page.wait_for_timeout(1000)

            # Site başlığı — editör açıkken
            title_selectors = [
                'input[aria-label*="Site name" i]',
                'input[aria-label*="site name" i]',
                'input[placeholder*="Site name" i]',
                '[contenteditable="true"]',
            ]
            title_set = False
            for sel in title_selectors:
                try:
                    el = page.locator(sel).first
                    if el.count() and el.is_visible(timeout=3000):
                        el.click(timeout=5000)
                        el.fill(site_title) if "input" in sel else el.type(site_title, delay=20)
                        title_set = True
                        break
                except Exception:
                    continue

            if not title_set:
                try:
                    page.keyboard.type(site_title, delay=25)
                    title_set = True
                except Exception:
                    pass

            page.wait_for_timeout(1500)

            # İlk sayfa içeriği
            main_page = pages[0] if pages else {}
            content_html = main_page.get("content_html") or ""
            blocks = _html_to_plain_blocks(content_html)

            insert_selectors = [
                'button[aria-label*="Insert" i]',
                'button[aria-label*="Text" i]',
                '[data-tooltip*="Text" i]',
            ]
            for sel in insert_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.count() and btn.is_visible(timeout=2000):
                        btn.click(timeout=5000)
                        break
                except Exception:
                    continue

            for block in blocks[:12]:
                try:
                    editable = page.locator('[contenteditable="true"]').last
                    if editable.count():
                        editable.click(timeout=3000)
                        editable.type(block[:800], delay=10)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(400)
                except Exception:
                    try:
                        page.keyboard.type(block[:800], delay=10)
                        page.keyboard.press("Enter")
                    except Exception:
                        pass

            # Ek sayfalar
            for extra in pages[1:_max_pages()]:
                pg_title = extra.get("title") or site_title
                try:
                    add_page = page.locator('button[aria-label*="Pages" i], button[aria-label*="Add page" i]').first
                    if add_page.count():
                        add_page.click(timeout=5000)
                        page.wait_for_timeout(800)
                    page.keyboard.type(pg_title[:80], delay=15)
                    page.keyboard.press("Enter")
                    for block in _html_to_plain_blocks(extra.get("content_html") or "")[:8]:
                        page.keyboard.type(block[:600], delay=10)
                        page.keyboard.press("Enter")
                except Exception as exc:
                    logger.debug("extra page: %s", exc)

            # Publish — toolbar
            publish_selectors = [
                'button:has-text("Yayınla")',
                'div[role="button"]:has-text("Yayınla")',
                'button:has-text("Publish")',
                '[aria-label*="Yayınla" i]',
                '[aria-label*="Publish" i]',
                'div[role="button"]:has-text("Publish")',
            ]
            published_clicked = False
            for sel in publish_selectors:
                try:
                    pub = page.locator(sel).first
                    if pub.count() and pub.is_visible(timeout=3000):
                        pub.click(timeout=8000)
                        published_clicked = True
                        break
                except Exception:
                    continue

            publish_dialog_ok = False
            publish_candidate_url: str | None = None
            if published_clicked:
                page.wait_for_timeout(1500)
                pub_result = _complete_publish_dialog(page, site_slug)
                publish_dialog_ok = bool(pub_result.get("published_url"))
                publish_candidate_url = pub_result.get("published_url")

            # URL yakalama — page + tüm sekmeler + HTML; yalnızca /view/
            published_url = publish_candidate_url or _extract_published_view_url(context, page)
            if published_url:
                published_url = _normalize_published_view_url(published_url)

            if not published_url or not _verify_published_url(published_url or ""):
                all_urls = " | ".join(
                    dict.fromkeys(
                        getattr(p, "url", "") or ""
                        for p in (context.pages if context else [page])
                        if getattr(p, "url", "")
                    )
                )
                _write_publish_debug(
                    page,
                    site_slug,
                    candidate_url=published_url or all_urls or page.url,
                    error=error_msg or ("publish_dialog_failed" if published_clicked and not publish_dialog_ok else "no_valid_view_url"),
                )

            if context:
                context.close()
            context = None
            page = None

    except PWTimeout as exc:
        error_msg = f"Playwright timeout: {exc}"
        if page is not None:
            _write_publish_debug(page, site_slug, candidate_url=published_url or page.url, error=error_msg)
        if _detect_login_required_url(str(exc)):
            return _login_required_result(url=str(exc))
    except Exception as exc:
        err = str(exc)
        if page is not None:
            _write_publish_debug(page, site_slug, candidate_url=published_url or getattr(page, "url", ""), error=err)
        if "Executable doesn't exist" in err or "playwright install" in err.lower():
            return {
                "success": False,
                "status": "browser_missing",
                "error": "browser_missing",
                "message": "Chromium binary eksik — python -m playwright install chromium",
            }
        if any(x in err.lower() for x in ("login", "captcha", "2fa", "sign in", "auth")):
            return _login_required_result("Login/captcha algılandı — bypass yok, kullanıcı müdahalesi gerekli", url=err)
        error_msg = err
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass

    if published_url and _verify_published_url(published_url):
        return {"success": True, "status": "published", "published_url": published_url}

    if error_msg and _detect_login_required_url(error_msg):
        return _login_required_result(error_msg, url=error_msg)

    if published_url:
        return {
            "success": False,
            "status": "review_required",
            "error": "published_url_verification_failed",
            "message": "URL doğrulanamadı — /view/ public link gerekli",
            "candidate_url": published_url,
        }

    return {
        "success": False,
        "status": "review_required" if title_set else "failed",
        "error": error_msg or "publish_incomplete",
        "message": error_msg or "Yayın tamamlanamadı veya /view/ URL alınamadı",
    }


def _chrome_channel_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            browser.close()
        return True
    except Exception:
        return False


def run_task_automation(task: dict[str, Any]) -> dict[str, Any]:
    """Authority Mesh delegasyonu — browser automation çalıştır."""
    ready, err, provider, err_code = _provider_ready()
    if not ready:
        status = err_code if err_code in ("browser_missing", "provider_missing") else "provider_missing"
        return {"success": False, "error": status, "status": status, "message": err}

    if provider == "openclaw":
        return _run_openclaw(task)
    if provider == "playwright":
        return _playwright_publish(task)
    return {"success": False, "error": "provider_missing", "message": err}


def _record_brain(event_type: str, *, domain: str = "", keyword: str = "", result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            "module_action",
            "google_sites_worker",
            domain=domain,
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "google_sites_worker", "gs_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain: %s", exc)


def _notify_integrations(task: dict[str, Any], *, network_id: str = "") -> dict[str, Any]:
    url = task.get("published_url") or ""
    keyword = task.get("target_keyword") or ""
    out: dict[str, Any] = {}

    if not url:
        return out

    try:
        from app.moduller.authority_mesh_engine import register_external_publish
        reg = register_external_publish(
            "google_sites",
            url=url,
            keyword=keyword,
            money_site=task.get("target_money_site", ""),
            role="support_hub",
            network_id=network_id,
        )
        out["authority_mesh"] = reg
        out["rank_watcher"] = reg.get("rank_watcher") or {}
    except Exception as exc:
        out["authority_mesh"] = {"success": False, "error": str(exc)}

    _record_brain(
        "authority_source_created",
        domain=url,
        keyword=keyword,
        result={"task_id": task.get("task_id")},
        reason=task.get("site_title", ""),
    )
    return out


def process_task(task_id: str, *, network_id: str = "", resume: bool = False) -> dict[str, Any]:
    ready, err, _, err_code = _provider_ready()
    if not ready:
        status = err_code if err_code in ("browser_missing", "provider_missing") else "provider_missing"
        return {"success": False, "error": status, "status": status, "message": err}

    task = _find_task(task_id)
    if not task:
        return {"success": False, "error": "task_not_found"}

    if task.get("status") == "published" and task.get("published_url"):
        return {"success": True, "task": task, "note": "already_published"}

    if task.get("status") == "login_required" and not resume:
        return {
            "success": False,
            "error": task.get("error") or "google_login_required",
            "status": "login_required",
            "message": "Login gerekli — resume-task ile devam edin",
            "task": task,
        }

    task["status"] = "processing"
    task["error"] = None
    _update_task(task)

    worker_res = run_task_automation(task)

    worker_status = worker_res.get("status")
    worker_error = worker_res.get("error")

    if worker_status == "login_required":
        task["status"] = "login_required"
        task["error"] = worker_error or _login_error_code("", worker_res.get("message", ""))
        _record_brain("google_sites_login_required", keyword=task.get("target_keyword", ""), result={"task_id": task_id}, reason=task.get("site_title", ""))
    elif worker_status in ("browser_missing", "provider_missing") or worker_error in ("browser_missing", "provider_missing"):
        task["status"] = worker_error or worker_status or "provider_missing"
        task["error"] = worker_res.get("message") or task["status"]
    elif worker_status == "published" and worker_res.get("published_url"):
        norm_url = _normalize_published_view_url(worker_res["published_url"])
        if not norm_url or not _verify_published_url(norm_url):
            task["status"] = "review_required"
            task["error"] = worker_res.get("message") or "published_url_verification_failed"
            if worker_res.get("candidate_url") or worker_res.get("published_url"):
                task["candidate_url"] = worker_res.get("candidate_url") or worker_res.get("published_url")
            _record_brain("google_sites_failed", keyword=task.get("target_keyword", ""), result=worker_res, reason="url_verify")
        else:
            task["status"] = "published"
            task["published_url"] = norm_url
            task["error"] = None
            integrations = _notify_integrations(task, network_id=network_id)
            _record_brain("google_sites_published", domain=task["published_url"], keyword=task.get("target_keyword", ""), result={"task_id": task_id}, reason=task.get("site_title", ""))
            worker_res["integrations"] = integrations
    elif worker_status == "review_required":
        task["status"] = "review_required"
        task["error"] = worker_res.get("error") or worker_res.get("message")
        if worker_res.get("candidate_url"):
            task["candidate_url"] = worker_res["candidate_url"]
    elif worker_error == "published_url_verification_failed":
        task["status"] = "review_required"
        task["error"] = worker_res.get("message") or "published_url_verification_failed"
        if worker_res.get("candidate_url"):
            task["candidate_url"] = worker_res["candidate_url"]
        _record_brain("google_sites_failed", keyword=task.get("target_keyword", ""), result=worker_res, reason="url_verify")
    else:
        task["status"] = "failed"
        task["error"] = worker_res.get("message") or worker_res.get("error")
        _record_brain("google_sites_failed", keyword=task.get("target_keyword", ""), result=worker_res, reason=task.get("site_title", ""))

    _update_task(task)
    st = _load_state()
    st.setdefault("history", []).insert(0, {
        "type": "task_processed",
        "task_id": task_id,
        "status": task["status"],
        "resume": resume,
        "at": _now(),
    })
    _save_state(st)

    terminal_ok = task["status"] in ("published", "review_required", "login_required")
    return {
        "success": terminal_ok,
        "task": task,
        "worker": worker_res,
    }


def resume_task(task_id: str, *, network_id: str = "") -> dict[str, Any]:
    task = _find_task(task_id)
    if not task:
        return {"success": False, "error": "task_not_found"}
    if task.get("status") not in ("login_required", "processing", "queued"):
        return {
            "success": False,
            "error": "invalid_status",
            "message": f"resume yalnızca login_required/queued için — mevcut: {task.get('status')}",
            "task": task,
        }
    return process_task(task_id, network_id=network_id, resume=True)


def list_tasks(limit: int = 50) -> dict[str, Any]:
    st = _load_state()
    tasks = list(st.get("tasks") or [])[:max(1, min(200, limit))]
    return {"success": True, "count": len(tasks), "tasks": tasks}


def get_task(task_id: str) -> dict[str, Any]:
    if not task_id:
        return {"success": False, "error": "task_id gerekli"}
    task = _find_task(task_id)
    if not task:
        return {"success": False, "error": "task_not_found"}
    return {"success": True, "task": task}


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = list_tasks(200) if report_type == "tasks" else {"health": health(), "tasks": list_tasks(100)}
    path = REPORTS_DIR / f"google-sites-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def health() -> dict[str, Any]:
    provider_info = detect_browser_provider()
    st = _load_state()
    tasks = st.get("tasks") or []
    profile = _config()["profile"]
    ready = bool(provider_info.get("ready"))
    provider = provider_info.get("provider") or "missing"
    return {
        "success": True,
        "module": "google_sites_worker",
        "provider": provider,
        "playwright_installed": _playwright_available(),
        "chromium_installed": bool(provider_info.get("chromium_installed")),
        "chromium_executable_path": _chromium_executable_path() or "",
        "browser_profile_dir": _browser_profile_dir(profile),
        "headless": _headless_enabled(),
        "ready": ready,
        "reason": "" if ready else (provider_info.get("reason") or provider_info.get("error") or "provider_missing"),
        # backward compatibility
        "provider_ready": ready,
        "error": None if ready else (provider_info.get("error") or provider_info.get("reason")),
        "openclaw_configured": provider_info.get("openclaw", False),
        "playwright_available": provider_info.get("playwright", False),
        "default_profile": profile,
        "max_pages_per_site": _max_pages(),
        "tasks_count": len(tasks),
        "published_count": sum(1 for t in tasks if t.get("status") == "published"),
        "login_required_count": sum(1 for t in tasks if t.get("status") == "login_required"),
        "browser_missing_count": sum(1 for t in tasks if t.get("status") == "browser_missing"),
        "provider_missing_count": sum(1 for t in tasks if t.get("status") == "provider_missing"),
        "failed_count": sum(1 for t in tasks if t.get("status") == "failed"),
    }


def create_task_from_mesh_item(
    *,
    title: str,
    keyword: str,
    money_site: str,
    account_profile: str = "default",
    link_policy: dict | None = None,
    pages: list | None = None,
) -> dict[str, Any]:
    """Authority Mesh process_plan delegasyonu."""
    return create_task(
        site_title=title,
        target_keyword=keyword,
        target_money_site=money_site,
        account_profile=account_profile,
        link_policy=link_policy,
        pages=pages,
    )
