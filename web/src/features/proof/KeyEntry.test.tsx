// web/src/features/proof/KeyEntry.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KeyEntry } from "./KeyEntry";
import * as api from "../../lib/api";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

afterEach(() => vi.restoreAllMocks());

describe("KeyEntry", () => {
  it("submits the typed key to setProviderKey", async () => {
    const spy = vi
      .spyOn(api, "setProviderKey")
      .mockResolvedValue({ provider_id: "anthropic", available: true });
    wrap(<KeyEntry providerId="anthropic" providerLabel="Anthropic" keyName="ANTHROPIC_API_KEY" />);
    fireEvent.click(screen.getByRole("button", { name: /add key/i }));
    fireEvent.change(screen.getByLabelText(/anthropic api key/i), {
      target: { value: "sk-ant-xyz" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save key/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("anthropic", "sk-ant-xyz"));
  });

  it("does not submit an outer form when Save is clicked or Enter pressed", () => {
    vi.spyOn(api, "setProviderKey").mockResolvedValue({ provider_id: "anthropic", available: true });
    const onSubmit = vi.fn((e: React.FormEvent) => e.preventDefault());
    wrap(
      <form aria-label="outer" onSubmit={onSubmit}>
        <KeyEntry providerId="anthropic" providerLabel="Anthropic" keyName="ANTHROPIC_API_KEY" />
      </form>,
    );
    fireEvent.click(screen.getByRole("button", { name: /add key/i }));
    const field = screen.getByLabelText(/anthropic api key/i);
    fireEvent.keyDown(field, { key: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: /save key/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
