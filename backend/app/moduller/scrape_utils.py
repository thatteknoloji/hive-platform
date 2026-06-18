"""Paylaşılan HTTP kazıma yardımcıları — Web Scraper & Lead Scraper."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "HIVE-Scraper/1.0 (+https://balkutusu.com; SEO research bot)"
FETCH_TIMEOUT = 20
MAX_HTML_BYTES = 500_000

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+90[\s\-]?)?(?:0)?5\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
    r"|(?:\+90[\s\-]?)?\(?0?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)


def normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = f"https://{u}"
    parsed = urlparse(u)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def same_domain(base_url: str, other_url: str) -> bool:
    try:
        a = urlparse(normalize_url(base_url)).netloc.lower().replace("www.", "")
        b = urlparse(normalize_url(other_url)).netloc.lower().replace("www.", "")
        return bool(a and b and a == b)
    except Exception:
        return False


def robots_allowed(url: str) -> tuple[bool, str | None]:
    parsed = urlparse(normalize_url(url))
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    path = parsed.path or "/"
    try:
        r = requests.get(robots_url, timeout=10, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return True, None
        for line in r.text.splitlines():
            line = line.strip()
            if line.lower().startswith("disallow:"):
                dis = line.split(":", 1)[1].strip()
                if dis and path.startswith(dis):
                    return False, f"robots.txt disallow: {dis}"
    except requests.RequestException:
        return True, None
    return True, None


def fetch_html(url: str) -> tuple[str | None, str | None]:
    target = normalize_url(url)
    if not target:
        return None, "URL geçersiz"
    allowed, reason = robots_allowed(target)
    if not allowed:
        return None, reason or "robots.txt engeli"
    try:
        r = requests.get(
            target,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            allow_redirects=True,
        )
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}"
        content_type = (r.headers.get("content-type") or "").lower()
        if "html" not in content_type and "text/" not in content_type:
            return None, f"HTML değil: {content_type[:60]}"
        r.encoding = r.encoding or "utf-8"
        return r.text[:MAX_HTML_BYTES], None
    except requests.RequestException as exc:
        return None, str(exc)


def extract_contacts(text: str) -> dict[str, list[str]]:
    emails = []
    for m in EMAIL_RE.findall(text or ""):
        low = m.lower()
        if low.endswith((".png", ".jpg", ".gif", ".webp", ".svg")):
            continue
        if "example.com" in low or "wixpress" in low or "sentry" in low:
            continue
        emails.append(m)
    phones = []
    for m in PHONE_RE.findall(text or ""):
        digits = re.sub(r"\D", "", m)
        if len(digits) >= 10:
            phones.append(m.strip())
    return {
        "emails": list(dict.fromkeys(emails))[:30],
        "phones": list(dict.fromkeys(phones))[:30],
    }


def parse_page(html: str, page_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    meta_desc = ""
    for meta in soup.find_all("meta"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        if name in ("description", "og:description"):
            meta_desc = (meta.get("content") or "").strip()
            if meta_desc:
                break

    headings: list[dict[str, str]] = []
    for level in ("h1", "h2", "h3"):
        for tag in soup.find_all(level)[:20]:
            text = tag.get_text(strip=True)
            if text:
                headings.append({"level": level, "text": text[:240]})

    links: list[dict[str, str]] = []
    internal_links: list[str] = []
    seen_hrefs: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"].strip())
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        text = a.get_text(strip=True)[:120]
        links.append({"href": href, "text": text})
        if same_domain(page_url, href):
            internal_links.append(href)
        if len(links) >= 80:
            break

    images: list[dict[str, str]] = []
    for img in soup.find_all("img")[:40]:
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        images.append({
            "src": urljoin(page_url, src),
            "alt": (img.get("alt") or "")[:160],
        })

    paragraphs = [
        p.get_text(strip=True)[:400]
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 40
    ][:12]

    plain = soup.get_text(separator=" ", strip=True)
    contacts = extract_contacts(plain)

    return {
        "title": title,
        "meta_description": meta_desc[:500],
        "headings": headings,
        "links": links,
        "internal_links": list(dict.fromkeys(internal_links))[:40],
        "images": images,
        "paragraphs": paragraphs,
        "word_count": len(plain.split()),
        "text_excerpt": plain[:1200],
        "emails": contacts["emails"],
        "phones": contacts["phones"],
    }
