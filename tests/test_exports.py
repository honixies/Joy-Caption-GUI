import json
from unittest.mock import patch

from joycaption_desktop.contracts import GenerateResult, GenerationMode, JobStatus
from joycaption_desktop.worker.exports import (
    SIDECAR_COMBINED,
    SIDECAR_TEXT_OUT,
    export_successful_sidecars,
    write_results_csv,
    write_results_json,
)


def test_export_outputs(tmp_path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake")
    result = GenerateResult(
        image_path=image_path,
        mode=GenerationMode.TAGS,
        preset_id="tags-dataset",
        text="cat, cat, grass",
        postprocessed_text="cat, grass",
        status=JobStatus.SUCCEEDED,
    )

    sidecars = export_successful_sidecars([result])
    csv_path = tmp_path / "job" / "results.csv"
    json_path = tmp_path / "job" / "results.json"
    write_results_csv([result], csv_path)
    write_results_json([result], json_path)

    assert sidecars == [tmp_path / "sample.txt"]
    assert (tmp_path / "sample.txt").read_text(encoding="utf-8") == "cat, grass"
    assert "sample.jpg" in csv_path.read_text(encoding="utf-8")
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded[0]["postprocessed_text"] == "cat, grass"


def test_export_sidecar_falls_back_when_primary_is_not_writable(tmp_path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake")
    result = GenerateResult(
        image_path=image_path,
        mode=GenerationMode.TAGS,
        preset_id="tags-dataset",
        text="cat",
        postprocessed_text="cat",
        status=JobStatus.SUCCEEDED,
    )

    original_write_text = type(image_path).write_text

    def fail_primary(path, *args, **kwargs):
        if path == tmp_path / "sample.txt":
            raise PermissionError(13, "Permission denied", str(path))
        return original_write_text(path, *args, **kwargs)

    with patch.object(type(image_path), "write_text", fail_primary):
        sidecars = export_successful_sidecars([result])

    assert sidecars == [tmp_path / "sample.joycaption.txt"]
    assert (tmp_path / "sample.joycaption.txt").read_text(encoding="utf-8") == "cat"


def test_export_sidecar_to_text_out_folder(tmp_path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake")
    result = GenerateResult(
        image_path=image_path,
        mode=GenerationMode.TAGS,
        preset_id="tags-dataset",
        text="cat",
        postprocessed_text="cat",
        status=JobStatus.SUCCEEDED,
    )

    sidecars = export_successful_sidecars([result], mode=SIDECAR_TEXT_OUT, source_dir=tmp_path)

    assert sidecars == [tmp_path / "text_out" / "sample.txt"]
    assert (tmp_path / "text_out" / "sample.txt").read_text(encoding="utf-8") == "cat"


def test_export_combined_folder_text(tmp_path):
    first = tmp_path / "a.jpg"
    second = tmp_path / "b.png"
    first.write_bytes(b"fake")
    second.write_bytes(b"fake")
    results = [
        GenerateResult(
            image_path=first,
            mode=GenerationMode.TAGS,
            preset_id="tags-dataset",
            text="cat",
            postprocessed_text="cat\non grass",
            status=JobStatus.SUCCEEDED,
        ),
        GenerateResult(
            image_path=second,
            mode=GenerationMode.TAGS,
            preset_id="tags-dataset",
            text="dog",
            postprocessed_text="dog",
            status=JobStatus.SUCCEEDED,
        ),
    ]

    sidecars = export_successful_sidecars(results, mode=SIDECAR_COMBINED, source_dir=tmp_path)

    assert sidecars == [tmp_path / f"{tmp_path.name}.txt"]
    assert sidecars[0].read_text(encoding="utf-8") == "a.jpg\tcat on grass\nb.png\tdog"


def test_export_combined_folder_text_without_filenames(tmp_path):
    first = tmp_path / "a.jpg"
    second = tmp_path / "b.png"
    first.write_bytes(b"fake")
    second.write_bytes(b"fake")
    results = [
        GenerateResult(
            image_path=first,
            mode=GenerationMode.TAGS,
            preset_id="tags-dataset",
            text="cat",
            postprocessed_text="cat",
            status=JobStatus.SUCCEEDED,
        ),
        GenerateResult(
            image_path=second,
            mode=GenerationMode.TAGS,
            preset_id="tags-dataset",
            text="dog",
            postprocessed_text="dog\nrunning",
            status=JobStatus.SUCCEEDED,
        ),
    ]

    sidecars = export_successful_sidecars(
        results,
        mode=SIDECAR_COMBINED,
        source_dir=tmp_path,
        combined_include_filenames=False,
    )

    assert sidecars == [tmp_path / f"{tmp_path.name}.txt"]
    assert sidecars[0].read_text(encoding="utf-8") == "cat\ndog running"


def test_export_sidecar_raises_when_original_folder_is_not_writable(tmp_path):
    image_path = tmp_path / "sample.jpg"
    recovery_dir = tmp_path / "job"
    image_path.write_bytes(b"fake")
    result = GenerateResult(
        image_path=image_path,
        mode=GenerationMode.TAGS,
        preset_id="tags-dataset",
        text="cat",
        postprocessed_text="cat",
        status=JobStatus.SUCCEEDED,
    )

    original_write_text = type(image_path).write_text

    def fail_original_paths(path, *args, **kwargs):
        if path.parent == tmp_path:
            raise PermissionError(13, "Permission denied", str(path))
        return original_write_text(path, *args, **kwargs)

    with patch.object(type(image_path), "write_text", fail_original_paths):
        try:
            export_successful_sidecars([result], recovery_dir=recovery_dir)
        except PermissionError:
            pass
        else:
            raise AssertionError("Expected PermissionError when selected folder is not writable")

    assert not recovery_dir.exists()


def test_export_combined_raises_when_original_folder_is_not_writable(tmp_path):
    image_path = tmp_path / "sample.jpg"
    recovery_dir = tmp_path / "job"
    image_path.write_bytes(b"fake")
    result = GenerateResult(
        image_path=image_path,
        mode=GenerationMode.TAGS,
        preset_id="tags-dataset",
        text="cat",
        postprocessed_text="cat",
        status=JobStatus.SUCCEEDED,
    )

    original_write_text = type(image_path).write_text

    def fail_original_combined(path, *args, **kwargs):
        if path.parent == tmp_path:
            raise PermissionError(13, "Permission denied", str(path))
        return original_write_text(path, *args, **kwargs)

    with patch.object(type(image_path), "write_text", fail_original_combined):
        try:
            export_successful_sidecars(
                [result],
                mode=SIDECAR_COMBINED,
                source_dir=tmp_path,
                recovery_dir=recovery_dir,
            )
        except PermissionError:
            pass
        else:
            raise AssertionError("Expected PermissionError when selected folder is not writable")

    assert not recovery_dir.exists()
