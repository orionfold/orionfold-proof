import { useEffect, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Database,
  FlaskConical,
  Monitor,
  Moon,
  Palette,
  SlidersHorizontal,
  Sun,
  Trash2,
  type LucideIcon,
} from "lucide-react";

import {
  clearAllData,
  getSettings,
  removeSampleData,
  seedSampleData,
  setPowermetricsOptin,
  setSandbox,
  setThresholds,
  type Thresholds,
} from "../../lib/api";
import { useTheme, type ThemeChoice } from "../../lib/theme";
import { ViewShell } from "./ViewShell";

// "1 dataset" / "4 datasets" — the bundled sample set spans several rubric classes now, so the
// seed/remove confirmation copy must agree in number with whatever the API reports.
function pluralize(count: number | undefined, noun: string): string {
  const n = count ?? 0;
  return `${n} ${noun}${n === 1 ? "" : "s"}`;
}

// One Data Management card: a Sandbox toggle plus seed / remove-samples / clear-all. Destructive
// actions use an inline two-step confirm (no modal dependency); Clear all is the only red control.
export function SettingsView() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: getSettings });

  const invalidateData = () => {
    void qc.invalidateQueries({ queryKey: ["datasets"] });
    void qc.invalidateQueries({ queryKey: ["runs"] });
    void qc.invalidateQueries({ queryKey: ["selection"] });
  };

  const sandbox = useMutation({
    mutationFn: (enabled: boolean) => setSandbox(enabled),
    onSuccess: (s) => {
      qc.setQueryData(["settings"], s);
      void qc.invalidateQueries({ queryKey: ["selection"] });
    },
  });
  const thresholds = useMutation({
    mutationFn: (t: Thresholds) => setThresholds(t),
    onSuccess: (s) => qc.setQueryData(["settings"], s),
  });
  const gpuTelemetry = useMutation({
    mutationFn: (enabled: boolean) => setPowermetricsOptin(enabled),
    onSuccess: (s) => qc.setQueryData(["settings"], s),
  });
  const seed = useMutation({ mutationFn: seedSampleData, onSuccess: invalidateData });
  const removeSamples = useMutation({ mutationFn: removeSampleData, onSuccess: invalidateData });
  const clearAll = useMutation({ mutationFn: clearAllData, onSuccess: invalidateData });

  const on = settings.data?.sandbox_enabled ?? false;
  const gpuOn = settings.data?.powermetrics_gpu_optin ?? false;

  return (
    <ViewShell
      title="Settings"
      subtitle="Manage appearance, your local data, and the simulated sandbox. Everything here stays on this machine."
    >
      {/* Full-width bento (R1c): the sections tile into a responsive grid so the width carries
          density instead of stretched single-toggle rows. Appearance + Runtime are compact tiles;
          the threshold sliders and data actions are content-rich, so they span both columns. */}
      <div className="grid w-full auto-rows-min grid-cols-1 gap-6 lg:grid-cols-2">
        <SettingCard
          icon={Palette}
          title="Appearance"
          description="Choose how the cockpit looks. New installs start in dark; pick System to follow your OS."
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm text-(--color-ink)">Theme</p>
              <p className="text-xs text-(--color-ink-faint)">
                Applies instantly and is remembered on this machine.
              </p>
            </div>
            <ThemeSwitcher />
          </div>
        </SettingCard>

        <SettingCard
          icon={FlaskConical}
          title="Runtime"
          description="How runs behave on this machine — the simulated sandbox and GPU sampling."
        >
          <Toggle
            label="Sandbox"
            description="Show simulated Mock models in the picker for keyless trial runs. Off by default — mock runs are not a real evaluation."
            checked={on}
            disabled={settings.isLoading || sandbox.isPending}
            onToggle={() => sandbox.mutate(!on)}
          />
          <Toggle
            label="GPU metrics"
            description={
              <>
                Sample Apple Silicon GPU utilization during a run via powermetrics, which needs
                passwordless <code>sudo</code> (run <code>sudo powermetrics</code> once in a
                terminal, or configure sudoers). Without it, GPU stays "unavailable" — this toggle
                never prompts for a password. Off by default. Everything stays on this machine.
              </>
            }
            checked={gpuOn}
            disabled={settings.isLoading || gpuTelemetry.isPending}
            onToggle={() => gpuTelemetry.mutate(!gpuOn)}
          />
        </SettingCard>

        <SettingCard
          className="lg:col-span-2"
          icon={SlidersHorizontal}
          title="Default scoring thresholds"
          description="The passing score each method prefills on a new run. The resolved value is recorded in the receipt, so tuning here only changes the starting point — it never alters a saved proof."
        >
          <ThresholdSliders
            value={settings.data?.thresholds}
            disabled={settings.isLoading || thresholds.isPending}
            onCommit={(t) => thresholds.mutate(t)}
          />
        </SettingCard>

        <SettingCard
          className="lg:col-span-2"
          icon={Database}
          title="Data management"
          description="Reset or populate this install. Sample data is generated by the simulated mocks and is clearly flagged."
        >
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <ActionRow
              label="Seed sample data"
              description="Add sample datasets and finished Proof Receipts so the product isn't empty. Re-running replaces the previous samples."
              actionLabel="Seed sample data"
              icon={<Database aria-hidden className="h-4 w-4" />}
              pending={seed.isPending}
              onConfirm={() => seed.mutate()}
              done={
                seed.isSuccess
                  ? `Seeded ${pluralize(seed.data?.datasets, "dataset")}, ${pluralize(seed.data?.receipts, "receipt")}.`
                  : null
              }
            />
            <ActionRow
              label="Remove sample data"
              description="Delete only the seeded sample datasets and receipts. Your own datasets and receipts are kept."
              actionLabel="Remove sample data"
              pending={removeSamples.isPending}
              onConfirm={() => removeSamples.mutate()}
              done={removeSamples.isSuccess ? "Sample data removed." : null}
            />
            <ActionRow
              label="Clear all data"
              description="Permanently delete ALL datasets and receipts on this install (samples and your own). Settings are kept. This cannot be undone."
              actionLabel="Clear all data"
              confirmLabel="Confirm clear"
              destructive
              icon={<Trash2 aria-hidden className="h-4 w-4" />}
              pending={clearAll.isPending}
              onConfirm={() => clearAll.mutate()}
              done={clearAll.isSuccess ? "All data cleared." : null}
            />
          </div>
        </SettingCard>
      </div>
    </ViewShell>
  );
}

