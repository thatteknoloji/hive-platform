const RESTART_CMD = "bash scripts/stop-hive.sh && bash scripts/start-hive.sh";

/**
 * HIVE OS API hatalarını kullanıcı dostu kart verisine dönüştürür.
 * Raw "Not Found" asla döndürülmez.
 */
export function formatHiveApiError(err, endpoint = "/api/unknown") {
  const statusCode = err?.response?.status;
  const detail = err?.response?.data?.detail;
  const detailStr = typeof detail === "string" ? detail : "";
  const isNotFound = statusCode === 404 || detailStr === "Not Found";

  if (isNotFound) {
    return {
      title: "Backend endpoint bulunamadı",
      description: "Bu ekranın API route'u eksik veya backend eski çalışıyor.",
      endpoint,
      statusCode: statusCode || 404,
      action: `Backend'i yeniden başlatın: ${RESTART_CMD}`,
    };
  }

  if (statusCode === 401) {
    return {
      title: "API anahtarı geçersiz",
      description: "İstek yetkilendirme hatası aldı.",
      endpoint,
      statusCode: 401,
      action: "Giriş yapın veya backend/.env HIVE_API_KEY ile REACT_APP_HIVE_API_KEY eşleşmeli (dev).",
    };
  }

  if (!err?.response && /network|failed to fetch/i.test(err?.message || "")) {
    return {
      title: "Backend'e bağlanılamıyor",
      description: "Sunucu yanıt vermiyor.",
      endpoint,
      statusCode: 0,
      action: "Backend kapalı olabilir. Başlatın: bash scripts/start-hive.sh",
    };
  }

  const msg = err?.hiveMessage || detailStr || err?.message || "Bilinmeyen hata";
  if (msg === "Not Found") {
    return {
      title: "Backend endpoint bulunamadı",
      description: "Bu ekranın API route'u eksik veya backend eski çalışıyor.",
      endpoint,
      statusCode: statusCode || 404,
      action: `Backend'i yeniden başlatın: ${RESTART_CMD}`,
    };
  }

  return {
    title: msg,
    description: null,
    endpoint,
    statusCode: statusCode || null,
    action: statusCode >= 500
      ? `Sunucu hatası — logları kontrol edin veya yeniden başlatın: ${RESTART_CMD}`
      : "Sayfayı yenileyin veya birkaç saniye sonra tekrar deneyin.",
  };
}

/** Kısa hata metni — HiveAlert için */
export function parseApiError(err, endpoint = "") {
  const info = formatHiveApiError(err, endpoint);
  if (info.statusCode === 0) {
    return `${info.title} — ${info.action}`;
  }
  if (info.statusCode === 401) {
    return info.action;
  }
  if (info.statusCode === 404) {
    return `${info.title} — ${info.action}`;
  }
  return info.description ? `${info.title}: ${info.description}` : info.title;
}

/** @deprecated use formatHiveApiError */
export const formatMissionControlApiError = formatHiveApiError;
