import "@testing-library/jest-dom";

// jsdom has no matchMedia; the theme system queries prefers-color-scheme. Default to "not dark"
// (light) so components render deterministically; individual tests override as needed.
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
