import React, { useState } from "react";
import API from "../api";


export default function BackupCenter() {
  const [module_id, setModuleId] = useState("");
  const [periyot, setPeriyot] = useState("daily");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [sonuc, setSonuc] = useState(null);
  const [liste, setListe] = useState([]);

  const handleYedekAl = async () => {
    if (!module_id) { setHata("Modül ID gerekli"); return; }
    setHata(""); setSonuc(null); setLoading(l => ({ ...l, yedek: true }));
    try {
      const res = await API.post("/api/backup", { module_id });
      setSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, yedek: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try {
      const res = await API.get("/api/backup/liste");
      setListe(res.data?.sonuc?.yedekler || res.data?.yedekler || []);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleOtomatik = async () => {
    if (!module_id) { setHata("Modül ID gerekli"); return; }
    setHata(""); setSonuc(null); setLoading(l => ({ ...l, otomatik: true }));
    try {
      const res = await API.post("/api/backup/otomatik", { module_id, periyot });
      setSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, otomatik: false }));
  };

  const handleIndir = async (yedekId) => {
    try {
      const res = await API.get(`/api/backup/indir/${yedekId}`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = `yedek_${yedekId}.zip`; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { setHata("İndirme hatası: " + (err.response?.data?.detail || err.message)); }
  };

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">💾</div>
        <div className="info">
          <h2>Backup Center – Yedekleme Merkezi</h2>
          <p>Modül verilerinizi yedekleyin, otomatik yedekleme planlayın ve gerektiğinde indirin.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
            <label>Modül ID</label>
            <input value={module_id} onChange={e => setModuleId(e.target.value)} placeholder="örn: rank_tracker" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
            <label>Periyot (otomatik için)</label>
            <select value={periyot} onChange={e => setPeriyot(e.target.value)}>
              <option value="daily">Günlük</option>
              <option value="weekly">Haftalık</option>
              <option value="monthly">Aylık</option>
            </select>
          </div>
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-primary" onClick={handleYedekAl} disabled={loading.yedek}>
          {loading.yedek ? "⏳ Yedekleniyor..." : "💾 Yedek Al"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleOtomatik} disabled={loading.otomatik}>
          {loading.otomatik ? "⏳" : "⏰ Otomatik Zamanla"}
        </button>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}

      {sonuc && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto" }}>
            {JSON.stringify(sonuc, null, 2)}
          </pre>
        </div>
      )}

      {liste.length > 0 && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📋 Yedek Listesi</h3>
          <div className="table-container" style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr><th>Tarih</th><th>Modül</th><th>Boyut</th><th>İndir</th></tr>
              </thead>
              <tbody>
                {liste.map((y, i) => (
                  <tr key={i}>
                    <td>{y.tarih || y.date || y.olusturulma}</td>
                    <td>{y.modul || y.module || y.module_id}</td>
                    <td>{y.boyut || y.size || "-"}</td>
                    <td>
                      <button className="btn btn-sm btn-primary" onClick={() => handleIndir(y.id || y.yedek_id)}>
                        ⬇️ İndir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
