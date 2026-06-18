import React, { useState, useEffect } from "react";
import API from "../api";


export default function SystemMonitor() {
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [saglik, setSaglik] = useState(null);
  const [monitorListe, setMonitorListe] = useState([]);

  useEffect(() => {
    handleKontrol();
    handleListele();
  }, []);

  const handleKontrol = async () => {
    setHata(""); setLoading(l => ({ ...l, kontrol: true }));
    try {
      const res = await API.get("/api/monitor/kontrol");
      setSaglik(res.data?.sonuc || res.data);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, kontrol: false }));
  };

  const handleListele = async () => {
    setHata(""); setLoading(l => ({ ...l, listele: true }));
    try {
      const res = await API.get("/api/monitor/liste");
      setMonitorListe(res.data?.sonuc?.kayitlar || res.data?.kayitlar || []);
    } catch (err) { setHata("Backend hatası: " + (err.response?.data?.detail || err.message)); }
    setLoading(l => ({ ...l, listele: false }));
  };

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">📊</div>
        <div className="info">
          <h2>System Monitor – Sistem İzleme</h2>
          <p>Backend durumunu, modül sayılarını, çalışma süresini ve bellek kullanımını takip edin.</p>
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-primary" onClick={handleKontrol} disabled={loading.kontrol}>
          {loading.kontrol ? "⏳ Kontrol Ediliyor..." : "🔄 Kontrol Et"}
        </button>
        <button className="btn btn-outline" onClick={handleListele} disabled={loading.listele}>
          {loading.listele ? "⏳" : "📋 Listele"}
        </button>
      </div>

      {hata && <div className="hata" style={{ marginTop: "1rem" }}>{hata}</div>}

      {saglik && (
        <div style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>🩺 Sistem Sağlığı</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.8rem" }}>
            {saglik.backend_durumu !== undefined && (
              <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", textAlign: "center" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.3rem" }}>{saglik.backend_durumu ? "✅" : "❌"}</div>
                <div style={{ fontWeight: 600 }}>Backend Durumu</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text2)" }}>{saglik.backend_durumu === true || saglik.backend_durumu === "aktif" ? "Aktif" : "Pasif"}</div>
              </div>
            )}
            {saglik.modul_sayisi !== undefined && (
              <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", textAlign: "center" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.3rem" }}>📦</div>
                <div style={{ fontWeight: 600 }}>Modül Sayısı</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text2)" }}>{saglik.modul_sayisi || saglik.module_count || 0}</div>
              </div>
            )}
            {saglik.uptime !== undefined && (
              <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", textAlign: "center" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.3rem" }}>⏱️</div>
                <div style={{ fontWeight: 600 }}>Uptime</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text2)" }}>{saglik.uptime}</div>
              </div>
            )}
            {saglik.bellek !== undefined && (
              <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", textAlign: "center" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.3rem" }}>🧠</div>
                <div style={{ fontWeight: 600 }}>Bellek</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text2)" }}>{saglik.bellek || saglik.memory || "-"}</div>
              </div>
            )}
            {saglik.cpu !== undefined && (
              <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", textAlign: "center" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.3rem" }}>⚡</div>
                <div style={{ fontWeight: 600 }}>CPU</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text2)" }}>{saglik.cpu || "-"}</div>
              </div>
            )}
            {saglik.disk !== undefined && (
              <div style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem", textAlign: "center" }}>
                <div style={{ fontSize: "2rem", marginBottom: "0.3rem" }}>💾</div>
                <div style={{ fontWeight: 600 }}>Disk</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text2)" }}>{saglik.disk || "-"}</div>
              </div>
            )}
          </div>
          <details style={{ marginTop: "0.5rem" }}>
            <summary style={{ fontSize: "0.8rem", cursor: "pointer", color: "var(--text2)" }}>Ham Yanıt</summary>
            <pre style={{ fontSize: "0.7rem", maxHeight: 200, overflow: "auto", background: "var(--bg)", padding: 8, borderRadius: 4, marginTop: 4 }}>
              {JSON.stringify(saglik, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {monitorListe.length > 0 && (
        <div className="sonuc" style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📋 Monitor Geçmişi</h3>
          <div className="table-container" style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr><th>Tarih</th><th>Durum</th><th>Modül</th><th>Detay</th></tr>
              </thead>
              <tbody>
                {monitorListe.map((m, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: "0.8rem", whiteSpace: "nowrap" }}>{m.tarih || m.date || m.zaman}</td>
                    <td>
                      <span style={{
                        color: (m.durum === "aktif" || m.status === "ok") ? "var(--green)" :
                               (m.durum === "pasif" || m.status === "down") ? "var(--red)" : "var(--text2)"
                      }}>
                        {m.durum || m.status}
                      </span>
                    </td>
                    <td>{m.modul || m.module || "-"}</td>
                    <td style={{ fontSize: "0.8rem", maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.detay || m.detail || "-"}</td>
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
