import { useQuery } from "@tanstack/react-query";

import type { SelectionGroup, SelectionModel } from "../../lib/api";
import { getSelection } from "../../lib/api";
import { KeyEntry } from "./KeyEntry";
import { ProviderLogo } from "./ProviderLogo";
import { ProviderTag } from "./badges";
import { CLOUD_KEY_NAMES } from "./selectionMeta";
import { ViewNotice, ViewShell } from "./ViewShell";

// A read-only reference: what's available to prove — AND what isn't yet, with the one step that
// turns it on. Rendered from the selection panel (every catalog provider, available or not) rather
// than the available-only candidate list, so a cloud-only or no-Ollama user sees the missing
// providers and an inline way to configure them instead of an unexplained gap (WS-E1).
export function CandidatesView() {
  const selection = useQuery({ queryKey: ["selection"], queryFn: getSelection });

  return (
    <ViewShell
      title="Candidates"
      subtitle="The models, prompts, and providers available to prove. Mock candidates run instantly with no API key; cloud and local providers turn on once their key or host is configured — unconfigured ones show how below."
    >
      {selection.isLoading ? (
        <ViewNotice>Loading candidates…</ViewNotice>
      ) : selection.isError || !selection.data ? (
        <ViewNotice tone="error">
          Could not reach the local engine. Start it with <code>orionfold up</code>, then reload.
        </ViewNotice>
      ) : selection.data.providers.length === 0 ? (
        <ViewNotice>No candidates available.</ViewNotice>
      ) : (
        <ul className="grid gap-2">
          {selection.data.providers.map((g) => (
            <ProviderCard key={g.provider_id} group={g} />
          ))}
        </ul>
      )}
    </ViewShell>
  );
}

// One catalog provider. Available providers list their models; an unconfigured cloud provider
// explains its absence and offers the same inline KeyEntry used in run setup; an unconfigured
// local provider points at starting its host (no key to add).
function ProviderCard({ group }: { group: SelectionGroup }) {
  const keyName = CLOUD_KEY_NAMES[group.provider_id];
  return (
    <li className="grid gap-2 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) px-4 py-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <ProviderLogo providerId={group.provider_id} available={group.available} label={group.label} />
        <span className="font-medium text-(--color-ink)">{group.label}</span>
        <ProviderTag candidate={{ provider_id: group.provider_id, privacy: group.privacy }} />
        {!group.available ? (
          <span className="text-xs text-(--color-ink-faint)">Not configured</span>
        ) : null}
      </div>

      {group.available && group.models.length > 0 ? (
        <ul className="grid gap-1 pl-7">
          {group.models.map((m) => (
            <ModelRow key={m.candidate_id} model={m} />
          ))}
        </ul>
      ) : null}

      {!group.available && keyName ? (
        // Unconfigured cloud — reuse the proven inline KeyEntry (writes .env.local server-side,
        // never echoes the key, invalidates ["selection"] so this card flips to available live).
        <div className="flex flex-wrap items-center gap-2 pl-7">
          <span className="text-xs text-(--color-ink-faint)">
            Add a {keyName} key to compare {group.label} models.
          </span>
          <KeyEntry providerId={group.provider_id} providerLabel={group.label} keyName={keyName} />
        </div>
      ) : !group.available ? (
        // Unconfigured local — no key, it needs its host running.
        <p className="pl-7 text-xs text-(--color-ink-faint)">
          Start the local server (e.g. <code>ollama serve</code> or LM Studio), then reload.
        </p>
      ) : null}
    </li>
  );
}

// One model row inside an available provider. A curated HF/GGUF model that isn't pulled yet
// (available === false, carrying a repo_id) shows the one command that turns it on — the local
// mirror of the cloud "Add key" affordance (hf-own-models). All other models render plainly.
function ModelRow({ model }: { model: SelectionModel }) {
  const pullable = model.available === false && Boolean(model.repo_id);
  return (
    <li className="grid gap-1 text-sm text-(--color-ink-muted)">
      <div className="flex flex-wrap items-center gap-x-3">
        <span className={pullable ? "text-(--color-ink-muted)" : "text-(--color-ink)"}>
          {model.display_name}
        </span>
        <code className="text-xs text-(--color-ink-faint)">{model.model}</code>
        {pullable ? (
          <span className="text-xs text-(--color-ink-faint)">Not pulled</span>
        ) : null}
      </div>
      {pullable ? (
        <p className="text-xs text-(--color-ink-faint)">
          Pull to enable: <code className="text-(--color-ink-muted)">orionfold pull {model.repo_id}</code>
        </p>
      ) : null}
    </li>
  );
}
