# Operation Phoenix — Phase 2

> **Superseded:** Aktif sprint metriği artık **Customer Journey Completion Rate (CJCR)**.  
> Bkz. [`CUSTOMER_JOURNEY.md`](CUSTOMER_JOURNEY.md) ve `roadmap/customer-journey.json`.

**Metrik (eski):** Demo Success Rate → **100%**  
**Yöntem:** Modül modül değil — **gerçek müşteri akışı** bitirilir.

---

## Demo Akışı (Sıra)

```
GROUP A  Foundation     → Proje seç, dashboard aç, kullanıcı göster
GROUP B  SEO Core        → Keyword, entity, quality gate, audit
GROUP C  Authority       → Factory, citation, publish, mesh
GROUP D  Publishing      → Astro, deploy, WP, GitHub
GROUP E  Monitoring      → Rank, SERP, performance, logs
```

Tam tanım: `roadmap/phoenix-demo-flow.json`

---

## Modül Checklist (16 madde)

Bir modül **tamamlandı** sayılmaz:

- [ ] Production çalışıyor
- [ ] UI tamam
- [ ] API tamam
- [ ] Error Handling
- [ ] Loading
- [ ] Toast
- [ ] Empty State
- [ ] Tooltip
- [ ] Academy dokümanı (published)
- [ ] Screenshot
- [ ] Workflow (mermaid)
- [ ] API açıklaması
- [ ] Troubleshooting
- [ ] Changelog
- [ ] Test edildi
- [ ] Demo senaryosunda kullanıldı

---

## GROUP A — Foundation (Öncelik 1)

| Modül | HIVE ID | Academy | UI | Durum |
|-------|---------|---------|-----|-------|
| Project Manager | `projects` | ilk-firma / project-nedir | ProjectsHub | In progress |
| Project Context | `active_project_context` | active-project-context | ActiveProjectContext | Published doc |
| Dashboard | `mission_control_center` | mission_control_center | MissionControlCenter | Upgrading |
| Users | `users` | users-permissions | UsersRoles | Upgrading |
| Permissions | `permissions` | users-permissions | rbac.js + panel_identity | Upgrading |

**Demo senaryosu:** Müşteri → Projects → yeni proje → aktif yap → Mission Control → Users ekle.

---

## GROUP B — SEO Core (Öncelik 2)

| Modül | HIVE ID |
|-------|---------|
| SEO | `campaign_engine` |
| Keyword | `talon` |
| Entity / Graph | `entity_geo_graph` |
| Quality Gate | `seo_quality_gate` |
| SEO Audit | `seoaudit` |

---

## GROUP C — Authority (Öncelik 3)

`authority_factory` · `citation_engine` · `publisher_hub` · `authority_mesh_engine`

---

## GROUP D — Publishing (Öncelik 4)

`astro_factory` · `astro_auto_publisher` · `wordpress` · GitHub (mesh tab)

---

## GROUP E — Monitoring (Öncelik 5)

`rank_index_watcher` · `serp_defense_engine` · `provider_control_center` · `log`

---

## Araçlar

```bash
# Demo modüllerini checklist ile tara
python3 scripts/phoenix-demo-audit.py

# Tüm 116 modül baseline (Phase 3)
python3 scripts/phoenix-module-audit.py
```

Çıktı: `roadmap/phoenix-demo-audit.json`

---

## Documentation Policy (Phase 2)

Kod → Doküman → Workflow → Screenshot → Academy → Demo → Release

Academy `published` olmadan demo akışına eklenmez.

---

## Icebox

Yeni fikirler: `roadmap/icebox.md` — sprint bitene kadar geliştirilmez.
