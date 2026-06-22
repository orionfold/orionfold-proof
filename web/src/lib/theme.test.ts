import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { getStoredChoice, resolveTheme, useTheme } from "./theme";

afterEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  vi.restoreAllMocks();
});

function mockPrefersDark(dark: boolean) {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: dark,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList,
  );
}

test("defaults to dark when nothing is stored", () => {
  expect(getStoredChoice()).toBe("dark");
});

test("reads a stored explicit choice", () => {
  localStorage.setItem("orionfold-theme", "light");
  expect(getStoredChoice()).toBe("light");
});

test("resolves an explicit choice without consulting the OS", () => {
  expect(resolveTheme("light")).toBe("light");
  expect(resolveTheme("dark")).toBe("dark");
});

test("resolves system from prefers-color-scheme", () => {
  mockPrefersDark(true);
  expect(resolveTheme("system")).toBe("dark");
  mockPrefersDark(false);
  expect(resolveTheme("system")).toBe("light");
});

test("useTheme persists a choice and applies data-theme", () => {
  mockPrefersDark(true);
  const { result } = renderHook(() => useTheme());
  act(() => result.current.setChoice("light"));
  expect(localStorage.getItem("orionfold-theme")).toBe("light");
  expect(result.current.resolved).toBe("light");
  expect(document.documentElement.dataset.theme).toBe("light");
});
