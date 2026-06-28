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


# --- colour palette (inline themes via CSS vars; standalone bakes literal hex) ---
#
# The figures serve two render contexts from one source:
#   * INLINE (field note, receipt HTML) — the SVG lives in the page DOM, so `var(--color-*)`
#     themes with the host (light/dark). This is the default and stays byte-identical.
#   * STANDALONE (receipt-article extract) — the SVG is referenced as `<img src>`, an isolated
#     context that can't read page CSS vars (every var() paints invisible). So `standalone=True`
#     bakes literal, THEME-NEUTRAL hex that reads on both light + dark (an <img>-SVG can't be
#     theme-reactive). Values are the website's proven mapping (src/styles/index.css): ink-faint/
#     ink-muted use the light-theme tones (legible on white, still visible on dark); accent is the
#     brand cyan fill; warn/danger are mid-tones between the two themes' values.
_STANDALONE_HEX = {
    "--color-ink-faint": "#9aa1ab",  # gridlines/axes only (never text)
    "--color-ink-muted": "#6b7280",  # label text — ~4.8:1 on white, WCAG-legible
    "--color-accent": "#14c8c0",  # recommended dot/bar fill (brand cyan)
    "--color-ok": "#3fd55a",  # PASS green
    "--color-warn": "#d9952b",  # caution — between light #b06a00 / dark #f5b14a
    "--color-danger": "#dd5266",  # fail — between light #c0344d / dark #ff7a93
}


def _colour(token: str, *, standalone: bool) -> str:
    """Emit a paint value for a DS colour token: a literal hex in standalone mode, else `var(...)`."""
    if standalone:
        return _STANDALONE_HEX[token]
    return f"var({token})"


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


def _short_label(label: str, *, limit: int = 16) -> str:
    """A compact chart label: keep the most identifying tail of a long id (e.g.
    ``hf.co/Orionfold/Advisor-GGUF`` → ``Advisor-GGUF``, ``z-ai/glm-4.6`` → ``glm-4.6``) so the
    fixed-width gutter never clips. Splits on the last ``/`` or ``·`` and ellipsises if still long."""
    tail = label.rsplit("/", 1)[-1].rsplit("·", 1)[-1].strip()
    if len(tail) > limit:
        tail = tail[: limit - 1] + "…"
    return tail or label[:limit]


def _gridlines_v(
    x0: float, x1: float, y0: float, y1: float, *, steps: int = 4, standalone: bool = False
) -> str:
    """Faint vertical gridlines (subtle background structure for a bar chart) at even fractions of
    the inner width. Drawn BEFORE the bars so they sit behind. ink-faint at low opacity keeps them
    quiet."""
    stroke = _colour("--color-ink-faint", standalone=standalone)
    parts = []
    for k in range(1, steps + 1):
        x = x0 + (x1 - x0) * k / steps
        parts.append(
            f'<line x1="{_num(x)}" y1="{_num(y0)}" x2="{_num(x)}" y2="{_num(y1)}" '
            f'stroke="{stroke}" stroke-width="0.5" opacity="0.28"/>'
        )
    return "".join(parts)


def _gridlines_hv(
    x0: float, x1: float, y0: float, y1: float, *, steps: int = 4, standalone: bool = False
) -> str:
    """Faint horizontal + vertical gridlines for the scatter — a subtle plot grid behind the dots."""
    stroke = _colour("--color-ink-faint", standalone=standalone)
    parts = []
    for k in range(1, steps + 1):
        y = y0 + (y1 - y0) * k / steps
        parts.append(
            f'<line x1="{_num(x0)}" y1="{_num(y)}" x2="{_num(x1)}" y2="{_num(y)}" '
            f'stroke="{stroke}" stroke-width="0.5" opacity="0.22"/>'
        )
    for k in range(1, steps + 1):
        x = x0 + (x1 - x0) * k / steps
        parts.append(
            f'<line x1="{_num(x)}" y1="{_num(y0)}" x2="{_num(x)}" y2="{_num(y1)}" '
            f'stroke="{stroke}" stroke-width="0.5" opacity="0.22"/>'
        )
    return "".join(parts)


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


