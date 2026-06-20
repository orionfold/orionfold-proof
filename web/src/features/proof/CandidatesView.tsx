import { useQuery } from "@tanstack/react-query";

import { getCandidates } from "../../lib/api";
import { ProviderTag } from "./badges";
import { ViewNotice, ViewShell } from "./ViewShell";

// A read-only reference: what's available to prove. The provider boundary (Mock / Local / Cloud)
// is the thing to read at a glance — it's the difference between free-and-private and a paid call.
export function CandidatesView() {
  const candidates = useQuery({ queryKey: ["candidates"], queryFn: getCandidates });

  return (
    <ViewShell
      title="Candidates"
      subtitle="The models, prompts, and providers available to prove. Mock candidates run instantly with no API key; local and cloud providers appear here once their keys or hosts are configured."
    >
      {candidates.isLoading ? (
        <ViewNotice>Loading candidates…</ViewNotice>
      ) : candidates.isError || !candidates.data ? (
        <ViewNotice tone="error">
          Could not reach the local engine. Start it with <code>orionfold up</code>, then reload.
        </ViewNotice>
      ) : candidates.data.length === 0 ? (
        <ViewNotice>No candidates available.</ViewNotice>
      ) : (
        <ul className="grid gap-2">
          {candidates.data.map((c) => (
            <li
              key={c.id}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) px-4 py-3"
            >
              <span className="font-medium text-(--color-ink)">{c.label}</span>
              <ProviderTag candidate={c} />
              <span className="text-sm text-(--color-ink-faint)">
                <code className="text-(--color-ink-muted)">{c.id}</code>
              </span>
              <span className="ml-auto text-sm text-(--color-ink-muted)">
                {c.model ? <code>{c.model}</code> : "no model pinned"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </ViewShell>
  );
}
