from __future__ import annotations

from dataclasses import dataclass

from joycaption_desktop.contracts import GenerationMode


@dataclass(frozen=True)
class GenerationPreset:
    id: str
    name: str
    mode: GenerationMode
    prompt: str
    description: str


BUILTIN_PRESETS = {
    "tags-dataset": GenerationPreset(
        id="tags-dataset",
        name="Dataset Tags",
        mode=GenerationMode.TAGS,
        prompt=(
            "Generate concise comma-separated visual tags for this image. "
            "Prefer concrete subjects, attributes, clothing, setting, style, "
            "composition, and visible actions. Do not write full sentences."
        ),
        description="Comma-separated tags suitable for dataset sidecar files.",
    ),
    "caption-short": GenerationPreset(
        id="caption-short",
        name="Short Caption",
        mode=GenerationMode.SHORT_CAPTION,
        prompt="Write a short natural-language caption for this image.",
        description="One compact sentence for browsing and quick review.",
    ),
    "description-long": GenerationPreset(
        id="description-long",
        name="Long Description",
        mode=GenerationMode.LONG_DESCRIPTION,
        prompt=(
            "Write a detailed description of this image, including the main "
            "subject, setting, visual style, notable objects, and composition."
        ),
        description="Detailed descriptive caption for review and metadata.",
    ),
}
