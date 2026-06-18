import React, { useCallback, useEffect, useState } from "react";
import { gostergeFromPath, parseProjectsPath } from "../../config/hiveOsRoutes";
import ProjectsList from "./ProjectsList";
import ProjectWizard from "./ProjectWizard";
import ProjectDetail from "./ProjectDetail";

function routeFromLocation() {
  return parseProjectsPath(window.location.pathname);
}

export default function ProjectsHub({ setGosterge }) {
  const [route, setRoute] = useState(routeFromLocation);

  const navigatePath = useCallback((path) => {
    window.history.pushState({ hiveOsProjects: true }, "", path);
    const osId = gostergeFromPath(path);
    if (osId && setGosterge) setGosterge(osId);
    setRoute(parseProjectsPath(path));
  }, [setGosterge]);

  useEffect(() => {
    const onPop = () => setRoute(routeFromLocation());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  if (route?.mode === "wizard") {
    return <ProjectWizard onNavigate={navigatePath} />;
  }
  if (route?.mode === "detail" && route.projectId) {
    return <ProjectDetail projectId={route.projectId} onNavigate={navigatePath} />;
  }
  return <ProjectsList onNavigate={navigatePath} />;
}