// A bento tile: an icon-led header (title + description) over the section's controls. Keeps every
// Settings section visually consistent at the new full width (R1c). The icon follows the DS — a
// quiet ink glyph, not a control, so it never takes the cyan accent.
function SettingCard({
  icon: Icon,
  title,
  description,
  className = "",
  children,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={
        "flex flex-col gap-5 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-6 " +
        className
      }
    >
      <div>
        <h3 className="flex items-center gap-2 text-sm font-medium text-(--color-ink)">
          <Icon aria-hidden className="h-4 w-4 shrink-0 text-(--color-ink-muted)" />
          {title}
        </h3>
        <p className="mt-1 text-sm text-(--color-ink-muted)">{description}</p>
      </div>
      <div className="flex flex-col gap-5 border-t border-(--color-panel-line) pt-4">{children}</div>
    </section>
  );
}

// The Sandbox + GPU toggles share one switch shape (label/description left, switch right). Extracted
// so the two settings can't drift apart and a third toggle is a one-liner.
function Toggle({
  label,
  description,
  checked,
  disabled,
  onToggle,
}: {
  label: string;
  description: ReactNode;
  checked: boolean;
  disabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-sm text-(--color-ink)">{label}</p>
        <p className="text-xs text-(--color-ink-faint)">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        disabled={disabled}
        onClick={onToggle}
        className={
          "relative h-6 w-11 shrink-0 rounded-full transition-colors " +
          (checked ? "bg-(--color-accent)" : "bg-(--color-panel-line-strong)")
        }
      >
        <span
          className={
            "absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all " +
            (checked ? "left-[1.375rem]" : "left-0.5")
          }
        />
      </button>
    </div>
  );
}

const THRESHOLD_ROWS: { key: keyof Thresholds; label: string; hint: string }[] = [
  { key: "similarity", label: "Similarity", hint: "~0.55 fits good paraphrased summaries; 0.80 is strict." },
  { key: "keypoint", label: "Keypoint", hint: "Fraction of authored key facts that must appear." },
  { key: "judge", label: "LLM judge", hint: "Minimum judge score (0–1) to count as a pass." },
];

