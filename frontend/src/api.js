/**
 * Merkezi API istemcisi — tüm sayfalar bunu kullanmalı.
 */
import axios from "axios";
import { getStoredToken } from "./auth";
import { formatHiveApiError } from "./utils/hiveApiErrors";

// Dev: doğrudan backend (4001) — CRA proxy bazen backend kapalıyken sessizce düşer.
// Prod: same-origin /api via Nginx
const API_BASE =
  process.env.REACT_APP_API_URL ||
  (process.env.NODE_ENV === "development" ? "http://127.0.0.1:4001" : "");

const API = axios.create({
  baseURL: API_BASE,
  timeout: 90000,
});

API.interceptors.request.use((cfg) => {
  const token = getStoredToken();
  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`;
  } else if (process.env.NODE_ENV === "development" && process.env.REACT_APP_HIVE_API_KEY) {
    cfg.headers["X-API-Key"] = process.env.REACT_APP_HIVE_API_KEY;
  }
  return cfg;
});

API.interceptors.response.use(
  (res) => res,
  (err) => {
    const endpoint = err?.config?.url || "";
    const info = formatHiveApiError(err, endpoint);
    err.hiveErrorInfo = info;
    err.hiveMessage =
      info.statusCode === 0 || info.statusCode === 404 || info.statusCode === 401
        ? `${info.title} — ${info.action}`
        : (info.description ? `${info.title}: ${info.description}` : info.title);

    if (err?.response?.status === 401 && !endpoint.includes("/api/auth/login")) {
      const onLogin = typeof window !== "undefined" && window.location.pathname === "/login";
      if (!onLogin && typeof window !== "undefined") {
        import("./auth").then(({ clearStoredToken }) => {
          clearStoredToken();
          if (window.location.pathname !== "/login") {
            window.location.replace("/login");
          }
        });
      }
    }
    return Promise.reject(err);
  }
);

export default API;
