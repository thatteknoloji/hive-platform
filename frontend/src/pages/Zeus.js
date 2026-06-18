import React, { useState } from "react";
import API from "../api";


export default function Zeus() {
  const [platform, setPlatform] = useState("Google Sites");
  const [konu, setKonu] = useState("");
  const [hedefUrl, setHedefUrl] = useState("");
  const [pageId, setPageId] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [yerlestirSonuc, setYerlestirSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [analizSonuc, setAnalizSonuc] = useState(null);

  const handleYerlestir = async () => {
    setHata("");
    setLoading(l => ({ ...l, yerlestir: true }));
    try {
      const res = await API.post("/api/zeus", { platform, konu, hedef_url: hedefUrl });
      setYerlestirSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, yerlestir: false }));
  };

  const handleListele = async () => {
    setHata("");
    setLoading(l => ({ ...l, listele: true }));
    try {
      const url = platform ? `/api/zeus/listele/${platform}` : "/api/zeus/listele";
      const res = await API.get(url);
      setListeSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleSil = async () => {
    if (!pageId) { setHata("Page ID gerekli"); return; }
    setHata("");
    setLoading(l => ({ ...l, sil: true }));
    try {
      const res = await API.delete(`/api/zeus/sil/${pageId}`);
      setYerlestirSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, sil: false }));
  };

  const handleAnaliz = async () => {
    setHata("");
    setLoading(l => ({ ...l, analiz: true }));
    try {
      const res = await API.get("/api/zeus/analiz");
      setAnalizSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.message || "")); }
    setLoading(l => ({ ...l, analiz: false }));
  };

  const SonucKarti = ({ data }) => data && (
    <div style={{ background: "var(--bg3)", border: "1px solid var(--honey)", borderRadius: 8, padding: "1rem", marginTop: "1rem" }}>
      <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto" }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">⚡</div>
        <div className="info">
          <h2>Zeus'un Yıldırımı – Parasite SEO</h2>
          <p>Web 2.0 platformlarına parazit SEO sayfaları yerleştir, yönet ve analiz et.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
            <label>Platform</label>
            <select value={platform} onChange={e => setPlatform(e.target.value)}>
              <option value="Google Sites">Google Sites</option>
              <option value="Medium">Medium</option>
              <option value="Blogger">Blogger</option>
              <option value="WordPress.com">WordPress.com</option>
              <option value="Tumblr">Tumblr</option>
            </select>
          </div>
          <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
            <label>Konu (opsiyonel)</label>
            <input value={konu} onChange={e => setKonu(e.target.value)} placeholder="örn: vip escort" />
          </div>
          <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
            <label>Hedef URL (opsiyonel)</label>
            <input value={hedefUrl} onChange={e => setHedefUrl(e.target.value)} placeholder="örn: rakipsitesi.com" />
          </div>
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-primary" onClick={handleYerlestir} disabled={loading.yerlestir}
          style={{ background: "var(--honey)", color: "#000" }}>
          {loading.yerlestir ? "Yerleştiriliyor..." : "⚡ Parazit Yerleştir"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Parazit Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleAnaliz} disabled={loading.analiz}>
          {loading.analiz ? "⏳" : "📊 Platform Analiz"}
        </button>
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 200 }}>
            <label>Page ID (silme için)</label>
            <input value={pageId} onChange={e => setPageId(e.target.value)} placeholder="parazit_page_id" />
          </div>
          <button className="btn btn-danger" onClick={handleSil} disabled={loading.sil}>
            {loading.sil ? "⏳" : "🗑️ Parazit Sil"}
          </button>
        </div>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}
      <SonucKarti data={yerlestirSonuc} />
      <SonucKarti data={listeSonuc} />
      <SonucKarti data={analizSonuc} />
    </div>
  );
}