// Three 0–1 sliders that prefill each method's default passing threshold. Local state gives smooth
// dragging; the value is persisted on release (commit), so we don't write on every pixel. When the
// server value arrives or changes, it syncs back into the local draft.
function ThresholdSliders({
  value,
  disabled,
  onCommit,
}: {
  value: Thresholds | undefined;
  disabled: boolean;
  onCommit: (t: Thresholds) => void;
}) {
  const [draft, setDraft] = useState<Thresholds | undefined>(value);
  useEffect(() => setDraft(value), [value]);

  if (!draft) {
    return <p className="text-xs text-(--color-ink-faint)">Loading…</p>;
  }

  const set = (key: keyof Thresholds, v: number) => setDraft({ ...draft, [key]: v });

  return (
    <div className="grid gap-5 border-t border-(--color-panel-line) pt-4">
      {THRESHOLD_ROWS.map(({ key, label, hint }) => (
        <div key={key} className="grid gap-1.5">
          <div className="flex items-baseline justify-between gap-4">
            <p className="text-sm text-(--color-ink)">{label}</p>
            <span className="font-mono text-xs tabular-nums text-(--color-ink-muted)">
              {draft[key].toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={draft[key]}
            disabled={disabled}
            aria-label={`${label} default threshold`}
            onChange={(e) => set(key, Number(e.target.value))}
            onPointerUp={() => onCommit(draft)}
            onKeyUp={() => onCommit(draft)}
            className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-(--color-panel-line-strong) accent-(--color-accent) disabled:opacity-50"
          />
          <p className="text-xs text-(--color-ink-faint)">{hint}</p>
        </div>
      ))}
    </div>
  );
}

const THEMES: { value: ThemeChoice; label: string; Icon: LucideIcon }[] = [
  { value: "system", label: "System", Icon: Monitor },
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
];

// A calm 3-way theme control. radiogroup semantics so it's keyboard-navigable; the active
// segment uses the raised app surface to read as "selected" against the card it sits on.
function ThemeSwitcher() {
  const { choice, setChoice } = useTheme();
  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="flex gap-0.5 rounded-lg border border-(--color-panel-line) p-0.5"
    >
      {THEMES.map(({ value, label, Icon }) => {
        const active = value === choice;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => setChoice(value)}
            className={
              "flex items-center justify-center gap-1.5 rounded-md border px-3 py-1.5 text-xs transition-colors " +
              (active
                ? "border-(--color-accent)/50 bg-(--color-accent)/10 text-(--color-ink)"
                : "border-transparent text-(--color-ink-muted) hover:text-(--color-ink)")
            }
          >
            <Icon aria-hidden className="h-3.5 w-3.5 shrink-0" />
            {label}
          </button>
        );
      })}
    </div>
  );
}

// An action with an inline two-step confirm: first click reveals Confirm/Cancel; only Confirm fires.
function ActionRow({
  label,
  description,
  actionLabel,
  confirmLabel = "Confirm",
  destructive = false,
  icon,
  pending,
  onConfirm,
  done,
}: {
  label: string;
  description: string;
  actionLabel: string;
  confirmLabel?: string;
  destructive?: boolean;
  icon?: ReactNode;
  pending: boolean;
  onConfirm: () => void;
  done: string | null;
}) {
  const [armed, setArmed] = useState(false);
  const base =
    "inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition-colors disabled:opacity-50";
  return (
    <div className="grid gap-2 border-t border-(--color-panel-line) pt-4">
      <p className="text-sm text-(--color-ink)">{label}</p>
      <p className="text-xs text-(--color-ink-faint)">{description}</p>
      <div className="flex items-center gap-2">
        {!armed ? (
          <button
            type="button"
            aria-label={actionLabel}
            disabled={pending}
            onClick={() => setArmed(true)}
            className={
              base +
              " " +
              (destructive
                ? "border-(--color-danger)/50 text-(--color-danger) hover:bg-(--color-danger)/10"
                : "border-(--color-panel-line) text-(--color-ink) hover:border-(--color-panel-line-strong)")
            }
          >
            {icon}
            {actionLabel}
          </button>
        ) : (
          <>
            <button
              type="button"
              aria-label={confirmLabel}
              disabled={pending}
              onClick={() => {
                onConfirm();
                setArmed(false);
              }}
              className={
                base +
                " " +
                (destructive
                  ? "border-(--color-danger) bg-(--color-danger)/10 text-(--color-danger)"
                  : "border-(--color-accent) bg-(--color-accent)/10 text-(--color-ink)")
              }
            >
              {confirmLabel}
            </button>
            <button
              type="button"
              onClick={() => setArmed(false)}
              className={base + " border-(--color-panel-line) text-(--color-ink-muted)"}
            >
              Cancel
            </button>
          </>
        )}
        {done ? <span className="text-xs text-(--color-ink-faint)">{done}</span> : null}
      </div>
    </div>
  );
}