def _figure(body: str, *, title: str, caption: str, label: str, standalone: bool = False) -> str:
    """Wrap an inner SVG body for the chosen render context.

    Inline (default): the ainative ``fn-diagram`` ``<figure>`` shape (themeable + a11y caption).
    Standalone: a BARE ``<svg>`` root — Astro's ``image()`` importer hard-errors on a non-``<svg>``
    root, and the website supplies its own caption. The ``<title>``/``aria-label`` a11y spine is
    kept either way; only the surrounding ``<figure>``/``<figcaption>`` chrome is dropped.
    """
    svg = (
        f'<svg viewBox="0 0 {_W} {_H}" role="img" aria-label="{_esc(label)}" '
        f'xmlns="http://www.w3.org/2000/svg">\n'
        f"<title>{_esc(title)}</title>\n"
        f"{body}\n"
        f"</svg>"
    )
    if standalone:
        return svg
    return (
        f'<figure class="fn-diagram">\n'
        f"{svg}\n"
        f"<figcaption>{_esc(caption)}</figcaption>\n"
        f"</figure>"
    )


def pareto_svg(report: ProofReport, *, standalone: bool = False) -> str:
    """Cost-vs-quality scatter: cost (x, lower better) × pass-rate (y); frontier path drawn.

    The recommended candidate is the only accent; every other dot is status-toned. When fewer
    than two candidates have a positive cost spread the frontier path is omitted (nothing
    dominates) — honest, never a fabricated line.

    ``standalone=True`` bakes literal hex + a bare ``<svg>`` root for the receipt-article
    ``<img>`` path (see the colour-palette note above); the default themes inline via CSS vars.
    """
    ink_faint = _colour("--color-ink-faint", standalone=standalone)
    ink_muted = _colour("--color-ink-muted", standalone=standalone)
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
    # Subtle plot grid behind the dots — quiet structure so a dot's position reads against a scale.
    parts.append(
        _gridlines_hv(
            _PAD_L, _PAD_L + inner_w, _PAD_T, _PAD_T + inner_h, steps=4, standalone=standalone
        )
    )
    # axes (neutral ink)
    parts.append(
        f'<line x1="{_PAD_L}" y1="{_PAD_T}" x2="{_PAD_L}" y2="{_PAD_T + inner_h}" '
        f'stroke="{ink_faint}" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{_PAD_L}" y1="{_PAD_T + inner_h}" x2="{_PAD_L + inner_w}" '
        f'y2="{_PAD_T + inner_h}" stroke="{ink_faint}" stroke-width="1"/>'
    )
    # axis labels
    parts.append(
        f'<text x="{_PAD_L + inner_w / 2}" y="{_H - 8}" text-anchor="middle" '
        f'font-size="9" fill="{ink_muted}">Cost (lower better) →</text>'
    )
    parts.append(
        f'<text x="10" y="{_PAD_T + inner_h / 2}" text-anchor="middle" font-size="9" '
        f'fill="{ink_muted}" transform="rotate(-90 10 {_num(_PAD_T + inner_h / 2)})">'
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
            f'stroke="{ink_faint}" stroke-width="1" stroke-dasharray="3 3"/>'
        )

    for i, e in enumerate(entries):
        cx, cy = px(pts[i][0]), py(pts[i][1])
        if e.recommended:
            tone = "--color-accent"
            radius = 5
        else:
            tone = _pass_rate_tone(e.pass_rate)
            radius = 4
        parts.append(
            f'<circle cx="{_num(cx)}" cy="{_num(cy)}" r="{radius}" '
            f'fill="{_colour(tone, standalone=standalone)}"><title>{_esc(e.label)}</title></circle>'
        )
        # Visible short label by each dot. Anchor end (label to the LEFT) when the dot sits in the
        # right third so it never runs off the plot; otherwise start (label to the RIGHT). Nudge the
        # y up unless the dot is near the top, where it drops below to stay inside the frame.
        near_right = cx > _PAD_L + inner_w * 0.66
        anchor = "end" if near_right else "start"
        lx = cx - radius - 3 if near_right else cx + radius + 3
        ly = cy + 11 if cy < _PAD_T + 14 else cy - radius - 4
        parts.append(
            f'<text x="{_num(lx)}" y="{_num(ly)}" text-anchor="{anchor}" font-size="8" '
            f'fill="{ink_muted}">{_esc(_short_label(e.label))}</text>'
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
        standalone=standalone,
    )


