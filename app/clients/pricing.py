TOKENS_PER_MILLION = 1_000_000


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_price_per_mtok: float,
    output_price_per_mtok: float,
) -> float:
    """Estimated USD cost from token counts and per-million-token prices (set in `.env`)."""
    return (
        input_tokens * input_price_per_mtok + output_tokens * output_price_per_mtok
    ) / TOKENS_PER_MILLION
