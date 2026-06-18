import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

const API_PREFIX = "/api/medium-bot";

function apiError(e) {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : e?.message || "İstek başarısız";
}

export default function MediumBot() {
  const [health, setHealth] = useState(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("seo, hive");
  const [articleUrl, setArticleUrl] = useState("");
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activity, setActivity] = useState(null);

  const refreshHealth = useCallback(async () => {
    try {
      const r = await API.get(`${API_PREFIX}/health`);
      setHealth(r.data);
    } catch (e) {
      setHealth({ connected: false, error: apiError(e) });
    }
  }, []);

  useEffect(() => { refreshHealth(); }, [refreshHealth]);

  const publish = async () => {
    if (!title.trim() || !content.trim()) {
      setError("Başlık ve içerik gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const tagList = tags.split(",").map((t) => t.trim()).filter(Boolean);
      const r = await API.post(`${API_PREFIX}/publish`, { title, content, tags: tagList });
      setResult(r.data);
      refreshHealth();
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const postComment = async () => {
    if (!articleUrl.trim() || !comment.trim()) {
      setError("Makale URL ve yorum gerekli");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const r = await API.post(`${API_PREFIX}/comment`, { article_url: articleUrl, comment_text: comment });
      setResult(r.data);
    } catch (e) {
      setError(apiError(e));
    } finally {
      setLoading(false);
    }
  };

  const loadActivity = async () => {
    try {
      const r = await API.get(`${API_PREFIX}/activity`);
      setActivity(r.data);
    } catch (e) {
      setError(apiError(e));
    }
  };

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">✍️</div>
        <div className="info">
          <h2>Medium Bot</h2>
          <p>Medium Integration API — yazı yayınla ve makaleye response gönder.</p>
        </div>
      </div>

      <div className="hive-alert" style={{ background: "rgba(120,0,0,0.12)", border: "1px solid #8b0000", padding: "0.75rem", borderRadius: 8, marginBottom: "1rem" }}>
        🏴‍☠️ MEDIUM_TOKEN gerekli (.env). Medium kullanım şartlarına uyun.
      </div>

      {health && (
        <div style={{ marginBottom: "1rem", fontSize: "0.85rem", color: health.connected ? "var(--success)" : "var(--danger)" }}>
          {health.connected ? `✓ Bağlı — @${health.username || "medium"}` : `✗ ${health.error || "Medium bağlantısı kurulmamış"}`}
        </div>
      )}

      {error && <div className="hata">{error}</div>}

      <div className="talon-form">
        <h3>Yazı Yayınla</h3>
        <div className="form-grup">
          <label>Başlık</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Yazı başlığı" />
        </div>
        <div className="form-grup">
          <label>İçerik (Markdown)</label>
          <textarea rows={8} value={content} onChange={(e) => setContent(e.target.value)} placeholder="Markdown içerik..." style={{ width: "100%" }} />
        </div>
        <div className="form-grup">
          <label>Etiketler (virgülle)</label>
          <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="seo, marketing" />
        </div>
        <button className="btn btn-primary" onClick={publish} disabled={loading}>
          {loading ? "Yayınlanıyor…" : "📤 Yayınla"}
        </button>
      </div>

      <div className="talon-form" style={{ marginTop: "1.5rem" }}>
        <h3>Makaleye Yorum (Response Post)</h3>
        <div className="form-grup">
          <label>Makale URL</label>
          <input value={articleUrl} onChange={(e) => setArticleUrl(e.target.value)} placeholder="https://medium.com/@user/post-id" />
        </div>
        <div className="form-grup">
          <label>Yorum</label>
          <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} style={{ width: "100%" }} />
        </div>
        <button className="btn btn-outline" onClick={postComment} disabled={loading}>
          💬 Yorum Gönder
        </button>
      </div>

      <div style={{ marginTop: "1rem" }}>
        <button className="btn btn-outline" onClick={loadActivity}>📋 Aktivite</button>
      </div>

      {result && (
        <pre style={{ marginTop: "1rem", fontSize: "0.8rem", whiteSpace: "pre-wrap", maxHeight: 300, overflow: "auto" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
      {activity && (
        <pre style={{ marginTop: "1rem", fontSize: "0.8rem", whiteSpace: "pre-wrap", maxHeight: 300, overflow: "auto" }}>
          {JSON.stringify(activity, null, 2)}
        </pre>
      )}
    </div>
  );
}
