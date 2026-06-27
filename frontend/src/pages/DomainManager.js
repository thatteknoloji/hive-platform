import React, { useCallback, useEffect, useMemo, useState } from "react";
import API from "../api";
import { useActiveProject } from "../context/ActiveProjectContext";
import {
  HiveShell,
  HivePanel,
  HiveField,
  HiveInput,
  HiveBtn,
  HiveAlert,
  HiveEmptyState,
  HiveToast,
  HiveSkeleton,
  HiveStatusBadge,
} from "../components/HiveModuleUI";
import HiveApiErrorCard from "../components/HiveApiErrorCard";
import { formatHiveApiError } from "../utils/hiveApiErrors";

const API_PREFIX = "/api/v3/projects";

function normalizeDomain(raw) {
  return (raw || "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/\/.*$/, "")
    .replace(/\.$/, "");
}

function isValidDomain(domain) {
  const d = normalizeDomain(domain);
  if (!d || d.length > 253) return false;
  return /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/i.test(d);
}

function StatusRow({ label, value, tone }) {
  return (
    <div className="hive-domain-status-row">
      <span className="hive-domain-status-label" title={label}>{label}</span>
      <span className={`hive-domain-status-value hive-val-badge ${tone || ""}`}>{value || "—"}</span>
    </div>
  );
}

export default function DomainManager({ onNavigate }) {
  const { activeProjectId, project, loading: ctxLoading, refresh: refreshActive } = useActiveProject();
  const [domainInput, setDomainInput] = useState("");
  const [includeWww, setIncludeWww] = useState(true);
  const [domainStatus, setDomainStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(false);
  const [errorInfo, setErrorInfo] = useState(null);
  const [toast, setToast] = useState("");
  const [validationError, setValidationError] = useState("");

  const isPhoenixDemo = Boolean(
    project?.metadata?.phoenix_demo || project?.metadata?.customer_journey_demo,
  );

  const loadStatus = useCallback(async (pid) => {
    if (!pid) return;
    setStatusLoading(true);
    try {
      const res = await API.get(`${API_PREFIX}/${pid}/domain/status`);
      setDomainStatus(res.data);
    } catch {
      setDomainStatus(null);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    if (project?.domain) {
      setDomainInput(project.domain);
      } else {
      setDomainInput("");
    }
    if (activeProjectId) loadStatus(activeProjectId);
  }, [project?.domain, activeProjectId, loadStatus]);

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const domainValid = useMemo(() => isValidDomain(domainInput), [domainInput]);

  const saveDomain = async () => {
    setValidationError("");
    setErrorInfo(null);
    const clean = normalizeDomain(domainInput);
    if (!clean) {
      setValidationError("Domain alanı boş olamaz.");
      return;
    }
    if (!isValidDomain(clean)) {
      setValidationError("Geçerli bir domain girin (ör. demo.thiqos.com).");
      return;
    }
    setLoading(true);
    try {
      await API.patch(`${API_PREFIX}/${activeProjectId}`, { domain: clean });
      await API.post(`${API_PREFIX}/${activeProjectId}/domain/bind`, {
        domain: clean,
        include_www: includeWww,
      });
      window.dispatchEvent(new CustomEvent("hive-active-project-changed"));
      await refreshActive();
      await loadStatus(activeProjectId);
      setToast(`Domain kaydedildi: ${clean}`);
    } catch (e) {
      setErrorInfo(formatHiveApiError(e, `${API_PREFIX}/${activeProjectId}/domain/bind`));
    } finally {
      setLoading(false);
    }
  };

  const verifyDomain = async () => {
    setErrorInfo(null);
    if (!activeProjectId) return;
    setLoading(true);
    try {
      await loadStatus(activeProjectId);
      const res = await API.get(`${API_PREFIX}/${activeProjectId}`);
      const p = res.data?.project;
      const bound = p?.metadata?.domain_binding;
      if (bound?.domain) {
        setToast(`Doğrulama: ${bound.domain} — ${bound.status || "configured"} / SSL: ${bound.ssl_status || "pending"}`);
      } else if (p?.domain) {
        setToast(`Proje domain: ${p.domain} — bind için Kaydet & Bağla kullanın.`);
      } else {
        setToast("Henüz domain bağlanmamış.");
      }
    } catch (e) {
      setErrorInfo(formatHiveApiError(e, `${API_PREFIX}/${activeProjectId}/domain/status`));
    } finally {
      setLoading(false);
    }
  };

  if (ctxLoading) {
    return (
      <HiveShell title="Domain Manager" subtitle="Aktif proje domain bağlama">
        <HiveSkeleton lines={6} />
      </HiveShell>
    );
  }

  if (!activeProjectId) {
    return (
      <HiveShell
        title="Domain Manager"
        subtitle="Customer Journey — Adım 3: Domain"
        actions={(
          <HiveBtn variant="secondary" size="sm" title="Academy domain rehberi" onClick={() => window.open("/academy", "_blank")}>
            Academy
          </HiveBtn>
        )}
      >
        <HiveEmptyState
          icon="🌐"
          title="Aktif proje seçilmedi"
          description="Domain bağlamak için önce bir proje seçin. Phoenix demo için Projects ekranından demo projeyi aktif yapın."
          actionLabel="Projects'e git"
          onAction={() => onNavigate?.("projects")}
          navigateLabel="Academy Rehberi"
          onNavigate={() => window.open("/academy", "_blank")}
        />
      </HiveShell>
    );
  }

  const binding = domainStatus || project?.metadata?.domain_binding || {};

  return (
    <HiveShell
      title="Domain Manager"
      subtitle={`Customer Journey — ${project?.name || activeProjectId}`}
      actions={(
        <>
          <HiveBtn variant="secondary" size="sm" title="Domain Academy rehberi" onClick={() => window.open("/academy", "_blank")}>
            Academy
          </HiveBtn>
          <HiveBtn variant="secondary" size="sm" disabled={statusLoading} onClick={() => loadStatus(activeProjectId)} title="Durumu yenile">
            Yenile
          </HiveBtn>
        </>
      )}
    >
      {errorInfo && <HiveApiErrorCard errorInfo={errorInfo} />}
      {toast && <HiveToast message={toast} onClose={() => setToast("")} />}

      {isPhoenixDemo && (
        <HivePanel title="Phoenix Demo" className="hive-project-demo-banner">
          <p style={{ margin: "0 0 8px" }}>
            <strong>{project?.name}</strong>
            {project?.domain ? ` · ${project.domain}` : ""}
          </p>
          <HiveStatusBadge status="active" />
          <p className="hive-domain-hint" style={{ marginTop: 8, marginBottom: 0 }}>
            Customer Journey demo domain: <code>demo.thiqos.com</code> — SEO, Authority ve Publish modülleri bu domain&apos;i kullanır.
          </p>
        </HivePanel>
      )}

      <div className="hive-domain-grid">
        <HivePanel title="Proje Domain">
          <p className="hive-domain-hint">
            Domain aktif projeye kaydedilir; Talon, Rank Watcher ve Publisher Hub otomatik olarak bu adresi okur.
          </p>
          <HiveField label="Üretim domain">
            <HiveInput
              value={domainInput}
              onChange={(e) => {
                setDomainInput(e.target.value);
                setValidationError("");
              }}
              placeholder="demo.thiqos.com"
              title="Örn. demo.thiqos.com — http/https yazmayın"
              disabled={loading}
            />
          </HiveField>
          {validationError && <HiveAlert type="error">{validationError}</HiveAlert>}
          <label className="hive-domain-checkbox" title="www alt domain nginx bind'e dahil edilsin">
              <input
              type="checkbox"
              checked={includeWww}
              onChange={(e) => setIncludeWww(e.target.checked)}
              disabled={loading}
            />
            www dahil et
          </label>
          <div className="hive-domain-actions">
            <HiveBtn
              variant="primary"
              disabled={loading || !domainValid}
              onClick={saveDomain}
              title="Domain kaydet ve bind et"
            >
              {loading ? "Kaydediliyor…" : "Kaydet & Bağla"}
            </HiveBtn>
            <HiveBtn disabled={loading} onClick={verifyDomain} title="DNS / SSL / bind durumunu kontrol et">
              Domain Doğrula
            </HiveBtn>
          </div>
        </HivePanel>

        <HivePanel title="DNS / SSL / Health">
          {statusLoading ? (
            <HiveSkeleton lines={4} />
          ) : (
            <>
              <StatusRow label="Domain" value={binding.domain || project?.domain} tone="ok" />
              <StatusRow label="WWW" value={binding.www_domain || (includeWww && project?.domain ? `www.${normalizeDomain(project.domain)}` : "—")} />
              <StatusRow label="Bind durumu" value={binding.status || "not_configured"} tone={binding.status === "configured" ? "ok" : "warn"} />
              <StatusRow label="SSL" value={binding.ssl_status || "pending"} tone={binding.ssl_status === "active" ? "ok" : "warn"} />
              <StatusRow label="Target" value={binding.target_type || "hive_cloud"} />
              <StatusRow label="Proje ID" value={activeProjectId} />
              {!binding.domain && !project?.domain && (
                <HiveEmptyState
                  title="Domain henüz bağlı değil"
                  description="Sol panelden domain girin ve Kaydet & Bağla ile bağlayın."
                />
              )}
            </>
          )}
        </HivePanel>
    </div>

      <HivePanel title="Customer Journey notu" className="hive-domain-journey-note">
        <p style={{ margin: 0, fontSize: 13, opacity: 0.85 }}>
          Adım 3 tamamlandığında domain aktif projede görünür, Mission Control CJCR güncellenir ve sonraki modüller (SEO → Authority → Publish) aynı domain bağlamını kullanır.
        </p>
      </HivePanel>
    </HiveShell>
  );
}
