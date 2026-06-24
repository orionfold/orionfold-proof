"""Pure-Python SVG figures for the Proof field note (no browser, no charting lib).

A field note (``orionfold field-note``) ships the same two charts the cockpit shows, but
rendered as self-contained inline ``<svg>`` so they theme with the publishing site (light/
dark via ``var(--color-*)``), reflow, and read native — a raster screenshot can't. Keeping
the figures here, in the public package, means the standalone export carries real charts and
Layer B (the private authoring skill) needs no browser dependency.

Two invariants make these safe to commit and diff like generated code:

* **Deterministic.** The same ``ProofReport`` renders byte-identical SVG forever. Every
  number routes through :func:`_num` (fixed 2-decimal, trailing-zero-trimmed) so no float
  formatting drifts across machines — the same trick the threshold codegen uses.
* **DS accent/status split.** The recommended candidate is the *only* ``--color-accent``;
  every other dot is status-toned (ok/warn/danger). Pass-rate bars are ``--color-ok`` (PASS
  is the one thing green means). Labels and axes are neutral ink. We never invent a colour.

The Pareto math is a faithful port of the cockpit's ``paretoFrontier.ts`` (lower-cost-better,
tier-resolved ties) so the field note and the live scatter agree on which dots dominate.
"""

from __future__ import annotations

from orionfold.domain.models import LeaderboardEntry, ProofReport

# --- geometry (a fixed viewBox keeps the SVG self-contained and deterministic) ---
_W = 320  # viewBox width
_H = 200  # viewBox height
_PAD_L = 44  # left gutter for the y-axis labels
_PAD_R = 12
_PAD_T = 12
_PAD_B = 28  # bottom gutter for the x-axis label


def _num(value: float) -> str:
    """Fixed 2-decimal, trailing zeros trimmed — stable across machines (no float drift)."""
    s = f"{value:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _esc(text: str) -> str:
    """Minimal XML text escaping for labels embedded in <text>/aria-label."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _pareto_frontier(pts: list[tuple[float, float]]) -> set[int]:
    """Indices of Pareto-optimal points for lower-cost-better × higher-quality-better.

    Faithful port of ``web/.../paretoFrontier.ts`` — sort cost-ascending (quality-descending
    to break cost ties), sweep one cost tier at a time, and keep a point only when its quality
    ties the best in its own tier AND beats everything strictly cheaper. Equal-cost points are
    resolved as a group so a cost tie never spuriously drops the higher-quality one.
    """
    order = sorted(range(len(pts)), key=lambda i: (pts[i][0], -pts[i][1]))

    on_frontier: set[int] = set()
    best_quality_strictly_cheaper = float("-inf")
    tier_cost = float("nan")
    tier_members: list[int] = []
    tier_best = float("-inf")

    def flush_tier() -> None:
        nonlocal best_quality_strictly_cheaper
        if not tier_members:
            return
        if tier_best > best_quality_strictly_cheaper:
            for idx in tier_members:
                if pts[idx][1] == tier_best:
                    on_frontier.add(idx)
        best_quality_strictly_cheaper = max(best_quality_strictly_cheaper, tier_best)

    for i in order:
        cost, quality = pts[i]
        if cost != tier_cost:
            flush_tier()
            tier_cost = cost
            tier_members = []
            tier_best = float("-inf")
        tier_members.append(i)
        tier_best = max(tier_best, quality)
    flush_tier()

    return on_frontier


def _pass_rate_tone(rate: float) -> str:
    """Status colour for a non-recommended dot/bar, mirroring the cockpit's passRateTone."""
    if rate >= 0.6:
        return "--color-ok"
    if rate >= 0.3:
        return "--color-warn"
    return "--color-danger"


def _figure(body: str, *, title: str, caption: str, label: str) -> str:
    """Wrap an inner SVG body in the ainative ``fn-diagram`` figure shape (themeable + a11y)."""
    return (
        f'<figure class="fn-diagram">\n'
        f'<svg viewBox="0 0 {_W} {_H}" role="img" aria-label="{_esc(label)}" '
        f'xmlns="http://www.w3.org/2000/svg">\n'
        f"<title>{_esc(title)}</title>\n"
        f"{body}\n"
        f"</svg>\n"
        f"<figcaption>{_esc(caption)}</figcaption>\n"
        f"</figure>"
    )


