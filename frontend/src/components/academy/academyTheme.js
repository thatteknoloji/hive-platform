import { useEffect, useState } from "react";

const THEME_KEY = "hive_academy_theme";
const READING_KEY = "hive_academy_reading_mode";

export function useAcademyTheme() {
  const [theme, setThemeState] = useState(() => localStorage.getItem(THEME_KEY) || "system");

  useEffect(() => {
    const root = document.documentElement;
    const apply = (mode) => {
      root.classList.remove("ha-theme-light", "ha-theme-dark");
      if (mode === "light") root.classList.add("ha-theme-light");
      else if (mode === "dark") root.classList.add("ha-theme-dark");
      else if (window.matchMedia("(prefers-color-scheme: light)").matches) {
        root.classList.add("ha-theme-light");
      }
    };
    apply(theme);
    localStorage.setItem(THEME_KEY, theme);
    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: light)");
      const handler = () => apply("system");
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
    return undefined;
  }, [theme]);

  const setTheme = (t) => setThemeState(t);
  return { theme, setTheme };
}

export function useReadingMode() {
  const [mode, setModeState] = useState(() => localStorage.getItem(READING_KEY) || "normal");
  const setMode = (m) => {
    setModeState(m);
    localStorage.setItem(READING_KEY, m);
  };
  return { mode, setMode };
}
