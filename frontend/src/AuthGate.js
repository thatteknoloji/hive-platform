import React, { useCallback, useEffect, useState } from "react";
import API from "./api";
import { clearStoredToken, getStoredToken } from "./auth";
import Login from "./pages/Login";
import App from "./App";

export default function AuthGate() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [authRequired, setAuthRequired] = useState(true);
  const isLoginPath = typeof window !== "undefined" && window.location.pathname === "/login";

  const checkSession = useCallback(async () => {
    setLoading(true);
    try {
      const res = await API.get("/api/auth/me");
      if (res.data?.authenticated) {
        setUser(res.data.user || { email: "" });
        setAuthRequired(true);
      } else if (res.data?.auth_required === false) {
        setAuthRequired(false);
        setUser({ email: "dev" });
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  const handleLogout = useCallback(async () => {
    try {
      await API.post("/api/auth/logout");
    } catch {
      /* ignore */
    }
    clearStoredToken();
    setUser(null);
    try {
      sessionStorage.removeItem("hive_mesh_tab");
    } catch {
      /* ignore */
    }
    window.location.replace("/login");
  }, []);

  if (loading) {
    return (
      <div className="hive-login-page">
        <div className="hive-login-card">
          <p>Oturum kontrol ediliyor…</p>
        </div>
      </div>
    );
  }

  if (isLoginPath) {
    if (user && authRequired) {
      window.location.replace("/");
      return null;
    }
    return <Login onSuccess={(data) => setUser(data?.user || { email: "" })} />;
  }

  if (authRequired && !user) {
    window.location.replace("/login");
    return null;
  }

  return <App onLogout={handleLogout} user={user} />;
}
