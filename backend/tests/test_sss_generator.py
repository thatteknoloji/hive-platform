"""SSS üretici — kelime limitleri ve HTML yapısı."""

from unittest.mock import patch

from app.moduller.sss_generator import (
    MIN_ANSWER_WORDS,
    MIN_FAQ_COUNT,
    MIN_HTML_CHARS,
    MIN_INTRO_WORDS,
    build_html,
    generate_sss_page,
)


def test_fallback_page_meets_limits():
    with patch("app.moduller.sss_generator._ollama_generate", return_value=("", False)):
        page = generate_sss_page(
            "Aydın", "Kuşadası", "Gece Hayatı", "Barlar",
            "kuşadası test sss",
        )
    stats = page["word_stats"]
    assert stats["intro_words"] >= MIN_INTRO_WORDS
    assert stats["faq_count"] >= MIN_FAQ_COUNT
    assert stats["min_answer_words"] >= MIN_ANSWER_WORDS
    assert len(page["html"]) >= MIN_HTML_CHARS
    assert "<h1>" in page["html"]
    assert "Sık Sorulan Sorular" in page["html"]
    assert "application/ld+json" in page["html"]


def test_build_html_internal_links():
    html = build_html({
        "h1": "Test Başlık",
        "intro": "Giriş metni.",
        "faqs": [{"question": "Soru?", "answer": "Cevap."}],
        "internal_links": [{"text": "İlan listesi", "url": "https://www.balkutusu.com/profil/"}],
        "schema": {"@type": "FAQPage", "mainEntity": []},
    })
    assert 'href="https://www.balkutusu.com/profil/"' in html
    assert "İlan listesi" in html
