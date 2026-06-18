import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import { buildSSSPrefill, saveSSSPrefill } from "../utils/sssPrefill";


export default function Talon({ onNavigateToSSS, embedded = false, settingsPulse = 0 }) {
  const [anaKelime, setAnaKelime] = useState("kuşadası escort");
  const [adet, setAdet] = useState(10);
  const [sehir, setSehir] = useState("kuşadası");
  const [negatifFiltre, setNegatifFiltre] = useState("");
  const [kelimeler, setKelimeler] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hata, setHata] = useState("");
  const [apiDurum, setApiDurum] = useState({});
  const [durumYukleniyor, setDurumYukleniyor] = useState(true);

  const [gecmis, setGecmis] = useState([]);
  const [gecmisAcik, setGecmisAcik] = useState(false);
  const [gecmisYukleniyor, setGecmisYukleniyor] = useState(false);

  const [favoriler, setFavoriler] = useState([]);
  const [favoriAcik, setFavoriAcik] = useState(false);
  const [favoriYukleniyor, setFavoriYukleniyor] = useState(false);

  const [gruplar, setGruplar] = useState(null);
  const [grupModalAcik, setGrupModalAcik] = useState(false);
  const [exportFormat, setExportFormat] = useState("csv");
  const [exportIcerik, setExportIcerik] = useState("");
  const [exportModalAcik, setExportModalAcik] = useState(false);
  const [searchId, setSearchId] = useState(null);
  const [simulasyon, setSimulasyon] = useState(false);
  const [mesaj, setMesaj] = useState("");
  const [sektor, setSektor] = useState("escort");
  const [sektorler, setSektorler] = useState([]);
  const [domain, setDomain] = useState("balkutusu.com");
  const [rakipDomain, setRakipDomain] = useState("");
  const [trendSonuc, setTrendSonuc] = useState(null);
  const [gapSonuc, setGapSonuc] = useState(null);
  const [trendModalAcik, setTrendModalAcik] = useState(false);
  const [gapModalAcik, setGapModalAcik] = useState(false);
  const [researchQuery, setResearchQuery] = useState("kuşadası gece hayatı");
  const [researchSonuc, setResearchSonuc] = useState(null);
  const [researchAcik, setResearchAcik] = useState(false);
  const [health, setHealth] = useState(null);

  const [ayarlarAcik, setAyarlarAcik] = useState(false);
  const [ayarlar, setAyarlar] = useState({
    tavily: "",
    exa: "",
    searxng_url: "http://localhost:8080",
    openrouter: "",
    ollama_host: "http://localhost:11434",
    dataforseo_login: "",
    dataforseo_password: "",
    serpapi: "",
  });
  const [ayarlarKaydediliyor, setAyarlarKaydediliyor] = useState(false);

  const apiDurumYukle = useCallback(async () => {
    try {
      const [statusRes, healthRes] = await Promise.all([
        API.get("/api/talon/status"),
        API.get("/api/talon/health"),
      ]);
      setApiDurum(statusRes.data.api || {});
      setHealth(healthRes.data);
    } catch {
      setApiDurum({});
      setHealth(null);
    }
    setDurumYukleniyor(false);
  }, []);

  const gecmisYukle = useCallback(async () => {
    setGecmisYukleniyor(true);
    try {
      const res = await API.get("/api/talon/gecmis");
      setGecmis(res.data.kayitlar || []);
    } catch {
      setGecmis([]);
    }
    setGecmisYukleniyor(false);
  }, []);

  const favoriYukle = useCallback(async () => {
    setFavoriYukleniyor(true);
    try {
      const res = await API.get("/api/talon/favoriler");
      setFavoriler(res.data.favoriler || []);
    } catch {
      setFavoriler([]);
    }
    setFavoriYukleniyor(false);
  }, []);

  useEffect(() => {
    apiDurumYukle();
    gecmisYukle();
    favoriYukle();
    API.get("/api/talon/sektorler")
      .then((res) => setSektorler(res.data.sektorler || []))
      .catch(() => setSektorler([]));
  }, [apiDurumYukle, gecmisYukle, favoriYukle]);

  const kelimeUret = async (forceSim = false) => {
    setHata("");
    setMesaj("");
    const v2aktif = apiDurum.stack?.var || apiDurum.searxng?.var || apiDurum.tavily?.var || apiDurum.exa?.var;
    if (!v2aktif && !forceSim) {
      setHata("V2 provider yok — simülasyon için 'Yine de Çalıştır' butonuna basın. .env'e TAVILY/EXA/SEARXNG ekleyin.");
      return;
    }
    setLoading(true);
    setKelimeler([]);
    setSearchId(null);
    setSimulasyon(false);
    try {
      const res = await API.post("/api/talon", {
        ana_kelime: anaKelime,
        adet: adet,
        sehir: sehir,
        negatif_filtre: negatifFiltre || null,
        sektor: sektor,
      });
      if (res.data.status === "hata") {
        setHata(res.data.hata || "Bilinmeyen hata");
      } else {
        setKelimeler(res.data.kelimeler || []);
        setSearchId(res.data.search_id || null);
        setSimulasyon(!!res.data.simulasyon);
        if (res.data.simulasyon) {
          setMesaj("Simülasyon modu — gerçek veri için Tavily/Exa/SearXNG anahtarlarını ayarlardan veya .env'e ekleyin.");
        } else {
          setMesaj(`${res.data.kelimeler?.length || 0} kelime üretildi (API aktif).`);
        }
        gecmisYukle();
      }
    } catch (err) {
      setHata("Backend bağlantı hatası: " + (err.hiveMessage || err.message || "Bilinmeyen hata"));
    }
    setLoading(false);
  };

  const handleUret = () => kelimeUret(false);
  const yineDeCalistir = () => kelimeUret(true);

  const gecmistenYukle = (kayit) => {
    setAnaKelime(kayit.ana_kelime);
    setAdet(kayit.adet);
    setSehir(kayit.sehir);
    setNegatifFiltre(kayit.negatif_filtre || "");
    setGecmisAcik(false);
    setHata("");
    if (kayit.id) {
      API.get(`/api/talon/history/${kayit.id}`)
        .then((res) => {
          const data = res.data;
          if (Array.isArray(data.kelimeler)) {
            setKelimeler(data.kelimeler);
            setSearchId(kayit.id);
          } else if (data.kayit && Array.isArray(data.kayit[1])) {
            setKelimeler(data.kayit[1]);
          } else {
            setKelimeler([]);
          }
        })
        .catch((e) => setHata("Geçmiş yüklenemedi: " + (e.message || "")));
    }
  };

  const gecmisSil = async (id) => {
    try {
      await API.delete(`/api/talon/history/${id}`);
      gecmisYukle();
      setMesaj("Geçmiş kaydı silindi.");
    } catch (e) {
      setHata("Silme hatası: " + (e.message || ""));
    }
  };

  const favoriEkle = async (item) => {
    try {
      await API.post("/api/talon/favoriler", {
        kelime: item.kelime,
        rekabet: item.rekabet,
        arama_hacmi: item.arama_hacmi,
        rakip_var: item.rakip_var,
      });
      favoriYukle();
      setMesaj(`"${item.kelime}" favorilere eklendi.`);
    } catch (e) {
      setHata("Favori eklenemedi: " + (e.message || ""));
    }
  };

  const favoriKaldir = async (kelime) => {
    try {
      await API.delete(`/api/talon/favoriler/${encodeURIComponent(kelime)}`);
      favoriYukle();
    } catch (e) {
      setHata("Favori kaldırılamadı: " + (e.message || ""));
    }
  };

  const favoriMi = (kelime) => favoriler.some((f) => f.kelime === kelime);
  const kopyala = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
  };

  const hepsiniKopyala = () => {
    const text = kelimeler.map((k) => k.kelime).join("\n");
    kopyala(text);
  };

  const grupla = async () => {
    if (kelimeler.length === 0) return;
    try {
      const res = await API.post("/api/talon/grupla", { kelimeler });
      setGruplar(res.data.gruplar);
      setGrupModalAcik(true);
    } catch (e) {
      setHata("Gruplama hatası: " + (e.message || ""));
    }
  };

  const handleExport = async () => {
    if (kelimeler.length === 0) return;
    try {
      const res = await API.post(`/api/talon/export/${exportFormat}`, { kelimeler });
      setExportIcerik(res.data.content || "");
      setExportModalAcik(true);
    } catch (err) {
      setHata("Export başarısız: " + (err.message || ""));
    }
  };

  const rankTrackerAktar = async () => {
    if (kelimeler.length === 0) return;
    setLoading(true);
    setHata("");
    try {
      const res = await API.post("/api/talon/ranktracker-transfer", {
        kelimeler,
        domain,
        sehir,
      });
      setMesaj(`Rank Tracker: ${res.data.toplam_kaydedilen} kelime aktarıldı, ${res.data.zaten_var?.length || 0} zaten vardı.`);
    } catch (e) {
      setHata("Rank Tracker aktarım hatası: " + (e.response?.data?.detail || e.message || ""));
    }
    setLoading(false);
  };

  const trendAnaliz = async () => {
    if (kelimeler.length === 0) return;
    setLoading(true);
    setHata("");
    try {
      const res = await API.post("/api/talon/trend-analiz", { kelimeler, sehir });
      setTrendSonuc(res.data);
      setTrendModalAcik(true);
    } catch (e) {
      setHata("Trend analiz hatası: " + (e.message || ""));
    }
    setLoading(false);
  };

  const rakipGap = async () => {
    if (kelimeler.length === 0) return;
    setLoading(true);
    setHata("");
    try {
      const res = await API.post("/api/talon/rakip-gap", {
        bizim_kelimeler: kelimeler,
        rakip_domain: rakipDomain,
        hedef_domain: domain,
        limit: 30,
      });
      setGapSonuc(res.data);
      setGapModalAcik(true);
    } catch (e) {
      setHata("Rakip gap hatası: " + (e.message || ""));
    }
    setLoading(false);
  };

  const fullSeoResearch = async () => {
    if (!researchQuery.trim()) return;
    setLoading(true);
    setHata("");
    try {
      const res = await API.post("/api/talon/full-seo-research", {
        seed_keyword: researchQuery.trim(),
        num_results: 10,
      });
      setResearchSonuc(res.data);
      setResearchAcik(true);
      setMesaj("Full SEO Research tamamlandı.");
    } catch (e) {
      setHata("Research hatası: " + (e.response?.data?.detail || e.message || ""));
    }
    setLoading(false);
  };

  const sssZincirineGonder = (autoStart = false) => {
    if (!onNavigateToSSS) {
      setHata("SSS sayfasına yönlendirme yapılandırılmamış.");
      return;
    }
    const hasResearch = researchSonuc && researchAcik;
    const hasKeywords = kelimeler.length > 0;
    if (!hasResearch && !hasKeywords && !researchQuery.trim() && !anaKelime.trim()) {
      setHata("Önce Full SEO Research çalıştırın veya anahtar kelime üretin.");
      return;
    }

    const payload = buildSSSPrefill({
      researchSonuc: hasResearch ? researchSonuc : null,
      sehir,
      sektor,
      sektorler,
      kelimeler,
      researchQuery,
      anaKelime,
    });

    const kwCount = payload.keyword_count || 50;
    const msg = autoStart
      ? `${kwCount} adet GEO/SEO uyumlu SSS sayfası üretilip WordPress'e yayınlanacak. Devam?`
      : `SSS Otomasyon sayfasına ${kwCount} kelime aktarılacak. Formu kontrol edip başlatabilirsiniz. Devam?`;

    if (!window.confirm(msg)) return;

    saveSSSPrefill(payload, { autoStart });
    setMesaj(
      autoStart
        ? "SSS zinciri başlatılıyor — SSS Otomasyon sayfasına yönlendiriliyorsunuz..."
        : "Research verileri SSS zincirine aktarıldı — yönlendiriliyorsunuz..."
    );
    onNavigateToSSS({ autoStart, summary: payload.research_summary });
  };

  const migrasyonCalistir = async (dryRun = false) => {
    setLoading(true);
    setHata("");
    try {
      const res = await API.post("/api/talon/migrate", { dry_run: dryRun });
      const g = res.data.gecmis || {};
      const f = res.data.favoriler || {};
      setMesaj(
        dryRun
          ? `Migrasyon önizleme: ${g.tasinan || 0} geçmiş, ${f.tasinan || 0} favori taşınabilir.`
          : `Migrasyon tamam: ${g.tasinan || 0} geçmiş, ${f.tasinan || 0} favori SQLite'a aktarıldı.`
      );
      if (!dryRun) gecmisYukle();
    } catch (e) {
      setHata("Migrasyon hatası: " + (e.message || ""));
    }
    setLoading(false);
  };

  const subdomainOlustur = async () => {
    if (kelimeler.length === 0) return;
    setLoading(true);
    setHata("");
    try {
      const res = await API.post("/api/subdomain/talon-create", {
        kelimeler: kelimeler.map((k) => k.kelime),
        parent_domain: "",
        icerik_doldur: true,
      });
      setMesaj(`Subdomain oluşturma: ${res.data.olusan?.length || 0} site eklendi.`);
    } catch (e) {
      setHata("Subdomain hatası: " + (e.response?.data?.detail || e.message || ""));
    }
    setLoading(false);
  };

  const exportIndir = () => {
    const ext = exportFormat === "csv" ? "csv" : exportFormat === "json" ? "json" : "txt";
    const mime =
      exportFormat === "csv"
        ? "text/csv"
        : exportFormat === "json"
        ? "application/json"
        : "text/plain";
    const blob = new Blob([exportIcerik], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `talon_kelimeler.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const ayarlariAc = async () => {
    setAyarlarAcik(true);
    try {
      const res = await API.get("/api/talon/status");
      const durum = res.data.api || {};
      setAyarlar({
        tavily: durum.tavily?.var ? "••••••••" : "",
        exa: durum.exa?.var ? "••••••••" : "",
        searxng_url: durum.searxng?.var ? "••••••••" : "http://localhost:8080",
        openrouter: durum.openrouter?.var ? "••••••••" : "",
        ollama_host: durum.ollama?.var ? "http://localhost:11434" : "http://localhost:11434",
        dataforseo_login: durum.dataforseo?.var ? "••••••••" : "",
        dataforseo_password: durum.dataforseo?.var ? "••••••••" : "",
        serpapi: durum.serpapi?.var ? "••••••••" : "",
      });
    } catch {}
  };

  useEffect(() => {
    if (settingsPulse > 0) ayarlariAc();
  }, [settingsPulse]);

  const ayarlariKaydet = async () => {
    setAyarlarKaydediliyor(true);
    try {
      const payload = {};
      const fieldMapping = [
        "tavily", "exa", "searxng_url", "openrouter", "ollama_host",
        "dataforseo_login", "dataforseo_password", "serpapi",
      ];
      fieldMapping.forEach((key) => {
        if (ayarlar[key] && !ayarlar[key].startsWith("••")) {
          payload[key] = ayarlar[key];
        }
      });
      if (Object.keys(payload).length > 0) {
        await API.post("/api/talon/settings", payload);
      }
      setAyarlarAcik(false);
      apiDurumYukle();
    } catch (err) {
      setHata("Ayarlar kaydedilemedi: " + (err.message || ""));
    }
    setAyarlarKaydediliyor(false);
  };

  const grupAdiGoster = (g) => {
    const isimler = {
      lokasyon_bazli: "Lokasyon Bazlı",
      hizmet_bazli: "Hizmet Bazlı",
      fiyat_bazli: "Fiyat Bazlı",
      zaman_bazli: "Zaman Bazlı",
      diger: "Diğer",
    };
    return isimler[g] || g;
  };

  const rekabetRengi = (r) => {
    if (r === "düşük") return "var(--green)";
    if (r === "orta") return "var(--honey)";
    return "var(--red)";
  };

  const hacimRengi = (h) => {
    if (h === "0-100") return "var(--red)";
    if (h === "100-500") return "var(--orange)";
    if (h === "500-1000") return "var(--honey)";
    return "var(--green)";
  };

  return (
    <div className={embedded ? "talon-page talon-page-embedded" : "talon-page"}>
      {!embedded && (
      <div className="header">
        <div className="icon">🐝</div>
        <div className="info">
          <h2>Talon – Hiper-Lokal Anahtar Kelime Avcısı</h2>
          <p>
            Bir ana kelimeyi lokasyon ve hizmet türleriyle birleştirerek
            hiper-lokal SEO anahtar kelimeleri üretir. Rekabet, arama hacmi ve
            rakip analizi yapar.
          </p>
        </div>
        <button
          onClick={ayarlariAc}
          title="Ayarlar"
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: 6,
            color: "var(--text)",
            cursor: "pointer",
            fontSize: "1.3rem",
            padding: "0.5rem 0.7rem",
            alignSelf: "flex-start",
            marginLeft: "auto",
          }}
        >
          ⚙️
        </button>
      </div>
      )}

      {!embedded && (
      <div className="status-badge" style={{
        background: (apiDurum.stack?.var || apiDurum.searxng?.var || apiDurum.tavily?.var) ? "rgba(107,142,35,0.2)" : "rgba(255,68,68,0.15)",
        color: (apiDurum.stack?.var || apiDurum.searxng?.var || apiDurum.tavily?.var) ? "var(--olive2)" : "var(--red)",
        border: `1px solid ${(apiDurum.stack?.var || apiDurum.searxng?.var || apiDurum.tavily?.var) ? "var(--olive2)" : "var(--red)"}`,
        padding: "0.3rem 0.8rem",
        borderRadius: 6,
        display: "inline-flex",
        alignItems: "center",
        gap: "0.4rem",
        fontSize: "0.85rem",
        marginBottom: "0.8rem",
      }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%",
          background: (apiDurum.stack?.var || apiDurum.searxng?.var || apiDurum.tavily?.var) ? "var(--olive2)" : "var(--red)",
          display: "inline-block",
        }} />
        {durumYukleniyor ? "Durum kontrol ediliyor..." : ((apiDurum.stack?.var || apiDurum.searxng?.var || apiDurum.tavily?.var || apiDurum.exa?.var) ? "Talon V2 Stack Aktif" : "V2 Provider Eksik (Autocomplete/OSM yine çalışır)")}
      </div>
      )}

      {!embedded && (
      <div className="talon-api-status" style={{
        display: "flex",
        gap: "0.8rem",
        flexWrap: "wrap",
        marginBottom: "1.2rem",
      }}>
        {["searxng", "tavily", "exa", "autocomplete", "openstreetmap", "openrouter", "ollama"].map((s) => {
          const servis = apiDurum[s];
          const ad = servis ? servis.ad : s;
          const aktif = servis && servis.var;
          return (
            <div key={s} style={{
              flex: 1,
              minWidth: 120,
              background: "var(--bg3)",
              border: `1px solid ${aktif ? "var(--olive2)" : "var(--border)"}`,
              borderRadius: 6,
              padding: "0.5rem 0.8rem",
              opacity: durumYukleniyor ? 0.5 : 1,
            }}>
              <div style={{ fontSize: "0.7rem", color: "var(--text2)", marginBottom: "0.2rem" }}>{ad}</div>
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: aktif ? "var(--olive2)" : "var(--text2)",
              }}>
                <span style={{
                  width: 10, height: 10, borderRadius: "50%",
                  background: aktif ? "var(--olive2)" : "var(--border)",
                  display: "inline-block",
                }} />
                {durumYukleniyor ? "..." : (aktif ? "Aktif" : "Eksik")}
              </div>
            </div>
          );
        })}
      </div>
      )}

      {!embedded && (
      <div style={{ marginBottom: "1.2rem", padding: "0.8rem", background: "var(--bg3)", borderRadius: 8 }}>
        <h4 style={{ margin: "0 0 0.5rem" }}>🔬 Full SEO Research (V2 Stack)</h4>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <input
            value={researchQuery}
            onChange={(e) => setResearchQuery(e.target.value)}
            placeholder="Seed keyword"
            style={{ flex: 2, minWidth: 200, padding: "0.5rem" }}
          />
          <button className="btn btn-primary" onClick={fullSeoResearch} disabled={loading}>
            {loading ? "Araştırılıyor..." : "Full SEO Research"}
          </button>
          {onNavigateToSSS && (
            <>
              <button
                className="btn btn-outline"
                onClick={() => sssZincirineGonder(false)}
                disabled={loading}
                style={{ borderColor: "var(--olive2)", color: "var(--olive2)" }}
                title="Research sonuçlarını SSS Otomasyon formuna aktar"
              >
                ❓ SSS Zincirine Gönder
              </button>
              <button
                className="btn btn-outline"
                onClick={() => sssZincirineGonder(true)}
                disabled={loading}
                style={{ borderColor: "var(--honey)", color: "var(--honey)" }}
                title="Aktar ve üretimi hemen başlat (WP bağlantısı gerekir)"
              >
                🚀 SSS Üret & Yayınla
              </button>
            </>
          )}
        </div>
      </div>
      )}

      <div className="talon-form">
        <div className="form-row" style={{ flexWrap: "wrap", display: "flex", gap: "0.8rem" }}>
          <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
            <label>Ana Kelime</label>
            <input type="text" value={anaKelime} onChange={(e) => setAnaKelime(e.target.value)} placeholder="örn: kuşadası escort" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 80 }}>
            <label>Adet</label>
            <input type="number" value={adet} onChange={(e) => setAdet(parseInt(e.target.value) || 10)} min={1} max={100} />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 120 }}>
            <label>Şehir</label>
            <select value={sehir} onChange={(e) => setSehir(e.target.value)}>
              <option value="kuşadası">Kuşadası</option>
              <option value="istanbul">İstanbul</option>
              <option value="izmir">İzmir</option>
              <option value="ankara">Ankara</option>
              <option value="antalya">Antalya</option>
              <option value="bursa">Bursa</option>
              <option value="adana">Adana</option>
              <option value="mersin">Mersin</option>
              <option value="muğla">Muğla</option>
              <option value="aydın">Aydın</option>
            </select>
          </div>
          <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
            <label>Negatif Filtre (virgülle ayırın)</label>
            <input type="text" value={negatifFiltre} onChange={(e) => setNegatifFiltre(e.target.value)} placeholder="örn: ucuz, ekonomik" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 160 }}>
            <label>Sektör Şablonu</label>
            <select value={sektor} onChange={(e) => setSektor(e.target.value)}>
              {sektorler.length > 0 ? (
                sektorler.map((s) => (
                  <option key={s.id} value={s.id}>{s.ad}</option>
                ))
              ) : (
                <>
                  <option value="escort">Escort</option>
                  <option value="gece_hayati">Gece Hayatı</option>
                  <option value="otel_turizm">Otel & Turizm</option>
                  <option value="emlak">Emlak</option>
                  <option value="seo_dijital">SEO & Dijital</option>
                </>
              )}
            </select>
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 160 }}>
            <label>Domain (Rank Tracker)</label>
            <input type="text" value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="balkutusu.com" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 160 }}>
            <label>Rakip Domain (Gap)</label>
            <input type="text" value={rakipDomain} onChange={(e) => setRakipDomain(e.target.value)} placeholder="rakip-site.com" />
          </div>
        </div>
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button className="btn btn-primary" onClick={handleUret} disabled={loading} style={{ fontSize: "1rem", padding: "0.6rem 1.5rem" }}>
            {loading ? "Üretiliyor..." : "Anahtar Kelime Üret"}
          </button>
          {hata && hata.includes("V2 provider") && (
            <button className="btn btn-outline" onClick={yineDeCalistir} disabled={loading} style={{ fontSize: "0.85rem", borderColor: "var(--honey)", color: "var(--honey)" }}>
              Yine de Çalıştır (Simülasyon)
            </button>
          )}
          <button className="btn btn-outline" onClick={() => { gecmisYukle(); setGecmisAcik(!gecmisAcik); }} style={{ fontSize: "0.85rem" }}>
            Geçmiş Göster ({gecmis.length})
          </button>
          <button className="btn btn-outline" onClick={() => { favoriYukle(); setFavoriAcik(!favoriAcik); }} style={{ fontSize: "0.85rem" }}>
            Favoriler ({favoriler.length})
          </button>
          <button className="btn btn-outline" onClick={() => migrasyonCalistir(true)} disabled={loading} style={{ fontSize: "0.85rem" }}>
            Migrasyon Önizle
          </button>
          <button className="btn btn-outline" onClick={() => migrasyonCalistir(false)} disabled={loading} style={{ fontSize: "0.85rem" }}>
            JSON → SQLite
          </button>
          {onNavigateToSSS && kelimeler.length > 0 && (
            <button
              className="btn btn-outline"
              onClick={() => sssZincirineGonder(false)}
              disabled={loading}
              style={{ fontSize: "0.85rem", borderColor: "var(--olive2)", color: "var(--olive2)" }}
            >
              ❓ {kelimeler.length} Kelimeyi SSS Zincirine Gönder
            </button>
          )}
        </div>
      </div>

      {gecmisAcik && (
        <div className="talon-gecmis" style={{ marginTop: "1rem", background: "var(--bg3)", borderRadius: 8, padding: "0.8rem" }}>
          <h4 style={{ margin: "0 0 0.5rem" }}>Geçmiş Üretimler</h4>
          {gecmisYukleniyor && <p style={{ color: "var(--text2)", fontSize: "0.85rem" }}>Yükleniyor...</p>}
          {!gecmisYukleniyor && gecmis.length === 0 && <p style={{ color: "var(--text2)", fontSize: "0.85rem" }}>Henüz geçmiş yok.</p>}
          {gecmis.length > 0 && (
            <div style={{ maxHeight: 200, overflowY: "auto" }}>
              {gecmis.map((k) => (
                <div key={k.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.4rem 0", borderBottom: "1px solid var(--border)", fontSize: "0.85rem" }}>
                  <div style={{ flex: 1, cursor: "pointer" }} onClick={() => gecmistenYukle(k)}>
                    <strong>{k.ana_kelime}</strong>
                    <span style={{ color: "var(--text2)", marginLeft: "0.5rem" }}>
                      {k.sehir} | {k.kelime_sayisi || 0} kelime | {k.timestamp ? new Date(k.timestamp).toLocaleString("tr-TR") : ""}
                    </span>
                  </div>
                  <button className="btn btn-sm" style={{ background: "transparent", color: "var(--red)", border: "none", cursor: "pointer", padding: "0.25rem" }} onClick={() => gecmisSil(k.id)}>🗑️</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {favoriAcik && (
        <div className="talon-favoriler" style={{ marginTop: "1rem", background: "var(--bg3)", borderRadius: 8, padding: "0.8rem" }}>
          <h4 style={{ margin: "0 0 0.5rem" }}>Favori Kelimeler</h4>
          {favoriYukleniyor && <p style={{ color: "var(--text2)", fontSize: "0.85rem" }}>Yükleniyor...</p>}
          {!favoriYukleniyor && favoriler.length === 0 && <p style={{ color: "var(--text2)", fontSize: "0.85rem" }}>Henüz favori kelime yok.</p>}
          {favoriler.length > 0 && (
            <div style={{ maxHeight: 200, overflowY: "auto" }}>
              {favoriler.map((f, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.4rem 0", borderBottom: "1px solid var(--border)", fontSize: "0.85rem" }}>
                  <span style={{ flex: 1 }}>{f.kelime}</span>
                  <span style={{ color: rekabetRengi(f.rekabet), marginRight: "0.5rem", fontSize: "0.75rem" }}>{f.rekabet}</span>
                  <span style={{ color: hacimRengi(f.arama_hacmi), marginRight: "0.5rem", fontSize: "0.75rem" }}>{f.arama_hacmi}</span>
                  <button className="btn btn-sm" style={{ background: "transparent", color: "var(--honey)", border: "none", cursor: "pointer" }} onClick={() => favoriKaldir(f.kelime)}>⭐</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {hata && (
        <div className="hata" style={{ marginTop: "1rem", background: "rgba(255,68,68,0.1)", border: "1px solid var(--red)", borderRadius: 8, padding: "0.8rem", color: "var(--red)" }}>
          {hata}
        </div>
      )}

      {mesaj && !hata && (
        <div style={{ marginTop: "1rem", background: "rgba(107,142,35,0.1)", border: "1px solid var(--olive2)", borderRadius: 8, padding: "0.8rem", color: "var(--olive2)" }}>
          {mesaj}
        </div>
      )}

      {kelimeler.length > 0 && (
        <div className="talon-sonuc" style={{ marginTop: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.8rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <h3 style={{ margin: 0 }}>
              Üretilen Anahtar Kelimeler ({kelimeler.length})
              {searchId && <span style={{ fontSize: "0.75rem", color: "var(--text2)", marginLeft: "0.5rem" }}>#{searchId}</span>}
              {simulasyon && <span style={{ fontSize: "0.7rem", color: "var(--honey)", marginLeft: "0.5rem" }}>⚡ Simülasyon</span>}
            </h3>
            <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
              <button className="btn btn-outline" onClick={hepsiniKopyala} style={{ fontSize: "0.8rem" }}>Tümünü Kopyala</button>
              <button className="btn btn-outline" onClick={grupla} style={{ fontSize: "0.8rem" }}>Grupları Göster</button>
              <button className="btn btn-outline" onClick={rankTrackerAktar} disabled={loading} style={{ fontSize: "0.8rem" }}>Rank Tracker'a Aktar</button>
              <button className="btn btn-outline" onClick={trendAnaliz} disabled={loading} style={{ fontSize: "0.8rem" }}>Trend / Sezon</button>
              <button className="btn btn-outline" onClick={rakipGap} disabled={loading} style={{ fontSize: "0.8rem" }}>Rakip Gap</button>
              <button className="btn btn-outline" onClick={subdomainOlustur} disabled={loading} style={{ fontSize: "0.8rem" }}>Subdomain Oluştur</button>
              <div style={{ display: "flex", gap: "0.3rem", alignItems: "center" }}>
                <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value)} style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.25rem", fontSize: "0.8rem" }}>
                  <option value="csv">CSV</option>
                  <option value="json">JSON</option>
                  <option value="txt">TXT</option>
                </select>
                <button className="btn btn-outline" onClick={handleExport} style={{ fontSize: "0.8rem" }}>Dışa Aktar</button>
              </div>
            </div>
          </div>

          <div className="talon-tablo" style={{ overflowX: "auto" }}>
            <table className="table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>#</th>
                  <th style={{ textAlign: "left", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>Anahtar Kelime</th>
                  <th style={{ textAlign: "center", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>Rekabet</th>
                  <th style={{ textAlign: "center", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>Arama Hacmi</th>
                  <th style={{ textAlign: "center", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>CPC</th>
                  <th style={{ textAlign: "center", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>Rakip Var</th>
                  <th style={{ textAlign: "center", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>Favori</th>
                  <th style={{ textAlign: "center", padding: "0.5rem", borderBottom: "1px solid var(--border)" }}>Kopyala</th>
                </tr>
              </thead>
              <tbody>
                {kelimeler.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "0.5rem", color: "var(--text2)" }}>{idx + 1}</td>
                    <td style={{ padding: "0.5rem", fontWeight: 500 }}>{item.kelime}</td>
                    <td style={{ padding: "0.5rem", textAlign: "center" }}>
                      <span style={{ color: rekabetRengi(item.rekabet), fontWeight: 600 }}>{item.rekabet}</span>
                    </td>
                    <td style={{ padding: "0.5rem", textAlign: "center" }}>
                      <span style={{ color: hacimRengi(item.arama_hacmi), fontWeight: 600 }}>{item.arama_hacmi}</span>
                    </td>
                    <td style={{ padding: "0.5rem", textAlign: "center", color: "var(--text2)" }}>
                      {item.cpc || "0"}
                    </td>
                    <td style={{ padding: "0.5rem", textAlign: "center" }}>
                      <span style={{ color: item.rakip_var ? "var(--red)" : "var(--green)" }}>
                        {item.rakip_var ? "Var" : "Yok"}
                      </span>
                    </td>
                    <td style={{ padding: "0.5rem", textAlign: "center" }}>
                      <button
                        className="btn btn-sm"
                        style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: "1.1rem" }}
                        onClick={() => favoriMi(item.kelime) ? favoriKaldir(item.kelime) : favoriEkle(item)}
                      >
                        {favoriMi(item.kelime) ? "⭐" : "☆"}
                      </button>
                    </td>
                    <td style={{ padding: "0.5rem", textAlign: "center" }}>
                      <button
                        className="btn btn-sm"
                        onClick={() => kopyala(item.kelime)}
                        style={{ background: "var(--honey)", color: "#000", border: "none", borderRadius: 4, cursor: "pointer", padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                      >
                        📋
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {grupModalAcik && gruplar && (
        <div className="modal-overlay" onClick={() => setGrupModalAcik(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600 }}>
            <div className="modal-header">
              <h3>Kelime Grupları</h3>
              <button className="btn btn-sm" onClick={() => setGrupModalAcik(false)} style={{ background: "transparent", border: "none", color: "var(--text2)", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
            </div>
            <div className="modal-body" style={{ maxHeight: 400, overflowY: "auto" }}>
              {Object.entries(gruplar).map(([grup, items]) => (
                <div key={grup} style={{ marginBottom: "1rem" }}>
                  <h4 style={{ margin: "0 0 0.3rem", fontSize: "0.95rem" }}>{grupAdiGoster(grup)} ({items.length})</h4>
                  {items.length === 0 && <p style={{ color: "var(--text2)", fontSize: "0.8rem", margin: 0 }}>Bu grupta kelime yok.</p>}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                    {items.map((item, i) => (
                      <span key={i} style={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.2rem 0.5rem", fontSize: "0.8rem" }}>
                        {item.kelime}
                        <span style={{ color: rekabetRengi(item.rekabet), marginLeft: "0.3rem", fontSize: "0.7rem" }}>{item.rekabet}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {exportModalAcik && (
        <div className="modal-overlay" onClick={() => setExportModalAcik(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600 }}>
            <div className="modal-header">
              <h3>Dışa Aktar</h3>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn btn-primary" onClick={exportIndir} style={{ fontSize: "0.8rem", padding: "0.3rem 0.8rem" }}>İndir</button>
                <button className="btn btn-sm" onClick={() => setExportModalAcik(false)} style={{ background: "transparent", border: "none", color: "var(--text2)", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
              </div>
            </div>
            <div className="modal-body">
              <pre style={{ background: "var(--bg2)", padding: "0.8rem", borderRadius: 6, fontSize: "0.75rem", maxHeight: 300, overflow: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                {exportIcerik.slice(0, 5000)}
              </pre>
            </div>
          </div>
        </div>
      )}

      {trendModalAcik && trendSonuc && (
        <div className="modal-overlay" onClick={() => setTrendModalAcik(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 700 }}>
            <div className="modal-header">
              <h3>Trend / Sezon Analizi — {trendSonuc.aktif_sezon}</h3>
              <button className="btn btn-sm" onClick={() => setTrendModalAcik(false)} style={{ background: "transparent", border: "none", color: "var(--text2)", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
            </div>
            <div className="modal-body" style={{ maxHeight: 450, overflowY: "auto" }}>
              {(trendSonuc.analizler || []).map((a, i) => (
                <div key={i} style={{ marginBottom: "1rem", padding: "0.6rem", background: "var(--bg3)", borderRadius: 6 }}>
                  <strong>{a.kelime}</strong>
                  <div style={{ fontSize: "0.8rem", color: "var(--text2)", marginTop: "0.3rem" }}>
                    Momentum: {a.momentum} | Popülerlik: {a.populerlik}
                    {a.gercek_hacim != null && <> | Gerçek hacim: {a.gercek_hacim}</>}
                  </div>
                  <div style={{ fontSize: "0.8rem", marginTop: "0.3rem" }}>{a.tavsiye}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {researchAcik && researchSonuc && (
        <div style={{ marginTop: "1.5rem", padding: "1rem", border: "1px solid var(--border)", borderRadius: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <h3 style={{ margin: 0 }}>SEO Research — {researchSonuc.seedKeyword}</h3>
            {onNavigateToSSS && (
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                <button className="btn btn-sm btn-outline" onClick={() => sssZincirineGonder(false)} style={{ fontSize: "0.8rem" }}>
                  ❓ SSS Zincirine Gönder
                </button>
                <button className="btn btn-sm btn-primary" onClick={() => sssZincirineGonder(true)} style={{ fontSize: "0.8rem" }}>
                  🚀 SSS Üret & Yayınla
                </button>
              </div>
            )}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
            <div>
              <h4>SERP ({researchSonuc.serpResults?.length || 0})</h4>
              <ul style={{ fontSize: "0.8rem", maxHeight: 160, overflowY: "auto" }}>
                {(researchSonuc.serpResults || []).slice(0, 5).map((r, i) => (
                  <li key={i}>{r.title || r.url}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Rakipler</h4>
              <ul style={{ fontSize: "0.8rem" }}>
                {(researchSonuc.competitors || []).slice(0, 6).map((c, i) => (
                  <li key={i}>{c.domain}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Keyword Fikirleri</h4>
              <ul style={{ fontSize: "0.8rem", maxHeight: 160, overflowY: "auto" }}>
                {(researchSonuc.autocompleteKeywords || []).slice(0, 8).map((k, i) => (
                  <li key={i}>{k}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>SSS Fikirleri</h4>
              <ul style={{ fontSize: "0.8rem", maxHeight: 160, overflowY: "auto" }}>
                {(researchSonuc.faqIdeas || []).slice(0, 6).map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>GEO Sayfa Önerileri</h4>
              <ul style={{ fontSize: "0.8rem" }}>
                {(researchSonuc.recommendedPages || []).slice(0, 5).map((p, i) => (
                  <li key={i}>{p.title}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>İçerik Başlıkları</h4>
              <ul style={{ fontSize: "0.8rem" }}>
                {(researchSonuc.contentAngles || []).slice(0, 6).map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {gapModalAcik && gapSonuc && (
        <div className="modal-overlay" onClick={() => setGapModalAcik(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 700 }}>
            <div className="modal-header">
              <h3>Rakip Keyword Gap — {gapSonuc.rakip_domain || "heuristic"}</h3>
              <button className="btn btn-sm" onClick={() => setGapModalAcik(false)} style={{ background: "transparent", border: "none", color: "var(--text2)", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
            </div>
            <div className="modal-body" style={{ maxHeight: 450, overflowY: "auto" }}>
              <p style={{ fontSize: "0.85rem", color: "var(--text2)" }}>
                Bizde {gapSonuc.bizim_kelime_sayisi} | Rakipte {gapSonuc.rakip_kelime_sayisi} | Gap: {gapSonuc.gap_kelimeler?.length || 0}
              </p>
              {(gapSonuc.gap_kelimeler || []).map((g, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid var(--border)", fontSize: "0.85rem" }}>
                  <span>{g.kelime}</span>
                  <span style={{ color: g.firsat === "yüksek" ? "var(--green)" : "var(--honey)" }}>{g.firsat}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {ayarlarAcik && (
        <div className="modal-overlay" onClick={() => setAyarlarAcik(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
            <div className="modal-header">
              <h3>Talon V2 — API Ayarları</h3>
              <button className="btn btn-sm" onClick={() => setAyarlarAcik(false)} style={{ background: "transparent", border: "none", color: "var(--text2)", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: "0.8rem", color: "var(--olive2)", marginBottom: "1rem", fontWeight: 600 }}>
                V2 Search Stack (varsayılan)
              </p>
              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", fontWeight: 600 }}>Tavily API Key</label>
                <input
                  type="password"
                  value={ayarlar.tavily}
                  onChange={(e) => setAyarlar({ ...ayarlar, tavily: e.target.value })}
                  placeholder="tvly-..."
                  style={{ width: "100%", padding: "0.5rem", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text)" }}
                />
              </div>
              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", fontWeight: 600 }}>Exa API Key</label>
                <input
                  type="password"
                  value={ayarlar.exa}
                  onChange={(e) => setAyarlar({ ...ayarlar, exa: e.target.value })}
                  placeholder="Exa API anahtarı"
                  style={{ width: "100%", padding: "0.5rem", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text)" }}
                />
              </div>
              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", fontWeight: 600 }}>SearXNG URL</label>
                <input
                  type="text"
                  value={ayarlar.searxng_url}
                  onChange={(e) => setAyarlar({ ...ayarlar, searxng_url: e.target.value })}
                  placeholder="http://localhost:8080"
                  style={{ width: "100%", padding: "0.5rem", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text)" }}
                />
              </div>
              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", fontWeight: 600 }}>OpenRouter API Key <span style={{ fontWeight: 400, color: "var(--text2)" }}>(opsiyonel)</span></label>
                <input
                  type="password"
                  value={ayarlar.openrouter}
                  onChange={(e) => setAyarlar({ ...ayarlar, openrouter: e.target.value })}
                  placeholder="LLM sentezi için"
                  style={{ width: "100%", padding: "0.5rem", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text)" }}
                />
              </div>
              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", fontWeight: 600 }}>Ollama Host</label>
                <input
                  type="text"
                  value={ayarlar.ollama_host}
                  onChange={(e) => setAyarlar({ ...ayarlar, ollama_host: e.target.value })}
                  placeholder="http://localhost:11434"
                  style={{ width: "100%", padding: "0.5rem", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text)" }}
                />
              </div>

              <details style={{ marginBottom: "1rem" }}>
                <summary style={{ fontSize: "0.8rem", color: "var(--text2)", cursor: "pointer", fontWeight: 600 }}>
                  Legacy API&apos;ler (deprecated)
                </summary>
                <p style={{ fontSize: "0.75rem", color: "var(--text2)", margin: "0.5rem 0" }}>
                  Yalnızca TALON_USE_LEGACY_APIS=true iken kullanılır.
                </p>
                <div style={{ marginBottom: "0.8rem" }}>
                  <label style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", fontWeight: 600 }}>DataForSEO Email</label>
                  <input
                    type="text"
                    value={ayarlar.dataforseo_login}
                    onChange={(e) => setAyarlar({ ...ayarlar, dataforseo_login: e.target.value })}
                    placeholder="DataForSEO email"
                    style={{ width: "100%", padding: "0.5rem", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text)" }}
                  />
                </div>
                <div style={{ marginBottom: "0.8rem" }}>
                  <label style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", fontWeight: 600 }}>DataForSEO Password</label>
                  <input
                    type="password"
                    value={ayarlar.dataforseo_password}
                    onChange={(e) => setAyarlar({ ...ayarlar, dataforseo_password: e.target.value })}
                    placeholder="DataForSEO şifresi"
                    style={{ width: "100%", padding: "0.5rem", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text)" }}
                  />
                </div>
                <div style={{ marginBottom: "0.8rem" }}>
                  <label style={{ display: "block", marginBottom: "0.3rem", fontSize: "0.85rem", fontWeight: 600 }}>SerpAPI Key</label>
                  <input
                    type="password"
                    value={ayarlar.serpapi}
                    onChange={(e) => setAyarlar({ ...ayarlar, serpapi: e.target.value })}
                    placeholder="SerpAPI anahtarı"
                    style={{ width: "100%", padding: "0.5rem", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 4, color: "var(--text)" }}
                  />
                </div>
              </details>

              <p style={{ fontSize: "0.8rem", color: "var(--text2)", marginBottom: "0.8rem" }}>
                Anahtarlar .env veya Talon SQLite üzerinden okunur. Mevcut anahtarlar maskelenir; değiştirmek için yeni değer girin.
              </p>
              <button
                className="btn btn-primary"
                onClick={ayarlariKaydet}
                disabled={ayarlarKaydediliyor}
                style={{ width: "100%", padding: "0.6rem", fontSize: "0.95rem" }}
              >
                {ayarlarKaydediliyor ? "Kaydediliyor..." : "Ayarları Kaydet"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
