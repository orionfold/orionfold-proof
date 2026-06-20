import { useEffect, useState } from "react";

export type ThemeChoice = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

const KEY = "orionfold-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

export function getStoredChoice(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {
    /* localStorage unavailable — fall through to default */
  }
  return "system";
}

export function resolveTheme(choice: ThemeChoice): ResolvedTheme {
  if (choice === "light" || choice === "dark") return choice;
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

export function applyTheme(resolved: ResolvedTheme): void {
  document.documentElement.dataset.theme = resolved;
}

// One hook owns the choice, its resolved value, and live OS-change tracking while on "system".
export function useTheme(): {
  choice: ThemeChoice;
  resolved: ResolvedTheme;
  setChoice: (c: ThemeChoice) => void;
} {
  const [choice, setChoiceState] = useState<ThemeChoice>(getStoredChoice);
  const [resolved, setResolved] = useState<ResolvedTheme>(() => resolveTheme(getStoredChoice()));

  const setChoice = (next: ThemeChoice) => {
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* ignore persistence failure */
    }
    setChoiceState(next);
    const r = resolveTheme(next);
    setResolved(r);
    applyTheme(r);
  };

  useEffect(() => {
    if (choice !== "system") return;
    const mq = window.matchMedia(DARK_QUERY);
    const onChange = () => {
      const r: ResolvedTheme = mq.matches ? "dark" : "light";
      setResolved(r);
      applyTheme(r);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [choice]);

  return { choice, resolved, setChoice };
}
