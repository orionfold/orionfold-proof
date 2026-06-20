import { useEffect, useState } from "react";

interface Health {
  status: string;
  service: string;
  version: string;
}

type Probe =
  | { state: "loading" }
  | { state: "ok"; health: Health }
  | { state: "error"; message: string };

// Plain fetch is deliberate for the Gate 4 skeleton. TanStack Query arrives with the
// vertical slice (Gate 5), when there is real server state worth caching.
function useHealth(): Probe {
  const [probe, setProbe] = useState<Probe>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return (await res.json()) as Health;
      })
      .then((health) => {
        if (!cancelled) setProbe({ state: "ok", health });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setProbe({ state: "error", message: err instanceof Error ? err.message : "unknown" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return probe;
}

function HealthCard() {
  const probe = useHealth();

  return (
    <section
      aria-label="API health"
      className="w-full max-w-md rounded-xl border border-[--color-panel-line] bg-[--color-panel-card] p-6"
    >
      <h2 className="text-sm font-medium uppercase tracking-wide text-[--color-ink-muted]">
        Local engine
      </h2>

      {probe.state === "loading" && (
        <p className="mt-3 text-[--color-ink-muted]">Checking the local engine…</p>
      )}

      {probe.state === "ok" && (
        <div className="mt-3 flex items-center gap-3">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400"
          />
          <p className="text-[--color-ink]">
            Connected · <span className="text-[--color-ink-muted]">{probe.health.service}</span> v
            {probe.health.version}
          </p>
        </div>
      )}

      {probe.state === "error" && (
        <div className="mt-3 flex items-center gap-3">
          <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-full bg-rose-400" />
          <p className="text-[--color-ink]">
            Engine unreachable <span className="text-[--color-ink-muted]">({probe.message})</span>
          </p>
        </div>
      )}
    </section>
  );
}

export function App() {
  return (
    <main className="flex min-h-full flex-col items-center justify-center gap-8 px-6 py-16">
      <header className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight">Orionfold Proof</h1>
        <p className="mt-2 max-w-md text-[--color-ink-muted]">
          Prove which AI model, prompt, or workflow is worth trusting.
        </p>
      </header>
      <HealthCard />
    </main>
  );
}
