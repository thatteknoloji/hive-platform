#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kuşadası Gece Hayatı — 180 mekan rehberini WordPress'e import eder.

CPT: gece_hayati
Taxonomies: gece_mahalle, gece_saat, gece_tur
İç linkleme: mahalle/saat/tür arşivleri + aynı mahalledeki diğer mekanlar

Kullanım (VPS):
  python3 sites/import-gece-hayati.py --url https://balkutusu.com
  python3 sites/import-gece-hayati.py --host 13.140.138.135 --url https://balkutusu.com --limit 180

Yerel Docker:
  python3 sites/import-gece-hayati.py --url https://balkutusu.com --dry-run
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import textwrap
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

import importlib.util

_gen_path = SCRIPT_DIR / "generate-gece-hayati-rehberi.py"
_spec = importlib.util.spec_from_file_location("gece_hayati_gen", _gen_path)
_gece_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_gece_mod)

SLOTS = _gece_mod.SLOTS
TYPES = _gece_mod.TYPES
build_content_map = _gece_mod.build_content_map

CONTENT_DIR = SCRIPT_DIR / "content" / "gece-hayati" / "mekanlar"


def wp_cli(cmd: list[str], url: str, host: str | None, ssh_user: str, ssh_pass: str) -> subprocess.CompletedProcess:
    inner = ["docker", "exec", "hive_wordpress", "wp", "--allow-root", f"--url={url}"] + cmd
    if host:
        full = ["sshpass", "-p", ssh_pass, "ssh", "-o", "StrictHostKeyChecking=no", f"{ssh_user}@{host}"] + inner
    else:
        full = inner
    return subprocess.run(full, capture_output=True, text=True)


def wp_out(r: subprocess.CompletedProcess) -> str:
    return (r.stdout or "").strip()


def ensure_term(tax: str, slug: str, name: str, url: str, host: str | None, user: str, pwd: str) -> None:
    r = wp_cli(["term", "list", tax, f"--slug={slug}", "--field=term_id", "--format=ids"], url, host, user, pwd)
    if wp_out(r):
        return
    wp_cli(["term", "create", tax, name, f"--slug={slug}"], url, host, user, pwd)


def post_exists(slug: str, url: str, host: str | None, user: str, pwd: str) -> str | None:
    r = wp_cli(
        ["post", "list", "--post_type=gece_hayati", f"--name={slug}", "--field=ID", "--format=ids", "--post_status=any"],
        url,
        host,
        user,
        pwd,
    )
    out = wp_out(r)
    return out.split()[0] if out else None


def md_to_html(text: str) -> str:
    lines = text.splitlines()
    html: list[str] = []
    in_ul = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            html.append("</ul>")
            in_ul = False

    for raw in lines:
        line = raw.rstrip()
        if not line or line.startswith("─"):
            close_ul()
            continue
        if line.startswith("### "):
            close_ul()
            html.append(f"<h2>{_inline(line[4:])}</h2>")
            continue
        if line.startswith("**") and line.endswith("**") and line.count("**") == 2:
            close_ul()
            html.append(f"<h3>{_inline(line[2:-2])}</h3>")
            continue
        if line.startswith("- "):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{_inline(line[2:])}</li>")
            continue
        if line.startswith("  • "):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{_inline(line[4:])}</li>")
            continue
        close_ul()
        html.append(f"<p>{_inline(line)}</p>")

    close_ul()
    return "\n".join(html)


