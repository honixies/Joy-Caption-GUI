import json

from joycaption_desktop.runtime.profiles import WINDOWS_NVIDIA_4BIT
from joycaption_desktop.worker.protocol import json_ready
from joycaption_desktop.worker.service import JoyCaptionWorker
from joycaption_desktop.worker_cli import handle_command


def test_worker_jsonl_health_command(tmp_path):
    worker = JoyCaptionWorker(WINDOWS_NVIDIA_4BIT, tmp_path / "models")

    response = handle_command(worker, '{"command":"health"}')

    assert response["ok"] is True
    assert response["payload"]["profile_id"] == "windows-nvidia-4bit"


def test_worker_jsonl_placeholder_generate_command(tmp_path):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"fake")
    worker = JoyCaptionWorker(WINDOWS_NVIDIA_4BIT, tmp_path / "models")
    load_response = handle_command(worker, '{"command":"load_model"}')
    generate_response = handle_command(
        worker,
        json.dumps(
            {
                "command": "generate",
                "request": {
                    "image_path": str(image_path),
                    "mode": "tags",
                    "preset_id": "tags-dataset",
                    "postprocessor_ids": ["normalize-commas", "dedupe-tags"],
                },
            }
        ),
    )

    assert load_response["payload"]["model_loaded"] is True
    assert generate_response["ok"] is True
    assert generate_response["payload"]["status"] == "succeeded"


def test_json_ready_converts_paths_and_enums(tmp_path):
    worker = JoyCaptionWorker(WINDOWS_NVIDIA_4BIT, tmp_path / "models")

    ready = json_ready(worker.health())

    assert ready["profile_id"] == "windows-nvidia-4bit"
    assert isinstance(ready["dependencies_available"], dict)
