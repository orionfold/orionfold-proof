"""Estimated token pricing for hosted candidates (Gate 6).

Costs on the leaderboard and receipt are always labeled **estimated** — the charter says
never to block the local-first path on cost precision. This is a deliberately tiny table for
the default models; an unknown model yields ``0.0`` (shown as estimated, not authoritative).
Prices are USD per 1M tokens (input, output) and easy to update as rates change.
"""

from __future__ import annotations

# (input_usd_per_1m, output_usd_per_1m). Estimated list prices, kept in step with the bundled
# catalog (src/orionfold/catalog/catalog.json). An unknown model still yields 0.0.
_PRICES: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
    # OpenAI (current GPT-5.x line; gpt-4o* kept for legacy/tests)
    "gpt-5.4-nano": (0.20, 1.25),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.5": (5.00, 30.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    # Google Gemini (current 3.x line; 2.5-flash kept for legacy/tests)
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-2.5-flash": (0.30, 2.50),
    # OpenRouter slugs (the model id is passed through verbatim to the API)
    "meta-llama/llama-3.1-8b-instruct": (0.02, 0.03),
    "meta-llama/llama-3.3-70b-instruct": (0.10, 0.32),
    "openai/gpt-5.4-mini": (0.75, 4.50),
    "anthropic/claude-opus-4.8": (5.00, 25.00),
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