def pass_rate_svg(report: ProofReport, *, standalone: bool = False) -> str:
    """Per-candidate pass-rate bars (``--color-ok``), neutral-ink labels.

    Omitted (returns ``""``) when the run is unscored — a quick run (``rubric.kind == "none"``)
    rolls every pass rate up to 0, which is indistinguishable from "scored, all failed", so we
    read the rubric kind to tell them apart and never draw a fake bar. Also omitted when there
    are no candidates.

    ``standalone=True`` bakes literal hex + a bare ``<svg>`` root for the receipt-article
    ``<img>`` path (see the colour-palette note above); the default themes inline via CSS vars.
    """
    if report.run.rubric.kind == "none":
        return ""
    entries: list[LeaderboardEntry] = list(report.leaderboard)
    if not entries:
        return ""

    ink_faint = _colour("--color-ink-faint", standalone=standalone)
    ink_muted = _colour("--color-ink-muted", standalone=standalone)

    inner_w = _W - _PAD_L - _PAD_R
    inner_h = _H - _PAD_T - _PAD_B
    n = len(entries)
    gap = 8
    # Cap bar thickness so a 1–2 candidate run gets calm, readable bars instead of one slab filling
    # the card; the band of bars is then centred vertically in the plot area.
    bar_h = min(26.0, (inner_h - gap * (n - 1)) / n) if n else inner_h
    band_h = bar_h * n + gap * (n - 1)
    y_top = _PAD_T + max(0.0, (inner_h - band_h) / 2)

    parts: list[str] = []
    # Subtle 25/50/75/100% vertical gridlines behind the bars (the 0–100% scale is implicit).
    parts.append(
        _gridlines_v(
            _PAD_L, _PAD_L + inner_w, _PAD_T, _PAD_T + inner_h, steps=4, standalone=standalone
        )
    )
    # axis baseline (neutral ink)
    parts.append(
        f'<line x1="{_PAD_L}" y1="{_PAD_T}" x2="{_PAD_L}" y2="{_PAD_T + inner_h}" '
        f'stroke="{ink_faint}" stroke-width="1"/>'
    )
    for i, e in enumerate(entries):
        y = y_top + i * (bar_h + gap)
        width = e.pass_rate * inner_w
        tone = "--color-accent" if e.recommended else "--color-ok"
        parts.append(
            f'<rect x="{_PAD_L}" y="{_num(y)}" width="{_num(width)}" height="{_num(bar_h)}" '
            f'rx="2" fill="{_colour(tone, standalone=standalone)}">'
            f"<title>{_esc(e.label)}</title></rect>"
        )
        # Label limit ~8 chars so the most-identifying tail fits the fixed left gutter without
        # clipping at the SVG edge (the gutter is _PAD_L px wide at font-size 8).
        parts.append(
            f'<text x="{_PAD_L - 5}" y="{_num(y + bar_h / 2 + 3)}" text-anchor="end" '
            f'font-size="8" fill="{ink_muted}">{_esc(_short_label(e.label, limit=8))}</text>'
        )
        # The % readout sits OUTSIDE the bar. Inline it stays the quiet faint tone (unchanged);
        # standalone promotes it to muted ink so it passes contrast on a light <img> background
        # (the faint #9aa1ab gridline grey would be too low-contrast for text on white).
        pct_fill = ink_muted if standalone else _colour("--color-ink-faint", standalone=False)
        parts.append(
            f'<text x="{_num(_PAD_L + width + 4)}" y="{_num(y + bar_h / 2 + 3)}" '
            f'font-size="8" fill="{pct_fill}">{e.pass_rate:.0%}</text>'
        )

    return _figure(
        "".join(parts),
        title="Pass rate by candidate",
        caption="Pass rate per candidate (higher is better).",
        label="Horizontal bar chart of pass rate for each candidate.",
        standalone=standalone,
    )
