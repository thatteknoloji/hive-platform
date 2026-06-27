#!/usr/bin/env python3
"""HIVE Academy V1 — docs/academy içerik ve index üretici."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACADEMY = ROOT / "docs" / "academy"
MODUL_DIR = ACADEMY / "06-modul-ansiklopedisi"
sys.path.insert(0, str(ROOT / "backend"))

from app.moduller.liste import MODULLER  # noqa: E402

TODAY = "2026-06-26"


def fm(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f'{k}:')
            for item in v:
                lines.append(f'  - "{item}"')
        else:
            lines.append(f'{k}: "{v}"')
    lines.append("---")
    return "\n".join(lines)


def doc_block(title: str, sections: dict[str, str]) -> str:
    parts = [f"# {title}", ""]
    order = [
        "learn", "short", "detail", "where", "steps", "scenario",
        "visual", "mermaid", "best", "dont", "errors", "faq", "related", "next",
    ]
    labels = {
        "learn": "## Bu bölümde ne öğreneceksiniz?",
        "short": "## Kısa cevap",
        "detail": "## Detaylı açıklama",
        "where": "## HIVE içinde nerede kullanılır?",
        "steps": "## Adım adım kullanım",
        "scenario": "## Örnek senaryo",
        "visual": "## Görsel alanı",
        "mermaid": "## Akış diyagramı",
        "best": "## En iyi kullanım",
        "dont": "## Yapılmaması gerekenler",
        "errors": "## Yaygın hatalar",
        "faq": "## Sık sorulan sorular",
        "related": "## İlgili konular",
        "next": "## Sonraki konu",
    }
    for key in order:
        if key in sections:
            parts.append(labels[key])
            parts.append("")
            parts.append(sections[key])
            parts.append("")
    return "\n".join(parts)


PAGES: list[dict] = [
    {
        "path": "00-baslangic/001-hive-nedir.md",
        "meta": {
            "title": "HIVE Nedir?", "slug": "hive-nedir", "category": "Başlangıç",
            "level": "Beginner", "order": 1, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team",
            "related": ["SEO", "GEO", "AEO", "Firma Yönetimi"],
        },
        "body": doc_block("HIVE Nedir?", {
            "learn": "HIVE'in ne olduğunu, kimler için tasarlandığını ve panel + modül mimarisinin temel mantığını öğreneceksiniz.",
            "short": "**HIVE**, birden fazla web sitesi ve SEO kampanyasını tek panelden yönetmenizi sağlayan modüler bir **SEO Operating System (SEO OS)** platformudur.",
            "detail": """HIVE; keyword araştırması (Talon), içerik üretimi (QIE, Astro Factory), yayın (Publisher Hub), otorite ağı (Authority Mesh), izleme (Rank Watcher) ve komuta (Mission Control) katmanlarını bir araya getirir.

Kodda **firma** entity'si yoktur; her müşteri veya site bağlamı bir **proje (project)** olarak tanımlanır. Aktif proje seçildiğinde modüller domain ve site URL bilgisini otomatik çözer.

