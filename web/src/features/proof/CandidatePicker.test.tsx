import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";

import { CandidatePicker } from "./CandidatePicker";
import type { ProviderHealth, SelectionPanel } from "../../lib/api";

// PANEL includes an unavailable Anthropic (cloud) provider; KeyEntry calls useQueryClient at
// render, so all renders of PANEL now require a QueryClientProvider wrapper.
function withQueryClient(ui: ReactNode) {
  return render(
    <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>,
  );
}

const PANEL: SelectionPanel = {
  providers: [
    {
      provider_id: "mock_good",
      label: "Mock · good",
      privacy: "local",
      available: true,
      supports_custom: false,
      candidate_id: "mock_good",
      models: [],
    },
    {
      provider_id: "anthropic",
      label: "Anthropic",
      privacy: "cloud",
      available: false,
      supports_custom: true,
      candidate_id: null,
      models: [
        { candidate_id: "anthropic:claude-haiku-4-5", model: "claude-haiku-4-5", display_name: "Claude Haiku 4.5", tier: "economy", cost_class: "$", context_window: 200000, latest: false, recommended: true },
      ],
    },
    {
      provider_id: "ollama",
      label: "Ollama",
      privacy: "local",
      available: true,
      supports_custom: true,
      candidate_id: null,
      models: [
        { candidate_id: "ollama:llama3.2", model: "llama3.2", display_name: "Llama 3.2", tier: "balanced", cost_class: "free", context_window: 8192, latest: true, recommended: true },
      ],
    },
  ],
};

test("renders a mock chip and provider model chips", () => {
  withQueryClient(<CandidatePicker panel={PANEL} selected={["mock_good"]} onToggle={vi.fn()} />);
  expect(screen.getByRole("checkbox", { name: "Mock · good" })).toBeChecked();
  expect(screen.getByText("Claude Haiku 4.5")).toBeVisible();
  expect(screen.getByText("Llama 3.2")).toBeVisible();
});

test("toggling an available model chip emits its candidate_id", () => {
  const onToggle = vi.fn();
  withQueryClient(<CandidatePicker panel={PANEL} selected={[]} onToggle={onToggle} />);
  fireEvent.click(screen.getByLabelText("Llama 3.2"));
  expect(onToggle).toHaveBeenCalledWith("ollama:llama3.2");
});

test("unavailable provider model chips are disabled", () => {
  withQueryClient(<CandidatePicker panel={PANEL} selected={[]} onToggle={vi.fn()} />);
  expect(screen.getByLabelText("Claude Haiku 4.5")).toBeDisabled();
});

test("custom entry builds a provider:model candidate id", () => {
  const onToggle = vi.fn();
  withQueryClient(<CandidatePicker panel={PANEL} selected={[]} onToggle={onToggle} />);
  fireEvent.click(screen.getByRole("button", { name: /custom model for Ollama/i }));
  fireEvent.change(screen.getByLabelText(/custom Ollama model/i), { target: { value: "phi3:mini" } });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));
  expect(onToggle).toHaveBeenCalledWith("ollama:phi3:mini");
});

test("custom Add adds a candidate without submitting a surrounding form", () => {
  const onToggle = vi.fn();
  const onSubmit = vi.fn((e) => e.preventDefault());
  render(
    <QueryClientProvider client={new QueryClient()}>
      <form onSubmit={onSubmit}>
        <CandidatePicker panel={PANEL} selected={[]} onToggle={onToggle} />
      </form>
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: /custom model for Ollama/i }));
  fireEvent.change(screen.getByLabelText(/custom Ollama model/i), { target: { value: "phi3:mini" } });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));
  expect(onToggle).toHaveBeenCalledWith("ollama:phi3:mini");
  expect(onSubmit).not.toHaveBeenCalled();
});

test("offers a key entry on a greyed cloud provider", () => {
  const panel = {
    providers: [
      {
        provider_id: "anthropic",
        label: "Anthropic",
        privacy: "cloud" as const,
        available: false,
        supports_custom: true,
        candidate_id: null,
        models: [
          {
            candidate_id: "anthropic:claude-haiku-4-5",
            model: "claude-haiku-4-5",
            display_name: "Claude Haiku 4.5",
            tier: "economy" as const,
            cost_class: "$" as const,
            context_window: 200000,
            latest: false,
            recommended: true,
          },
        ],
      },
    ],
  };
  render(
    <QueryClientProvider client={new QueryClient()}>
      <CandidatePicker panel={panel} selected={[]} onToggle={() => {}} />
    </QueryClientProvider>,
  );
  expect(screen.getByRole("button", { name: /add key/i })).toBeInTheDocument();
});

// --- health gating: a configured provider whose probe failed is hard-gated ---------------------

const HEALTHY_PANEL: SelectionPanel = {
  providers: [
    {
      provider_id: "anthropic",
      label: "Anthropic",
      privacy: "cloud",
      available: true, // key IS present...
      supports_custom: true,
      candidate_id: null,
      models: [
        { candidate_id: "anthropic:claude-haiku-4-5", model: "claude-haiku-4-5", display_name: "Claude Haiku 4.5", tier: "economy", cost_class: "$", context_window: 200000, latest: false, recommended: true },
      ],
    },
  ],
};

function healthMap(entries: ProviderHealth[]): Map<string, ProviderHealth> {
  return new Map(entries.map((h) => [h.provider_id, h]));
}

test("a configured provider with a failed health probe has disabled chips", () => {
  const health = healthMap([
    { provider_id: "anthropic", status: "auth", message: "HTTP 401", remediation: "Check `ANTHROPIC_API_KEY`." },
  ]);
  withQueryClient(
    <CandidatePicker panel={HEALTHY_PANEL} selected={[]} onToggle={vi.fn()} health={health} />,
  );
  // ...but the probe says the key is bad, so the chip is hard-gated.
  expect(screen.getByLabelText("Claude Haiku 4.5")).toBeDisabled();
  // The custom escape hatch is suppressed too (the whole provider is unusable).
  expect(screen.queryByRole("button", { name: /custom model for Anthropic/i })).toBeNull();
});

test("a failed health probe shows a badge and its remediation", () => {
  const health = healthMap([
    {
      provider_id: "anthropic",
      status: "quota",
      message: "HTTP 429",
      remediation: "Quota or rate limit hit. Retry shortly.",
    },
  ]);
  withQueryClient(
    <CandidatePicker panel={HEALTHY_PANEL} selected={[]} onToggle={vi.fn()} health={health} />,
  );
  expect(screen.getByText(/Quota \/ rate limit/i)).toBeVisible();
  expect(screen.getByText(/Quota or rate limit hit/i)).toBeVisible();
});

test("a healthy provider stays enabled", () => {
  const health = healthMap([
    { provider_id: "anthropic", status: "ok", message: "Reachable and authorized.", remediation: "" },
  ]);
  withQueryClient(
    <CandidatePicker panel={HEALTHY_PANEL} selected={[]} onToggle={vi.fn()} health={health} />,
  );
  expect(screen.getByLabelText("Claude Haiku 4.5")).not.toBeDisabled();
});

test("no health data yet leaves providers enabled (render-first, probe-async)", () => {
  withQueryClient(
    <CandidatePicker panel={HEALTHY_PANEL} selected={[]} onToggle={vi.fn()} />,
  );
  expect(screen.getByLabelText("Claude Haiku 4.5")).not.toBeDisabled();
});
