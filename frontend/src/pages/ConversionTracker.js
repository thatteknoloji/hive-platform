import React, { useState } from "react";
import API from "../api";


export default function ConversionTracker() {
  const [url, setUrl] = useState("");
  const [hedef, setHedef] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [takipSonuc, setTakipSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [istatistikSonuc, setIstatistikSonuc] = useState(null);
  const [hedefSonuc, setHedefSonuc] = useState(null);

  const handleTakip = async () => {
    if (!url) { setHata("URL gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, takip: true }));
    try { const res = await API.post("/api/conversion", { url, hedef }); setTakipSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, takip: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try { const res = await API.get("/api/conversion/liste"); setListeSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleIstatistik = async () => {
    setHata(""); setLoading(l => ({ ...l, istatistik: true }));
    try { const res = await API.get("/api/conversion/istatistik"); setIstatistikSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, istatistik: false }));
  };

  const handleHedefEkle = async () => {
    if (!hedef) { setHata("Hedef gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, hedef: true }));
    try { const res = await API.post("/api/conversion/hedef", { hedef, url }); setHedefSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, hedef: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">📈</div>
        <div className="info"><h2>Conversion Tracker</h2><p>Dönüşüm takibi, hedef yönetimi ve istatistikler</p></div>
      </div>
      <div className="form-row">
        <div className="form-grup" style={{ flex: 2 }}>
          <label>Sayfa URL</label>
          <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://ornek.com/sayfa" />
        </div>
        <div className="form-grup" style={{ flex: 1 }}>
          <label>Hedef</label>
          <input value={hedef} onChange={e => setHedef(e.target.value)} placeholder="ör: kayit-ol" />
        </div>
      </div>
      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleTakip} disabled={loading.takip}>
          {loading.takip ? "⏳" : "📈 Takip Et"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleIstatistik} disabled={loading.istatistik}>
          {loading.istatistik ? "⏳" : "📊 İstatistik"}
        </button>
        <button className="btn btn-outline" onClick={handleHedefEkle} disabled={loading.hedef}>
          {loading.hedef ? "⏳" : "➕ Hedef Ekle"}
        </button>
      </div>
      {hata && <div className="hata">{hata}</div>}
      {(takipSonuc || listeSonuc) && (
        <div className="sonuc">
          <table className="table">
            <thead>
              <tr>
                <th>Sayfa</th>
                <th>Hedef</th>
                <th>Tamamlanma</th>
                <th>Dönüşüm Oranı</th>
                <th>Hunü Adımları</th>
              </tr>
            </thead>
            <tbody>
              {(Array.isArray(takipSonuc || listeSonuc) ? takipSonuc || listeSonuc : [takipSonuc || listeSonuc]).map((r, i) => (
                <tr key={i}>
                  <td>{r.sayfa || r.url || "-"}</td>
                  <td>{r.hedef || r.goal || "-"}</td>
                  <td>{r.tamamlama ?? r.completions ?? "-"}</td>
                  <td>{r.donusum_oran ?? r.conversion_rate ?? r.oran ?? "-"}</td>
                  <td>{r.hunu_adimlari ? (Array.isArray(r.hunu_adimlari) ? r.hunu_adimlari.join(", ") : r.hunu_adimlari) : r.funnel_steps || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {istatistikSonuc && (
        <div className="sonuc">
          {Object.entries(istatistikSonuc).map(([k, v]) => (
            <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
          ))}
        </div>
      )}
      {hedefSonuc && (
        <div className="sonuc">
          {Object.entries(hedefSonuc).map(([k, v]) => (
            <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}
