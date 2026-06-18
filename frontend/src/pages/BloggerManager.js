import React, { useState, useEffect, useCallback } from "react";
import API from "../api";


export default function BloggerManager() {
  const [status, setStatus] = useState(null);
  const [posts, setPosts] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState("yeni");
  const [postForm, setPostForm] = useState({
    title: "",
    content: "",
    labels: "",
    publish: true,
  });

  const blogId = status?.default_blog_id || status?.blogs?.[0]?.id || "";
  const blogUrl = status?.blogs?.[0]?.url || "";
  const connected = status?.connected;

  const refresh = useCallback(async () => {
    try {
      const st = await API.get("/api/blogger/status");
      setStatus(st.data);
      if (st.data?.connected) {
        const bid = st.data.default_blog_id || st.data.blogs?.[0]?.id || "";
        const live = await API.get("/api/blogger/posts", {
          params: { blog_id: bid, status: "live", limit: 15 },
        });
        setPosts(live.data.posts || []);
        try {
          const draft = await API.get("/api/blogger/posts", {
            params: { blog_id: bid, status: "draft", limit: 10 },
          });
          setDrafts(draft.data.posts || []);
        } catch (draftErr) {
          setDrafts([]);
          setError(draftErr.response?.data?.detail || draftErr.message);
        }
      } else if (st.data?.configured) {
        setError(st.data.error || "Google refresh token geçersiz — API Settings'ten yenileyin");
      }
    } catch (e) {
      setStatus({ connected: false, configured: false });
      setError(e.response?.data?.detail || e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleCreate = async (asDraft = false) => {
    if (!postForm.title.trim()) {
      setError("Başlık gerekli");
      return;
    }
    if (!postForm.content.trim()) {
      setError("İçerik gerekli");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("/api/blogger/post", {
        title: postForm.title,
        content: postForm.content,
        blog_id: blogId,
        labels: postForm.labels
          ? postForm.labels.split(",").map((t) => t.trim()).filter(Boolean)
          : [],
        publish: asDraft ? false : postForm.publish,
      });
      setMessage(
        (res.data.message || "Kaydedildi") +
          (res.data.url ? ` — ${res.data.url}` : "")
      );
      setPostForm({ title: "", content: "", labels: "", publish: true });
      await refresh();
      setTab("yazilar");
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const handlePublish = async (postId) => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post(`/api/blogger/publish/${postId}`, null, {
        params: { blog_id: blogId },
      });
      setMessage(res.data.message || "Yayınlandı");
      await refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  const handleDelete = async (postId) => {
    if (!window.confirm("Bu yazı silinsin mi?")) return;
    setLoading(true);
    setError("");
    try {
      await API.delete(`/api/blogger/post/${postId}`, { params: { blog_id: blogId } });
      setMessage("Yazı silindi");
      await refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: "1.25rem", maxWidth: 900, margin: "0 auto" }}>
      <div className="header" style={{ marginBottom: "1.25rem" }}>
        <div className="icon">📰</div>
        <div className="info">
          <h2 style={{ margin: 0 }}>Blogger Yöneticisi</h2>
          <p style={{ margin: "0.25rem 0 0", color: "var(--text2)" }}>
            Google Blogger&apos;a yazı oluştur, taslak kaydet veya doğrudan yayınla
          </p>
        </div>
      </div>

      {connected ? (
        <div className="storyforge-stats" style={{ marginBottom: "1rem" }}>
          <span className="sf-ok">Bağlı</span>
          {status.blogs?.map((b) => (
            <span key={b.id}>
              {b.name} — <a href={b.url} target="_blank" rel="noreferrer">{b.url}</a>
            </span>
          ))}
        </div>
      ) : (
        <div className="hata" style={{ marginBottom: "1rem" }}>
          Blogger bağlantısı yok. API Settings → GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
          GOOGLE_REFRESH_TOKEN kontrol edin.
          {status?.configured && status?.error ? ` (${status.error})` : ""}
        </div>
      )}

      {message && (
        <div className="basari" style={{ marginBottom: "0.75rem", color: "var(--olive2)" }}>
          {message}
        </div>
      )}
      {error && <div className="hata" style={{ marginBottom: "0.75rem" }}>{error}</div>}

      <div className="btn-group" style={{ marginBottom: "1rem" }}>
        {["yeni", "yazilar", "taslaklar"].map((t) => (
          <button
            key={t}
            className={`btn ${tab === t ? "btn-primary" : "btn-outline"}`}
            onClick={() => setTab(t)}
          >
            {t === "yeni" ? "✍️ Yeni Yazı" : t === "yazilar" ? "📋 Yayında" : "📝 Taslaklar"}
          </button>
        ))}
        <button className="btn btn-outline" onClick={refresh} disabled={loading}>
          🔄 Yenile
        </button>
        {blogUrl && (
          <a className="btn btn-outline" href={blogUrl} target="_blank" rel="noreferrer">
            Blogu Aç
          </a>
        )}
      </div>

      {tab === "yeni" && (
        <section className="storyforge-auto">
          <div className="form-grup">
            <label>Başlık</label>
            <input
              value={postForm.title}
              onChange={(e) => setPostForm({ ...postForm, title: e.target.value })}
              placeholder="Yazı başlığı"
            />
          </div>
          <div className="form-grup">
            <label>İçerik (HTML desteklenir)</label>
            <textarea
              rows={14}
              style={{ width: "100%" }}
              value={postForm.content}
              onChange={(e) => setPostForm({ ...postForm, content: e.target.value })}
              placeholder="<p>Kuşadası gece hayatı hakkında...</p>"
            />
          </div>
          <div className="form-grup">
            <label>Etiketler (virgülle)</label>
            <input
              value={postForm.labels}
              onChange={(e) => setPostForm({ ...postForm, labels: e.target.value })}
              placeholder="kusadasi, escort, gece hayati"
            />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <input
              type="checkbox"
              checked={postForm.publish}
              onChange={(e) => setPostForm({ ...postForm, publish: e.target.checked })}
            />
            Kaydedince doğrudan yayınla
          </label>
          <div className="btn-group">
            <button
              className="btn btn-primary"
              onClick={() => handleCreate(false)}
              disabled={loading || !connected}
            >
              {loading ? "⏳" : postForm.publish ? "🚀 Yayınla" : "💾 Kaydet"}
            </button>
            <button
              className="btn btn-outline"
              onClick={() => handleCreate(true)}
              disabled={loading || !connected}
            >
              📝 Taslak Olarak Kaydet
            </button>
          </div>
        </section>
      )}

      {tab === "yazilar" && (
        <table className="table">
          <thead>
            <tr>
              <th>Başlık</th>
              <th>Tarih</th>
              <th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {posts.length === 0 && (
              <tr><td colSpan={3}>Yayında yazı yok</td></tr>
            )}
            {posts.map((p) => (
              <tr key={p.id}>
                <td>
                  {p.url ? (
                    <a href={p.url} target="_blank" rel="noreferrer">{p.title}</a>
                  ) : (
                    p.title
                  )}
                </td>
                <td>{p.published ? new Date(p.published).toLocaleDateString("tr") : "—"}</td>
                <td>
                  <button className="btn btn-outline" style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }} onClick={() => handleDelete(p.id)} disabled={loading}>
                    Sil
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "taslaklar" && (
        <table className="table">
          <thead>
            <tr>
              <th>Başlık</th>
              <th>Güncelleme</th>
              <th>İşlem</th>
            </tr>
          </thead>
          <tbody>
            {drafts.length === 0 && (
              <tr><td colSpan={3}>Taslak yok</td></tr>
            )}
            {drafts.map((p) => (
              <tr key={p.id}>
                <td>{p.title}</td>
                <td>{p.updated ? new Date(p.updated).toLocaleDateString("tr") : "—"}</td>
                <td>
                  <button className="btn btn-primary" style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem", marginRight: "0.35rem" }} onClick={() => handlePublish(p.id)} disabled={loading}>
                    Yayınla
                  </button>
                  <button className="btn btn-outline" style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }} onClick={() => handleDelete(p.id)} disabled={loading}>
                    Sil
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
