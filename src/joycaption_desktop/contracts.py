from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class GenerationMode(str, Enum):
    TAGS = "tags"
    SHORT_CAPTION = "short_caption"
    LONG_DESCRIPTION = "long_description"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ModelProfile:
    id: str
    name: str
    model_id: str
    device: str
    precision: str
    min_vram_gb: float | None
    dependencies: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class GenerateRequest:
    image_path: Path
    mode: GenerationMode
    preset_id: str
    postprocessor_ids: tuple[str, ...] = ()
    max_words: int | None = None
    extra_options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerateResult:
    image_path: Path
    mode: GenerationMode
    preset_id: str
    text: str
    postprocessed_text: str
    status: JobStatus
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchJob:
    id: str
    input_dir: Path
    output_dir: Path | None
    mode: GenerationMode
    preset_id: str
    postprocessor_ids: tuple[str, ...]
    extra_options: dict[str, Any] = field(default_factory=dict)
    image_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    include_subfolders: bool = False


@dataclass(frozen=True)
class GpuDiagnostic:
    backend: str
    device_name: str | None
    vram_gb: float | None
    available: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkerHealth:
    ok: bool
    profile_id: str
    model_loaded: bool
    backend: str
    device_name: str | None
    vram_gb: float | None
    dependencies_available: dict[str, bool]
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class SetupState:
    sandbox_root: Path
    selected_profile: str | None
    runtime_ready: bool
    model_ready: bool
    smoke_test_passed: bool
    diagnostics: tuple[GpuDiagnostic, ...] = ()
