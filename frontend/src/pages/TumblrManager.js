import React, { useState, useEffect } from "react";
import API from "../api";

const STORAGE_KEY = "hive_tumblr_tokens";

function TumblrManager() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [token, setToken] = useState(null);
  const [message, setMessage] = useState("");
  const [callbackUrl, setCallbackUrl] = useState("http://localhost:4000");
  const [tab, setTab] = useState("otomatik");
  const [preview, setPreview] = useState(null);

  const [autoForm, setAutoForm] = useState({
    topic: "kuşadası gece hayatı",
    city: "Kuşadası",
    district: "",
    extra_keywords: "escort, gece hayatı, rehber",
    site_url: "https://www.balkutusu.com",
    blog_name: "balkutusucom.tumblr.com",
  });

  const [manualForm, setManualForm] = useState({
    blog_name: "balkutusucom.tumblr.com",
    title: "",
    content: "",
    tags: "",
  });

  const loadStatus = async () => {
    try {
      const res = await API.get("/api/tumblr/status");
      setStatus(res.data);
      if (res.data?.callback_url) setCallbackUrl(res.data.callback_url);
      const blogId = res.data?.blog_identifier || res.data?.blog_name;
      if (blogId) {
        setAutoForm((f) => ({ ...f, blog_name: blogId }));
        setManualForm((f) => ({ ...f, blog_name: blogId }));
      }
    } catch {
      setStatus(null);
    }
  };

  const restoreToken = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.oauth_token && parsed.oauth_token_secret) setToken(parsed);
      }
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    restoreToken();
    loadStatus();
    const params = new URLSearchParams(window.location.search);
    const oauthToken = params.get("oauth_token");
    const oauthVerifier = params.get("oauth_verifier");
    if (oauthToken && oauthVerifier) finishCallback(oauthToken, oauthVerifier);
  }, []);

  const finishCallback = async (oauthToken, oauthVerifier) => {
    setLoading(true);
    setMessage("");
    try {
      const res = await API.get("/api/tumblr/callback", {
        params: { oauth_token: oauthToken, oauth_verifier: oauthVerifier },
      });
      const access = res.data?.token;
      if (access) {
        setToken(access);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(access));
        setMessage("Tumblr hesabı başarıyla bağlandı.");
      }
      window.history.replaceState({}, document.title, window.location.pathname);
      await loadStatus();
    } catch (err) {
      setMessage("Callback hatası: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await API.get("/api/tumblr/connect");
      if (res.data?.callback_url) setCallbackUrl(res.data.callback_url);
      if (res.data?.authorize_url) window.location.href = res.data.authorize_url;
      else setMessage("Authorize URL alınamadı.");
    } catch (err) {
      setMessage("Bağlantı hatası: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      await API.post("/api/tumblr/disconnect");
    } catch {
      /* ignore */
    }
    setToken(null);
    localStorage.removeItem(STORAGE_KEY);
    setMessage("Tumblr bağlantısı kesildi.");
    await loadStatus();
    setLoading(false);
  };

  const buildPayload = (publish) => ({
    topic: autoForm.topic.trim(),
    city: autoForm.city.trim(),
    district: autoForm.district.trim(),
    site_url: autoForm.site_url.trim(),
    blog_name: autoForm.blog_name.trim(),
    extra_keywords: autoForm.extra_keywords
      ? autoForm.extra_keywords.split(",").map((t) => t.trim()).filter(Boolean)
      : [],
    publish,
  });

  const handlePreview = async () => {
    if (!autoForm.topic.trim()) {
      setMessage("Konu girin — ne hakkında yazılacağını belirtin.");
      return;
    }
    setLoading(true);
    setMessage("");
    setPreview(null);
    try {
      const res = await API.post("/api/tumblr/auto-post", buildPayload(false));
      setPreview(res.data);
      setMessage(
        `Önizleme hazır (${res.data.mode || "?"})` +
          (res.data.ai_ollama ? " — Ollama AI" : " — şablon+Talon")
      );
    } catch (err) {
      setMessage("Üretim hatası: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleAutoPost = async () => {
    if (!connected) {
      setMessage("Önce Tumblr hesabını bağla.");
      return;
    }
    if (!autoForm.topic.trim()) {
      setMessage("Konu girin.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const res = await API.post("/api/tumblr/auto-post", buildPayload(true));
      setPreview(res.data);
      setMessage(
        `Yayınlandı! Post ID: ${res.data.post_id || "—"} — ${res.data.title || ""}`
      );
    } catch (err) {
      setMessage("Yayın hatası: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleManualPost = async () => {
    if (!connected) {
      setMessage("Önce Tumblr hesabını bağla.");
      return;
    }
    if (!manualForm.content.trim()) {
      setMessage("İçerik boş olamaz.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const payload = {
        blog_name: manualForm.blog_name || status?.blog_name || "balkutumcom",
        title: manualForm.title,
        content: manualForm.content,
        tags: manualForm.tags
          ? manualForm.tags.split(",").map((t) => t.trim()).filter(Boolean)
          : [],
      };
      if (token?.oauth_token) {
        payload.oauth_token = token.oauth_token;
        payload.oauth_token_secret = token.oauth_token_secret;
      }
      const res = await API.post("/api/tumblr/post", payload);
      setMessage("Post gönderildi! ID: " + (res.data?.post_id || "—"));
    } catch (err) {
      setMessage("Post hatası: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const connected = Boolean(token?.oauth_token) || Boolean(status?.connected);

  return (
    <div style={{ padding: "1.25rem", maxWidth: 900, margin: "0 auto" }}>
      <h2 style={{ marginTop: 0 }}>📝 Tumblr Yöneticisi</h2>
      <p style={{ color: "var(--text2)", fontSize: "0.9rem" }}>
        Konuyu söyle — SEO/GEO uyumlu içerik üretilir ve Tumblr&apos;a otomatik yayınlanır.
        Callback URL: <code>{callbackUrl}</code>
      </p>

      <div className="btn-group" style={{ marginBottom: "1rem" }}>
        <button
          className={`btn ${tab === "otomatik" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setTab("otomatik")}
        >
          ⚡ Otomatik Yayın
        </button>
        <button
          className={`btn ${tab === "manuel" ? "btn-primary" : "btn-outline"}`}
          onClick={() => setTab("manuel")}
        >
          ✍️ Manuel
        </button>
        <button className="btn btn-outline" onClick={handleConnect} disabled={loading}>
          {connected ? "Yeniden Bağla" : "Tumblr Bağla"}
        </button>
        {connected && (
          <button className="btn btn-outline" onClick={handleDisconnect} disabled={loading}>
            Bağlantıyı Kes
          </button>
        )}
      </div>

      {connected && (
        <div className="status-badge aktif" style={{ marginBottom: "1rem" }}>
          Bağlı — blog: {status?.blog_identifier || status?.blog_name || autoForm.blog_name}
        </div>
      )}

      {message && (
        <div
          className={message.toLowerCase().includes("hata") ? "hata" : "sonuc"}
          style={{ marginBottom: "1rem", padding: "0.75rem" }}
        >
          {message}
        </div>
      )}

      {tab === "otomatik" && (
        <section className="storyforge-auto">
          <div className="form-grup">
            <label>Ne hakkında yazılsın? *</label>
            <input
              value={autoForm.topic}
              onChange={(e) => setAutoForm({ ...autoForm, topic: e.target.value })}
              placeholder="kuşadası gece hayatı, marina escort rehberi..."
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
            <div className="form-grup">
              <label>Şehir</label>
              <input
                value={autoForm.city}
                onChange={(e) => setAutoForm({ ...autoForm, city: e.target.value })}
              />
            </div>
            <div className="form-grup">
              <label>İlçe / Semt (opsiyonel)</label>
              <input
                value={autoForm.district}
                onChange={(e) => setAutoForm({ ...autoForm, district: e.target.value })}
                placeholder="Merkez, Kadınlar Denizi..."
              />
            </div>
          </div>
          <div className="form-grup">
            <label>Ek anahtar kelimeler (virgülle)</label>
            <input
              value={autoForm.extra_keywords}
              onChange={(e) => setAutoForm({ ...autoForm, extra_keywords: e.target.value })}
            />
          </div>
          <div className="form-grup">
            <label>Site linki (içerikte geçer)</label>
            <input
              value={autoForm.site_url}
              onChange={(e) => setAutoForm({ ...autoForm, site_url: e.target.value })}
            />
          </div>
          <div className="form-grup">
            <label>Tumblr blog</label>
            {status?.blogs?.length > 0 ? (
              <select
                value={autoForm.blog_name}
                onChange={(e) => setAutoForm({ ...autoForm, blog_name: e.target.value })}
              >
                {status.blogs.map((b) => (
                  <option key={b.uuid || b.identifier} value={b.identifier}>
                    {b.title || b.name} ({b.identifier})
                  </option>
                ))}
              </select>
            ) : (
              <input
                value={autoForm.blog_name}
                onChange={(e) => setAutoForm({ ...autoForm, blog_name: e.target.value })}
                placeholder="ornek.tumblr.com"
              />
            )}
          </div>
          <div className="btn-group" style={{ marginTop: "0.5rem" }}>
            <button className="btn btn-outline" onClick={handlePreview} disabled={loading}>
              👁️ Önizle
            </button>
            <button
              className="btn btn-primary"
              onClick={handleAutoPost}
              disabled={loading || !connected}
            >
              {loading ? "⏳" : "🚀 Üret ve Tumblr'a Yayınla"}
            </button>
          </div>
          <p style={{ fontSize: "0.8rem", color: "var(--text2)", marginTop: "0.75rem" }}>
            Talon GEO + Ollama ile içerik üretilir. Ollama kapalıysa Talon+şablon kullanılır.
          </p>
        </section>
      )}

      {tab === "manuel" && (
        <section>
          <div className="form-grup">
            <label>Blog</label>
            {status?.blogs?.length > 0 ? (
              <select
                value={manualForm.blog_name}
                onChange={(e) => setManualForm({ ...manualForm, blog_name: e.target.value })}
              >
                {status.blogs.map((b) => (
                  <option key={b.uuid || b.identifier} value={b.identifier}>
                    {b.title || b.name} ({b.identifier})
                  </option>
                ))}
              </select>
            ) : (
              <input
                value={manualForm.blog_name}
                onChange={(e) => setManualForm({ ...manualForm, blog_name: e.target.value })}
                placeholder="ornek.tumblr.com"
              />
            )}
          </div>
          <div className="form-grup">
            <label>Başlık</label>
            <input
              value={manualForm.title}
              onChange={(e) => setManualForm({ ...manualForm, title: e.target.value })}
            />
          </div>
          <div className="form-grup">
            <label>İçerik (HTML)</label>
            <textarea
              rows={10}
              style={{ width: "100%" }}
              value={manualForm.content}
              onChange={(e) => setManualForm({ ...manualForm, content: e.target.value })}
            />
          </div>
          <div className="form-grup">
            <label>Etiketler</label>
            <input
              value={manualForm.tags}
              onChange={(e) => setManualForm({ ...manualForm, tags: e.target.value })}
            />
          </div>
          <button className="btn btn-primary" onClick={handleManualPost} disabled={loading || !connected}>
            Gönder
          </button>
        </section>
      )}

      {preview && (
        <div style={{ marginTop: "1.5rem", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem" }}>
          <h3 style={{ marginTop: 0 }}>Önizleme — {preview.title}</h3>
          {preview.tags?.length > 0 && (
            <p style={{ fontSize: "0.85rem", color: "var(--text2)" }}>
              Etiketler: {preview.tags.join(", ")}
            </p>
          )}
          <div
            style={{ fontSize: "0.9rem", lineHeight: 1.6 }}
            dangerouslySetInnerHTML={{ __html: preview.content || preview.content_preview || "" }}
          />
        </div>
      )}
    </div>
  );
}

export default TumblrManager;
