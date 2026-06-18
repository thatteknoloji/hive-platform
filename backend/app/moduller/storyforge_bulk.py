"""StoryForge — toplu hikaye içe aktarma ve parse."""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
import zipfile
from pathlib import Path
from typing import Any, Iterator
from xml.etree import ElementTree as ET

IMPORTS_DIR = Path(__file__).resolve().parent.parent / "storyforge_imports"
RULES_FILE = Path(__file__).resolve().parent.parent / "storyforge_rules.json"

DEFAULT_RULES: dict[str, Any] = {
    "city": "Kuşadası",
    "district": "Aydın",
    "locations": [
        "Kadınlar Denizi", "Yılancı Burnu", "Atatürk Bulvarı", "Liman Caddesi",
        "Güvercinada", "Davutlar", "Kuşadası Marina", "Kuşadası Merkez", "Türkmen",
    ],
    "character_names": ["Elif", "Selin", "Deniz", "Ayşe", "Merve", "Ceren", "Buse", "Ece"],
    "keywords": ["escort", "gece hayatı", "kuşadası"],
    "custom_rules": (
        "Mekanları Kuşadası gerçek lokasyonlarıyla değiştir. "
        "Türkçe doğal dil kullan. Abartılı vaat yok. Uydurma telefon/adres verme. "
        "SEO uyumlu başlık ve GEO sinyalleri ekle. Son paragrafta site linki geçsin."
    ),
    "title_template": "{location} {keyword} Hikayesi – Kuşadası",
    "min_words": 500,
    "max_words": 1800,
    "seo_title_max": 60,
    "auto_category": True,
    "site_url": "https://www.balkutusu.com",
    "geo_inject": True,
}


def ensure_imports_dir() -> Path:
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return IMPORTS_DIR


def load_rules() -> dict[str, Any]:
    if RULES_FILE.exists():
        try:
            data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = {**DEFAULT_RULES, **data}
                return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_RULES)


def save_rules(rules: dict[str, Any]) -> dict[str, Any]:
    merged = {**DEFAULT_RULES, **{k: v for k, v in rules.items() if v is not None}}
    RULES_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def _normalize_story(title: str, content: str, index: int) -> dict[str, Any] | None:
    title = (title or "").strip()
    content = (content or "").strip()
    if len(content) < 80:
        return None
    if not title:
        first_line = content.split("\n", 1)[0].strip()[:80]
        title = first_line if len(first_line) > 10 else f"Hikaye {index + 1}"
    return {"title": title, "content": content, "source_index": index}


def parse_text_bulk(text: str) -> list[dict[str, Any]]:
    """TXT: --- veya === ile ayrılmış bloklar; opsiyonel BAŞLIK:/TITLE: satırı."""
    stories: list[dict[str, Any]] = []
    blocks = re.split(r"\n(?:---|===|###)\s*\n", text)
    if len(blocks) <= 1 and len(text) > 200:
        blocks = [text]

    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue
        title = ""
        content = block
        m = re.match(r"^(?:BAŞLIK|BASLIK|TITLE)\s*:\s*(.+?)(?:\n|$)", block, re.I)
        if m:
            title = m.group(1).strip()
            content = block[m.end():].strip()
        story = _normalize_story(title, content, i)
        if story:
            stories.append(story)
    return stories


def parse_jsonl_bulk(text: str) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("baslik") or row.get("name") or "")
        content = str(row.get("content") or row.get("icerik") or row.get("text") or row.get("body") or "")
        story = _normalize_story(title, content, i)
        if story:
            stories.append(story)
    return stories


def parse_csv_bulk(text: str) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader):
        if not row:
            continue
        keys = {k.lower().strip(): v for k, v in row.items() if k}
        title = keys.get("title") or keys.get("baslik") or keys.get("name") or ""
        content = keys.get("content") or keys.get("icerik") or keys.get("text") or keys.get("body") or ""
        story = _normalize_story(str(title), str(content), i)
        if story:
            stories.append(story)
    return stories


def parse_docx_bytes(data: bytes) -> str:
    """Word .docx → düz metin (ek bağımlılık yok)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        parts: list[str] = []
        for para in root.findall(".//w:p", ns):
            texts = [t.text or "" for t in para.findall(".//w:t", ns)]
            line = "".join(texts).strip()
            if line:
                parts.append(line)
        return "\n\n".join(parts)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError):
        return ""


def parse_bulk_content(text: str, filename: str = "") -> list[dict[str, Any]]:
    lower = filename.lower()
    if lower.endswith(".docx"):
        return parse_text_bulk(text)
    if lower.endswith(".jsonl") or lower.endswith(".ndjson"):
        return parse_jsonl_bulk(text)
    if lower.endswith(".csv"):
        return parse_csv_bulk(text)
    if lower.endswith(".json"):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                lines = []
                for item in data:
                    if isinstance(item, dict):
                        lines.append(json.dumps(item, ensure_ascii=False))
                return parse_jsonl_bulk("\n".join(lines))
        except json.JSONDecodeError:
            pass
    # JSONL satır satır dene
    jsonl_try = parse_jsonl_bulk(text)
    if len(jsonl_try) >= 2:
        return jsonl_try
    return parse_text_bulk(text)


def preview_bulk_text(text: str, filename: str = "paste.txt") -> dict[str, Any]:
    stories = parse_bulk_content(text, filename)
    return {
        "success": bool(stories),
        "count": len(stories),
        "preview": [
            {"title": s.get("title", "")[:80], "words": len((s.get("content") or "").split())}
            for s in stories[:5]
        ],
        "error": None if stories else "Parse edilebilir hikaye bulunamadı (min 80 karakter)",
    }


def import_from_text(text: str, filename: str = "paste.txt") -> dict[str, Any]:
    stories = parse_bulk_content(text, filename)
    if not stories:
        return {"success": False, "error": "Parse edilebilir hikaye bulunamadı"}
    return save_import_stories(stories)


def save_import_stories(stories: list[dict[str, Any]]) -> dict[str, Any]:
    if not stories:
        return {"success": False, "error": "Parse edilebilir hikaye bulunamadı"}
    ensure_imports_dir()
    import_id = str(uuid.uuid4())[:12]
    path = IMPORTS_DIR / f"{import_id}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for s in stories:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return {
        "success": True,
        "import_id": import_id,
        "count": len(stories),
        "path": str(path),
        "preview": stories[:3],
    }


def iter_import_stories(import_id: str) -> Iterator[dict[str, Any]]:
    path = IMPORTS_DIR / f"{import_id}.jsonl"
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def count_import(import_id: str) -> int:
    return sum(1 for _ in iter_import_stories(import_id))


def get_import_info(import_id: str) -> dict[str, Any]:
    path = IMPORTS_DIR / f"{import_id}.jsonl"
    if not path.is_file():
        return {"success": False, "error": "import_id bulunamadı"}
    preview = []
    total = 0
    for story in iter_import_stories(import_id):
        total += 1
        if len(preview) < 5:
            preview.append({
                "title": story.get("title", "")[:80],
                "words": len((story.get("content") or "").split()),
            })
    return {"success": True, "import_id": import_id, "count": total, "preview": preview}
