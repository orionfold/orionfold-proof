// web/src/features/proof/KeyEntry.tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { setProviderKey } from "../../lib/api";

// Inline key entry for an unavailable cloud provider. The key is written to .env.local server-side
// (never echoed); on success we invalidate selection + recipes so availability flips live.
// Nested-form-safe (the #4 lesson): a div, type="button", and Enter handled locally — it must NOT
// submit the surrounding RunSetup <form>. The value lives only in local state and clears on success.
export function KeyEntry({
  providerId,
  providerLabel,
  keyName,
}: {
  providerId: string;
  providerLabel: string;
  keyName: string;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");

  const mutation = useMutation({
    mutationFn: (key: string) => setProviderKey(providerId, key),
    onSuccess: () => {
      setValue("");
      setOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["selection"] });
      void queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });

  function submit() {
    const key = value.trim();
    if (key) mutation.mutate(key);
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg border border-dashed border-(--color-panel-line) px-3 py-2 text-xs text-(--color-ink-muted) hover:border-(--color-panel-line-strong)"
      >
        Add key
      </button>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <input
        autoFocus
        type="password"
        autoComplete="off"
        aria-label={`${providerLabel} API key`}
        placeholder={keyName}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            e.stopPropagation();
            submit();
          } else if (e.key === "Escape") {
            setValue("");
            setOpen(false);
          }
        }}
        className="w-52 rounded-lg border border-(--color-panel-line) bg-(--color-panel) px-2 py-1.5 text-(--color-ink)"
      />
      <button
        type="button"
        onClick={submit}
        disabled={mutation.isPending}
        className="rounded-lg bg-(--color-accent-strong) px-2 py-1.5 text-(--color-accent-ink) disabled:opacity-40"
      >
        Save key
      </button>
      {mutation.isError ? (
        <span role="alert" className="text-xs text-rose-300">
          Could not save the key.
        </span>
      ) : null}
    </div>
  );
}