def _inline(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s


def parse_meta_from_html(html: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    m = re.search(r"Telefon:\s*([^<\n]+)", html)
    if m:
        meta["mekan_telefon"] = m.group(1).strip()
    m = re.search(r"Instagram:\s*([^<\n]+)", html)
    if m:
        meta["mekan_instagram"] = m.group(1).strip()
    m = re.search(r"Tam Adres:\s*([^<\n]+)", html)
    if m:
        meta["mekan_adres"] = m.group(1).strip()
    m = re.search(r"Koordinatlar:\s*([\d.]+)°K,\s*([\d.]+)°D", html)
    if m:
        meta["mekan_lat"] = m.group(1)
        meta["mekan_lon"] = m.group(2)
    return meta


def build_link_map(base_url: str, venues: list[dict], slug_to_id: dict[str, str]) -> dict[str, str]:
    """Placeholder metin → gerçek URL."""
    base = base_url.rstrip("/")
    links: dict[str, str] = {}

    for slot_slug, _label, _title, slot_seo in SLOTS:
        links[f"Kuşadası Gece Hayatı {slot_seo}"] = f"{base}/gece-saat/{slot_slug}/"

    for type_slug, type_label, _suffixes in TYPES:
        links[f"Kuşadası {type_label} Rehberi"] = f"{base}/gece-tur/{type_slug}/"

    mahalle_names: set[str] = set()
    for v in venues:
        mahalle_names.add(v["mahalle_name"])
        links[f"Kuşadası {v['mahalle_name']} Otel Rehberi"] = f"{base}/gece-mahalle/{v['mahalle_slug']}/"
        links[f"{v['mahalle_name']}'nin En İyi 5 Barı"] = f"{base}/gece-mahalle/{v['mahalle_slug']}/"
        links[f"{v['mahalle_name']} Plaj Rehberi"] = f"{base}/gece-mahalle/{v['mahalle_slug']}/"

    # Aynı mahalle+bar türündeki ilk başka mekan
    by_key: dict[str, list[str]] = {}
    for v in venues:
        key = f"{v['mahalle_slug']}-{v['type_slug']}"
        by_key.setdefault(key, []).append(v["slug"])

    for v in venues:
        key = f"{v['mahalle_slug']}-{v['type_slug']}"
        others = [s for s in by_key.get(key, []) if s != v["slug"]]
        if others and others[0] in slug_to_id:
            links.setdefault(f"{v['mahalle_name']} bar", f"{base}/gece-hayati/{others[0]}/")

    return links


def apply_internal_links(html: str, link_map: dict[str, str]) -> str:
    def repl(match: re.Match) -> str:
        label = match.group(1).strip()
        url = link_map.get(label)
        if not url:
            # Kısmi eşleşme
            for k, u in link_map.items():
                if k in label or label in k:
                    return f'<a href="{u}">{label}</a>'
            return label
        return f'<a href="{url}">{label}</a>'

    html = re.sub(r"\[Link:\s*([^\]]+)\]", repl, html)
    return html


def create_post(
    venue: dict,
    html: str,
    excerpt: str,
    url: str,
    host: str | None,
    user: str,
    pwd: str,
    dry_run: bool,
) -> str | None:
    slug = venue["slug"]
    title = f"{venue['name']} – Kuşadası {venue['slot_seo']} Rehberi"

    if dry_run:
        print(f"  [dry] {venue['id']:03d} {title}")
        return "0"

    existing = post_exists(slug, url, host, user, pwd)
    if existing:
        print(f"  [skip] {slug} (ID {existing})")
        return existing

    r = wp_cli(
        [
            "post",
            "create",
            "--post_type=gece_hayati",
            "--post_status=publish",
            f"--post_title={title}",
            f"--post_name={slug}",
            f"--post_excerpt={excerpt[:280]}",
            f"--post_content={html}",
            "--porcelain",
        ],
        url,
        host,
        user,
        pwd,
    )
    post_id = wp_out(r)
    if not post_id or not post_id.isdigit():
        print(f"  [ERR] {slug}: {r.stderr or r.stdout}", file=sys.stderr)
        return None

    wp_cli(
        [
            "post",
            "term",
            "set",
            post_id,
            "gece_mahalle",
            venue["mahalle_slug"],
            "gece_saat",
            venue["slot_slug"],
            "gece_tur",
            venue["type_slug"],
        ],
        url,
        host,
        user,
        pwd,
    )

    meta = parse_meta_from_html(html)
    for key, val in meta.items():
        wp_cli(["post", "meta", "update", post_id, key, val], url, host, user, pwd)

    print(f"  [ok] {slug} → ID {post_id}")
    return post_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Gece hayatı rehberlerini WordPress'e import et")
    parser.add_argument("--url", default="https://balkutusu.com", help="WP site URL")
    parser.add_argument("--host", default=None, help="SSH host (VPS)")
    parser.add_argument("--ssh-user", default="root")
    parser.add_argument("--ssh-pass", default="Fadafx35")
    parser.add_argument("--limit", type=int, default=180)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-flush", action="store_true")
    args = parser.parse_args()

    venues = build_content_map()[args.offset : args.offset + args.limit]
    if not venues:
        print("İçerik bulunamadı. Önce generate-gece-hayati-rehberi.py çalıştırın.")
        sys.exit(1)

    print(f"Import: {len(venues)} mekan → {args.url}")

    # Taxonomy terimleri
    if not args.dry_run:
        mahalle_done: set[str] = set()
        for v in venues:
            if v["mahalle_slug"] not in mahalle_done:
                ensure_term("gece_mahalle", v["mahalle_slug"], v["mahalle_name"], args.url, args.host, args.ssh_user, args.ssh_pass)
                mahalle_done.add(v["mahalle_slug"])
        for slot_slug, slot_label, _st, slot_seo in SLOTS:
            ensure_term("gece_saat", slot_slug, f"{slot_seo} ({slot_label})", args.url, args.host, args.ssh_user, args.ssh_pass)
        for type_slug, type_label, _suffixes in TYPES:
            ensure_term("gece_tur", type_slug, type_label, args.url, args.host, args.ssh_user, args.ssh_pass)

    slug_to_id: dict[str, str] = {}
    pending: list[tuple[dict, str, str]] = []

    for v in venues:
        fname = f"{v['id']:03d}-{v['slug']}.txt"
        fpath = CONTENT_DIR / fname
        if not fpath.exists():
            print(f"  [WARN] dosya yok: {fname}", file=sys.stderr)
            continue
        raw = fpath.read_text(encoding="utf-8")
        html = md_to_html(raw)
        excerpt = textwrap.shorten(
            re.sub(r"^#+\s*", "", raw.split("\n\n")[1] if "\n\n" in raw else raw, count=1).replace("\n", " "),
            width=300,
            placeholder="…",
        )
        pending.append((v, html, excerpt))

    # İlk geçiş: oluştur
    for v, html, excerpt in pending:
        post_id = create_post(v, html, excerpt, args.url, args.host, args.ssh_user, args.ssh_pass, args.dry_run)
        if post_id:
            slug_to_id[v["slug"]] = post_id

    # İkinci geçiş: iç linkleme güncelle
    link_map = build_link_map(args.url, build_content_map(), slug_to_id)
    if not args.dry_run:
        for v, html, _excerpt in pending:
            post_id = slug_to_id.get(v["slug"])
            if not post_id or post_id == "0":
                continue
            linked = apply_internal_links(html, link_map)
            if linked != html:
                wp_cli(["post", "update", post_id, f"--post_content={linked}"], args.url, args.host, args.ssh_user, args.ssh_pass)

        if not args.skip_flush:
            wp_cli(["rewrite", "flush"], args.url, args.host, args.ssh_user, args.ssh_pass)
            print("Rewrite rules flushed.")

    print(f"Tamamlandı: {len(slug_to_id)} post.")


if __name__ == "__main__":
    main()
