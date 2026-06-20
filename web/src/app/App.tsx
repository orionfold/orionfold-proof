import { useEffect, useState } from "react";

import { getHealth, type Health } from "../lib/api";
import { ProofCockpit } from "../features/proof/ProofCockpit";

type Probe =
  | { state: "loading" }
  | { state: "ok"; health: Health }
  | { state: "error"; message: string };

// A compact engine status pill — calm reassurance that the local engine is reachable,
// without stealing focus from the proof loop below.
function useHealth(): Probe {
  const [probe, setProbe] = useState<Probe>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then((health) => {
        if (!cancelled) setProbe({ state: "ok", health });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setProbe({
            state: "error",
            message: err instanceof Error ? err.message : "unknown",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return probe;
}

function EngineStatus() {
  const probe = useHealth();

  if (probe.state === "loading") {
    return <span className="text-sm text-[--color-ink-muted]">Checking the local engine…</span>;
  }
  if (probe.state === "error") {
    return (
      <span className="flex items-center gap-2 text-sm text-[--color-ink]">
        <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-rose-400" />
        Engine unreachable <span className="text-[--color-ink-muted]">({probe.message})</span>
      </span>
    );
  }
  return (
    <span className="flex items-center gap-2 text-sm text-[--color-ink]">
      <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-emerald-400" />
      Connected · <span className="text-[--color-ink-muted]">{probe.health.service}</span> v
      {probe.health.version}
    </span>
  );
}

export function App() {
  return (
    <main className="mx-auto flex min-h-full max-w-3xl flex-col gap-10 px-6 py-12">
      <header className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold tracking-tight">Orionfold Proof</h1>
          <EngineStatus />
        </div>
        <p className="max-w-xl text-[--color-ink-muted]">
          Prove which AI model, prompt, or workflow is worth trusting — privately, with a
          repeatable receipt.
        </p>
      </header>
      <ProofCockpit />
    </main>
  );
}
