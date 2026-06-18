import React, { useState } from "react";
import API from "../api";


export default function ABTestPanel() {
  const [varyantA, setVaryantA] = useState("");
  const [varyantB, setVaryantB] = useState("");
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [baslatSonuc, setBaslatSonuc] = useState(null);
  const [listeSonuc, setListeSonuc] = useState(null);

  const handleBaslat = async () => {
    if (!varyantA || !varyantB) { setHata("Her iki varyant da gerekli"); return; }
    setHata(""); setLoading(l => ({ ...l, baslat: true }));
    try { const res = await API.post("/api/abtest", { varyant_a: varyantA, varyant_b: varyantB }); setBaslatSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, baslat: false }));
  };

  const handleListe = async () => {
    setHata(""); setLoading(l => ({ ...l, liste: true }));
    try { const res = await API.get("/api/abtest/liste"); setListeSonuc(res.data); }
    catch { setHata("Backend hatası"); }
    setLoading(l => ({ ...l, liste: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">🧪</div>
        <div className="info"><h2>A/B Test Paneli</h2><p>Varyant testleri oluştur, ziyaretçi ve dönüşümleri karşılaştır</p></div>
      </div>
      <div className="form-row">
        <div className="form-grup">
          <label>Varyant A</label>
          <input value={varyantA} onChange={e => setVaryantA(e.target.value)} placeholder="Varyant A açıklaması veya URL" />
        </div>
        <div className="form-grup">
          <label>Varyant B</label>
          <input value={varyantB} onChange={e => setVaryantB(e.target.value)} placeholder="Varyant B açıklaması veya URL" />
        </div>
      </div>
      <div className="btn-group">
        <button className="btn btn-primary" onClick={handleBaslat} disabled={loading.baslat}>
          {loading.baslat ? "⏳" : "🧪 Test Başlat"}
        </button>
        <button className="btn btn-outline" onClick={handleListe} disabled={loading.liste}>
          {loading.liste ? "⏳" : "📋 Testlerim"}
        </button>
      </div>
      {hata && <div className="hata">{hata}</div>}
      {baslatSonuc && !Array.isArray(baslatSonuc) && (
        <div className="sonuc">
          {Object.entries(baslatSonuc).map(([k, v]) => (
            <div key={k} className="item"><span className="key">{k}: </span><span className="val">{String(v)}</span></div>
          ))}
        </div>
      )}
      {(listeSonuc || (Array.isArray(baslatSonuc) && baslatSonuc)) && (
        <div className="sonuc">
          {(listeSonuc || baslatSonuc).length > 0 && <h4 style={{ color: "var(--honey)", marginBottom: "0.75rem" }}>A/B Test Sonuçları</h4>}
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {(listeSonuc || baslatSonuc || []).map((test, i) => (
              <div key={i} style={{ background: "var(--bg3)", border: "1px solid var(--border)", borderRadius: 8, padding: "1rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                  <strong style={{ color: "var(--honey)" }}>{test.ad || test.id || `Test #${i + 1}`}</strong>
                  <span style={{ color: test.kazanan ? "var(--green)" : "var(--text2)", fontWeight: 600 }}>
                    {test.kazanan ? `🏆 ${test.kazanan}` : "⏳ Devam ediyor"}
                  </span>
                </div>
                <div className="item"><span className="key">Varyant A: </span><span className="val">{test.varyant_a || test.a || "-"}</span></div>
                <div className="item"><span className="key">Varyant B: </span><span className="val">{test.varyant_b || test.b || "-"}</span></div>
                <div className="item"><span className="key">Ziyaretçi: </span><span className="val">{test.ziyaretci ?? test.visitors ?? "-"}</span></div>
                <div className="item"><span className="key">Dönüşüm: </span><span className="val">{test.donusum ?? test.conversions ?? "-"}</span></div>
                <div className="item"><span className="key">Anlamlılık: </span><span className="val">{test.anlamlilik ?? test.significance ?? test.guven ?? "-"}</span></div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
