import React, { useState, useEffect, useCallback } from "react";
import API from "../api";


const TABS = [
  { id: "posts", label: "📝 Yazılar" },
  { id: "pages", label: "📄 Sayfalar" },
  { id: "profiles", label: "👤 Profiller" },
  { id: "categories", label: "🏷️ Kategoriler" },
  { id: "media", label: "🖼️ Medya" },
  { id: "users", label: "👥 Kullanıcılar" },
  { id: "comments", label: "💬 Yorumlar" },
  { id: "plugins", label: "🔌 Plugin'ler" },
  { id: "themes", label: "🎨 Temalar" },
  { id: "settings", label: "⚙️ Ayarlar" },
  { id: "sites", label: "🌐 Siteler" },
];

const PROFILE_META = ["yas", "telefon", "telegram", "lokasyon", "fiyat", "odeme_sekli", "ozellikler", "vip"];

function Skeleton({ rows = 5 }) {
  return (
    <div className="wp-skeleton">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="wp-skeleton-row" />
      ))}
    </div>
  );
}

export default function WPManager() {
  const [tab, setTab] = useState("posts");
  const [connected, setConnected] = useState(false);
  const [connInfo, setConnInfo] = useState(null);
  const [login, setLogin] = useState({ url: "https://balkutusu.com", username: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [items, setItems] = useState([]);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({});

  const flash = (msg, isErr = false) => {
    if (isErr) setError(msg);
    else setSuccess(msg);
    setTimeout(() => { setError(""); setSuccess(""); }, 4000);
  };

  const checkStatus = useCallback(async () => {
    try {
      let res = await API.get("/api/wp/status");
      if (!res.data.connected) {
        res = await API.post("/api/wp/auto-connect");
      }
      if (res.data.connected) {
        setConnected(true);
        setConnInfo(res.data);
        if (res.data.auto_connected) {
          flash(`Otomatik bağlandı: ${res.data.url || ""}`);
        }
      }
    } catch { /* not connected */ }
  }, []);

  useEffect(() => { checkStatus(); }, [checkStatus]);

  const handleConnect = async () => {
    setLoading(true);
    try {
      const res = await API.post("/api/wp/login", login);
      if (res.data.success) {
        setConnected(true);
        setConnInfo(res.data);
        setLogin((p) => ({ ...p, password: "" }));
        flash(`Bağlandı (${res.data.auth_mode || "basic"})`);
        loadTab(tab);
      } else {
        flash(res.data.error || "Bağlantı hatası", true);
      }
    } catch (e) {
      flash(e.response?.data?.detail || e.message, true);
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await API.post("/api/wp/disconnect", {});
    } catch (e) {
      flash(e.response?.data?.detail || e.message, true);
      return;
    }
    setConnected(false);
    setConnInfo(null);
    setItems([]);
    flash("Bağlantı kesildi");
  };

  const loadTab = async (t = tab) => {
    if (!connected) return;
    setLoading(true);
    setItems([]);
    const map = {
      posts: "/api/wp/posts",
      pages: "/api/wp/pages",
      profiles: "/api/wp/profiles",
      categories: "/api/wp/categories",
      media: "/api/wp/media",
      users: "/api/wp/users",
      comments: "/api/wp/comments?status=hold",
      plugins: "/api/wp/plugins",
      themes: "/api/wp/themes",
      settings: "/api/wp/settings",
      sites: "/api/wp/sites",
    };
    try {
      const res = await API.get(map[t]);
      if (!res.data.success && res.data.error) {
        flash(res.data.error, true);
        return;
      }
      if (t === "plugins") setItems(res.data.plugins || []);
      else if (t === "themes") setItems(res.data.themes || []);
      else if (t === "sites") setItems(res.data.sites || res.data.data || []);
      else if (t === "settings") setItems([res.data.settings || res.data]);
      else if (Array.isArray(res.data.data)) setItems(res.data.data);
      else if (Array.isArray(res.data)) setItems(res.data);
      else setItems([]);
    } catch (e) {
      flash(e.response?.data?.detail || e.message, true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (connected) loadTab(tab);
  }, [tab, connected]);

  const openCreate = () => {
    setForm({ title: "", content: "", status: "publish" });
    setModal("create");
  };

  const saveCreate = async () => {
    const endpoints = { posts: "/api/wp/posts", pages: "/api/wp/pages", profiles: "/api/wp/profiles" };
    if (!endpoints[tab]) return;
    setLoading(true);
    try {
      const res = await API.post(endpoints[tab], form);
      if (res.data.success === false) flash(res.data.error, true);
      else { flash("Oluşturuldu"); setModal(null); loadTab(); }
    } catch (e) { flash(e.response?.data?.detail || e.message, true); }
    setLoading(false);
  };

  const deleteItem = async (id) => {
    if (!window.confirm("Silmek istediğinize emin misiniz?")) return;
    const map = { posts: "posts", pages: "pages", profiles: "profiles", media: "media", comments: "comments" };
    if (!map[tab]) return;
    setLoading(true);
    try {
      await API.delete(`/api/wp/${map[tab]}/${id}`);
      flash("Silindi");
      loadTab();
    } catch (e) { flash(e.message, true); }
    setLoading(false);
  };

  const togglePlugin = async (file, active) => {
    const action = active ? "deactivate" : "activate";
    await API.post(`/api/wp/plugins/${encodeURIComponent(file)}/${action}`);
    loadTab("plugins");
  };

  const activateTheme = async (stylesheet) => {
    await API.post(`/api/wp/themes/${encodeURIComponent(stylesheet)}/activate`);
    flash("Tema aktif");
    loadTab("themes");
  };

  const approveComment = async (id) => {
    await API.post(`/api/wp/comments/${id}/approve`);
    loadTab("comments");
  };

  const handleMediaUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    setLoading(true);
    try {
      await API.post("/api/wp/media/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      flash("Yüklendi");
      loadTab("media");
    } catch (err) { flash(err.message, true); }
    setLoading(false);
  };

  const renderTable = () => {
    if (loading) return <Skeleton />;
    if (tab === "settings" && items[0]) {
      const s = items[0];
      return (
        <div className="wp-settings-form">
          {["title", "description", "admin_email", "timezone", "language"].map((k) => (
            <div key={k} className="form-grup">
              <label>{k}</label>
              <input value={form[k] ?? s[k] ?? ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            </div>
          ))}
          <button className="btn btn-primary" onClick={async () => {
            await API.put("/api/wp/settings", form);
            flash("Ayarlar kaydedildi");
          }}>Kaydet</button>
        </div>
      );
    }
    if (tab === "plugins") {
      return (
        <table className="wp-table">
          <thead><tr><th>Plugin</th><th>Versiyon</th><th>Durum</th><th></th></tr></thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.file}>
                <td>{p.name}</td>
                <td>{p.version}</td>
                <td>{p.active ? "✅ Aktif" : "—"}</td>
                <td>
                  <button className="btn btn-outline btn-small" onClick={() => togglePlugin(p.file, p.active)}>
                    {p.active ? "Pasif" : "Aktif"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (tab === "themes") {
      return (
        <div className="wp-grid">
          {items.map((t) => (
            <div key={t.stylesheet} className={`wp-card ${t.active ? "active" : ""}`}>
              <strong>{t.name}</strong>
              <p>{t.version}</p>
              {!t.active && (
                <button className="btn btn-primary btn-small" onClick={() => activateTheme(t.stylesheet)}>Aktif Et</button>
              )}
            </div>
          ))}
        </div>
      );
    }
    if (tab === "media") {
      return (
        <>
          <div className="wp-upload-zone">
            <input type="file" onChange={handleMediaUpload} />
          </div>
          <div className="wp-grid">
            {items.map((m) => (
              <div key={m.id} className="wp-card">
                {m.source_url && <img src={m.source_url} alt="" style={{ maxWidth: "100%", borderRadius: 8 }} />}
                <p>{m.title?.rendered || m.id}</p>
                <button className="btn btn-danger btn-small" onClick={() => deleteItem(m.id)}>Sil</button>
              </div>
            ))}
          </div>
        </>
      );
    }
    if (tab === "sites") {
      return (
        <table className="wp-table">
          <thead><tr><th>ID</th><th>Domain</th><th>Başlık</th><th>URL</th></tr></thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id}>
                <td>{s.id}</td>
                <td>{s.domain}</td>
                <td>{s.title}</td>
                <td><a href={s.site_url} target="_blank" rel="noreferrer">{s.site_url}</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (tab === "comments") {
      return (
        <table className="wp-table">
          <thead><tr><th>ID</th><th>Yazar</th><th>İçerik</th><th></th></tr></thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>{c.author_name}</td>
                <td>{(c.content?.rendered || "").replace(/<[^>]+>/g, "").slice(0, 80)}</td>
                <td>
                  <button className="btn btn-primary btn-small" onClick={() => approveComment(c.id)}>Onayla</button>
                  <button className="btn btn-danger btn-small" onClick={() => deleteItem(c.id)}>Sil</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    if (tab === "categories") {
      const tree = {};
      items.forEach((c) => {
        const p = c.parent || 0;
        if (!tree[p]) tree[p] = [];
        tree[p].push(c);
      });
      const renderTree = (parent = 0, depth = 0) =>
        (tree[parent] || []).map((c) => (
          <div key={c.id} style={{ paddingLeft: depth * 16 }}>
            {c.name} <small>({c.count})</small>
            {renderTree(c.id, depth + 1)}
          </div>
        ));
      return <div className="wp-cat-tree">{renderTree()}</div>;
    }
    if (tab === "profiles") {
      return (
        <table className="wp-table">
          <thead><tr><th>ID</th><th>Başlık</th><th>Yaş</th><th>Lokasyon</th><th>Fiyat</th><th></th></tr></thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td>
                <td>{p.title?.rendered || p.title}</td>
                <td>{p.meta?.yas || "—"}</td>
                <td>{p.meta?.lokasyon || "—"}</td>
                <td>{p.meta?.fiyat || "—"}</td>
                <td><button className="btn btn-danger btn-small" onClick={() => deleteItem(p.id)}>Sil</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    return (
      <table className="wp-table">
        <thead><tr><th>ID</th><th>Başlık</th><th>Durum</th><th></th></tr></thead>
        <tbody>
          {items.map((p) => (
            <tr key={p.id}>
              <td>{p.id}</td>
              <td>{p.title?.rendered || p.title}</td>
              <td>{p.status}</td>
              <td><button className="btn btn-danger btn-small" onClick={() => deleteItem(p.id)}>Sil</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <div className="wp-manager">
      <h2 style={{ marginTop: 0 }}>🌐 WordPress Yöneticisi</h2>
      <p style={{ color: "var(--text2)", fontSize: "0.9rem" }}>
        balkutusu.com — yazı, sayfa, profil, kategori, medya, multisite tam yönetim
      </p>

      {!connected ? (
        <div className="wp-login-box">
          <div className="form-grup">
            <label>WordPress URL</label>
            <input value={login.url} onChange={(e) => setLogin({ ...login, url: e.target.value })} placeholder="https://balkutusu.com" />
          </div>
          <div className="form-grup">
            <label>Kullanıcı adı</label>
            <input value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })} autoComplete="username" />
          </div>
          <div className="form-grup">
            <label>Application Password / Şifre</label>
            <input type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} autoComplete="current-password" />
            <small style={{ color: "var(--text2)" }}>WP Admin → Kullanıcılar → Uygulama Parolaları</small>
          </div>
          <button className="btn btn-primary" onClick={handleConnect} disabled={loading}>
            {loading ? "Bağlanıyor…" : "WordPress'e Bağlan"}
          </button>
        </div>
      ) : (
        <>
          <div className="wp-status-bar">
            <span className="status-badge aktif">✅ {connInfo?.url || login.url}</span>
            <span>{connInfo?.current_user || connInfo?.username}</span>
            {connInfo?.is_multisite && <span>{connInfo?.site_count} site</span>}
            <button className="btn btn-outline btn-small" onClick={handleDisconnect}>Bağlantıyı Kes</button>
            <button className="btn btn-outline btn-small" onClick={() => loadTab()}>Yenile</button>
          </div>

          <div className="wp-tabs">
            {TABS.map((t) => (
              <button key={t.id} className={`wp-tab ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </div>

          {["posts", "pages", "profiles"].includes(tab) && (
            <button className="btn btn-primary" style={{ marginBottom: "1rem" }} onClick={openCreate}>+ Yeni Ekle</button>
          )}

          {renderTable()}
        </>
      )}

      {error && <div className="hata" style={{ marginTop: "1rem" }}>{error}</div>}
      {success && <div className="sonuc" style={{ marginTop: "1rem" }}>{success}</div>}

      {modal === "create" && (
        <div className="wp-modal-backdrop" onClick={() => setModal(null)}>
          <div className="wp-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Yeni {tab}</h3>
            <div className="form-grup">
              <label>Başlık</label>
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </div>
            <div className="form-grup">
              <label>İçerik</label>
              <textarea rows={6} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
            </div>
            {tab === "profiles" && PROFILE_META.map((k) => (
              <div key={k} className="form-grup">
                <label>{k}</label>
                <input value={form[k] || ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
              </div>
            ))}
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="btn btn-primary" onClick={saveCreate}>Kaydet</button>
              <button className="btn btn-outline" onClick={() => setModal(null)}>İptal</button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .wp-manager .wp-tabs { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 1rem 0; }
        .wp-tab { padding: 0.4rem 0.75rem; border: 1px solid var(--border); background: transparent; color: var(--text); border-radius: 8px; cursor: pointer; font-size: 0.82rem; }
        .wp-tab.active { background: var(--color-accent); border-color: var(--color-accent); color: #fff; }
        .wp-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
        .wp-table th, .wp-table td { padding: 0.5rem; border-bottom: 1px solid var(--border); text-align: left; }
        .wp-status-bar { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; margin-bottom: 1rem; }
        .wp-login-box { max-width: 420px; }
        .wp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 0.75rem; }
        .wp-card { padding: 0.75rem; border: 1px solid var(--border); border-radius: 8px; }
        .wp-card.active { border-color: var(--color-accent); }
        .wp-skeleton-row { height: 36px; background: linear-gradient(90deg, #222 25%, #333 50%, #222 75%); background-size: 200% 100%; animation: wp-shimmer 1.2s infinite; border-radius: 6px; margin-bottom: 0.5rem; }
        @keyframes wp-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
        .wp-modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 2000; display: flex; align-items: center; justify-content: center; }
        .wp-modal { background: var(--color-card-bg); padding: 1.5rem; border-radius: 12px; max-width: 520px; width: 90%; max-height: 90vh; overflow: auto; }
        .wp-cat-tree { font-size: 0.9rem; line-height: 1.8; }
        .wp-upload-zone { margin-bottom: 1rem; padding: 1rem; border: 2px dashed var(--border); border-radius: 8px; text-align: center; }
      `}</style>
    </div>
  );
}
