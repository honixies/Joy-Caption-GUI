from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from joycaption_desktop.contracts import GenerateRequest, GenerationMode


def json_ready(value: Any) -> Any:
    if is_dataclass(value):
        return json_ready(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if hasattr(value, "value"):
        return value.value
    return value


def request_from_payload(payload: dict[str, Any]) -> GenerateRequest:
    return GenerateRequest(
        image_path=Path(payload["image_path"]),
        mode=GenerationMode(payload["mode"]),
        preset_id=payload["preset_id"],
        postprocessor_ids=tuple(payload.get("postprocessor_ids", ())),
        max_words=payload.get("max_words"),
        extra_options=dict(payload.get("extra_options", {})),
    )
