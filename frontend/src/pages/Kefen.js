import React, { useState } from "react";
import API from "../api";


export default function Kefen() {
  const [domain, setDomain] = useState("");
  const [adet, setAdet] = useState(100);
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [analizSonuc, setAnalizSonuc] = useState(null);
  const [btkSonuc, setBtkSonuc] = useState(null);
  const [spamSonuc, setSpamSonuc] = useState(null);
  const [raporSonuc, setRaporSonuc] = useState(null);
  const [exportFormat, setExportFormat] = useState("csv");
  const [exportIcerik, setExportIcerik] = useState("");
  const [exportModalAcik, setExportModalAcik] = useState(false);

  const kopyala = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
  };

  const handleAnaliz = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata("");
    setLoading(l => ({ ...l, analiz: true }));
    try {
      const res = await API.post("/api/kefen/analiz", { domain });
      setAnalizSonuc(res.data);
    } catch (err) {
      setHata("Backend hatası: " + (err.message || ""));
    }
    setLoading(l => ({ ...l, analiz: false }));
  };

  const handleBtk = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata("");
    setLoading(l => ({ ...l, btk: true }));
    try {
      const res = await API.post("/api/kefen/btk", { domain });
      setBtkSonuc(res.data);
    } catch (err) {
      setHata("Backend hatası: " + (err.message || ""));
    }
    setLoading(l => ({ ...l, btk: false }));
  };

  const handleSpam = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata("");
    setLoading(l => ({ ...l, spam: true }));
    try {
      const res = await API.post("/api/kefen/spam", { domain, adet });
      setSpamSonuc(res.data);
    } catch (err) {
      setHata("Backend hatası: " + (err.message || ""));
    }
    setLoading(l => ({ ...l, spam: false }));
  };

  const handleRapor = async () => {
    if (!domain) { setHata("Domain gerekli"); return; }
    setHata("");
    setLoading(l => ({ ...l, rapor: true }));
    setAnalizSonuc(null);
    setBtkSonuc(null);
    setSpamSonuc(null);
    try {
      const res = await API.post("/api/kefen/rapor", { domain });
      setRaporSonuc(res.data);
    } catch (err) {
      setHata("Backend hatası: " + (err.message || ""));
    }
    setLoading(l => ({ ...l, rapor: false }));
  };

  const handleExport = (data) => {
    if (!data) return;
    if (exportFormat === "csv") {
      const satirlar = ["source,anchor,dofollow,date"];
      data.forEach(b => satirlar.push(`${b.source},${b.anchor},${b.dofollow},${b.date}`));
      setExportIcerik(satirlar.join("\n"));
    } else if (exportFormat === "json") {
      setExportIcerik(JSON.stringify(data, null, 2));
    } else {
      setExportIcerik(data.map(b => `${b.source} | ${b.anchor} | ${b.dofollow ? "dofollow" : "nofollow"} | ${b.date}`).join("\n"));
    }
    setExportModalAcik(true);
  };

  const exportIndir = () => {
    const ext = exportFormat === "csv" ? "csv" : exportFormat === "json" ? "json" : "txt";
    const mime = exportFormat === "csv" ? "text/csv" : exportFormat === "json" ? "application/json" : "text/plain";
    const blob = new Blob([exportIcerik], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kefen_rapor.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const SonucKarti = ({ baslik, data, renk }) => (
    <div style={{
      background: "var(--bg3)", border: `1px solid ${renk || "var(--border)"}`, borderRadius: 8,
      padding: "1rem", marginTop: "1rem",
    }}>
      <h4 style={{ margin: "0 0 0.5rem", color: renk || "var(--text)" }}>{baslik}</h4>
      <pre style={{
        background: "var(--bg2)", padding: "0.8rem", borderRadius: 6,
        fontSize: "0.8rem", maxHeight: 300, overflow: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all",
      }}>
        {JSON.stringify(data, null, 2)}
      </pre>
      {data.backlinkler && (
        <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <select value={exportFormat} onChange={e => setExportFormat(e.target.value)}
            style={{ background: "var(--bg3)", color: "var(--text)", border: "1px solid var(--border)", borderRadius: 4, padding: "0.25rem", fontSize: "0.8rem" }}>
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
            <option value="txt">TXT</option>
          </select>
          <button className="btn btn-outline" onClick={() => handleExport(data.backlinkler)} style={{ fontSize: "0.8rem" }}>Dışa Aktar</button>
          <button className="btn btn-outline" onClick={() => kopyala(JSON.stringify(data.backlinkler, null, 2))} style={{ fontSize: "0.8rem" }}>📋 Kopyala</button>
        </div>
      )}
    </div>
  );

  return (
    <div className="talon-page">
      <div className="header">
        <div className="icon">⚰️</div>
        <div className="info">
          <h2>KEFEN (Catastrophe) – Rakip Backlink Profiline Müdahale</h2>
          <p>
            Rakip sitelerin backlink profiline sız, BTK'ya şikayet gönder,
            spam backlink yağdır ve kapsamlı rapor üret.
          </p>
        </div>
      </div>

      <div className="talon-form">
        <div className="form-row" style={{ display: "flex", gap: "0.8rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="form-grup" style={{ flex: 2, minWidth: 250 }}>
            <label>Hedef Domain</label>
            <input type="text" value={domain} onChange={e => setDomain(e.target.value)}
              placeholder="örn: rakipsitesi.com" />
          </div>
          <div className="form-grup" style={{ flex: 1, minWidth: 100 }}>
            <label>Backlink Adedi (spam için)</label>
            <input type="number" value={adet} onChange={e => setAdet(parseInt(e.target.value) || 100)} min={1} max={10000} />
          </div>
        </div>
      </div>

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
        <button className="btn btn-primary" onClick={handleAnaliz} disabled={loading.analiz}
          style={{ background: "var(--honey)", color: "#000" }}>
          {loading.analiz ? "Analiz Ediliyor..." : "🔍 Backlink Analizi"}
        </button>
        <button className="btn btn-primary" onClick={handleBtk} disabled={loading.btk}
          style={{ background: "var(--red)", color: "#fff" }}>
          {loading.btk ? "Gönderiliyor..." : "⚖️ BTK Şikayeti"}
        </button>
        <button className="btn btn-primary" onClick={handleSpam} disabled={loading.spam}
          style={{ background: "var(--orange)", color: "#000" }}>
          {loading.spam ? "Gönderiliyor..." : "💀 Spam Backlink Gönder"}
        </button>
        <button className="btn btn-primary" onClick={handleRapor} disabled={loading.rapor}
          style={{ background: "var(--purple)", color: "#fff" }}>
          {loading.rapor ? "Üretiliyor..." : "📊 Kapsamlı Rapor Üret"}
        </button>
      </div>

      {hata && (
        <div style={{ marginTop: "1rem", background: "rgba(255,68,68,0.1)", border: "1px solid var(--red)", borderRadius: 8, padding: "0.8rem", color: "var(--red)" }}>
          {hata}
        </div>
      )}

      {analizSonuc && (
        <SonucKarti baslik={`Backlink Analizi – ${analizSonuc.domain || domain}`} data={analizSonuc} renk="var(--honey)" />
      )}

      {btkSonuc && (
        <SonucKarti baslik={`BTK Şikayeti – ${btkSonuc.domain || domain}`} data={btkSonuc} renk="var(--red)" />
      )}

      {spamSonuc && (
        <SonucKarti baslik={`Spam Backlink – ${spamSonuc.hedef || domain}`} data={spamSonuc} renk="var(--orange)" />
      )}

      {raporSonuc && (
        <div style={{
          background: "var(--bg3)", border: "1px solid var(--purple)", borderRadius: 8,
          padding: "1rem", marginTop: "1.5rem",
        }}>
          <h3 style={{ margin: "0 0 0.5rem", color: "var(--purple)" }}>
            Kapsamlı Rapor – {raporSonuc.rakip || domain}
          </h3>
          <div style={{ marginBottom: "1rem" }}>
            <h4 style={{ margin: "0.5rem 0", color: "var(--honey)" }}>Öneriler</h4>
            <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
              {(raporSonuc.oneriler || []).map((o, i) => (
                <li key={i} style={{ fontSize: "0.9rem", marginBottom: "0.3rem" }}>{o}</li>
              ))}
            </ul>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <div style={{
              flex: 1, minWidth: 200, background: "var(--bg2)", borderRadius: 6, padding: "0.8rem",
              border: "1px solid var(--honey)",
            }}>
              <strong style={{ color: "var(--honey)" }}>Backlink Analizi</strong>
              <pre style={{ fontSize: "0.75rem", marginTop: "0.3rem", whiteSpace: "pre-wrap" }}>
                {JSON.stringify(raporSonuc.backlink_analizi, null, 2)}
              </pre>
            </div>
            <div style={{
              flex: 1, minWidth: 200, background: "var(--bg2)", borderRadius: 6, padding: "0.8rem",
              border: "1px solid var(--red)",
            }}>
              <strong style={{ color: "var(--red)" }}>BTK Şikayeti</strong>
              <pre style={{ fontSize: "0.75rem", marginTop: "0.3rem", whiteSpace: "pre-wrap" }}>
                {JSON.stringify(raporSonuc.btk_sikayet, null, 2)}
              </pre>
            </div>
            <div style={{
              flex: 1, minWidth: 200, background: "var(--bg2)", borderRadius: 6, padding: "0.8rem",
              border: "1px solid var(--orange)",
            }}>
              <strong style={{ color: "var(--orange)" }}>Spam Backlink</strong>
              <pre style={{ fontSize: "0.75rem", marginTop: "0.3rem", whiteSpace: "pre-wrap" }}>
                {JSON.stringify(raporSonuc.spam_sonuc, null, 2)}
              </pre>
            </div>
          </div>
          <button className="btn btn-outline" onClick={() => kopyala(JSON.stringify(raporSonuc, null, 2))}
            style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
            📋 Raporu Kopyala
          </button>
        </div>
      )}

      {exportModalAcik && (
        <div className="modal-overlay" onClick={() => setExportModalAcik(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 600 }}>
            <div className="modal-header">
              <h3>Dışa Aktar</h3>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button className="btn btn-primary" onClick={exportIndir} style={{ fontSize: "0.8rem", padding: "0.3rem 0.8rem" }}>İndir</button>
                <button className="btn btn-sm" onClick={() => setExportModalAcik(false)}
                  style={{ background: "transparent", border: "none", color: "var(--text2)", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
              </div>
            </div>
            <div className="modal-body">
              <pre style={{ background: "var(--bg2)", padding: "0.8rem", borderRadius: 6, fontSize: "0.75rem", maxHeight: 300, overflow: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                {exportIcerik.slice(0, 5000)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