HIVE Panel 3.0 şu adreslerde çalışır:
- **Canlı:** https://hive.thiqos.com
- **Geliştirme:** http://localhost:4000 (panel), http://localhost:4001 (API)""",
            "where": "- Sol menü: **HIVE OS** grupları (COMMAND, SEO CORE, CONTENT, NETWORK…)\n- Üst bar: **Projects** — aktif firma/site seçimi\n- **Mission Control** — tüm modüllerin özet cockpit'i",
            "steps": """1. Panele giriş yapın.\n2. İlk projenizi oluşturun (Projects → Yeni Proje).\n3. Projeyi aktif yapın.\n4. **First Run Wizard** veya **HIVE Academy** ile öğrenme yolunu takip edin.\n5. Talon ile keyword araştırması başlatın.""",
            "scenario": "Bir dijital ajans 8 müşteri sitesini yönetiyor. Her müşteri için HIVE'da ayrı proje açılır. SEO uzmanı sabah Mission Control'dan decay alarmlarına bakar, Content Refresh ile güncelleme planlar, Publisher Hub ile yayınlar.",
            "visual": "> 📷 Screenshot placeholder: Mission Control ana ekranı — alarm kartları, kampanya durumu ve provider sağlığı.",
            "mermaid": """```mermaid
flowchart TD
    A[Kullanıcı] --> B[HIVE Panel]
    B --> C[Proje Bağlamı]
    C --> D[Modüller]
    D --> E[WordPress / Astro / Cloudflare]
    D --> F[HIVE Brain Hafıza]
```""",
            "best": "- Her operasyon öncesi doğru projeyi aktif seçin.\n- Mission Control'u günlük kontrol noktası yapın.\n- Modül çıktılarını HIVE Brain'de takip edin.",
            "dont": "- Tek projeye tüm domainleri yığmayın.\n- API key olmadan provider modüllerini canlıda zorlamayın.\n- Black Ops modüllerini eğitim amacı dışında kullanmayın.",
            "errors": "**Modül yanlış domain kullanıyor** → Aktif proje kontrol edin.\n**401 Unauthorized** → Oturum süresi dolmuş; yeniden giriş yapın.",
            "faq": "**HIVE bir CMS mi?** Hayır; CMS'lerle (WordPress) entegre olur ama kendisi içerik yönetim sistemi değildir.\n\n**Kaç modül var?** Kayıt defterinde 116+ panel modülü bulunur.",
            "related": "- [HIVE Ne Değildir?](hive-ne-degildir)\n- [HIVE Mantığı](hive-mantigi)\n- [Project Nedir?](project-nedir)",
            "next": "Sonraki konu: **HIVE Ne Değildir?**",
        }),
    },
    {
        "path": "00-baslangic/002-hive-ne-degildir.md",
        "meta": {
            "title": "HIVE Ne Değildir?", "slug": "hive-ne-degildir", "category": "Başlangıç",
            "level": "Beginner", "order": 2, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["HIVE", "CRM", "Hosting"],
        },
        "body": doc_block("HIVE Ne Değildir?", {
            "learn": "HIVE'ın sınırlarını ve yanlış beklentileri netleştireceksiniz.",
            "short": "HIVE bir CRM, muhasebe yazılımı, hosting paneli veya sıra garantisi veren sihirli bir araç **değildir**.",
            "detail": """| HIVE değildir | Gerçek |
|---------------|--------|
| CRM / ERP | Müşteri faturalama, sözleşme, muhasebe yok |
| Hosting paneli | cPanel alternatifi değil; deploy scriptleri sunar |
| Sıra garantisi | SEO araçları + otomasyon; sonuç garantisi yok |
| İlan sitesi motoru | Listing Hub ilan tutar; Place SEO otorite içeriği üretir |
| Tam otonom AI | Autonomous Agent önerir; insan onayı gerekebilir |""",
            "where": "Bu sınırlar **Production Readiness**, **Quality Gate** ve **Executive AI** özetlerinde de vurgulanır.",
            "steps": "1. Yeni modül kullanmadan önce 'ne yapmaz' bölümünü okuyun.\n2. Provider Control Center'dan API durumunu kontrol edin.\n3. Beklentiyi modül ansiklopedisiyle eşleştirin.",
            "scenario": "Kullanıcı Rank Tracker'ın otomatik içerik yazacağını sanıyor. Rank Tracker yalnızca sıra izler; içerik için QIE veya SEO Content Agent gerekir.",
            "visual": "> 📷 Screenshot placeholder: Modül detay sayfasında 'Ne yapmaz' uyarı alanı.",
            "mermaid": """```mermaid
flowchart LR
    A[Beklenti] --> B{Doğru modül?}
    B -->|Evet| C[Sonuç]
    B -->|Hayır| D[Hayal kırıklığı]
```""",
            "best": "Modülü kullanmadan önce Academy ansiklopedisinde 'Ne işe yaramaz' bölümünü okuyun.",
            "dont": "HIVE'ı tek başına tüm dijital pazarlama stack'i sanmayın.",
            "errors": "Yanlış modül seçimi en yaygın hatadır — Campaign Engine planlar, içerik üretmez.",
            "faq": "**WordPress yerine geçer mi?** Hayır; WP Manager ile WP'yi yönetirsiniz.",
            "related": "- [HIVE Nedir?](hive-nedir)\n- [Quality Gate](quality-gate-nedir)",
            "next": "Sonraki: **SEO, GEO ve AEO Nedir?**",
        }),
    },
    {
        "path": "00-baslangic/003-seo-geo-aeo-nedir.md",
        "meta": {
            "title": "SEO, GEO ve AEO Nedir?", "slug": "seo-geo-aeo-nedir", "category": "Başlangıç",
            "level": "Beginner", "order": 3, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team",
            "related": ["SEO", "GEO", "AEO", "Quality Gate"],
        },
        "body": doc_block("SEO, GEO ve AEO Nedir?", {
            "learn": "Üç kavramın farkını ve HIVE modüllerinde nasıl bir arada kullanıldığını öğreneceksiniz.",
            "short": "**SEO** klasik arama optimizasyonu, **GEO** yapay zekâ ve yerel/konumsal görünürlük, **AEO** cevap motorları ve AI Overview uyumluluğudur.",
            "detail": """**SEO (Search Engine Optimization):** Teknik sağlık, keyword, backlink, içerik yapısı. HIVE: Talon, Crawl Gap, Rank Watcher.

**GEO (Generative Engine Optimization):** ChatGPT, Perplexity, Google AI Overview gibi sistemlerde görünürlük. HIVE: Entity GEO Graph, Citation Engine, Place SEO.

**AEO (Answer Engine Optimization):** Soru-cevap formatı, FAQ, PAA, snippet uyumu. HIVE: QIE, SSS Automation, Quality Gate AEO skoru.""",
            "where": "- **SEO Quality Gate** — üç alanı birlikte skorlar\n- **QIE** — AEO içerik üretimi\n- **Entity GEO Graph** — GEO haritası",
            "steps": "1. Talon ile seed keyword seçin.\n2. QIE ile FAQ üretin.\n3. Quality Gate'den geçirin.\n4. Publisher Hub ile yayınlayın.\n5. Citation Engine ile AI görünürlüğü ölçün.",
            "scenario": "Kuşadası gece hayatı sitesi: SEO için pillar sayfalar, GEO için mekan entity'leri, AEO için 'Kuşadası'da gece nereye gidilir?' FAQ blokları.",
            "visual": "> 📷 Screenshot placeholder: Quality Gate diagnostik ekranı — SEO/GEO/AEO skorları.",
            "mermaid": """```mermaid
flowchart TD
    SEO[SEO: Sıra ve teknik] --> QG[Quality Gate]
    GEO[GEO: Entity ve konum] --> QG
    AEO[AEO: FAQ ve cevap] --> QG
    QG --> PUB[Publisher Hub]
```""",
            "best": "Her içerik parçasını üç perspektiften kontrol edin.",
            "dont": "Yalnızca keyword doldurup GEO/AEO alanlarını boş bırakmayın.",
            "errors": "FAQ'sız uzun makaleler AEO skorunu düşürür.",
            "faq": "**GEO ile Local SEO aynı mı?** Yakın ama GEO daha geniş — AI ve generative arama dahil.",
            "related": "- [Quality Gate](quality-gate-nedir)\n- [Entity SEO](entity-seo) — bölüm 03",
            "next": "Sonraki: **HIVE Mantığı**",
        }),
    },
    {
        "path": "00-baslangic/004-hive-mantigi.md",
        "meta": {
            "title": "HIVE Mantığı", "slug": "hive-mantigi", "category": "Başlangıç",
            "level": "Beginner", "order": 4, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Proje", "Mission Control", "Brain"],
        },
        "body": doc_block("HIVE Mantığı", {
            "learn": "Proje merkezli çalışma, modül orkestrasyonu ve hafıza katmanını anlayacaksınız.",
            "short": "HIVE **proje seç → modül çalıştır → kalite kontrol → yayın → izle → öğren** döngüsüyle çalışır.",
            "detail": """1. **Bağlam:** Aktif proje domain ve sektör bilgisini taşır.\n2. **Keşif:** Talon, Opportunity, Crawl Gap veri üretir.\n3. **Plan:** Campaign Engine, Executive AI önceliklendirir.\n4. **Üretim:** QIE, Astro, StoryForge içerik oluşturur.\n5. **Kalite:** SEO Quality Gate engelleyici olabilir.\n6. **Yayın:** Publisher Hub, WP Manager, Cloudflare deploy.\n7. **Hafıza:** HIVE Brain olayları saklar.\n8. **Komuta:** Mission Control özeti sunar.""",
            "where": "Mission Control, HIVE Brain, Action Orchestrator bu döngünün üst katmanıdır.",
            "steps": "1. Proje oluştur ve aktif yap.\n2. First Run Wizard'ı tamamla.\n3. Günlük Mission Control kontrolü.\n4. Modül çıktılarını Brain'de incele.",
            "scenario": "Decay alarmı → Content Refresh → Quality Gate → Publish → Rank Watcher doğrulama.",
            "visual": "> 📷 Screenshot placeholder: HIVE Brain timeline görünümü.",
            "mermaid": """```mermaid
flowchart LR
    P[Proje] --> K[Keşif]
    K --> U[Üretim]
    U --> G[Quality Gate]
    G --> Y[Yayın]
    Y --> I[İzleme]
    I --> B[Brain]
    B --> P
```""",
            "best": "Kısa döngülerle ilerleyin; büyük patlama yerine sürekli iyileştirme.",
            "dont": "Quality Gate'i atlayarak toplu publish yapmayın.",
            "errors": "Aktif proje olmadan modül çalıştırmak yanlış domain'e işlem riski taşır.",
            "faq": "**Modüller birbirini otomatik tetikler mi?** Bazı zincirler var (SSS Automation); çoğu manuel veya Action Orchestrator ile.",
            "related": "- [Active Project Context](active-project-context)\n- [Mission Control](hive-nedir)",
            "next": "Sonraki bölüm: **İlk Gün** — İlk Giriş",
        }),
    },
    {
        "path": "01-ilk-gun/001-ilk-giris.md",
        "meta": {
            "title": "İlk Giriş", "slug": "ilk-giris", "category": "İlk Gün",
            "level": "Beginner", "order": 1, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Giriş", "Auth", "Panel"],
        },
        "body": doc_block("İlk Giriş", {
            "learn": "HIVE paneline nasıl giriş yapılacağını ve oturum güvenliğini öğreneceksiniz.",
            "short": "https://hive.thiqos.com adresine gidin, admin e-posta ve şifrenizle **Login** ekranından giriş yapın.",
            "detail": """Kimlik doğrulama JWT tabanlıdır. Başarılı girişte tarayıcı token saklar ve API isteklerine `Authorization: Bearer` eklenir.

Geliştirme ortamında auth yapılandırılmamışsa API key modu devreye girebilir; production'da mutlaka `HIVE_ADMIN_EMAIL` ve `HIVE_ADMIN_PASSWORD_HASH` tanımlı olmalıdır.""",
            "where": "Login sayfası: panel kökü `/` — oturum yoksa yönlendirilir.",
            "steps": "1. Tarayıcıda panel URL'sini açın.\n2. E-posta ve şifreyi girin.\n3. **Giriş** butonuna tıklayın.\n4. Dashboard veya son kaldığınız sayfa açılır.\n5. Sağ üstten kullanıcı menüsünden şifre değiştirin (ilk girişte önerilir).",
            "scenario": "Yeni SEO uzmanı ilk gün: admin hesabıyla giriş → Users & Roles'da kendi viewer/editor hesabı istenir → First Run Wizard başlatılır.",
            "visual": "> 📷 Screenshot placeholder: HIVE Login ekranı.",
            "mermaid": """```mermaid
flowchart TD
    A[Login formu] --> B{Kimlik doğru?}
    B -->|Evet| C[JWT token]
    C --> D[Panel]
    B -->|Hayır| E[Hata mesajı]
```""",
            "best": "Güçlü şifre kullanın; paylaşımlı admin hesabından kaçının.",
            "dont": "Şifreyi chat veya e-postada paylaşmayın.",
            "errors": "**401 Invalid** — yanlış şifre veya süresi dolmuş oturum.",
            "faq": "**API key ile panel?** Otomasyon içindir; günlük kullanımda JWT tercih edin.",
            "related": "- [Paneli Tanıyalım](paneli-taniyalim)\n- [Kullanıcı ve Roller](kullanici-ve-roller)",
            "next": "Sonraki: **Paneli Tanıyalım**",
        }),
    },
    {
        "path": "01-ilk-gun/002-paneli-taniyalim.md",
        "meta": {
            "title": "Paneli Tanıyalım", "slug": "paneli-taniyalim", "category": "İlk Gün",
            "level": "Beginner", "order": 2, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Sidebar", "Navigation", "Projects"],
        },
        "body": doc_block("Paneli Tanıyalım", {
            "learn": "Sidebar, üst bar, command palette ve sayfa yapısını tanıyacaksınız.",
            "short": "Sol tarafta **HIVE OS** menüsü, üstte **aktif proje seçici**, ortada modül sayfası, `Cmd+K` ile command palette bulunur.",
            "detail": """**Ana bölgeler:**
- **HiveOsSidebar:** COMMAND, SEO CORE, CONTENT, NETWORK, WORKERS, LEARN, TOOLS
- **Üst bar:** Proje seçici, kullanıcı, palette kısayolu
- **İçerik alanı:** Seçilen modülün React sayfası
- **Klasik modül listesi:** Tüm 116 modüle erişim (gruplu)

Deep link örneği: `/mission-control`, `/talon`, `/academy`""",
            "where": "Navigasyon: `frontend/src/config/hiveOsNav.js` ve `hiveOsRoutes.js`",
            "steps": "1. Sidebar'da Mission Control'a tıklayın.\n2. `Cmd+K` / `Ctrl+K` ile palette açın — 'Talon' arayın.\n3. Projects menüsünden proje listesine gidin.\n4. LEARN grubundan HIVE Academy'yi açın.",
            "scenario": "Operatör sabah palette'ten 'Rank Watcher' yazar, doğrudan modüle gider.",
            "visual": "> 📷 Screenshot placeholder: HIVE OS sidebar ve üst proje seçici.",
            "mermaid": """```mermaid
flowchart TD
    SB[Sidebar] --> PG[Sayfa]
    UB[Üst Bar Proje] --> CTX[Aktif Bağlam]
    CTX --> PG
    CP[Command Palette] --> PG
```""",
            "best": "Sık kullanılan modülleri palette'e alışkanlık yapın.",
            "dont": "Proje seçmeden domain gerektiren modül çalıştırmayın.",
            "errors": "Sayfa boş — yetki yoksa RBAC menüyü gizler; admin'e başvurun.",
            "faq": "**Eski modül listesi nerede?** Klasik gruplu sidebar hâlâ mevcuttur.",
            "related": "- [İlk Firma Nasıl Eklenir](ilk-firma-nasil-eklenir)\n- [Active Project Context](active-project-context)",
            "next": "Sonraki: **İlk Firma Nasıl Eklenir?**",
        }),
    },
    {
        "path": "01-ilk-gun/003-ilk-firma-nasil-eklenir.md",
        "meta": {
            "title": "İlk Firma Nasıl Eklenir?", "slug": "ilk-firma-nasil-eklenir", "category": "İlk Gün",
            "level": "Beginner", "order": 3, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Proje", "Firma", "Wizard"],
        },
        "body": doc_block("İlk Firma Nasıl Eklenir?", {
            "learn": "HIVE'da firma = proje mantığını ve ilk proje oluşturma adımlarını öğreneceksiniz.",
            "short": "**Projects → Yeni Proje** ile ad, sektör ve kısa iş tanımı girerek firmanızı (projeyi) oluşturun.",
            "detail": """HIVE'da her müşteri veya marka bir **proje** kaydıdır. Proje oluşturulunca:
- `project_engine_state.json` güncellenir
- Sektör paketine göre sayfa iskeleti üretilir
- SEO/GEO skorları hesaplanır
- Durum `draft` olarak başlar""",
            "where": "- Menü: **Projects** (`/projects`)\n- Sihirbaz: `/projects/new`\n- API: `POST /api/v3/projects`",
            "steps": """1. Projects → **Yeni Proje**.\n2. **Proje adı:** örn. Balkutusu\n3. **Sektör:** nightlife, restaurant vb. seçin\n4. **Domain:** balkutusu.com (opsiyonel ama önerilir)\n5. **Business brief:** 2-3 cümle iş tanımı\n6. **Deploy mode:** hive_cloud (varsayılan)\n7. Oluştur → detay sayfasında içeriği düzenleyin\n8. Üst bardan **aktif proje** yapın""",
            "scenario": "Ajans yeni müşteri aldı: 5 dakikada proje açtı, aktif yaptı, Talon'da domain otomatik geldi.",
            "visual": "> 📷 Screenshot placeholder: Project Wizard formu.",
            "mermaid": """```mermaid
flowchart TD
    A[Project Wizard] --> B[site_seed iskelet]
    B --> C[project_engine_state]
    C --> D[Aktif proje seç]
```""",
            "best": "Anlamlı proje adı ve dolu business brief kullanın — LLM modülleri bunu okur.",
            "dont": "Test projelerini production domain ile karıştırmayın.",
            "errors": "**sector gerekli** — sektör seçilmeden kayıt olmaz.",
            "faq": "**Firma ve proje farkı?** Kodda fark yok; proje = firma bağlamı.",
            "related": "- [Project Nedir?](project-nedir)\n- [İlk Domain Nasıl Eklenir](ilk-domain-nasil-eklenir)",
            "next": "Sonraki: **İlk Domain Nasıl Eklenir?**",
        }),
    },
    {
        "path": "01-ilk-gun/004-ilk-domain-nasil-eklenir.md",
        "meta": {
            "title": "İlk Domain Nasıl Eklenir?", "slug": "ilk-domain-nasil-eklenir", "category": "İlk Gün",
            "level": "Beginner", "order": 4, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Domain", "DNS", "Proje"],
        },
        "body": doc_block("İlk Domain Nasıl Eklenir?", {
            "learn": "Projeye domain bağlama, DNS ve HIVE modüllerinin domain çözümlemesini öğreneceksiniz.",
            "short": "Domain'i proje oluştururken veya proje detayından ekleyin; DNS'i sunucuya yönlendirin; **bind-domain** ile HIVE'a bağlayın.",
            "detail": """Domain iki katmanda çalışır:
1. **Proje kaydı:** `domain` alanı — modüller bunu okur
2. **Altyapı:** DNS A/CNAME → VPS veya Cloudflare → nginx / CF Pages

WordPress multisite için **Domain Manager** ayrıca domain CRUD yapar.""",
            "where": "- Proje detay → Domain alanı\n- `POST /api/v3/projects/{id}/bind-domain`\n- Domain Manager modülü",
            "steps": """1. Proje detayda domain yazın (örn. `orneksite.com`).\n2. Kayıt firmasında DNS: A kaydı → sunucu IP veya CF proxy.\n3. SSL: certbot veya Cloudflare.\n4. Publish sonrası bind-domain API çağrısı.\n5. Indexing Fix ile permalink/GSC kontrolü.""",
            "scenario": "Yeni Astro sitesi: publish → hive_cloud `/sites/slug` → nginx server_name bağlama → IndexNow.",
            "visual": "> 📷 Screenshot placeholder: Proje detay domain alanı ve DNS talimatları.",
            "mermaid": """```mermaid
flowchart TD
    D[Domain DNS] --> S[Sunucu/CF]
    P[Proje domain alanı] --> M[Modüller]
    S --> LIVE[Canlı site]
```""",
            "best": "www ve non-www tutarlılığı için bind-domain'de include_www kullanın.",
            "dont": "DNS yayılımını beklemeden publish sanmayın.",
            "errors": "Modül yanlış siteye gidiyor — aktif proje domain'i kontrol edin.",
            "faq": "**Alt domain?** Subdomain Manager ile yönetilir.",
            "related": "- [Domain Yönetimi](domain-yonetimi)\n- [İlk Publish](ilk-publish)",
            "next": "Sonraki: **İlk SEO Analizi**",
        }),
    },
    {
        "path": "01-ilk-gun/005-ilk-seo-analizi.md",
        "meta": {
            "title": "İlk SEO Analizi", "slug": "ilk-seo-analizi", "category": "İlk Gün",
            "level": "Beginner", "order": 5, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Talon", "Crawl Gap", "SEO Audit"],
        },
        "body": doc_block("İlk SEO Analizi", {
            "learn": "İlk gün yapılacak minimum SEO analiz paketini öğreneceksiniz.",
            "short": "Sıra: **Talon** keyword → **Crawl Gap** veya **SEO Audit** → **Rank Watcher** kurulumu.",
            "detail": """İlk gün hedefi mükemmel strateji değil, **baseline** oluşturmaktır:
- Hangi keyword'lere odaklanılacak?
- Sitede hangi sayfalar var / eksik?
- Teknik sorun var mı?
- Mevcut sıralama nedir?""",
            "where": "- Talon: `/talon`\n- Crawl Gap: `/crawl-gap`\n- SEO Audit: klasik modül\n- Rank Watcher: `/rank-watcher`",
            "steps": "1. Aktif projeyi seç.\n2. Talon'da seed keyword gir → Full Research.\n3. Crawl Gap ile site URL tara.\n4. SEO Audit çalıştır.\n5. Rank Watcher'a 5-10 keyword ekle.",
            "scenario": "Yeni site: Talon 'kuşadası escort' yerine 'kuşadası gece hayatı' önerdi; crawl 12 sayfa, 8 gap buldu.",
            "visual": "> 📷 Screenshot placeholder: Talon Full Research sonuç ekranı.",
            "mermaid": """```mermaid
flowchart LR
    T[Talon] --> C[Crawl Gap]
    C --> A[SEO Audit]
    A --> R[Rank Watcher]
```""",
            "best": "İlk analizi Brain'e not düşecek şekilde modülleri sırayla çalıştırın.",
            "dont": "Tek modül çıktısıyla tüm stratejiyi kilitlemeyin.",
            "errors": "Provider key eksik — API Settings'ten Tavily/SearXNG yapılandırın.",
            "faq": "**DataForSEO şart mı?** Hayır; ücretsiz provider'lar Talon V2'de mevcut.",
            "related": "- [SEO Mantığı](seo-mantigi)\n- [Campaign Engine](hive-mantigi)",
            "next": "Sonraki: **İlk Publish**",
        }),
    },
    {
        "path": "01-ilk-gun/006-ilk-publish.md",
        "meta": {
            "title": "İlk Publish", "slug": "ilk-publish", "category": "İlk Gün",
            "level": "Beginner", "order": 6, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Publish", "Quality Gate", "WordPress"],
        },
        "body": doc_block("İlk Publish", {
            "learn": "İlk içeriği veya siteyi canlıya alma adımlarını öğreneceksiniz.",
            "short": "İçerik üret → **Quality Gate** → **Publisher Hub** veya proje **Publish pipeline** → **IndexNow**.",
            "detail": """İki yayın yolu:
**A) V3 Astro proje:** export → build → publish → bind-domain
**B) WordPress içerik:** SEO Content Agent / QIE → Publisher Hub → WP REST

Her iki yolda da Quality Gate fail ise Auto Publisher deploy engeller.""",
            "where": "- Proje detay: Publish butonları\n- Publisher Hub: `/publisher-hub`\n- Astro Auto Publisher: `/astro-auto-publisher`",
            "steps": "1. En az bir sayfa/içerik hazırla.\n2. Diagnostics (Quality Gate) çalıştır.\n3. Publisher Hub kuyruğuna ekle veya proje Publish.\n4. IndexNow bildir.\n5. Rank Watcher'da indeks/sıra izle.",
            "scenario": "İlk FAQ sayfası QIE'den üretildi, gate geçti, WP'ye yayınlandı, IndexNow 202 döndü.",
            "visual": "> 📷 Screenshot placeholder: Publisher Hub kuyruk ekranı.",
            "mermaid": """```mermaid
flowchart TD
    I[İçerik] --> Q[Quality Gate]
    Q -->|OK| P[Publish]
    P --> N[IndexNow]
    N --> W[Rank Watcher]
```""",
            "best": "İlk publish küçük olsun — tek sayfa doğrulama.",
            "dont": "Gate uyarılarını yok saymayın.",
            "errors": "Build fail — Astro loglarını proje detaydan inceleyin.",
            "faq": "**Cloudflare mi WP mi?** deploy_mode ve içerik tipine göre değişir.",
            "related": "- [Publish Pipeline](publish-pipeline-nedir)\n- [Publisher Hub](publisher-hub-nedir)",
            "next": "Bölüm 02: **Project Nedir?**",
        }),
    },
    {
        "path": "02-firma-proje-yonetimi/001-project-nedir.md",
        "meta": {
            "title": "Project Nedir?", "slug": "project-nedir", "category": "Firma & Proje",
            "level": "Intermediate", "order": 1, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Proje", "V3", "project_engine"],
        },
        "body": doc_block("Project Nedir?", {
            "learn": "V3 proje modelinin alanlarını, durumlarını ve yaşam döngüsünü öğreneceksiniz.",
            "short": "**Project**, HIVE'da bir site/kampanya bağlamını taşıyan kalıcı kayıttır — domain, sektör, sayfalar, skorlar ve deploy modu içerir.",
            "detail": """**Durumlar:** draft, building, active, paused, error

**Temel alanlar:** id, name, sector, domain, business_brief, design, pages, theme, navigation, deploy_mode, seo_score, geo_score

**Motor:** `project_engine.py` — state: `project_engine_state.json`""",
            "where": "Projects UI, `/api/v3/projects/*`",
            "steps": "1. Liste: GET /api/v3/projects\n2. Detay: GET /api/v3/projects/{id}\n3. Güncelle: PATCH\n4. Sil: DELETE (dikkatli)",
            "scenario": "8 aktif proje; her birinin farklı sector pack'i ve Astro export'u var.",
            "visual": "> 📷 Screenshot placeholder: Projects listesi kart görünümü.",
            "mermaid": """```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> building
    building --> active
    active --> paused
    building --> error
```""",
            "best": "Proje metadata'sını güncel tutun — Executive AI bunu okur.",
            "dont": "Production projeyi test build ile silmeyin.",
            "errors": "not_found — yanlış project id veya yetki.",
            "faq": "**Legacy /api/projects?** Eski API; V3 tercih edin.",
            "related": "- [Active Project Context](active-project-context)\n- [İlk Firma Nasıl Eklenir](ilk-firma-nasil-eklenir)",
            "next": "Sonraki: **Active Project Context**",
        }),
    },
    {
        "path": "02-firma-proje-yonetimi/002-active-project-context.md",
        "meta": {
            "title": "Active Project Context Nedir?", "slug": "active-project-context", "category": "Firma & Proje",
            "level": "Intermediate", "order": 2, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Proje", "Domain", "Context"],
        },
        "body": doc_block("Active Project Context Nedir?", {
            "learn": "Aktif proje mekanizmasının modüllere domain nasıl ilettiğini öğreneceksiniz.",
            "short": "Üst barda seçilen proje **active_project_id** olarak saklanır; modüller `project_context.resolve_domain()` ile domain alır.",
            "detail": """**Kaynak:** `panel_identity_state.json` → `active_project_id`

**Kod:** `project_context.py` — get/set active, resolve_domain, resolve_site_url

**Frontend:** `ActiveProjectContext.js`, `useProjectSiteField.js`

Proje değişince `hive-active-project-changed` event'i tetiklenir.""",
            "where": "Üst bar proje dropdown; POST `/api/v3/projects/{id}/set-active`",
            "steps": "1. Proje listesinden seç.\n2. Sayfayı yenilemeden modül formları güncellenir.\n3. `/api/auth/me` active_project_id döner.",
            "scenario": "Kullanıcı A projesindeyken Rank Tracker B domain'ine bakmış — aktif proje yanlışlığı klasik hatadır.",
            "visual": "> 📷 Screenshot placeholder: Üst bar aktif proje seçici açık.",
            "mermaid": """```mermaid
flowchart TD
    UI[Üst bar seçim] --> PI[panel_identity_state]
    PI --> PC[project_context]
    PC --> M1[Talon]
    PC --> M2[Rank Watcher]
    PC --> M3[Publisher Hub]
```""",
            "best": "Modül çalıştırmadan önce üst barda doğru proje adını doğrulayın.",
            "dont": "Her modülde manuel domain yazıp aktif projeyi bypass etmeyin.",
            "errors": "Boş domain — projede domain alanı doldurulmamış.",
            "faq": "**Çoklu sekme?** Her sekme aynı active_project_id paylaşır (local state).",
            "related": "- [Domain Yönetimi](domain-yonetimi)\n- [Project Nedir?](project-nedir)",
            "next": "Bölüm 03: **Quality Gate**",
        }),
    },
    {
        "path": "03-seo-geo-aeo/005-quality-gate.md",
        "meta": {
            "title": "Quality Gate Nedir?", "slug": "quality-gate-nedir", "category": "SEO / GEO / AEO",
            "level": "Intermediate", "order": 5, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["SEO", "GEO", "AEO", "Diagnostics"],
        },
        "body": doc_block("Quality Gate Nedir?", {
            "learn": "SEO/GEO/AEO kalite kapısının nasıl çalıştığını ve publish engelini öğreneceksiniz.",
            "short": "**Quality Gate**, içeriğin SEO, GEO, AEO ve entity standartlarına uygunluğunu skorlar; fail durumda Astro Auto Publisher deploy'u **engeller**.",
            "detail": """Modül: `seo_quality_gate.py`

Kontroller: başlık yapısı, FAQ varlığı, entity coverage, AI Overview uyumu, spam sinyalleri.

Route: `/diagnostics` — HIVE OS TOOLS altında **Diagnostics**""",
            "where": "Publisher Hub ve Astro Auto Publisher bu gate çıktısını okur.",
            "steps": "1. İçerik üret.\n2. Diagnostics'te çalıştır.\n3. Fail maddeleri düzelt.\n4. Tekrar test.\n5. Publish.",
            "scenario": "FAQ eksik makale gate'de kaldı; QIE ile 5 soru eklendi, geçti.",
            "visual": "> 📷 Screenshot placeholder: Quality Gate skor kartları.",
            "mermaid": """```mermaid
flowchart TD
    C[İçerik] --> G{Quality Gate}
    G -->|Pass| P[Publish]
    G -->|Fail| F[Düzeltme]
    F --> C
```""",
            "best": "Gate'i publish öncesi zorunlu checklist yapın.",
            "dont": "Skoru manuel bypass etmeye çalışmayın.",
            "errors": "Sürekli fail — business_brief ve sector pack uyumsuz olabilir.",
            "faq": "**Sadece Astro mu?** WP içerikleri için de kullanılır.",
            "related": "- [SEO GEO AEO](seo-geo-aeo-nedir)\n- [Publisher Hub](publisher-hub-nedir)",
            "next": "Bölüm 04: **Authority Factory**",
        }),
    },
    {
        "path": "04-authority/002-authority-factory.md",
        "meta": {
            "title": "Authority Factory Nedir?", "slug": "authority-factory-nedir", "category": "Authority",
            "level": "Advanced", "order": 2, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Authority", "Mesh", "GitHub Pages"],
        },
        "body": doc_block("Authority Factory Nedir?", {
            "learn": "Authority Mesh planlarını toplu üretim batch'ine çeviren fabrika katmanını öğreneceksiniz.",
            "short": "**Authority Factory**, Mesh Engine'in ürettiği otorite planını GitHub Pages, Google Sites ve diğer worker'lara dağıtılabilir görevlere böler.",
            "detail": """Dosya: `authority_factory.py`

Mesh planı → batch job → github_pages_worker / google_sites_worker

Route: `/authority-factory`""",
            "where": "NETWORK grubu; Authority Mesh ile birlikte kullanılır.",
            "steps": "1. Authority Mesh'te ağ planı oluştur.\n2. Factory'de batch başlat.\n3. Worker durumunu izle.\n4. Publisher Hub ile senkron.",
            "scenario": "10 destek domaini için GitHub Pages microsite batch'i 45 dakikada tamamlandı.",
            "visual": "> 📷 Screenshot placeholder: Authority Factory batch kuyruğu.",
            "mermaid": """```mermaid
flowchart TD
    M[Authority Mesh Plan] --> F[Authority Factory]
    F --> G[GitHub Pages Worker]
    F --> S[Google Sites Worker]
    G --> P[Publisher Hub]
```""",
            "best": "Küçük batch ile worker credentials doğrula.",
            "dont": "API quota olmadan yüzlerce site açmayın.",
            "errors": "Worker fail — Provider Control Center'dan token kontrolü.",
            "faq": "**Mesh'ten farkı?** Mesh planlar; Factory üretir.",
            "related": "- [Authority Nedir](authority-nedir)\n- [Publisher Hub](publisher-hub-nedir)",
            "next": "Sonraki: **Publisher Hub**",
        }),
    },
    {
        "path": "04-authority/004-publisher-hub.md",
        "meta": {
            "title": "Publisher Hub Nedir?", "slug": "publisher-hub-nedir", "category": "Authority",
            "level": "Intermediate", "order": 4, "status": "published", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Publish", "WordPress", "Tumblr"],
        },
        "body": doc_block("Publisher Hub Nedir?", {
            "learn": "Çok kanallı merkezi yayın kuyruğunu öğreneceksiniz.",
            "short": "**Publisher Hub**, WordPress, Ghost, Dev.to, Tumblr, Medium ve daha fazlasına tek kuyruktan yayın yönetir.",
            "detail": """Modül: `publisher_hub.py` — state: `publisher_hub_state.json`

Quality Gate entegrasyonu vardır. Başarısız içerik kuyruğa alınmayabilir.

Route: `/publisher-hub`""",
            "where": "CONTENT grubu; içerik modüllerinin çıkış noktası.",
            "steps": "1. İçerik kaynağı seç (QIE, Astro, manuel).\n2. Hedef kanal ekle.\n3. Kuyruğu gözden geçir.\n4. Publish / schedule.\n5. Brain'de olayı kontrol et.",
            "scenario": "Tek makale WP + Tumblr + Dev.to'ya sırayla gitti; Rank Watcher 48 saat sonra sıra değişimi gördü.",
            "visual": "> 📷 Screenshot placeholder: Publisher Hub kanal listesi ve kuyruk.",
            "mermaid": """```mermaid
flowchart LR
    QIE[QIE] --> PH[Publisher Hub]
    AST[Astro] --> PH
    PH --> WP[WordPress]
    PH --> TB[Tumblr]
    PH --> DT[Dev.to]
```""",
            "best": "Kanal başına rate limit ve API key doğrula.",
            "dont": "Aynı içeriği spam hızında tüm kanallara basmayın.",
            "errors": "WP 401 — wordpress_api bağlantısı kopuk.",
            "faq": "**Ghost destekleniyor mu?** Evet; API key gerekir.",
            "related": "- [İlk Publish](ilk-publish)\n- [Quality Gate](quality-gate-nedir)",
            "next": "Modül ansiklopedisine geçin veya Publish Pipeline bölümünü okuyun.",
        }),
    },
]


