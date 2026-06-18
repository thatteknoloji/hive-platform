import React, { useState, useEffect } from "react";
import API from "../api";
import { MODULE_API_MAP } from "../apiConfig";
import { ProviderSettingsPanel } from "../components/ProviderSelector";

const SERVICES = [
  "serpapi", "github", "namecheap_user", "namecheap_key",
  "praw_client_id", "praw_client_secret", "openai", "anthropic",
  "gemini", "groq", "huggingface", "perplexity", "btk_ihbar",
  "proxy", "selenium", "gsc_client_id", "gsc_client_secret",
  "tumblr_consumer_key", "tumblr_consumer_secret", "cloudflare",
  "ga4_measurement_id", "ga4_property_id", "gsc_site_url",
  "google_client_id", "google_client_secret", "google_refresh_token", "blogger_default_blog_id",
  "dataforseo_login", "dataforseo_password", "vps_ssh_pass",
];

export default function ApiSettings() {
  const [keys, setKeys] = useState({});
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [basari, setBasari] = useState("");
  const [statusTest, setStatusTest] = useState({ serpapi: null, github: null });
  const [statusTestLoading, setStatusTestLoading] = useState({ serpapi: false, github: false });

  useEffect(() => {
    handleFetch();
  }, []);

  const handleFetch = async () => {
    setHata(""); setLoading(l => ({ ...l, fetch: true }));
    try {
      const res = await API.get("/api/settings/apikeys");
      const data = res.data?.sonuc || res.data;
      const initial = {};
      SERVICES.forEach(s => { initial[s] = data[s] || ""; });
      setKeys(initial);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, fetch: false }));
  };

  const handleSave = async () => {
    setHata(""); setBasari(""); setLoading(l => ({ ...l, save: true }));
    try {
      const payload = {};
      SERVICES.forEach(s => { payload[s] = keys[s] || ""; });
      const res = await API.post("/api/settings/apikeys", payload);
      setBasari("API anahtarları başarıyla kaydedildi.");
      setTimeout(() => setBasari(""), 3000);
    } catch (err) { setHata("Kaydetme hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, save: false }));
  };

  const testService = async (service) => {
    setStatusTestLoading(p => ({ ...p, [service]: true }));
    setStatusTest(p => ({ ...p, [service]: null }));
    try {
      if (service === "serpapi") {
        const res = await API.post("/api/search", { query: "test", num: 1 });
        setStatusTest(p => ({ ...p, serpapi: res.data?.sonuclar ? "✅ Çalışıyor" : "⚠️ Yanıt alındı ama sonuç yok" }));
      } else if (service === "github") {
        const res = await API.get("/api/github/repos");
        setStatusTest(p => ({ ...p, github: res.data?.repolar ? `✅ Çalışıyor (${res.data.repolar.length} repo)` : "⚠️ Yanıt alındı" }));
      }
    } catch (err) {
      setStatusTest(p => ({ ...p, [service]: "❌ Hata: " + (err.response?.data?.detail || err.message) }));
    }
    setStatusTestLoading(p => ({ ...p, [service]: false }));
  };

  const setKey = (service, value) => {
    setKeys(prev => ({ ...prev, [service]: value }));
  };

  const LABELS = {
    serpapi: "SERP API",
    github: "GitHub Token",
    namecheap_user: "Namecheap Kullanıcı",
    namecheap_key: "Namecheap API Key",
    praw_client_id: "Reddit Client ID",
    praw_client_secret: "Reddit Client Secret",
    openai: "OpenAI API Key",
    anthropic: "Anthropic API Key",
    gemini: "Gemini API Key",
    groq: "Groq API Key",
    huggingface: "HuggingFace Token",
    perplexity: "Perplexity API Key",
    btk_ihbar: "BTK İhbar",
    proxy: "Proxy",
    selenium: "Selenium",
    gsc_client_id: "GSC Client ID",
    gsc_client_secret: "GSC Client Secret",
    tumblr_consumer_key: "Tumblr Consumer Key",
    tumblr_consumer_secret: "Tumblr Consumer Secret",
    cloudflare: "Cloudflare API Token",
    ga4_measurement_id: "GA4 Measurement ID (G-...)",
    ga4_property_id: "GA4 Property ID (sayısal)",
    gsc_site_url: "Search Console Site URL",
    google_client_id: "Google OAuth Client ID (Blogger)",
    google_client_secret: "Google OAuth Client Secret",
    google_refresh_token: "Google Refresh Token",
    blogger_default_blog_id: "Blogger Default Blog ID",
    dataforseo_login: "DataForSEO Login (email)",
    dataforseo_password: "DataForSEO Password",
  };

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">🔑</div>
        <div className="info">
          <h2>API Ayarları – Servis Anahtarları</h2>
          <p>Tüm entegrasyon servislerinin API anahtarlarını buradan yönetin.</p>
        </div>
      </div>

      <div style={{ marginTop: "1rem", marginBottom: "1.5rem" }}>
        <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>🔌 API Durum Kontrolü</h3>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", flex: 1, minWidth: 250 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <span style={{ fontWeight: 600 }}>🔍 SERPAPI</span>
              <button className="btn btn-sm btn-outline" onClick={() => testService("serpapi")} disabled={statusTestLoading.serpapi}>
                {statusTestLoading.serpapi ? "⏳" : "🔄 Test"}
              </button>
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text2)" }}>
              {MODULE_API_MAP.search}, {MODULE_API_MAP.trends}, {MODULE_API_MAP.news}, {MODULE_API_MAP.scraper}
            </div>
            {statusTest.serpapi && (
              <div style={{ marginTop: "0.4rem", fontSize: "0.85rem", color: statusTest.serpapi.includes("✅") ? "var(--green)" : "var(--red)" }}>
                {statusTest.serpapi}
              </div>
            )}
          </div>
          <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", flex: 1, minWidth: 250 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <span style={{ fontWeight: 600 }}>🐙 GitHub</span>
              <button className="btn btn-sm btn-outline" onClick={() => testService("github")} disabled={statusTestLoading.github}>
                {statusTestLoading.github ? "⏳" : "🔄 Test"}
              </button>
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text2)" }}>
              {MODULE_API_MAP.github_integration}, {MODULE_API_MAP.version_control}, {MODULE_API_MAP.backup}, {MODULE_API_MAP.docs_automation}
            </div>
            {statusTest.github && (
              <div style={{ marginTop: "0.4rem", fontSize: "0.85rem", color: statusTest.github.includes("✅") ? "var(--green)" : "var(--red)" }}>
                {statusTest.github}
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{ marginTop: "2rem", paddingTop: "1.5rem", borderTop: "1px solid var(--border)" }}>
        <ProviderSettingsPanel />
      </div>

      {loading.fetch ? (
        <p style={{ color: "var(--text2)", marginTop: "1rem" }}>Anahtarlar yükleniyor...</p>
      ) : (
        <div style={{ marginTop: "1rem", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))", gap: "0.8rem" }}>
          {SERVICES.map(service => (
            <div key={service} style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "0.8rem" }}>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.3rem", color: "var(--text)" }}>
                {LABELS[service] || service}
              </label>
              <input
                type={service.includes("secret") || service.includes("key") || service.includes("token") || service === "proxy" ? "password" : "text"}
                value={keys[service] || ""}
                onChange={e => setKey(service, e.target.value)}
                placeholder={LABELS[service] || service}
                style={{ width: "100%" }}
              />
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: "1.5rem" }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={loading.save || loading.fetch}>
          {loading.save ? "⏳ Kaydediliyor..." : "💾 Kaydet"}
        </button>
        <button className="btn btn-outline" onClick={handleFetch} disabled={loading.fetch} style={{ marginLeft: "0.6rem" }}>
          {loading.fetch ? "⏳" : "🔄 Yenile"}
        </button>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}
      {basari && <div className="sonuc" style={{ marginTop: "1rem", color: "var(--green)" }}>{basari}</div>}
    </div>
  );
}
