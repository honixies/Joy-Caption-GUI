from joycaption_desktop.contracts import GenerateRequest, GenerationMode, JobStatus
from joycaption_desktop.runtime.profiles import WINDOWS_NVIDIA_4BIT
from joycaption_desktop.worker.service import JoyCaptionWorker


def test_worker_placeholder_generation_requires_loaded_model(tmp_path):
    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"fake")
    worker = JoyCaptionWorker(WINDOWS_NVIDIA_4BIT, tmp_path / "models")
    request = GenerateRequest(
        image_path=image_path,
        mode=GenerationMode.TAGS,
        preset_id="tags-dataset",
        postprocessor_ids=("normalize-commas", "dedupe-tags"),
    )

    failed = worker.generate(request)
    worker.load_model()
    succeeded = worker.generate(request)

    assert failed.status == JobStatus.FAILED
    assert succeeded.status == JobStatus.SUCCEEDED
    assert "테스트 추론 결과" in succeeded.postprocessed_text
