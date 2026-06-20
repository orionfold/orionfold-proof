"""Estimated token pricing for hosted candidates (Gate 6).

Costs on the leaderboard and receipt are always labeled **estimated** — the charter says
never to block the local-first path on cost precision. This is a deliberately tiny table for
the default models; an unknown model yields ``0.0`` (shown as estimated, not authoritative).
Prices are USD per 1M tokens (input, output) and easy to update as rates change.
"""

from __future__ import annotations

# (input_usd_per_1m, output_usd_per_1m). Anthropic rates per the claude-api skill table.
_PRICES: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
    # OpenAI (approximate, public list pricing)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    # Google Gemini (approximate, public list pricing)
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-3.5-flash": (0.30, 2.50),
}


def estimate_cost(model: str | None, input_tokens: int, output_tokens: int) -> float:
    """Estimated USD cost for a single completion. Unknown/local models → ``0.0``."""
    if not model:
        return 0.0
    rates = _PRICES.get(model)
    if rates is None:
        return 0.0
    in_rate, out_rate = rates
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
