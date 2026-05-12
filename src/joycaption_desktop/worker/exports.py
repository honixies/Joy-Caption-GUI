from __future__ import annotations

import csv
import json
from dataclasses import asdict
from errno import EACCES
from pathlib import Path

from joycaption_desktop.contracts import GenerateResult, JobStatus

SIDECAR_BESIDE = "beside"
SIDECAR_TEXT_OUT = "text_out"
SIDECAR_COMBINED = "combined"


def write_sidecar_txt(result: GenerateResult, output_dir: Path | None = None) -> Path:
    sidecar_path = (
        output_dir / f"{result.image_path.stem}.txt"
        if output_dir is not None
        else result.image_path.with_suffix(".txt")
    )
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        sidecar_path.write_text(result.postprocessed_text, encoding="utf-8")
        return sidecar_path
    except OSError as exc:
        if getattr(exc, "errno", None) != EACCES:
            raise

    fallback_path = _unique_sidecar_path(result.image_path, output_dir)
    fallback_path.write_text(result.postprocessed_text, encoding="utf-8")
    return fallback_path


def write_sidecar_txt_with_recovery(
    result: GenerateResult,
    *,
    output_dir: Path | None = None,
    recovery_dir: Path | None = None,
) -> Path:
    # Kept for API compatibility. Text outputs must stay in the selected source
    # folder; the sandbox is only for internal job artifacts.
    _ = recovery_dir
    return write_sidecar_txt(result, output_dir=output_dir)


def _unique_sidecar_path(image_path: Path, output_dir: Path | None = None) -> Path:
    parent = output_dir or image_path.parent
    base_path = parent / f"{image_path.stem}.joycaption.txt"
    if not base_path.exists():
        return base_path
    for index in range(2, 1000):
        candidate = parent / f"{image_path.stem}.joycaption-{index}.txt"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"No available sidecar filename beside {image_path}")


def write_combined_txt(
    results: list[GenerateResult],
    source_dir: Path,
    *,
    include_filenames: bool = True,
) -> Path:
    output_path = source_dir / f"{source_dir.name}.txt"
    lines = [
        _combined_line(result, include_filenames=include_filenames)
        for result in results
        if result.status == JobStatus.SUCCEEDED
    ]
    try:
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path
    except OSError as exc:
        if getattr(exc, "errno", None) != EACCES:
            raise
    fallback_path = _unique_combined_path(source_dir)
    fallback_path.write_text("\n".join(lines), encoding="utf-8")
    return fallback_path


def write_combined_txt_with_recovery(
    results: list[GenerateResult],
    source_dir: Path,
    *,
    include_filenames: bool = True,
    recovery_dir: Path | None = None,
) -> Path:
    # Kept for API compatibility. Combined text output belongs in source_dir;
    # permission errors should surface instead of silently saving to sandbox.
    _ = recovery_dir
    return write_combined_txt(
        results,
        source_dir,
        include_filenames=include_filenames,
    )


def _unique_combined_path(source_dir: Path) -> Path:
    base_path = source_dir / f"{source_dir.name}.joycaption.txt"
    if not base_path.exists():
        return base_path
    for index in range(2, 1000):
        candidate = source_dir / f"{source_dir.name}.joycaption-{index}.txt"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"No available combined output filename in {source_dir}")


def _single_line(text: str) -> str:
    return " ".join(text.splitlines()).strip()


def _combined_line(result: GenerateResult, *, include_filenames: bool) -> str:
    text = _single_line(result.postprocessed_text)
    return f"{result.image_path.name}\t{text}" if include_filenames else text


def write_results_csv(results: list[GenerateResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "image_path",
                "mode",
                "preset_id",
                "status",
                "text",
                "postprocessed_text",
                "error",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "image_path": str(result.image_path),
                    "mode": result.mode.value,
                    "preset_id": result.preset_id,
                    "status": result.status.value,
                    "text": result.text,
                    "postprocessed_text": result.postprocessed_text,
                    "error": result.error or "",
                }
            )


def write_results_json(results: list[GenerateResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = []
    for result in results:
        item = asdict(result)
        item["image_path"] = str(result.image_path)
        item["mode"] = result.mode.value
        item["status"] = result.status.value
        serializable.append(item)
    output_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_successful_sidecars(
    results: list[GenerateResult],
    *,
    mode: str = SIDECAR_BESIDE,
    source_dir: Path | None = None,
    combined_include_filenames: bool = True,
    recovery_dir: Path | None = None,
) -> list[Path]:
    if mode == SIDECAR_COMBINED:
        if source_dir is None:
            successful = [result for result in results if result.status == JobStatus.SUCCEEDED]
            if not successful:
                return []
            source_dir = successful[0].image_path.parent
        return [
            write_combined_txt_with_recovery(
                results,
                source_dir,
                include_filenames=combined_include_filenames,
                recovery_dir=recovery_dir,
            )
        ]

    written: list[Path] = []
    for result in results:
        if result.status == JobStatus.SUCCEEDED:
            output_dir = result.image_path.parent / "text_out" if mode == SIDECAR_TEXT_OUT else None
            written.append(
                write_sidecar_txt_with_recovery(
                    result,
                    output_dir=output_dir,
                    recovery_dir=recovery_dir,
                )
            )
    return written
