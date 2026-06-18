"""StoryForge bulk import parse tests."""

from app.moduller.storyforge_bulk import (
    parse_bulk_content,
    save_import_stories,
    load_rules,
    save_rules,
    count_import,
)


def test_parse_text_blocks():
    text = """BAŞLIK: İlk Hikaye
Bu uzun bir hikaye metnidir ve en az seksen karakter olmalıdır ki parse edilebilsin.
Kuşadası'nda geçen bir anı anlatır.

---

TITLE: Second
Another story with enough content to pass the minimum length check for normalization.
"""
    stories = parse_bulk_content(text, "stories.txt")
    assert len(stories) == 2
    assert stories[0]["title"] == "İlk Hikaye"
    assert "uzun bir hikaye" in stories[0]["content"]


def test_parse_jsonl():
    text = (
        '{"title":"A","content":"' + "x" * 100 + '"}\n'
        '{"title":"B","content":"' + "y" * 100 + '"}\n'
    )
    stories = parse_bulk_content(text, "data.jsonl")
    assert len(stories) == 2


def test_save_and_count_import(tmp_path, monkeypatch):
    import app.moduller.storyforge_bulk as bulk_mod

    monkeypatch.setattr(bulk_mod, "IMPORTS_DIR", tmp_path)
    stories = [{"title": "T", "content": "c" * 100, "source_index": 0}]
    result = save_import_stories(stories)
    assert result["success"]
    assert count_import(result["import_id"]) == 1


def test_rules_roundtrip(tmp_path, monkeypatch):
    import app.moduller.storyforge_bulk as bulk_mod

    monkeypatch.setattr(bulk_mod, "RULES_FILE", tmp_path / "rules.json")
    merged = save_rules({"city": "İzmir", "keywords": ["test"]})
    assert merged["city"] == "İzmir"
    loaded = load_rules()
    assert loaded["city"] == "İzmir"
    assert "test" in loaded["keywords"]
