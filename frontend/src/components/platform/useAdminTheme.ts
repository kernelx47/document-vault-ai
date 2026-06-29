"use client";

import { useCallback, useEffect, useState } from "react";

export type AdminTheme = "light" | "dark";

const STORAGE_KEY = "vault-admin-theme";

export function useAdminTheme() {
  const [theme, setThemeState] = useState<AdminTheme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY) as AdminTheme | null;
    if (stored === "light" || stored === "dark") {
      setThemeState(stored);
    }
    setMounted(true);
  }, []);

  const setTheme = useCallback((next: AdminTheme) => {
    setThemeState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((current) => {
      const next: AdminTheme = current === "dark" ? "light" : "dark";
      window.localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  return { theme, setTheme, toggleTheme, mounted };
}