def pareto_svg(report: ProofReport) -> str:
    """Cost-vs-quality scatter: cost (x, lower better) × pass-rate (y); frontier path drawn.

    The recommended candidate is the only accent; every other dot is status-toned. When fewer
    than two candidates have a positive cost spread the frontier path is omitted (nothing
    dominates) — honest, never a fabricated line.
    """
    entries = [e for e in report.leaderboard if e.error_count < e.total or e.total == 0]
    pts = [(e.total_estimated_cost_usd, e.pass_rate) for e in entries]

    inner_w = _W - _PAD_L - _PAD_R
    inner_h = _H - _PAD_T - _PAD_B
    max_cost = max((c for c, _ in pts), default=0.0)
    # Quality (pass rate) is already 0–1; cost scales to its own max (or a flat axis if free).

    def px(cost: float) -> float:
        if max_cost <= 0:
            return _PAD_L + inner_w / 2
        return _PAD_L + (cost / max_cost) * inner_w

    def py(quality: float) -> float:
        return _PAD_T + (1 - quality) * inner_h

    parts: list[str] = []
    # axes (neutral ink)
    parts.append(
        f'<line x1="{_PAD_L}" y1="{_PAD_T}" x2="{_PAD_L}" y2="{_PAD_T + inner_h}" '
        f'stroke="var(--color-ink-faint)" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{_PAD_L}" y1="{_PAD_T + inner_h}" x2="{_PAD_L + inner_w}" '
        f'y2="{_PAD_T + inner_h}" stroke="var(--color-ink-faint)" stroke-width="1"/>'
    )
    # axis labels
    parts.append(
        f'<text x="{_PAD_L + inner_w / 2}" y="{_H - 8}" text-anchor="middle" '
        f'font-size="9" fill="var(--color-ink-muted)">Cost (lower better) →</text>'
    )
    parts.append(
        f'<text x="10" y="{_PAD_T + inner_h / 2}" text-anchor="middle" font-size="9" '
        f'fill="var(--color-ink-muted)" transform="rotate(-90 10 {_num(_PAD_T + inner_h / 2)})">'
        f"Pass rate →</text>"
    )

    frontier = _pareto_frontier(pts)
    # The frontier path connects on-frontier points in cost order, but only when ≥2 of them
    # exist with a real cost spread — a single dot or an all-free run has nothing to connect.
    fpts = sorted((i for i in frontier), key=lambda i: (pts[i][0], -pts[i][1]))
    if len(fpts) >= 2 and max_cost > 0:
        coords = " ".join(f"{_num(px(pts[i][0]))},{_num(py(pts[i][1]))}" for i in fpts)
        parts.append(
            f'<polyline points="{coords}" fill="none" '
            f'stroke="var(--color-ink-faint)" stroke-width="1" stroke-dasharray="3 3"/>'
        )

    for i, e in enumerate(entries):
        cx, cy = px(pts[i][0]), py(pts[i][1])
        if e.recommended:
            colour = "--color-accent"
            radius = 5
        else:
            colour = _pass_rate_tone(e.pass_rate)
            radius = 4
        parts.append(
            f'<circle cx="{_num(cx)}" cy="{_num(cy)}" r="{radius}" '
            f'fill="var({colour})"><title>{_esc(e.label)}</title></circle>'
        )

    rec = next((e.label for e in entries if e.recommended), None)
    caption = (
        f"Cost vs. pass rate — {rec} is the recommended pick (accent)."
        if rec
        else "Cost vs. pass rate across the candidates."
    )
    return _figure(
        "".join(parts),
        title="Cost vs. quality",
        caption=caption,
        label="Scatter plot of candidate cost against pass rate, recommended pick highlighted.",
    )


def pass_rate_svg(report: ProofReport) -> str:
    """Per-candidate pass-rate bars (``--color-ok``), neutral-ink labels.

    Omitted (returns ``""``) when the run is unscored — a quick run (``rubric.kind == "none"``)
    rolls every pass rate up to 0, which is indistinguishable from "scored, all failed", so we
    read the rubric kind to tell them apart and never draw a fake bar. Also omitted when there
    are no candidates.
    """
    if report.run.rubric.kind == "none":
        return ""
    entries: list[LeaderboardEntry] = list(report.leaderboard)
    if not entries:
        return ""

    inner_w = _W - _PAD_L - _PAD_R
    inner_h = _H - _PAD_T - _PAD_B
    n = len(entries)
    gap = 6
    bar_h = (inner_h - gap * (n - 1)) / n if n else inner_h

    parts: list[str] = []
    for i, e in enumerate(entries):
        y = _PAD_T + i * (bar_h + gap)
        width = e.pass_rate * inner_w
        colour = "--color-accent" if e.recommended else "--color-ok"
        parts.append(
            f'<rect x="{_PAD_L}" y="{_num(y)}" width="{_num(width)}" height="{_num(bar_h)}" '
            f'rx="2" fill="var({colour})"><title>{_esc(e.label)}</title></rect>'
        )
        parts.append(
            f'<text x="{_PAD_L - 4}" y="{_num(y + bar_h / 2 + 3)}" text-anchor="end" '
            f'font-size="8" fill="var(--color-ink-muted)">{_esc(e.label)}</text>'
        )
        parts.append(
            f'<text x="{_num(_PAD_L + width + 4)}" y="{_num(y + bar_h / 2 + 3)}" '
            f'font-size="8" fill="var(--color-ink-faint)">{e.pass_rate:.0%}</text>'
        )

    return _figure(
        "".join(parts),
        title="Pass rate by candidate",
        caption="Pass rate per candidate (higher is better).",
        label="Horizontal bar chart of pass rate for each candidate.",
    )
