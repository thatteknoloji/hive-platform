import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

export default function AnalyticsHub() {
  const [url, setUrl] = useState("https://balkutusu.com");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [basari, setBasari] = useState("");
  const [raporSonuc, setRaporSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [ozetSonuc, setOzetSonuc] = useState(null);
  const [gaStatus, setGaStatus] = useState(null);
  const [measurementId, setMeasurementId] = useState("");
  const [propertyId, setPropertyId] = useState("");
  const [realtime, setRealtime] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [topPages, setTopPages] = useState([]);
  const [chartDays, setChartDays] = useState(7);
  const [saFile, setSaFile] = useState(null);
  const [gtmId, setGtmId] = useState("");
  const [metaPixel, setMetaPixel] = useState("");
  const [gscVerify, setGscVerify] = useState("");

  const loadGaStatus = async () => {
    try {
      const res = await API.get("/api/analytics/ga-status");
      setGaStatus(res.data);
      if (res.data.measurement_id) setMeasurementId(res.data.measurement_id);
      if (res.data.property_id) setPropertyId(res.data.property_id);
    } catch {
      /* sessiz */
    }
  };

  const loadLiveData = useCallback(async () => {
    if (!gaStatus?.data_api?.ready) return;
    try {
      const [rt, ch, tp] = await Promise.all([
        API.get("/api/analytics/ga-realtime"),
        API.get(`/api/analytics/ga-chart?days=${chartDays}`),
        API.get("/api/analytics/ga-top-pages?limit=8"),
      ]);
      setRealtime(rt.data);
      setChartData(ch.data?.data || []);
      setTopPages(tp.data?.pages || []);
    } catch {
      /* sessiz */
    }
  }, [gaStatus?.data_api?.ready, chartDays]);

  useEffect(() => {
    loadGaStatus();
  }, []);

  useEffect(() => {
    loadLiveData();
    if (!gaStatus?.data_api?.ready) return undefined;
    const t = setInterval(loadLiveData, 60000);
    return () => clearInterval(t);
  }, [gaStatus?.data_api?.ready, loadLiveData]);

  const buildHeadInjections = () => {
    const items = [
      {
        id: "ga4",
        name: "Google Analytics 4",
        provider: "google_analytics",
        enabled: !!measurementId.trim(),
        config: { measurement_id: measurementId.trim().toUpperCase() },
      },
    ];
    if (gtmId.trim()) {
      items.push({
        id: "gtm",
        name: "Google Tag Manager",
        provider: "google_tag_manager",
        enabled: true,
        config: { container_id: gtmId.trim().toUpperCase() },
      });
    }
    if (metaPixel.trim()) {
      items.push({
        id: "meta",
        name: "Meta Pixel",
        provider: "meta_pixel",
        enabled: true,
        config: { pixel_id: metaPixel.trim() },
      });
    }
    if (gscVerify.trim()) {
      items.push({
        id: "gsc_verify",
        name: "Google Site Verification",
        provider: "google_site_verification",
        enabled: true,
        config: { token: gscVerify.trim() },
      });
    }
    return items;
  };

  const handleHeadInjectSave = async () => {
    setHata("");
    setBasari("");
    setLoading((l) => ({ ...l, head: true }));
    try {
      const res = await API.put("/api/wp/head-injections", { injections: buildHeadInjections() });
      if (!res.data?.success) throw new Error(res.data?.error || "Kayıt başarısız");
      setBasari("Head kodları tüm sitelere yazıldı");
    } catch (e) {
      setHata(e.response?.data?.error || e.response?.data?.detail || e.message);
    }
    setLoading((l) => ({ ...l, head: false }));
  };

  const handleGaSetup = async () => {
    if (!measurementId.trim()) {
      setHata("GA4 Measurement ID gerekli (G-...)");
      return;
    }
    setHata("");
    setBasari("");
    setLoading((l) => ({ ...l, ga: true }));
    try {
      const res = await API.post("/api/analytics/ga-setup", {
        measurement_id: measurementId.trim(),
        property_id: propertyId.trim(),
        sync_wordpress: true,
      });
      try {
        await API.put("/api/wp/head-injections", { injections: buildHeadInjections() });
      } catch {
        /* WP bağlı değilse sadece .env kaydı yeterli */
      }
      setBasari((res.data.message || "GA4 bağlandı") + " — head kodları güncellendi");
      await loadGaStatus();
    } catch (e) {
      setHata(e.response?.data?.detail || e.message);
    }
    setLoading((l) => ({ ...l, ga: false }));
  };

  const handleSaUpload = async () => {
    if (!saFile) {
      setHata("Service account JSON dosyası seçin");
      return;
    }
    setHata("");
    setBasari("");
    setLoading((l) => ({ ...l, sa: true }));
    try {
      const fd = new FormData();
      fd.append("file", saFile);
      const res = await API.post("/api/analytics/ga-credentials", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      let msg = res.data.message || "Kaydedildi";
      if (res.data.next_step) msg += ` — ${res.data.next_step}`;
      if (res.data.property_id) setPropertyId(res.data.property_id);
      setBasari(msg);
      setSaFile(null);
      await loadGaStatus();
      await loadLiveData();
    } catch (e) {
      setHata(e.response?.data?.detail || e.message);
    }
    setLoading((l) => ({ ...l, sa: false }));
  };

  const handleDiscover = async () => {
    setHata("");
    setBasari("");
    setLoading((l) => ({ ...l, discover: true }));
    try {
      const res = await API.post("/api/analytics/ga-discover");
      setPropertyId(res.data.property_id || "");
      setBasari(res.data.message || `Property ID: ${res.data.property_id}`);
      await loadGaStatus();
      await loadLiveData();
    } catch (e) {
      setHata(e.response?.data?.detail || e.message);
    }
    setLoading((l) => ({ ...l, discover: false }));
  };

  const handleRapor = async () => {
    if (!url) { setHata("URL gerekli"); return; }
    setHata(""); setLoading((l) => ({ ...l, rapor: true }));
    try { const res = await API.post("/api/analytics", { url }); setRaporSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading((l) => ({ ...l, rapor: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading((l) => ({ ...l, liste: true }));
    try { const res = await API.get("/api/analytics/liste"); setListeSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading((l) => ({ ...l, liste: false }));
  };

  const handleOzet = async () => {
    setHata(""); setLoading((l) => ({ ...l, ozet: true }));
    try { const res = await API.get("/api/analytics/ozet"); setOzetSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading((l) => ({ ...l, ozet: false }));
  };

  const renderTable = (data) => {
    if (!data) return null;
    const rows = Array.isArray(data) ? data : data.sayfalar || data.raporlar || [data];
    return (
      <table className="table">
        <thead>
          <tr>
            <th>Sayfa</th>
            <th>Görüntülenme</th>
            <th>Hemen Çıkma</th>
            <th>Ort. Süre</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{r.sayfa || r.url || r.page || "-"}</td>
              <td>{r.goruntulenme ?? r.page_views ?? r.views ?? r.sayfa_goruntuleme ?? "-"}</td>
              <td>{r.hemen_cikma ?? r.bounce_rate ?? r.bounce ?? r.hemen_cikma_orani ?? "%-"}</td>
              <td>{r.ortalama_sure ?? r.session_duration ?? r.sure ?? r.ortalama_oturum_suresi_sn ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  const liveReady = gaStatus?.data_api?.ready;
  const trackingOnly = gaStatus?.site_tracking_active && !liveReady;

  return (
    <div>
      <div className="header">
        <div className="icon">📊</div>
        <div className="info">
          <h2>Analytics Hub</h2>
          <p>Google Analytics 4 bağlantısı ve canlı trafik grafikleri</p>
        </div>
      </div>

      {/* ID değiştirme rehberi */}
      <section className="storyforge-auto" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0 }}>🔄 Measurement ID değiştirmek</h3>
        <p style={{ fontSize: "0.88rem", color: "var(--text2)", lineHeight: 1.6 }}>
          İleride GA4 kimliği değişirse üç yoldan biri yeterli — hepsi aynı <code>GA4_MEASUREMENT_ID</code> değerini günceller:
        </p>
        <ol style={{ fontSize: "0.88rem", lineHeight: 1.7, color: "var(--text2)", paddingLeft: "1.2rem" }}>
          <li>
            <strong>HIVE Panel → Analytics Hub</strong> → Measurement ID alanına yeni <code>G-...</code> yapıştır →
            {" "}<strong>Siteye Bağla</strong> (WP Manager bağlıysa WordPress&apos;e de yazar)
          </li>
          <li>
            <strong>API Settings</strong> → <em>GA4 Measurement ID</em> → Kaydet
          </li>
          <li>
            <code>backend/.env</code> → <code>GA4_MEASUREMENT_ID=G-...</code> satırını düzenle, backend&apos;i yeniden başlat
          </li>
        </ol>
      </section>

      {/* Head Inject — tüm siteler */}
      <section className="storyforge-auto" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0 }}>🧩 Head Inject — Tüm Siteler</h3>
        <p style={{ fontSize: "0.88rem", color: "var(--text2)", lineHeight: 1.6 }}>
          Google, Meta ve diğer servislerin istediği kodlar otomatik olarak her sayfanın
          <code> &lt;head&gt;</code> bölümünün <strong>hemen altına</strong> eklenir (multisite dahil).
        </p>
        <div className="storyforge-meta-row">
          <div>
            <label className="storyforge-label">GTM Container (opsiyonel)</label>
            <input className="storyforge-input" placeholder="GTM-XXXX" value={gtmId} onChange={(e) => setGtmId(e.target.value)} />
          </div>
          <div>
            <label className="storyforge-label">Meta Pixel ID (opsiyonel)</label>
            <input className="storyforge-input" placeholder="123456789" value={metaPixel} onChange={(e) => setMetaPixel(e.target.value)} />
          </div>
          <div>
            <label className="storyforge-label">Google Site Verification (opsiyonel)</label>
            <input className="storyforge-input" placeholder="meta content token" value={gscVerify} onChange={(e) => setGscVerify(e.target.value)} />
          </div>
        </div>
        <button className="btn btn-outline" onClick={handleHeadInjectSave} disabled={loading.head}>
          {loading.head ? "⏳" : "📡 Tüm Sitelere Head Kodu Gönder"}
        </button>
      </section>

      {/* Kurulum */}
      <section className="storyforge-auto" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0 }}>🔗 Google Analytics 4 Kurulumu</h3>
        <ol style={{ fontSize: "0.88rem", lineHeight: 1.6, color: "var(--text2)", paddingLeft: "1.2rem" }}>
          <li>
            <a href="https://analytics.google.com/" target="_blank" rel="noreferrer">analytics.google.com</a>
            {" "}→ Yönetici → Mülk oluştur → <strong>balkutusu.com</strong>
          </li>
          <li>Veri akışı → Web → URL: <code>https://balkutusu.com</code></li>
          <li><strong>Measurement ID</strong> kopyala (ör. <code>G-J1DKY19WRL</code>)</li>
          <li>Aşağıya yapıştır → <strong>Siteye Bağla</strong> (WordPress temasına gtag ekler)</li>
        </ol>

        {gaStatus && (
          <div className="storyforge-stats" style={{ marginBottom: "1rem", flexWrap: "wrap" }}>
            <span className={gaStatus.site_tracking_active ? "sf-ok" : "sf-warn"}>
              Site takibi: {gaStatus.site_tracking_active ? "Aktif" : "Kapalı"}
            </span>
            <span>WP: {gaStatus.wp_connected ? "Bağlı" : "Bağlı değil"}</span>
            <span className={liveReady ? "sf-ok" : "sf-warn"}>
              Panel grafikleri: {liveReady ? "Canlı" : "Kurulum gerekli"}
            </span>
            {gaStatus.wp_ga4_measurement_id && (
              <span>WP GA ID: {gaStatus.wp_ga4_measurement_id}</span>
            )}
          </div>
        )}

        <div className="storyforge-meta-row">
          <div>
            <label className="storyforge-label">GA4 Measurement ID</label>
            <input
              className="storyforge-input"
              placeholder="G-XXXXXXXXXX"
              value={measurementId}
              onChange={(e) => setMeasurementId(e.target.value)}
            />
          </div>
          <div>
            <label className="storyforge-label">Property ID (otomatik veya manuel)</label>
            <input
              className="storyforge-input"
              placeholder="JSON yükle → otomatik bulunur"
              value={propertyId}
              onChange={(e) => setPropertyId(e.target.value)}
            />
            <p style={{ fontSize: "0.75rem", color: "var(--text2)", margin: "0.25rem 0 0" }}>
              Akış kimliği <code>15020509258</code> değil — mülk kimliği JSON ile otomatik bulunur
            </p>
          </div>
        </div>
        <div className="btn-group">
          <button className="btn btn-primary" onClick={handleGaSetup} disabled={loading.ga}>
            {loading.ga ? "⏳" : "🚀 Siteye Bağla"}
          </button>
          <a className="btn btn-outline" href="https://analytics.google.com/" target="_blank" rel="noreferrer">
            GA4 Paneli Aç
          </a>
          <a className="btn btn-outline" href="https://analytics.google.com/analytics/web/#/p/realtime" target="_blank" rel="noreferrer">
            Gerçek Zamanlı
          </a>
        </div>
      </section>

      {/* Data API kurulumu */}
      <section className="storyforge-auto" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0 }}>📈 Panelde canlı grafikler (Data API)</h3>
        <p style={{ fontSize: "0.88rem", color: "var(--text2)", lineHeight: 1.6 }}>
          Site takibi Measurement ID ile çalışır. HIVE panelinde grafik görmek için ek olarak Property ID + Google service account gerekir.
        </p>
        <ol style={{ fontSize: "0.85rem", lineHeight: 1.65, color: "var(--text2)", paddingLeft: "1.2rem" }}>
          <li>
            <a href="https://console.cloud.google.com/iam-admin/serviceaccounts" target="_blank" rel="noreferrer">Google Cloud</a>
            {" "}→ Proje seç/oluştur → Service account → JSON anahtar indir
          </li>
          <li>
            <a href="https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com" target="_blank" rel="noreferrer">Analytics Data API</a>
            {" "}+{" "}
            <a href="https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com" target="_blank" rel="noreferrer">Analytics Admin API</a>
            {" "}→ Etkinleştir
          </li>
          <li>GA4 → Yönetici → Mülk erişimi → <code>@...iam.gserviceaccount.com</code> e-postasını <strong>Görüntüleyici</strong> ekle</li>
          <li>JSON dosyasını aşağıdan yükle → Property ID <strong>otomatik</strong> bulunur (<code>G-J1DKY19WRL</code>)</li>
        </ol>

        {gaStatus?.data_api?.hint && !liveReady && (
          <div className="hata" style={{ marginBottom: "0.75rem", fontSize: "0.85rem" }}>
            {gaStatus.data_api.hint}
          </div>
        )}

        <div className="storyforge-meta-row" style={{ alignItems: "flex-end" }}>
          <div>
            <label className="storyforge-label">Service Account JSON</label>
            <input
              type="file"
              accept=".json,application/json"
              onChange={(e) => setSaFile(e.target.files?.[0] || null)}
            />
          </div>
          <button className="btn btn-outline" onClick={handleSaUpload} disabled={loading.sa || !saFile}>
            {loading.sa ? "⏳" : "📁 JSON Yükle"}
          </button>
          <button
            className="btn btn-primary"
            onClick={handleDiscover}
            disabled={loading.discover || !gaStatus?.data_api?.service_account_configured}
          >
            {loading.discover ? "⏳" : "🔍 Property ID Otomatik Bul"}
          </button>
        </div>
        {gaStatus?.data_api?.service_account_configured && (
          <p style={{ fontSize: "0.8rem", color: "var(--olive2)", marginTop: "0.5rem" }}>
            ✓ Service account yapılandırıldı
          </p>
        )}
      </section>

      {basari && <div className="basari" style={{ color: "var(--olive2)", marginBottom: "0.75rem" }}>{basari}</div>}
      {hata && <div className="hata">{hata}</div>}

      {/* Canlı dashboard */}
      {liveReady && (
        <section style={{ marginBottom: "2rem" }}>
          <h3>⚡ Canlı trafik</h3>
          <div className="storyforge-stats" style={{ marginBottom: "1rem" }}>
            <span className="sf-ok">
              Aktif kullanıcı: {realtime?.active_users ?? "—"}
            </span>
            <span>
              Sayfa görüntüleme (30 dk): {realtime?.page_views_30min ?? "—"}
            </span>
            <button className="btn btn-outline" style={{ padding: "0.2rem 0.6rem", fontSize: "0.8rem" }} onClick={loadLiveData}>
              Yenile
            </button>
          </div>

          {realtime?.countries?.length > 0 && (
            <p style={{ fontSize: "0.85rem", color: "var(--text2)" }}>
              Ülkeler: {realtime.countries.map((c) => `${c.country} (${c.activeUsers})`).join(", ")}
            </p>
          )}

          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                className={`btn ${chartDays === d ? "btn-primary" : "btn-outline"}`}
                style={{ padding: "0.25rem 0.75rem", fontSize: "0.8rem" }}
                onClick={() => setChartDays(d)}
              >
                {d} gün
              </button>
            ))}
          </div>

          {chartData.length > 0 ? (
            <div style={{ width: "100%", height: 280, marginBottom: "1.5rem" }}>
              <ResponsiveContainer>
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="sessions" name="Oturum" stroke="#8fbc8f" fill="rgba(143,188,143,0.25)" />
                  <Area type="monotone" dataKey="users" name="Kullanıcı" stroke="#c4a35a" fill="rgba(196,163,90,0.2)" />
                  <Area type="monotone" dataKey="pageviews" name="Sayfa görüntüleme" stroke="#7eb8da" fill="rgba(126,184,218,0.15)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p style={{ color: "var(--text2)", fontSize: "0.85rem" }}>Grafik verisi yükleniyor veya henüz veri yok.</p>
          )}

          {topPages.length > 0 && (
            <>
              <h4 style={{ marginTop: "1rem" }}>En çok görüntülenen sayfalar (7 gün)</h4>
              <table className="table">
                <thead>
                  <tr>
                    <th>Sayfa</th>
                    <th>Görüntülenme</th>
                    <th>Kullanıcı</th>
                  </tr>
                </thead>
                <tbody>
                  {topPages.map((p, i) => (
                    <tr key={i}>
                      <td><code style={{ fontSize: "0.8rem" }}>{p.path}</code></td>
                      <td>{p.views}</td>
                      <td>{p.users}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>
      )}

      {trackingOnly && (
        <section className="storyforge-auto" style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ marginTop: 0 }}>👁 Trafik şu an nerede?</h3>
          <p style={{ fontSize: "0.88rem", color: "var(--text2)", lineHeight: 1.6 }}>
            Site takibi aktif — ziyaretçiler GA4&apos;e gidiyor. Panel grafikleri için yukarıda Property ID + service account JSON tamamlayın.
            Hızlı kontrol için{" "}
            <a href="https://analytics.google.com/analytics/web/#/p/realtime" target="_blank" rel="noreferrer">
              analytics.google.com → Gerçek zamanlı
            </a>
            {" "}yeterli.
          </p>
        </section>
      )}

      <hr className="storyforge-divider" />

      <h3>Simülasyon Raporları (eski modül)</h3>
      <div className="form-grup">
        <label>Site URL</label>
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://balkutusu.com" />
      </div>
      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleRapor} disabled={loading.rapor}>
          {loading.rapor ? "⏳" : "📊 Rapor Al"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Tüm Raporlar"}
        </button>
        <button className="btn btn-outline" onClick={handleOzet} disabled={loading.ozet}>
          {loading.ozet ? "⏳" : "📈 Özet"}
        </button>
      </div>
      {(raporSonuc || listeSonuc) && <div className="sonuc">{renderTable(raporSonuc || listeSonuc)}</div>}
      {ozetSonuc && (
        <div className="sonuc">
          {Object.entries(ozetSonuc).map(([k, v]) => (
            <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}
