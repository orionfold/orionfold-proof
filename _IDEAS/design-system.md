# Design-system application gaps

> Gaps between the live UI and the design-system reference
> (`orionfold-design-system/mocks/design-reference/2026-06-20/`). The token foundation in
> `web/src/styles/index.css` already matches the latest reference (`#14c8c0` cyan, Geist);
> these entries are about **consistent application** of the token kit and component patterns.
> See [README.md](README.md) for the template and legend.

<!-- Entry template:
## <Title>
- **Severity / Effort:** <low|med|high> / <quick-win|deeper>
- **Route / State:** <view> · <state> · <theme>
- **Observed:** <visual delta vs reference>
- **Evidence:** <screenshot path>
- **Recommendation:** <which token/component pattern to adopt>
- **Reference:** candidate-1.html / components.html (component name)
-->

## Dataset metadata line is inconsistent between bundled and user-created sets
- **Severity / Effort:** low / quick-win
- **Route / State:** Datasets · populated · dark
- **Observed:** The user-imported "Support ticket triage v1" card shows a rich metadata
  sub-line — `5 examples · created 6/22/2026 · pasted` plus an `Exact match` chip — while the
  bundled "Investment memo summarization" card shows only `5 examples` (no created/source/hint
  line). Side by side the bundled demo dataset looks "thinner"/older than user datasets, which
  undercuts the demo's role as the polished first impression.
- **Evidence:** ss_6017dm1dm (list), import flow ss_8072knxif / ss_7646ubcd5
- **Recommendation:** Backfill `created_at`/`source`/`check_hint` on the seeded sample
  dataset so its card renders the same metadata line + hint chip as user sets. Render the
  metadata as a consistent token-driven sub-line (ink-faint, mono for the date) and the hint
  as a categorical value tag (neutral/squared per the DS), not loose text.
- **Reference:** components.html (`.badge` neutral / categorical value tags)

## Leaderboard headers are not sortable (reference `.tbl` defines the pattern)
- **Severity / Effort:** med / quick-win
- **Route / State:** Proof Run · Decide · populated · dark+light
- **Observed:** The leaderboard table headers (`Leaderboard.tsx:27-34`) are plain
  `<th className="p-3 font-medium">` with no click/sort affordance. The reference component
  library defines a full sortable table: `.tbl th.sortable { cursor:pointer }`,
  `th.sortable:hover { color:var(--accent) }`, `th[aria-sort]` states, and a `.sort-ar`
  indicator. A consultant comparing several candidates can't re-sort by $/quality, latency, or
  cost — they're locked to the default ranking sort.
- **Evidence:** ss_07963zcfs / ss_0664sxxnm (static headers); source `Leaderboard.tsx`.
- **Recommendation:** Adopt the reference `.tbl` sortable pattern for the leaderboard
  (client-side sort, `aria-sort` for a11y, accent on the active column). Keep the documented
  default ranking sort key as the initial state.
- **Reference:** components.html (`.tbl th.sortable`, `aria-sort`, `.sort-ar`)

## Leaderboard column headers use sans `font-medium`, not the reference mono micro-caps
- **Severity / Effort:** low / quick-win
- **Route / State:** Proof Run · Decide · populated · dark+light
- **Observed:** Live headers are sans `font-medium` (`Leaderboard.tsx:27-34`). The reference
  `.tbl thead th` is **mono, 10px, uppercase** (the "field-label" voice used consistently for
  table/column/field labels in components.html). The live table reads slightly more "generic
  SaaS" than the reference's instrument-panel header style.
- **Evidence:** ss_07963zcfs; reference `.tbl thead th { font-family:var(--mono); font-size:10px; ... }`.
- **Recommendation:** Apply the mono micro-caps header treatment (`--font-mono`, ~10px,
  uppercase, letter-spacing, ink-muted) to leaderboard + other data-table headers for a
  consistent "receipt voice" on column labels.
- **Reference:** components.html (`.tbl thead th`, `.field-label`)

## Provider-boundary "Mock" badge styles identically to Local/Cloud (real vs simulated not distinct enough)
- **Severity / Effort:** low / quick-win
- **Route / State:** Candidates · populated · dark
- **Observed:** On Candidates, the Mock·good / Mock·bad rows carry a "Mock" chip styled the
  same neutral way as the "Local"/"Cloud" chips. The DS requires "Local / Cloud / Mock must be
  visually distinct at a glance," and the product is emphatic that a mock run is "not a real
  evaluation." A glanceable distinction (e.g. Mock as a muted/dashed/warn-tinted chip) would
  stop Mock reading as a peer of real providers.
- **Evidence:** ss_2366nw53x (Candidates: Mock/Local/Cloud chips share styling)
- **Recommendation:** Give the Mock boundary a distinct token treatment (muted or warn-leaning,
  per the `.badge.warn`/`.badge.neutral` set) so simulated sources never look like real ones.
- **Reference:** components.html (`.badge.neutral` vs `.badge.warn`); product-design-system.md
  ("Provider boundary … visually distinct at a glance").

## Settings & list pages leave the inspector column empty (no right-rail use of the 3-pane grid)
- **Severity / Effort:** low / quick-win
- **Route / State:** Settings, Datasets, Candidates · populated · dark+light
- **Observed:** The DS layout is rail · main · inspector. On Proof Run the inspector is richly
  used (run config, receipt, failure case). On Settings/Datasets/Candidates the main column is
  ~55% width and the right third is empty whitespace, so those pages feel unbalanced vs the
  cockpit. Not wrong, but inconsistent.
- **Evidence:** Settings ss_31825nes2; Datasets ss_6017dm1dm; Candidates ss_2366nw53x.
- **Recommendation:** Either widen the main column on inspector-less pages, or use the right
  rail for lightweight context (e.g. Datasets: selected-dataset summary / "what is a frozen
  dataset"; Settings: "everything stays on this machine" privacy note as a sidebar).
- **Reference:** product-design-system.md (Layout: rail · main · inspector)
