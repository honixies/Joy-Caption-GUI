from __future__ import annotations

import re
from collections.abc import Callable


def trim_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_commas(text: str) -> str:
    parts = [part.strip() for part in text.replace("\n", ",").split(",")]
    return ", ".join(part for part in parts if part)


def dedupe_tags(text: str) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for raw_part in text.split(","):
        tag = raw_part.strip()
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            output.append(tag)
    return ", ".join(output)


def strip_trailing_period_for_tags(text: str) -> str:
    return text[:-1] if text.endswith(".") else text


POSTPROCESSORS: dict[str, Callable[[str], str]] = {
    "trim-whitespace": trim_whitespace,
    "normalize-commas": normalize_commas,
    "dedupe-tags": dedupe_tags,
    "strip-tag-period": strip_trailing_period_for_tags,
}


def apply_postprocessors(text: str, ids: tuple[str, ...]) -> str:
    result = text
    for processor_id in ids:
        processor = POSTPROCESSORS.get(processor_id)
        if processor is None:
            raise KeyError(f"Unknown postprocessor: {processor_id}")
        result = processor(result)
    return result
