"""Record token counts already returned by Gemini; this makes no API calls."""

import json
import os
from pathlib import Path
from threading import Lock

_WRITE_LOCK = Lock()


def record_gemini_usage(stage: str, model: str, usage) -> None:
    path = os.environ.get("LMC_RUN_TOKEN_USAGE_PATH")
    if not path or usage is None:
        return

    input_tokens = getattr(usage, "total_input_tokens", None)
    if input_tokens is None:
        input_tokens = getattr(usage, "prompt_token_count", 0)
    output_tokens = getattr(usage, "total_output_tokens", None)
    if output_tokens is None:
        output_tokens = getattr(usage, "candidates_token_count", 0)
    cached_tokens = getattr(usage, "total_cached_tokens", 0)
    total_tokens = getattr(usage, "total_tokens", None)
    if total_tokens is None:
        total_tokens = getattr(usage, "total_token_count", None)
    if total_tokens is None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)

    record = {
        "stage": stage,
        "model": model,
        "input_tokens": int(input_tokens or 0),
        "cached_input_tokens": int(cached_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with _WRITE_LOCK, target.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record) + "\n")
    except OSError:
        # Usage reporting must never make an otherwise successful generation fail.
        return
