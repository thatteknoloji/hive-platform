import React, { useState, useEffect } from "react";
import API from "../../api";

/**
 * BLACK FLAG modülleri için generic panel — dedicated sayfa yoksa API / ModulUI fallback.
 */
export default function BlackModulePanel({ moduleId, title, description }) {
  const [modul, setModul] = useState(null);
  const [inputs, setInputs] = useState({});
  const [sonuc, setSonuc] = useState(null);
  const [hata, setHata] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);

  useEffect(() => {
    setSonuc(null);
    setHata("");
    setInputs({});
    API.get(`/api/modul/${moduleId}`)
      .then((res) => setModul({ ...res.data, id: moduleId, ad: title, aciklama: description }))
      .catch(() => setModul({ id: moduleId, ad: title, aciklama: description, durum: "panel" }));
  }, [moduleId, title, description]);

  const apiPost = async (path, body = {}) => {
    setYukleniyor(true);
    setHata("");
    try {
      const res = await API.post(path, body);
      setSonuc(res.data);
    } catch (err) {
      const d = err?.response?.data?.detail;
      setHata(typeof d === "string" ? d : err?.message || "İstek başarısız");
    } finally {
      setYukleniyor(false);
    }
  };

  const runModule = () => apiPost(`/api/${moduleId}`, inputs);

  return (
    <div className="talon-page hive-page">
      <div className="header">
        <div className="icon">🏴‍☠️</div>
        <div className="info">
          <h2>{title}</h2>
          <p>{description || modul?.aciklama || "BLACK FLAG modülü"}</p>
        </div>
      </div>

      <div className="hive-alert" style={{ background: "rgba(120,0,0,0.15)", border: "1px solid #8b0000", padding: "0.75rem", borderRadius: 8, marginBottom: "1rem" }}>
        ⚠️ BLACK FLAG — yalnızca yetkili test ortamında kullanın.
      </div>

      {hata && <div className="hive-alert danger">{hata}</div>}

      <div className="talon-form">
        <button type="button" className="btn btn-danger" disabled={yukleniyor} onClick={runModule}>
          {yukleniyor ? "Çalışıyor…" : "▶ Modülü Çalıştır"}
        </button>
      </div>

      {sonuc && (
        <pre style={{ marginTop: "1rem", fontSize: "0.8rem", whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" }}>
          {JSON.stringify(sonuc, null, 2)}
        </pre>
      )}
    </div>
  );
}
