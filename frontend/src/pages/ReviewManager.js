import React, { useState } from "react";
import API from "../api";


export default function ReviewManager() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [yorumSonuc, setYorumSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);
  const [istatistikSonuc, setIstatistikSonuc] = useState(null);

  const handleYorumTopla = async () => {
    if (!url) { setHata("URL gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, topla: true }));
    try { const res = await API.post("/api/review", { url }); setYorumSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, topla: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/review/liste"); setListeSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, liste: false }));
  };

  const handleIstatistik = async () => {
    setHata(""); setLoading(l => ({ ...l, istatistik: true }));
    try { const res = await API.get("/api/review/istatistik"); setIstatistikSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, istatistik: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">⭐</div>
        <div className="info"><h2>Review Manager</h2><p>Yorumları topla, listele ve istatistikleri görüntüle</p></div>
      </div>
      <div className="form-grup">
        <label>Sayfa URL</label>
        <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://ornek.com/sayfa" />
      </div>
      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleYorumTopla} disabled={loading.topla}>
          {loading.topla ? "⏳" : "⭐ Yorum Topla"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Listele"}
        </button>
        <button className="btn btn-outline" onClick={handleIstatistik} disabled={loading.istatistik}>
          {loading.istatistik ? "⏳" : "📊 İstatistik"}
        </button>
      </div>
      {hata && <div className="hata">{hata}</div>}
      {(yorumSonuc || listeSonuc) && (
        <div className="sonuc">
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {(Array.isArray(yorumSonuc || listeSonuc) ? yorumSonuc || listeSonuc : (yorumSonuc || listeSonuc).yorumlar || (yorumSonuc || listeSonuc).reviews || [yorumSonuc || listeSonuc]).map((y, i) => (
              <div key={i} style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <strong style={{ color: "var(--honey)" }}>{y.yazar || y.author || y.isim || "İsimsiz"}</strong>
                  <span style={{ color: "var(--orange)" }}>
                    {"★".repeat(y.puan ?? y.rating ?? 0)}{"☆".repeat(5 - (y.puan ?? y.rating ?? 0))}
                  </span>
                </div>
                <div style={{ color: "var(--text2)", fontSize: "0.8rem", marginBottom: "0.5rem" }}>
                  {y.tarih || y.date || y.zaman || "-"}
                </div>
                <div style={{ color: "var(--text)", fontSize: "0.85rem", lineHeight: 1.5 }}>
                  {y.yorum || y.review || y.metin || y.icerik || "-"}
                </div>
                {(y.cevap || y.yanit) && (
                  <div style={{ marginTop: "0.5rem", padding: "0.5rem", background: "var(--bg)", borderRadius: 6, borderLeft: "3px solid var(--olive2)" }}>
                    <span style={{ color: "var(--olive2)", fontSize: "0.75rem", fontWeight: 600 }}>Yanıt: </span>
                    <span style={{ color: "var(--text2)", fontSize: "0.8rem" }}>{y.cevap || y.yanit}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {istatistikSonuc && (
        <div className="sonuc">
          {Object.entries(istatistikSonuc).map(([k, v]) => (
            <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}
