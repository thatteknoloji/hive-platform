import React, { useState } from "react";
import API from "../api";


export default function ScheduleManager() {
  const [modul_id, setModulId] = useState("");
  const [zaman, setZaman] = useState("");
  const [parametreler, setParametreler] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [sonuc, setSonuc] = useState(null);
  const [liste, setListe] = useState([]);

  const handleZamanla = async () => {
    if (!modul_id || !zaman) { setHata("Modül ID ve zaman (cron) gerekli"); return; }
    setHata(""); setSonuc(null); setLoading(l => ({ ...l, zamanla: true }));
    try {
      let params = {};
      try { params = parametreler ? JSON.parse(parametreler) : {}; } catch { setHata("Parametreler geçerli JSON değil"); setLoading(l => ({ ...l, zamanla: false })); return; }
      const res = await API.post("/api/schedule", { modul_id, zaman, parametreler: params });
      setSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, zamanla: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try {
      const res = await API.get("/api/schedule/liste");
      setListe(res.data?.sonuc?.gorevler || res.data?.gorevler || []);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleDuraklat = async () => {
    if (!modul_id) { setHata("Modül ID gerekli"); return; }
    setHata(""); setSonuc(null); setLoading(l => ({ ...l, duraklat: true }));
    try {
      const res = await API.post("/api/schedule/duraklat", { modul_id });
      setSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, duraklat: false }));
  };

  const handleDevamEttir = async () => {
    if (!modul_id) { setHata("Modül ID gerekli"); return; }
    setHata(""); setSonuc(null); setLoading(l => ({ ...l, devam: true }));
    try {
      const res = await API.post("/api/schedule/devam-ettir", { modul_id });
      setSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, devam: false }));
  };

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">⏰</div>
        <div className="info">
          <h2>Schedule Manager – Zamanlayıcı Yönetimi</h2>
          <p>Modüllerinizi belirli aralıklarla çalıştırmak için cron tabanlı görevler oluşturun ve yönetin.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
            <label>Modül ID</label>
            <input value={modul_id} onChange={e => setModulId(e.target.value)} placeholder="örn: maps_bot" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 180 }}>
            <label>Zaman (cron)</label>
            <input value={zaman} onChange={e => setZaman(e.target.value)} placeholder="örn: */30 * * * *" />
          </div>
        </div>
        <div className="form-grup" style={{ marginTop: "0.5rem" }}>
          <label>Parametreler (JSON)</label>
          <textarea rows={3} value={parametreler} onChange={e => setParametreler(e.target.value)}
            placeholder='{"isletme": "ornek", "adet": 5}' style={{ width: "100%", fontFamily: "monospace", fontSize: "0.8rem" }} />
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-primary" onClick={handleZamanla} disabled={loading.zamanla}>
          {loading.zamanla ? "⏳" : "⏰ Zamanla"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleDuraklat} disabled={loading.duraklat}>
          {loading.duraklat ? "⏳" : "⏸️ Duraklat"}
        </button>
        <button className="btn btn-outline" onClick={handleDevamEttir} disabled={loading.devam}>
          {loading.devam ? "⏳" : "▶️ Devam Ettir"}
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
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📋 Zamanlanmış Görevler</h3>
          <div className="table-container" style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr><th>Modül</th><th>Zaman</th><th>Son Çalışma</th><th>Sonraki</th><th>Durum</th></tr>
              </thead>
              <tbody>
                {liste.map((g, i) => (
                  <tr key={i}>
                    <td>{g.modul_id || g.module}</td>
                    <td style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>{g.zaman || g.time}</td>
                    <td>{g.son_calisma || g.last_run || "-"}</td>
                    <td>{g.sonraki_calisma || g.next_run || "-"}</td>
                    <td><span style={{ color: g.durum === "aktif" || g.status === "active" ? "var(--green)" : "var(--red)" }}>{g.durum || g.status}</span></td>
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
