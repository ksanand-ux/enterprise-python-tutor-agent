import json
import logging
import os
from decimal import Decimal, InvalidOperation

logger = logging.getLogger("tutor")


def record_usage(response, model, trace_id):
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    details = getattr(usage, "input_tokens_details", None)
    cached_tokens = getattr(details, "cached_tokens", 0)
    estimate = None
    basis = os.getenv("TUTOR_PRICE_BASIS")
    # Optional operator-supplied token rates. Tool fees are deliberately excluded.
    if basis and input_tokens is not None and output_tokens is not None:
        try:
            rates = [Decimal(os.environ[name]) for name in (
                "TUTOR_INPUT_USD_PER_MILLION", "TUTOR_CACHED_INPUT_USD_PER_MILLION",
                "TUTOR_OUTPUT_USD_PER_MILLION",
            )]
            if all(rate.is_finite() and rate >= 0 for rate in rates):
                estimate = str((
                    (input_tokens - cached_tokens) * rates[0]
                    + cached_tokens * rates[1] + output_tokens * rates[2]
                ) / Decimal(1000000))
        except (KeyError, InvalidOperation, TypeError):
            pass
    logger.info(json.dumps({
        "event": "model_usage", "trace_id": trace_id, "model": model,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "cached_input_tokens": cached_tokens,
        "estimated_token_cost_usd": estimate,
        "price_basis": basis if estimate is not None else None,
        "tool_fees_included": False,
    }))
