import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import API from "../api";

const ActiveProjectContext = createContext({
  activeProjectId: "",
  project: null,
  siteUrl: "",
  domain: "",
  loading: true,
  refresh: async () => {},
});

function siteUrlFromDomain(domain) {
  const d = (domain || "").trim();
  if (!d) return "";
  if (d.startsWith("http://") || d.startsWith("https://")) return d.replace(/\/$/, "");
  return `https://${d.replace(/\/$/, "")}`;
}

export function ActiveProjectProvider({ children }) {
  const [activeProjectId, setActiveProjectId] = useState("");
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await API.get("/api/v3/projects/active");
      setActiveProjectId(res.data?.active_project_id || "");
      setProject(res.data?.project || null);
    } catch {
      setActiveProjectId("");
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const onChange = () => refresh();
    window.addEventListener("hive-active-project-changed", onChange);
    return () => window.removeEventListener("hive-active-project-changed", onChange);
  }, [refresh]);

  const domain = (project?.domain || "").trim();
  const siteUrl = siteUrlFromDomain(domain);

  const value = useMemo(
    () => ({ activeProjectId, project, siteUrl, domain, loading, refresh }),
    [activeProjectId, project, siteUrl, domain, loading, refresh],
  );

  return (
    <ActiveProjectContext.Provider value={value}>
      {children}
    </ActiveProjectContext.Provider>
  );
}

export function useActiveProject() {
  return useContext(ActiveProjectContext);
}

export default ActiveProjectContext;
