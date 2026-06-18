import React, { useState } from "react";
import API from "../api";


export default function HeatmapViewer() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [olusturSonuc, setOlusturSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);

  const handleOlustur = async () => {
    if (!url) { setHata("URL gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, olustur: true }));
    try { const res = await API.post("/api/heatmap", { url }); setOlusturSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, olustur: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/heatmap/liste"); setListeSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, liste: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">🔥</div>
        <div className="info"><h2>Heatmap Viewer</h2><p>Sayfa ısı haritası verileri, tıklama sayıları ve kaydırma derinliği</p></div>
      </div>
      <div className="form-grup">
        <label>Sayfa URL</label>
        <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://ornek.com/sayfa" />
      </div>
      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleOlustur} disabled={loading.olustur}>
          {loading.olustur ? "⏳" : "🔥 Oluştur"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Listele"}
        </button>
      </div>
      {hata && <div className="hata">{hata}</div>}
      {(olusturSonuc || listeSonuc) && (
        <div className="sonuc">
          <table className="table">
            <thead>
              <tr>
                <th>Sayfa</th>
                <th>Tıklama</th>
                <th>Kaydırma Derinliği</th>
                <th>Eleman Pozisyonu</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(olusturSonuc || listeSonuc) ? olusturSonuc || listeSonuc : [olusturSonuc || listeSonuc]).map((r, i) => (
                <tr key={i}>
                  <td>{r.sayfa || r.url || r.page || "-"}</td>
                  <td>{r.tiklama ?? r.click_count ?? r.clicks ?? "-"}</td>
                  <td>{r.kaydirma_derinligi ?? r.scroll_depth ?? r.scroll ?? "-"}</td>
                  <td>{r.eleman_pozisyonu ? JSON.stringify(r.eleman_pozisyonu) : r.element_position ? JSON.stringify(r.element_position) : r.pozisyon || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
