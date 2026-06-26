import { useEffect, useState } from "react";
import { useActiveProject } from "../context/ActiveProjectContext";

/** Site URL field seeded from active project (no hardcoded domain). */
export function useProjectSiteField(initial = "") {
  const { siteUrl } = useActiveProject();
  const [value, setValue] = useState(initial);
  useEffect(() => {
    if (siteUrl) setValue((prev) => prev || siteUrl);
  }, [siteUrl]);
  return [value, setValue];
}

/** Bare domain field seeded from active project. */
export function useProjectDomainField(initial = "") {
  const { domain } = useActiveProject();
  const [value, setValue] = useState(initial);
  useEffect(() => {
    if (domain) setValue((prev) => prev || domain.replace(/^https?:\/\//, "").replace(/\/$/, ""));
  }, [domain]);
  return [value, setValue];
}

/** Active project id field seeded from context. */
export function useProjectIdField(initial = "") {
  const { activeProjectId } = useActiveProject();
  const [value, setValue] = useState(initial);
  useEffect(() => {
    if (activeProjectId) setValue((prev) => prev || activeProjectId);
  }, [activeProjectId]);
  return [value, setValue];
}
