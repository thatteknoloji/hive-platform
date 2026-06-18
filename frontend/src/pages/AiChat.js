import React, { useState, useRef, useEffect } from "react";
import API from "../api";


export default function AiChat() {
  const [prompt, setPrompt] = useState("");
  const [sohbet, setSohbet] = useState([
    { role: "system", text: "Cloudflare Workers AI (LLaMA 3.1 8B) ile sohbet etmeye hazırsın." }
  ]);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState("");
  const altRef = useRef(null);

  useEffect(() => {
    altRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [sohbet]);

  const gonder = async () => {
    if (!prompt.trim()) return;
    const yeniPrompt = prompt.trim();
    setPrompt("");
    setHata("");
    setSohbet(prev => [...prev, { role: "user", text: yeniPrompt }]);
    setYukleniyor(true);
    try {
      const res = await API.post("/api/ai_chat", { prompt: yeniPrompt });
      const cevap = res.data?.response || res.data?.sonuc?.response || "Cevap alınamadı";
      setSohbet(prev => [...prev, { role: "assistant", text: cevap }]);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || "Bağlantı hatası";
      setHata(msg);
      setSohbet(prev => [...prev, { role: "error", text: `Hata: ${msg}` }]);
    } finally {
      setYukleniyor(false);
    }
  };

  const tusla = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      gonder();
    }
  };

  return (
    <div className="ai-chat">
      <div style={{
        border: "1px solid #2a2a2a",
        borderRadius: 8,
        padding: 16,
        height: 400,
        overflowY: "auto",
        marginBottom: 12,
        background: "#111"
      }}>
        {sohbet.map((m, i) => (
          <div key={i} style={{
            marginBottom: 10,
            textAlign: m.role === "user" ? "right" : "left",
            opacity: m.role === "system" ? 0.5 : 1,
            fontSize: m.role === "system" ? 12 : 14
          }}>
            <div style={{
              display: "inline-block",
              padding: "8px 14px",
              borderRadius: 12,
              maxWidth: "80%",
              background: m.role === "user" ? "#1a6dff" : m.role === "error" ? "#5c1a1a" : "#2a2a2a",
              color: "#fff",
              whiteSpace: "pre-wrap"
            }}>
              {m.text}
            </div>
          </div>
        ))}
        {yukleniyor && (
          <div style={{ textAlign: "left", marginBottom: 10 }}>
            <div style={{
              display: "inline-block",
              padding: "8px 14px",
              borderRadius: 12,
              background: "#2a2a2a",
              color: "#888"
            }}>Yazıyor...</div>
          </div>
        )}
        <div ref={altRef} />
      </div>

      {hata && <div style={{ color: "#ff6b6b", marginBottom: 8, fontSize: 13 }}>{hata}</div>}

      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={tusla}
          placeholder="Mesajını yaz..."
          disabled={yukleniyor}
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid #333",
            background: "#1a1a1a",
            color: "#fff",
            fontSize: 14
          }}
        />
        <button
          onClick={gonder}
          disabled={yukleniyor || !prompt.trim()}
          style={{
            padding: "10px 20px",
            borderRadius: 8,
            border: "none",
            background: yukleniyor ? "#444" : "#1a6dff",
            color: "#fff",
            cursor: yukleniyor ? "not-allowed" : "pointer",
            fontWeight: 600
          }}
        >
          {yukleniyor ? "..." : "Gönder"}
        </button>
        <button
          onClick={() => { setSohbet([{ role: "system", text: "Sohbet sıfırlandı." }]); setHata(""); }}
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid #333",
            background: "transparent",
            color: "#888",
            cursor: "pointer"
          }}
        >
          Temizle
        </button>
      </div>
    </div>
  );
}
