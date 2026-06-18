import React, { useState } from "react";
import API from "../api";


const SEVIYE_RENK = {
  INFO: "var(--blue)",
  WARNING: "var(--orange)",
  ERROR: "var(--red)",
  DEBUG: "var(--text2)",
};

export default function LogViewer() {
  const [module_id, setModuleId] = useState("");
  const [seviye, setSeviye] = useState("INFO");
  const [sorgu, setSorgu] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [liste, setListe] = useState([]);
  const [araSonuc, setAraSonuc] = useState([]);
  const [istatistik, setIstatistik] = useState(null);

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try {
      const params = {};
      if (module_id) params.module_id = module_id;
      if (seviye) params.seviye = seviye;
      const res = await API.get("/api/log/liste", { params });
      setListe(res.data?.sonuc?.loglar || res.data?.loglar || []);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, listele: false }));
  };

  const handleAra = async () => {
    if (!sorgu.trim()) { setHata("Arama sorgusu gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, ara: true }));
    try {
      const params = { sorgu };
      if (module_id) params.module_id = module_id;
      const res = await API.get("/api/log/ara", { params });
      setAraSonuc(res.data?.sonuc?.loglar || res.data?.loglar || []);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, ara: false }));
  };

  const handleIstatistik = async () => {
    setHata(""); setLoading(l => ({ ...l, istatistik: true }));
    try {
      const params = {};
      if (module_id) params.module_id = module_id;
      const res = await API.get("/api/log/istatistik", { params });
      setIstatistik(res.data?.sonuc || res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, istatistik: false }));
  };

  const handleTemizle = async () => {
    if (!window.confirm("Tüm logları temizlemek istediğinize emin misiniz?")) return;
    setHata(""); setLoading(l => ({ ...l, temizle: true }));
    try {
      const params = {};
      if (module_id) params.module_id = module_id;
      const res = await API.delete("/api/log/temizle", { data: params });
      setListe([]); setAraSonuc([]);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, temizle: false }));
  };

  const LogTablosu = ({ loglar }) => loglar.length === 0 ? (
    <p style={{ color: "var(--text2)", fontSize: "0.85rem" }}>Log bulunamadı.</p>
  ) : (
    <div className="table-container" style={{ overflowX: "auto" }}>
      <table className="table">
        <thead>
          <tr><th>Zaman</th><th>Modül</th><th>Seviye</th><th>Mesaj</th></tr>
        </thead>
        <tbody>
          {loglar.map((l, i) => (
            <tr key={i}>
              <td style={{ fontSize: "0.8rem", whiteSpace: "nowrap" }}>{l.zaman || l.timestamp || l.tarih}</td>
              <td>{l.modul || l.module || l.module_id}</td>
              <td><span style={{ color: SEVIYE_RENK[l.seviye || l.level] || "var(--text2)", fontWeight: 600 }}>{l.seviye || l.level}</span></td>
              <td style={{ fontSize: "0.8rem", maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{l.mesaj || l.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">📜</div>
        <div className="info">
          <h2>Log Viewer – Sistem Log Görüntüleyici</h2>
          <p>Modül loglarını görüntüleyin, arama yapın, istatistik alın ve logları temizleyin.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="form-grup" style={{ flex: 1, minWidth: 150 }}>
            <label>Modül ID</label>
            <input value={module_id} onChange={e => setModuleId(e.target.value)} placeholder="örn: api_hunter" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 120 }}>
            <label>Seviye</label>
            <select value={seviye} onChange={e => setSeviye(e.target.value)}>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="DEBUG">DEBUG</option>
            </select>
          </div>
          <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
            <label>Arama Sorgusu</label>
            <input value={sorgu} onChange={e => setSorgu(e.target.value)} placeholder="örn: hata, api, bağlantı" />
          </div>
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Listele"}
        </button>
        <button className="btn btn-primary" onClick={handleAra} disabled={loading.ara}>
          {loading.ara ? "⏳ Aranıyor..." : "🔍 Ara"}
        </button>
        <button className="btn btn-outline" onClick={handleIstatistik} disabled={loading.istatistik}>
          {loading.istatistik ? "⏳" : "📊 İstatistik"}
        </button>
        <button className="btn btn-danger" onClick={handleTemizle} disabled={loading.temizle}>
          {loading.temizle ? "⏳" : "🗑️ Temizle"}
        </button>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}

      {istatistik && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📊 Log İstatistikleri</h3>
          <div className="item"><span className="key">Toplam Log: </span><span className="val">{istatistik.toplam || istatistik.total || 0}</span></div>
          {istatistik.seviye_dagilimi && Object.entries(istatistik.seviye_dagilimi).map(([s, a]) => (
            <div key={s} className="item"><span className="key" style={{ color: SEVIYE_RENK[s] }}>{s}: </span><span className="val">{a}</span></div>
          ))}
          {istatistik.modul_dagilimi && Object.entries(istatistik.modul_dagilimi).slice(0, 10).map(([m, a]) => (
            <div key={m} className="item"><span className="key">{m}: </span><span className="val">{a}</span></div>
          ))}
          <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto", marginTop: "0.5rem" }}>
            {JSON.stringify(istatistik, null, 2)}
          </pre>
        </div>
      )}

      {liste.length > 0 && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📋 Log Listesi</h3>
          <LogTablosu loglar={liste} />
        </div>
      )}

      {araSonuc.length > 0 && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>🔍 Arama Sonuçları</h3>
          <LogTablosu loglar={araSonuc} />
        </div>
      )}
    </div>
  );
}
