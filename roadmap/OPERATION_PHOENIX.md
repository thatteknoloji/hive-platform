# Operation Phoenix — HIVE V1 Release

**Status:** ACTIVE  
**Mission:** First customer ready. Customer Journey first.

**Yön değişikliği (v2):** Modül odaklı sprint → **Customer Journey** odaklı sprint.  
Tam tanım: [`roadmap/CUSTOMER_JOURNEY.md`](CUSTOMER_JOURNEY.md)

---

## Success Metrics

| Metrik | Hedef | Durum |
|--------|-------|-------|
| **Customer Journey Completion Rate (CJCR)** | **100%** | Baseline — `scripts/phoenix-customer-journey-audit.py` |
| Academy Phase 1 | 100% | Done |
| Critical Bug (journey path) | 0 | Pending |
| Broken Link (journey path) | 0 | Pending |
| First Customer Ready | 100% | Pending |

~~Demo Success Rate~~ — deprecated (modül odaklı eski metrik)

---

## Customer Journey (8 adım)

```
Login → Project → Domain → SEO → Authority → Publish → Deploy → Monitoring
```

| Komut | Açıklama |
|-------|----------|
| `python3 scripts/seed-customer-journey-demo.py` | Demo proje + aktif proje |
| `python3 scripts/phoenix-customer-journey-audit.py` | CJCR raporu |

Config: `roadmap/customer-journey.json` · Rapor: `roadmap/phoenix-customer-journey-audit.json`

---

## Phase 1 — Academy

| Kontrol | Durum |
|---------|-------|
| Dashboard | Done |
| Sidebar | Done |
| Search (sidebar + ⌘K) | Done |
| Reading Progress | Done |
| Continue Learning | Done |
| Previous / Next | Done |
| Feedback | Done |
| Changelog | Done |
| Mermaid | Done |
| Markdown | Done |
| Screenshot Gallery | Done |
| Breadcrumb | Done |
| Mobile | Done |

---

## Phase 2 — Journey Modülleri

Yalnızca `customer-journey.json` içindeki modüller: published Academy doc + UI polish + demo senaryosu.

Journey dışı modüller → `roadmap/icebox.md`

---

## Phase 3 — CJCR Audit

Adım tamamlanması = tüm modül checklist %100 + data checks (demo proje, domain, aktif proje).

---

## Phase 4–7

UI Polish · QA · Journey E2E · Sales Ready — sprint sırasıyla.

---

## Release Pipeline

Idea → Development → Testing → QA → Academy → Production → Release

Eksik halka = tamamlanmış sayılmaz.

---

## HIVE Quality Score (journey modülü başına /100)

Kod · UI · UX · API · Documentation · Performance · Security · Accessibility · Production

**Eşik:** 95 (modül) · **CJCR hedefi:** 100% (adım)

---

## Documentation Policy

Kod → Doküman → Workflow → Screenshot → Academy → Release

Journey modülü Academy'de published olmadan sprint tamamlanmış sayılmaz.
