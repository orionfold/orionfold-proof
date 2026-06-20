import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Wraps a component in an isolated QueryClient (retries off, so error states surface fast).
export function renderWithQuery(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

// Routes a mocked fetch by URL so a test can serve health/datasets/candidates together.
export function mockFetchByUrl(routes: Record<string, unknown>) {
  return (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    const match = Object.keys(routes).find((key) => url.includes(key));
    if (!match) return Promise.reject(new Error(`unmocked url: ${url}`));
    return Promise.resolve(new Response(JSON.stringify(routes[match])));
  };
}
