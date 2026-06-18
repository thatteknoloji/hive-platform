import React, { useState } from "react";
import API from "../api";

const SIM_WARNING =
  "Bu modül simülasyon amaçlıdır — gerçek Google Maps yorumu göndermez. Yasal risk nedeniyle canlı yorum API'si devre dışıdır.";

export default function MapsBot() {
  const [isletme, setIsletme] = useState("");
  const [puan, setPuan] = useState(5);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [hata, setHata] = useState("");
  const [sonuc, setSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);

  const handleSimulate = async () => {
    if (!isletme.trim()) {
      setHata("İşletme adı gerekli");
      return;
    }
    setHata("");
    setLoading(true);
    try {
      const res = await API.post("/api/maps/simulate", {
        place_name: isletme.trim(),
        rating: puan,
        comment: comment,
      });
      setSonuc(res.data);
    } catch (err) {
      setHata(err?.response?.data?.detail || err.message || "Backend hatası");
    } finally {
      setLoading(false);
    }
  };

  const handleListele = async () => {
    setHata("");
    setLoading(true);
    try {
      const url = isletme ? `/api/maps/yorumlar/${encodeURIComponent(isletme)}` : "/api/maps/yorumlar";
      const res = await API.get(url);
      setListeSonuc(res.data);
    } catch (err) {
      setHata(err.message || "Liste alınamadı");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">📍</div>
        <div className="info">
          <h2>Maps Saldırı Botu — Simülasyon</h2>
          <p>Google Maps yorum simülasyonu (canlı gönderim yok).</p>
        </div>
      </div>

      <div
        className="hive-alert"
        role="alert"
        style={{
          background: "rgba(255, 140, 0, 0.25)",
          border: "3px solid #ff8c00",
          padding: "1.25rem",
          borderRadius: 10,
          marginBottom: "1.5rem",
          fontSize: "1rem",
          fontWeight: 700,
          color: "#fff3cd",
          textAlign: "center",
        }}
      >
        🚨 {SIM_WARNING}
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap" }}>
          <div className="form-grup" style={{ flex: 2, minWidth: 200 }}>
            <label>İşletme Adı</label>
            <input value={isletme} onChange={(e) => setIsletme(e.target.value)} placeholder="örn: Cafe Vienna" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 100 }}>
            <label>Puan (1-5)</label>
            <input type="number" value={puan} onChange={(e) => setPuan(parseInt(e.target.value, 10) || 5)} min={1} max={5} />
          </div>
        </div>
        <div className="form-grup" style={{ marginTop: "0.5rem" }}>
          <label>Yorum metni (simülasyon)</label>
          <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} style={{ width: "100%" }} />
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-outline" onClick={handleSimulate} disabled={loading}>
          {loading ? "Simüle ediliyor…" : "🧪 Simülasyon Çalıştır"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading}>
          📋 Simülasyon Geçmişi
        </button>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}

      {sonuc && (
        <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", marginTop: "1rem" }}>
          <p style={{ color: "var(--success)", fontWeight: 600 }}>{sonuc.message || "Simülasyon tamamlandı"}</p>
          <pre style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", maxHeight: 250, overflow: "auto" }}>
            {JSON.stringify(sonuc, null, 2)}
          </pre>
        </div>
      )}
      {listeSonuc && (
        <pre style={{ marginTop: "1rem", fontSize: "0.8rem", whiteSpace: "pre-wrap", maxHeight: 300, overflow: "auto" }}>
          {JSON.stringify(listeSonuc, null, 2)}
        </pre>
      )}
    </div>
  );
}
