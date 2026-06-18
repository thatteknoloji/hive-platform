import React, { useState } from "react";
import API from "../api";


export default function DebugConsole() {
  const [modulId, setModulId] = useState("");
  const [parametreler, setParametreler] = useState("{}");
  const [satir, setSatir] = useState(50);
  const [loading, setLoading] = useState({});
  const [hata, setHata] = useState("");
  const [sonuc, setSonuc] = useState(null);

  const handleError = (err) => setHata(err?.response?.data?.detail || err?.message || "İstek başarısız");

  const testEt = async () => {
    setHata(""); setSonuc(null);
    setLoading(l => ({ ...l, test: true }));
    try {
      const res = await API.post("/api/debug/test", { modul_id: modulId });
      setSonuc(res.data?.sonuc || res.data);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, test: false }));
  };

  const hataAyikla = async () => {
    setHata(""); setSonuc(null);
    setLoading(l => ({ ...l, debug: true }));
    try {
      let params = {};
      try { params = JSON.parse(parametreler); } catch {}
      const res = await API.post("/api/debug/hata-ayikla", { modul_id: modulId, parametreler: params });
      setSonuc(res.data?.sonuc || res.data);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, debug: false }));
  };

  const performans = async () => {
    setHata(""); setSonuc(null);
    setLoading(l => ({ ...l, perf: true }));
    try {
      const res = await API.post("/api/debug/performans", { modul_id: modulId });
      setSonuc(res.data?.sonuc || res.data);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, perf: false }));
  };

  const logIncele = async () => {
    setHata(""); setSonuc(null);
    setLoading(l => ({ ...l, log: true }));
    try {
      const res = await API.post("/api/debug/log-incele", { modul_id: modulId, satir });
      setSonuc(res.data?.sonuc || res.data);
    } catch (err) { handleError(err); }
    setLoading(l => ({ ...l, log: false }));
  };

  return (
    <div>
      <div className="header">
        <div className="icon">🐛</div>
        <div className="info"><h2>Debug Console</h2><p>Modül test, hata ayıklama ve performans analizi</p></div>
      </div>
      <div style={{ background: "var(--bg2)", padding: "1rem", borderRadius: 8, marginBottom: "1rem" }}>
        <div className="form-row">
          <div className="form-grup" style={{ flex: 1 }}>
            <label>Modül ID</label>
            <input placeholder="talon, kefen, ranktracker..." value={modulId} onChange={e => setModulId(e.target.value)} />
          </div>
          <div className="form-grup" style={{ flex: 1 }}>
            <label>Parametreler (JSON)</label>
            <input placeholder='{"domain": "ornek.com"}' value={parametreler} onChange={e => setParametreler(e.target.value)} />
          </div>
          <div className="form-grup" style={{ flex: 0, minWidth: 100 }}>
            <label>Log Satır</label>
            <input type="number" value={satir} onChange={e => setSatir(parseInt(e.target.value) || 50)} />
          </div>
        </div>
        <div className="btn-group">
          <button className="btn btn-primary" onClick={testEt} disabled={loading.test}>{loading.test ? "⏳" : "🧪"} Modül Test</button>
          <button className="btn btn-outline" onClick={hataAyikla} disabled={loading.debug}>{loading.debug ? "⏳" : "🔍"} Hata Ayıkla</button>
          <button className="btn btn-outline" onClick={performans} disabled={loading.perf}>{loading.perf ? "⏳" : "⚡"} Performans</button>
          <button className="btn btn-outline" onClick={logIncele} disabled={loading.log}>{loading.log ? "⏳" : "📋"} Log İncele</button>
        </div>
      </div>
      {hata && <div className="hata">{hata}</div>}
      {sonuc && (
        <div className="sonuc">
          {Object.entries(sonuc).map(([k, v]) => (
            <div key={k} className="item">
              <span className="key">{k}: </span>
              <span className="val">{typeof v === "object" ? JSON.stringify(v, null, 2) : String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
