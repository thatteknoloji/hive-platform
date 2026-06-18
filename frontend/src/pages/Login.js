import React, { useState } from "react";
import API from "../api";
import { setStoredToken, clearStoredToken } from "../auth";
import { parseApiError } from "../utils/hiveApiErrors";

export default function Login({ onSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    clearStoredToken();
    try {
      const res = await API.post("/api/auth/login", { email, password });
      const token = res.data?.token;
      if (!token) {
        setError("Giriş başarısız — token alınamadı.");
        return;
      }
      setStoredToken(token);
      if (onSuccess) onSuccess(res.data);
      window.location.replace("/");
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        setError("E-posta veya şifre hatalı.");
      } else if (status === 503) {
        setError("Panel kimlik doğrulama sunucuda yapılandırılmamış. Backend'i yeniden başlatın.");
      } else {
        setError(parseApiError(err, "/api/auth/login"));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="hive-login-page">
      <div className="hive-login-bg-grid" />
      <div className="hive-login-spotlight" />
      <div className="hive-login-card">
        <div className="hive-login-brand">
          <span className="hive-topbar-logo">◆</span>
          <h1>HIVE SEO OS</h1>
          <p>Digital Asset Factory</p>
        </div>
        <form onSubmit={handleSubmit} className="hive-login-form">
          <label>
            E-posta
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label>
            Şifre
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <div className="hive-login-error">{error}</div>}
          <button type="submit" disabled={loading} className="hive-login-btn">
            {loading ? "Giriş yapılıyor…" : "Giriş yap"}
          </button>
        </form>
      </div>
    </div>
  );
}
