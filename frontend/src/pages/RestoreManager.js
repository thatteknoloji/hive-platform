import React, { useState } from "react";
import API from "../api";


export default function RestoreManager() {
  const [yedek_id, setYedekId] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [onizleme, setOnizleme] = useState(null);
  const [sonuc, setSonuc] = useState(null);
  const [liste, setListe] = useState([]);

  const handleOnizle = async () => {
    if (!yedek_id) { setHata("Yedek ID gerekli"); return; }
    setHata(""); setOnizleme(null); setLoading(l => ({ ...l, onizle: true }));
    try {
      const res = await API.post("/api/restore/onizle", { yedek_id });
      setOnizleme(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, onizle: false }));
  };

  const handleGeriYukle = async () => {
    if (!yedek_id) { setHata("Yedek ID gerekli"); return; }
    if (!window.confirm(`${yedek_id} ID'li yedeği geri yüklemek istediğinize emin misiniz? Mevcut veriler değişebilir.`)) return;
    setHata(""); setSonuc(null); setLoading(l => ({ ...l, geri: true }));
    try {
      const res = await API.post("/api/restore/geri-yukle", { yedek_id });
      setSonuc(res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, geri: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try {
      const res = await API.get("/api/restore/liste");
      setListe(res.data?.sonuc?.kayitlar || res.data?.kayitlar || []);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, listele: false }));
  };

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">🔄</div>
        <div className="info">
          <h2>Restore Manager – Geri Yükleme Yöneticisi</h2>
          <p>Yedekleri önizleyin, geri yükleyin ve geçmiş geri yükleme kayıtlarını görüntüleyin.</p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-grup" style={{ maxWidth: 400 }}>
          <label>Yedek ID</label>
          <input value={yedek_id} onChange={e => setYedekId(e.target.value)} placeholder="örn: back_20240101_abc123" />
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-outline" onClick={handleOnizle} disabled={loading.onizle}>
          {loading.onizle ? "⏳" : "👁️ Önizle"}
        </button>
        <button className="btn btn-danger" onClick={handleGeriYukle} disabled={loading.geri}>
          {loading.geri ? "⏳ Geri Yükleniyor..." : "🔄 Geri Yükle"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Listele"}
        </button>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}

      {onizleme && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>👁️ Önizleme</h3>
          {onizleme.icerik && (
            <div className="item"><span className="key">İçerik: </span><span className="val">{typeof onizleme.icerik === "string" ? onizleme.icerik : JSON.stringify(onizleme.icerik)}</span></div>
          )}
          {onizleme.boyut && (
            <div className="item"><span className="key">Boyut: </span><span className="val">{onizleme.boyut}</span></div>
          )}
          {onizleme.modul && (
            <div className="item"><span className="key">Modül: </span><span className="val">{onizleme.modul}</span></div>
          )}
          {onizleme.tarih && (
            <div className="item"><span className="key">Tarih: </span><span className="val">{onizleme.tarih}</span></div>
          )}
          <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto", marginTop: "0.5rem" }}>
            {JSON.stringify(onizleme, null, 2)}
          </pre>
        </div>
      )}

      {sonuc && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", wordBreak: "break-all", maxHeight: 300, overflow: "auto" }}>
            {JSON.stringify(sonuc, null, 2)}
          </pre>
        </div>
      )}

      {liste.length > 0 && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📋 Geri Yükleme Geçmişi</h3>
          <div className="table-container" style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr><th>Tarih</th><th>Yedek Kaynağı</th><th>Durum</th></tr>
              </thead>
              <tbody>
                {liste.map((k, i) => (
                  <tr key={i}>
                    <td>{k.tarih || k.date || k.olusturulma}</td>
                    <td>{k.yedek_id || k.backup_source || k.kaynak}</td>
                    <td>
                      <span style={{
                        color: (k.durum === "başarılı" || k.status === "success") ? "var(--green)" :
                               (k.durum === "başarısız" || k.status === "failed") ? "var(--red)" : "var(--text2)"
                      }}>
                        {k.durum || k.status}
                      </span>
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
