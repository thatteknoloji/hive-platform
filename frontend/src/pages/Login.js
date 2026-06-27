import React, { useEffect, useState } from "react";
import API from "../api";
import { setStoredToken, clearStoredToken } from "../auth";
import { parseApiError } from "../utils/hiveApiErrors";

function sessionMessage() {
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get("session") === "expired") {
      return "Oturumunuz sona erdi. Lütfen tekrar giriş yapın.";
    }
  } catch {
    /* ignore */
  }
  return "";
}

export default function Login({ onSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(sessionMessage);
  const [healthWarn, setHealthWarn] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    API.get("/health", { timeout: 8000 })
      .then(() => {
        if (!cancelled) setHealthWarn("");
      })
      .catch(() => {
        if (!cancelled) {
          setHealthWarn(
            "Backend'e bağlanılamıyor. Sunucunun çalıştığından emin olun (bash scripts/start-hive.sh).",
          );
        }
      });
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!email.trim()) {
      setError("E-posta adresi gerekli.");
      return;
    }
    if (!password) {
      setError("Şifre gerekli.");
      return;
    }
    setLoading(true);
    clearStoredToken();
    try {
      const res = await API.post("/api/auth/login", { email: email.trim(), password });
      const token = res.data?.token;
      if (!token) {
        setError("Giriş başarısız — oturum token'ı alınamadı. Yöneticinize başvurun.");
        return;
      }
      setStoredToken(token);
      if (onSuccess) onSuccess(res.data);
      const next = new URLSearchParams(window.location.search).get("next");
      window.location.replace(next && next.startsWith("/") ? next : "/");
    } catch (err) {
      const status = err?.response?.status;
      if (status === 401) {
        setError("E-posta veya şifre hatalı. Bilgilerinizi kontrol edip tekrar deneyin.");
      } else if (status === 503) {
        setError("Panel kimlik doğrulama sunucuda yapılandırılmamış. Backend'i yeniden başlatın.");
      } else if (!err?.response) {
        setError(parseApiError(err, "/api/auth/login"));
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
          <span className="hive-topbar-logo" title="HIVE SEO OS">◆</span>
          <h1>HIVE SEO OS</h1>
          <p>Digital Asset Factory</p>
        </div>
        {healthWarn && (
          <div className="hive-login-error hive-login-warn" role="alert">
            {healthWarn}
          </div>
        )}
        <form onSubmit={handleSubmit} className="hive-login-form" noValidate>
          <label title="Panel giriş e-postanız">
            E-posta
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
              placeholder="admin@firma.com"
            />
          </label>
          <label title="Hesap şifreniz">
            Şifre
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
            />
          </label>
          {error && (
            <div className="hive-login-error" role="alert" aria-live="polite">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="hive-login-btn"
            title="Panele giriş yap"
          >
            {loading ? "Giriş yapılıyor…" : "Giriş yap"}
          </button>
        </form>
        <p className="hive-login-footer">
          <a href="/academy">SEO GEO AEO Fabrikası</a>
        </p>
      </div>
    </div>
  );
}