def write_page(item: dict) -> None:
    path = ACADEMY / item["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    content = fm(item["meta"]) + "\n\n" + item["body"]
    path.write_text(content, encoding="utf-8")


def module_doc(mod: dict) -> str:
    mid = mod["id"]
    meta = {
        "title": mod["ad"],
        "slug": mid,
        "category": "Modül Ansiklopedisi",
        "level": "Reference",
        "order": 0,
        "status": "auto-draft",
        "version": "1.0.0",
        "last_updated": TODAY,
        "owner": "HIVE Team",
        "related": [mod.get("grup", "").replace("📈 ", "").replace("🔍 ", "")[:20]],
    }
    body = doc_block(mod["ad"], {
        "learn": f"**{mod['ad']}** modülünün HIVE içindeki rolünü özet düzeyde öğreneceksiniz.",
        "short": mod.get("aciklama", ""),
        "detail": f"**Modül ID:** `{mid}`\n\n**Grup:** {mod.get('grup', '')}\n\n**API endpoint:** `{mod.get('endpoint', '/api/' + mid)}'`\n\n<!-- AI_UPDATE_SLOT: module_{mid}_detail -->",
        "where": f"Panel: `{mod.get('endpoint', '')}` veya klasik modül listesinden **{mod['ad']}**.",
        "steps": "1. Aktif projeyi seçin.\n2. Modül sayfasını açın.\n3. Gerekli alanları doldurun.\n4. Çalıştır ve sonucu Brain'de kontrol edin.\n\n<!-- TODO: modüle özel adımlar -->",
        "scenario": "<!-- TODO: örnek senaryo -->",
        "visual": f"> 📷 Screenshot placeholder: {mod['ad']} modül ekranı.",
        "mermaid": """```mermaid
flowchart TD
    A[Aktif Proje] --> B[Modül]
    B --> C[Sonuç / Log]
```""",
        "best": "<!-- TODO: en iyi kullanım -->",
        "dont": "<!-- TODO: yapılmaması gerekenler -->",
        "errors": "<!-- TODO: yaygın hatalar -->",
        "faq": f"**Bu modül içerik üretir mi?** Ansiklopedi taslağı — detay için Mission Control ve modül health endpoint'ini kontrol edin.\n\n<!-- EKSİK_BİLGİ: {mid} derin dokümantasyon -->",
        "related": f"- Grup: {mod.get('grup', '')}\n- [Modül Ansiklopedisi README](../06-modul-ansiklopedisi/README.md)",
        "next": "İlgili modül gruplarına göre Campaign Engine veya Mission Control'a bakın.",
    })
    return fm(meta) + "\n\n" + body


def build_index(module_count: int) -> dict:
    sections = [
        {"title": "Başlangıç", "slug": "baslangic", "items": []},
        {"title": "İlk Gün", "slug": "ilk-gun", "items": []},
        {"title": "Firma & Proje Yönetimi", "slug": "firma-proje", "items": []},
        {"title": "SEO / GEO / AEO", "slug": "seo-geo-aeo", "items": []},
        {"title": "Authority", "slug": "authority", "items": []},
        {"title": "Publish Pipeline", "slug": "publish-pipeline", "items": []},
        {"title": "Modül Ansiklopedisi", "slug": "modul-ansiklopedisi", "items": []},
        {"title": "API", "slug": "api", "items": []},
        {"title": "Deploy", "slug": "deploy", "items": []},
        {"title": "Troubleshooting", "slug": "troubleshooting", "items": []},
        {"title": "Sözlük", "slug": "glossary", "items": []},
    ]
    sec_map = {s["slug"]: s for s in sections}

    for p in PAGES:
        m = p["meta"]
        cat = m.get("category", "")
        if cat == "Başlangıç":
            sec = sec_map["baslangic"]
        elif cat == "İlk Gün":
            sec = sec_map["ilk-gun"]
        elif cat == "Firma & Proje":
            sec = sec_map["firma-proje"]
        elif cat == "SEO / GEO / AEO":
            sec = sec_map["seo-geo-aeo"]
        elif cat == "Authority":
            sec = sec_map["authority"]
        else:
            sec = sec_map["baslangic"]
        sec["items"].append({
            "title": m["title"],
            "slug": m["slug"],
            "path": p["path"],
            "level": m.get("level", "Beginner"),
            "status": m.get("status", "draft"),
        })

    for mod in MODULLER:
        mid = mod["id"]
        sec_map["modul-ansiklopedisi"]["items"].append({
            "title": mod["ad"],
            "slug": mid,
            "path": f"06-modul-ansiklopedisi/{mid}.md",
            "level": "Reference",
            "status": "auto-draft",
        })

    for slug, path, title in [
        ("api-readme", "07-api/README.md", "API Referansı"),
        ("deploy-readme", "08-deploy/README.md", "Deploy Rehberi"),
        ("troubleshooting-readme", "09-troubleshooting/README.md", "Sorun Giderme"),
        ("glossary-readme", "10-glossary/README.md", "Sözlük"),
        ("modul-ansiklopedisi-readme", "06-modul-ansiklopedisi/README.md", "Modül Ansiklopedisi"),
    ]:
        key = slug.split("-")[0] if slug != "modul-ansiklopedisi-readme" else "modul-ansiklopedisi"
        if slug == "modul-ansiklopedisi-readme":
            sec_map["modul-ansiklopedisi"]["items"].insert(0, {
                "title": title, "slug": "modul-ansiklopedisi", "path": path,
                "level": "Reference", "status": "published",
            })
        elif key == "api":
            sec_map["api"]["items"].append({"title": title, "slug": slug, "path": path, "level": "Reference", "status": "draft"})
        elif key == "deploy":
            sec_map["deploy"]["items"].append({"title": title, "slug": slug, "path": path, "level": "Reference", "status": "draft"})
        elif key == "troubleshooting":
            sec_map["troubleshooting"]["items"].append({"title": title, "slug": slug, "path": path, "level": "Reference", "status": "draft"})
        elif key == "glossary":
            sec_map["glossary"]["items"].append({"title": title, "slug": slug, "path": path, "level": "Reference", "status": "draft"})

    return {
        "title": "HIVE Academy",
        "version": "1.0.0",
        "last_updated": TODAY,
        "module_encyclopedia_count": module_count,
        "sections": sections,
    }


def write_readmes() -> None:
    readmes = {
        "README.md": "# HIVE Academy\n\nLiving docs — `academy-index.json` ile indekslenir.\n",
        "06-modul-ansiklopedisi/README.md": fm({
            "title": "Modül Ansiklopedisi", "slug": "modul-ansiklopedisi",
            "category": "Modül Ansiklopedisi", "level": "Reference", "order": 0,
            "status": "published", "version": "1.0.0", "last_updated": TODAY, "owner": "HIVE Team",
            "related": ["Modüller", "liste.py"],
        }) + "\n\n# Modül Ansiklopedisi\n\n`liste.py` kayıtlı tüm modüller için otomatik taslak dokümanlar.\n",
        "07-api/README.md": fm({
            "title": "API Referansı", "slug": "api-readme", "category": "API",
            "level": "Reference", "order": 1, "status": "draft", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["API", "Auth"],
        }) + "\n\n# API Referansı\n\n<!-- TODO: endpoint kataloğu -->\n",
        "08-deploy/README.md": fm({
            "title": "Deploy Rehberi", "slug": "deploy-readme", "category": "Deploy",
            "level": "Reference", "order": 1, "status": "draft", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["VPS", "nginx"],
        }) + "\n\n# Deploy\n\nBkz. `docs/HIVE_PRODUCTION_DEPLOYMENT.md`\n",
        "09-troubleshooting/README.md": fm({
            "title": "Sorun Giderme", "slug": "troubleshooting-readme", "category": "Troubleshooting",
            "level": "Reference", "order": 1, "status": "draft", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["Hatalar"],
        }) + "\n\n# Sorun Giderme\n\n<!-- TODO -->\n",
        "10-glossary/README.md": fm({
            "title": "Sözlük", "slug": "glossary-readme", "category": "Sözlük",
            "level": "Reference", "order": 1, "status": "draft", "version": "1.0.0",
            "last_updated": TODAY, "owner": "HIVE Team", "related": ["SEO", "GEO"],
        }) + "\n\n# Sözlük\n\n<!-- TODO: terimler -->\n",
    }
    for rel, text in readmes.items():
        p = ACADEMY / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def main() -> None:
    ACADEMY.mkdir(parents=True, exist_ok=True)
    MODUL_DIR.mkdir(parents=True, exist_ok=True)
    write_readmes()
    for p in PAGES:
        write_page(p)
    count = 0
    for mod in MODULLER:
        out = MODUL_DIR / f"{mod['id']}.md"
        out.write_text(module_doc(mod), encoding="utf-8")
        count += 1
    index = build_index(count)
    (ACADEMY / "academy-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK: {len(PAGES)} sayfa, {count} modül taslağı, index yazıldı.")


if __name__ == "__main__":
    main()
