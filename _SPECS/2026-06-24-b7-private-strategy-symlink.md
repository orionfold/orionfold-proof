# B7 — Private-strategy symlink + relay

> **Spec for a fresh implementation session.** Self-contained. Approved before code.
> Blast radius: git-history-touching, multi-file, irreversible-ish (a move + symlink swap).
> Spec depth matched to that per CLAUDE.md.

_Status: **DRAFT — awaiting operator approval.** Date: 2026-06-24._

## 1. Goal (one outcome)

> Move this repo's **private strategy + method-leaking** content into a project-scoped home
> in the separate `~/orionfold/strategy/` git repo, leaving behind **gitignored symlinks** so
> Claude Code keeps resolving everything normally — while the public `orionfold-proof` repo
> shrinks to *just the shippable, open-core product + license + readme*.

Privacy becomes **structural** (only released code is public), not a per-push scrub — the
fieldkit posture (ADR-0006 §5), now corrected to also treat **skills, agents, worklog, and
planning docs as private** (operator decision 2026-06-24; they leak engineering method and
don't ship). This is **the last blocker before the eventual git remote + push** (backlog #13).

## 2. Why this is safe / how skill resolution survives symlinking

- Claude Code resolves skills/agents/rules by **walking the real working tree** under `.claude/`
  and **follows symlinks transparently** — a symlinked `SKILL.md` loads identically to a real one.
- **Gitignoring a symlink only hides it from git**; it has zero effect on resolution (the harness
  reads the working tree, not the index).
- Skill scripts (`emit_bundle.py`) resolve paths **relative to CWD** (this repo root) and shell out
  to the `orionfold` CLI in *this* repo — both keep working through a symlink because CWD is
  unchanged. **This is the one thing we must prove live, not assume** → §7 full e2e.

## 3. Target structure (PROJECT-SCOPED — never strategy root)

`~/orionfold/strategy/` is **its own git repo**; `~/orionfold/strategy/_IDEAS` and `/_SPECS`
**already exist and belong to the strategy root** (they hold flows-factory / spark-mac specs —
unrelated to Proof). **Do NOT symlink into those.** Create a dedicated namespace:

```
~/orionfold/strategy/orionfold-proof/          ← NEW dir; this project's private home (in the strategy repo)
├── _IDEAS/
├── _SPECS/                                     ← includes THIS spec after the move
├── _field-notes/                               ← run_0fb312d3a087/, sample-support-ticket-triage/
├── docs-worklog/                               ← the relocated docs/worklog/ (renamed to avoid clashing w/ a future strategy docs/)
├── docs-superpowers/                           ← the relocated docs/superpowers/ (plans + specs)
├── HANDOFF.md
└── .claude/
    ├── skills/                                 ← all 8 product skills + proof-field-note
    └── agents/                                 ← codebase-investigator, diff-reviewer, security-reviewer
```

Symlinks left in `orionfold-proof/` (all **gitignored**), each pointing into that subdir:

| Symlink in this repo | → target |
| --- | --- |
| `_IDEAS` | `~/orionfold/strategy/orionfold-proof/_IDEAS` |
| `_SPECS` | `~/orionfold/strategy/orionfold-proof/_SPECS` |
| `_field-notes` | `~/orionfold/strategy/orionfold-proof/_field-notes` |
| `HANDOFF.md` | `~/orionfold/strategy/orionfold-proof/HANDOFF.md` |
| `docs/worklog` | `~/orionfold/strategy/orionfold-proof/docs-worklog` |
| `docs/superpowers` | `~/orionfold/strategy/orionfold-proof/docs-superpowers` |
| `.claude/skills` | `~/orionfold/strategy/orionfold-proof/.claude/skills` |
| `.claude/agents` | `~/orionfold/strategy/orionfold-proof/.claude/agents` |

> **Symlink granularity decision:** for `.claude`, symlink the **whole `skills/` and `agents/`
> dirs** (operator chose maximal privacy — all skills are secret sauce). This is safe because the
> remaining public `.claude/` entries (`hooks/`, `rules/`, `settings*.json`, `output-styles/`) are
> *siblings*, untouched, still real tracked files.

## 4. PUBLIC / PRIVATE classification (the open-core surface)

**STAYS PUBLIC (ships or must run for a contributor; minimal leak):**
- `src/`, `web/`, `tests/`, `e2e/`, `samples/`
- `docs/` **except** `worklog/` + `superpowers/` — i.e. KEEP public: `adr/`, `api/`, `ux/`,
  `tech/`, `opportunity.md`, `product-brief.md`, `release-charter.md`, `demo-script.md`,
  `claude-context-and-ux-addendum.md`
- `.claude/hooks/secrets-guard.py` (**enforced** safety boundary — a contributor needs it active)
- `.claude/rules/*.md` (path-scoped conventions; help a contributor, reveal little)
- `.claude/settings.json`, `.claude/settings.json.example`, `.claude/output-styles/`
- `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `pyproject.toml`, `uv.lock`, `.gitignore`, (future `LICENSE`)

**GOES PRIVATE (leaks method and/or doesn't ship):**
- `_IDEAS/`, `_SPECS/`, `_field-notes/` (already gitignored — physical move only)
- `HANDOFF.md` (live backlog / operator directives)
- `docs/worklog/` (the decision diary — every "chose X over Y because…")
- `docs/superpowers/` (32 plan+spec files — same category as `_SPECS`)
- `.claude/skills/` (all 8 — the engineering/verification playbook; none ship in the wheel)
- `.claude/agents/` (diff-reviewer, security-reviewer, codebase-investigator — review tooling, leaks method)

**OPERATOR CALL NEEDED AT IMPL (one borderline):** `docs/tech/global-skills-inventory.md` is an
inventory of which *global* skills this project uses — mildly method-revealing, doesn't ship. Default:
**keep public** (it's about global skills, not Proof's strategy). Flag it; move only if operator says so.

## 5. Procedure (ordered; verify each step)

Per operator decision: **`git rm --cached` only — NO history rewrite** (no remote yet; reversible;
strategy content stays in old commits, acceptable). For each moved path:

1. **Create the namespace:** `mkdir -p ~/orionfold/strategy/orionfold-proof/.claude`
2. **Move bytes** (preserve content): `git mv` is NOT used (we're leaving the repo). Use plain
   `mv <path> ~/orionfold/strategy/orionfold-proof/<dest>` for each. For the 3 already-gitignored
   dirs (`_IDEAS` real-tracked, `_SPECS` real-tracked, `_field-notes` gitignored) handle tracking in
   step 4. **`docs/worklog`→`docs-worklog`, `docs/superpowers`→`docs-superpowers`** (rename on move).
3. **Symlink back** (relative or absolute — use **absolute** `~/orionfold/...` expanded, for clarity):
   `ln -s ~/orionfold/strategy/orionfold-proof/<dest> <path>` for each row in §3's table.
4. **Stop tracking** (the ones currently tracked): `git rm -r --cached _IDEAS _SPECS HANDOFF.md
   docs/worklog docs/superpowers .claude/skills .claude/agents`. (`_field-notes` already untracked.)
   After this, `git status` shows the deletions staged; the new symlinks are untracked.
5. **Gitignore the symlinks** — add a B7 block to `.gitignore` (see §6). After this, `git status`
   shows ONLY the staged deletions (symlinks now ignored).
6. **Amend ADR-0006 §5** (see §8) — this is a PUBLIC doc edit, committed in THIS repo.
7. **`this spec` moved too:** since `_SPECS` relocates, this file rides along — after the move it
   lives at `~/orionfold/strategy/orionfold-proof/_SPECS/2026-06-24-b7-private-strategy-symlink.md`,
   reachable via the `_SPECS` symlink. (Do the move AFTER reading it into context.)
8. **Commit** in `orionfold-proof`: the `git rm --cached` deletions + `.gitignore` block + ADR
   amendment, in one commit. Then **separately commit** in `~/orionfold/strategy/` the newly-arrived
   `orionfold-proof/` subdir (that repo's own history).

## 6. .gitignore additions (B7 block)

```gitignore
# B7 — Private strategy content lives in ~/orionfold/strategy/orionfold-proof/ and is
# symlinked back here (structural privacy, ADR-0006 §5 as amended 2026-06-24).
# Only released code + public docs are public. These symlinks must never be committed.
/_IDEAS
/_SPECS
/HANDOFF.md
/docs/worklog
/docs/superpowers
/.claude/skills
/.claude/agents
```
(`_field-notes/` already ignored — leave its existing block.)

> **Anchoring matters:** `/_IDEAS` (leading slash) ignores only the root symlink, not any nested
> path. `.claude/hooks`, `.claude/rules`, `.claude/settings*.json` are NOT listed → stay tracked.

## 7. Verification (operator chose FULL e2e re-run)

After the symlink swap, prove the symlinked skill behaves byte-identically:

1. **Skill loads:** confirm `.claude/skills/proof-field-note/SKILL.md` resolves through the symlink
   (e.g. the Skill tool lists `proof-field-note`, or `cat` through the symlink succeeds).
2. **Full e2e on a real stored run** (mirrors how Layer B was originally verified):
   scaffold (`orionfold field-note <run_id>`) → confirm the marker guard **refuses** before authoring
   → author the narrative → `emit_bundle.py` emits a bundle into `_field-notes/` (now the symlink) →
   **the bytes land in `~/orionfold/strategy/orionfold-proof/_field-notes/`** → secret-free check
   (the 7-regex backstop) → `scripts/test_emit_bundle.py` green through the symlink.
3. **No package/test regression:** `uv run pytest` (366 BE) unchanged; ruff + pyright 0. The move
   touched **no `src/`** → mock `467ddd96c9a5`, the receipt, `RECEIPT_VERSION` untouched by construction.
4. **Public-surface audit:** `git ls-files` shows NO `_IDEAS|_SPECS|worklog|superpowers|skills|agents`
   entries remain tracked; `git status` is clean after commit; the secrets-guard hook + rules still tracked.

## 8. ADR-0006 §5 amendment (record the override)

Append a dated amendment under §5 (do NOT delete the original — ADRs are append-only):

> **Amendment (2026-06-24, B7):** §5's original "skills + public docs ship" posture is **narrowed**.
> The private boundary is now **"does it run in the shipped product, or does it leak engineering
> method?"** Skills, agents, the worklog decision-diary, and planning docs (`docs/superpowers/`)
> **leak method and do not ship** → they move to `~/orionfold/strategy/orionfold-proof/` (symlinked
> back, gitignored). **Stays public:** released code (`src/`,`web/`,`tests/`), public docs
> (`adr/`,`api/`,`ux/`,`tech/`, brief/charter/opportunity), the **enforced** `secrets-guard.py` hook,
> path-scoped `rules/`, settings, README/CHANGELOG/LICENSE. Rationale: these skills are the product's
> verification/quality playbook (secret sauce) and ship in no wheel — publishing them is all leak, no
> benefit. Privacy stays **structural** (the original §5 principle), just with a corrected boundary.

## 9. Out of scope (logged, not built)

- **History rewrite** (filter-repo to purge strategy from old commits) — explicitly deferred; revisit
  only if a remote is ever added with a clean-history requirement.
- **#7 packaging** (Apache-2.0 flip, PyPI metadata, optional-deps) — separate backlog item, downstream.
- **git remote + push** (#13) — still LAST; B7 unblocks it but does not perform it.
- Moving `.claude/hooks`, `.claude/rules`, public `docs/` — they stay public by design.

## 10. End-to-end check (definition of done)

`git ls-files` is free of private paths · the 8 symlinks resolve · the proof-field-note skill runs
full e2e through its symlink and writes a secret-free bundle into the strategy subdir · 366 BE green ·
ruff+pyright 0 · ADR-0006 amended · `orionfold-proof` commit + `~/orionfold/strategy` commit both clean ·
HANDOFF refreshed (it now lives in strategy, reached via the symlink).
