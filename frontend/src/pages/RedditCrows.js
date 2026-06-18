import React, { useState } from "react";
import API from "../api";


export default function RedditCrows() {
  const [baslik, setBaslik] = useState("");
  const [yorum, setYorum] = useState("");
  const [konu, setKonu] = useState("");
  const [icerik, setIcerik] = useState("");
  const [subreddit, setSubreddit] = useState("");
  const [yorumId, setYorumId] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [yorumSonuc, setYorumSonuc] = useState(null);
  const [postSonuc, setPostSonuc] = useState(null);
  const [yorumListeSonuc, setYorumListeSonuc] = useState(null);
  const [postListeSonuc, setPostListeSonuc] = useState(null);

  const handleYorumGonder = async () => {
    if (!baslik) { setHata("Başlık gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, yorum: true }));
    try { const res = await API.post("/api/reddit", { baslik, yorum }); setYorumSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, yorum: false }));
  };

  const handlePostAc = async () => {
    if (!konu) { setHata("Konu gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, post: true }));
    try { const res = await API.post("/api/reddit/post", { konu, icerik }); setPostSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, post: false }));
  };

  const handleYorumListele = async () => {
    setHata(""); setLoading(l => ({ ...l, yorumListe: true }));
    try {
      const url = subreddit ? `/api/reddit/yorumlar/${subreddit}` : "/api/reddit/yorumlar";
      const res = await API.get(url);
      setYorumListeSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, yorumListe: false }));
  };

  const handlePostListele = async () => {
    setHata(""); setLoading(l => ({ ...l, postListe: true }));
    try { const res = await API.get("/api/reddit/postlar"); setPostListeSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, postListe: false }));
  };

  const handleYorumSil = async () => {
    if (!yorumId) { setHata("Yorum ID gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, yorumSil: true }));
    try { const res = await API.delete(`/api/reddit/yorum/${yorumId}`); setYorumSonuc(res.data); }
    catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, yorumSil: false }));
  };

  const SonucKarti = ({ data }) => data && (
    <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", marginTop: "1rem" }}>
      <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto" }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">📤</div>
        <div className="info">
          <h2>Reddit Crows – Reddit Post ve Yorum Gönderme</h2>
          <p>Reddit'te post aç, yorum gönder, geçmişi listele ve yönet.</p>
        </div>
      </div>

      <div className="talon-form">
        <h4 style={{ color: "var(--honey)", marginBottom: "0.5rem" }}>Yorum Gönder</h4>
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
            <label>Başlık</label>
            <input value={baslik} onChange={e => setBaslik(e.target.value)} placeholder="Başlık veya URL" />
          </div>
        </div>
        <div className="form-grup" style={{ marginTop: "0.3rem" }}>
          <textarea rows={3} value={yorum} onChange={e => setYorum(e.target.value)}
            placeholder="Yorum (boş bırakılırsa otomatik oluşturulur)" style={{ width: "100%" }} />
        </div>
        <button className="btn btn-primary" onClick={handleYorumGonder} disabled={loading.yorum}
          style={{ marginTop: "0.5rem" }}>
          {loading.yorum ? "Gönderiliyor..." : "📤 Yorum Gönder"}
        </button>
      </div>

      <div className="talon-form" style={{ marginTop: "1.5rem" }}>
        <h4 style={{ color: "var(--orange)", marginBottom: "0.5rem" }}>Post Aç</h4>
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
            <label>Konu</label>
            <input value={konu} onChange={e => setKonu(e.target.value)} placeholder="Post konusu" />
          </div>
        </div>
        <div className="form-grup" style={{ marginTop: "0.3rem" }}>
          <textarea rows={3} value={icerik} onChange={e => setIcerik(e.target.value)}
            placeholder="İçerik (boş bırakılırsa otomatik oluşturulur)" style={{ width: "100%" }} />
        </div>
        <button className="btn btn-primary" onClick={handlePostAc} disabled={loading.post}
          style={{ marginTop: "0.5rem", background: "var(--orange)", color: "#000" }}>
          {loading.post ? "Açılıyor..." : "📄 Post Aç"}
        </button>
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <h4 style={{ color: "var(--text2)", marginBottom: "0.5rem" }}>Yönetim</h4>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
            <label>Subreddit (filtre)</label>
            <input value={subreddit} onChange={e => setSubreddit(e.target.value)} placeholder="all" />
          </div>
          <button className="btn btn-outline" onClick={handleYorumListele} disabled={loading.yorumListe}
            style={{ alignSelf: "flex-end" }}>
            {loading.yorumListe ? "⏳" : "💬 Yorumları Listele"}
          </button>
          <button className="btn btn-outline" onClick={handlePostListele} disabled={loading.postListe}
            style={{ alignSelf: "flex-end" }}>
            {loading.postListe ? "⏳" : "📋 Postları Listele"}
          </button>
          <div className="form-grup" style={{ flex: 1, minWidth: 120 }}>
            <label>Yorum ID (sil)</label>
            <input type="number" value={yorumId} onChange={e => setYorumId(e.target.value)} placeholder="1" />
          </div>
          <button className="btn btn-danger" onClick={handleYorumSil} disabled={loading.yorumSil}
            style={{ alignSelf: "flex-end" }}>
            {loading.yorumSil ? "⏳" : "🗑️ Yorum Sil"}
          </button>
        </div>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}
      <SonucKarti data={yorumSonuc} />
      <SonucKarti data={postSonuc} />
      <SonucKarti data={yorumListeSonuc} />
      <SonucKarti data={postListeSonuc} />
    </div>
  );
}
