#!/usr/bin/env python3
"""Living docs — docs/academy altındaki markdown dosyalarından academy-index.json üretir."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACADEMY = ROOT / "docs" / "academy"
INDEX_FILE = ACADEMY / "academy-index.json"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

SECTION_ORDER = [
    ("00-baslangic", "Başlangıç", "baslangic"),
    ("01-ilk-gun", "İlk Gün", "ilk-gun"),
    ("02-firma-proje-yonetimi", "Firma & Proje Yönetimi", "firma-proje"),
    ("03-seo-geo-aeo", "SEO / GEO / AEO", "seo-geo-aeo"),
    ("04-authority", "Authority", "authority"),
    ("05-publish-pipeline", "Publish Pipeline", "publish-pipeline"),
    ("06-modul-ansiklopedisi", "Modül Ansiklopedisi", "modul-ansiklopedisi"),
    ("07-api", "API", "api"),
    ("08-deploy", "Deploy", "deploy"),
    ("09-troubleshooting", "Sorun Giderme", "troubleshooting"),
    ("10-glossary", "Sözlük", "glossary"),
    ("11-certification", "Academy Certification", "certification"),
]


def parse_fm(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    meta: dict = {}
    list_key = None
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- ") and list_key:
            meta.setdefault(list_key, []).append(line[2:].strip().strip('"'))
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip().strip('"')
        if not v:
            list_key = k
            meta[k] = []
        else:
            list_key = None
            meta[k] = v
    return meta


def main() -> None:
    sections = []
    module_count = 0
    for folder, title, slug in SECTION_ORDER:
        dir_path = ACADEMY / folder
        if not dir_path.is_dir():
            continue
        items = []
        for md in sorted(dir_path.glob("*.md")):
            if md.name.upper() == "README.MD":
                rel = f"{folder}/{md.name}"
                fm = parse_fm(md.read_text(encoding="utf-8"))
                items.append({
                    "title": fm.get("title") or title,
                    "slug": fm.get("slug") or slug,
                    "path": rel,
                    "level": fm.get("level", "Reference"),
                    "status": fm.get("status", "draft"),
                    "last_updated": fm.get("last_updated", ""),
                })
                continue
            text = md.read_text(encoding="utf-8")
            fm = parse_fm(text)
            rel = f"{folder}/{md.name}"
            item_slug = fm.get("slug") or md.stem.split("-", 1)[-1]
            items.append({
                "title": fm.get("title") or md.stem,
                "slug": item_slug,
                "path": rel,
                "level": fm.get("level", "Beginner"),
                "status": fm.get("status", "draft"),
                "last_updated": fm.get("last_updated", ""),
                "reading_time_minutes": fm.get("reading_time_minutes", ""),
                "difficulty": fm.get("difficulty", fm.get("level", "")),
            })
            if folder == "06-modul-ansiklopedisi" and md.name != "README.md":
                module_count += 1
        if items:
            sections.append({"title": title, "slug": slug, "items": items})

    index = {
        "title": "HIVE Academy",
        "version": "2.0.0",
        "last_updated": date.today().isoformat(),
        "module_encyclopedia_count": module_count,
        "sections": sections,
    }
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {sum(len(s['items']) for s in sections)} docs, index → {INDEX_FILE}")


if __name__ == "__main__":
    main()
