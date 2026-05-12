from __future__ import annotations

from pathlib import Path

from joycaption_desktop.contracts import (
    BatchJob,
    GenerateRequest,
    GenerateResult,
    GenerationMode,
    JobStatus,
    ModelProfile,
)
from joycaption_desktop.postprocessors.builtin import apply_postprocessors
from joycaption_desktop.presets.builtin import BUILTIN_PRESETS
from joycaption_desktop.worker.diagnostics import build_worker_health
from joycaption_desktop.worker.joycaption_adapter import JoyCaptionAdapter


class JoyCaptionWorker:
    """Boundary around JoyCaption model loading and inference.

    The real model integration should be adapted from the reference
    `Run_GUI.py`, but UI code should only call this service contract.
    """

    def __init__(
        self,
        profile: ModelProfile,
        model_cache_dir: Path,
        *,
        use_real_model: bool = False,
    ) -> None:
        self.profile = profile
        self.model_cache_dir = model_cache_dir
        self.use_real_model = use_real_model
        self.adapter = JoyCaptionAdapter(profile, model_cache_dir)
        self._model_loaded = False

    @property
    def model_loaded(self) -> bool:
        return self._model_loaded

    def load_model(self) -> None:
        if not self.model_cache_dir.exists():
            self.model_cache_dir.mkdir(parents=True, exist_ok=True)
        if self.use_real_model:
            self.adapter.load()
        self._model_loaded = True

    def health(self):
        return build_worker_health(self.profile, self.model_loaded)

    def generate(self, request: GenerateRequest) -> GenerateResult:
        if request.preset_id not in BUILTIN_PRESETS and not request.extra_options.get("custom_prompt"):
            return self._failure(request, f"Unknown preset: {request.preset_id}")
        if not request.image_path.exists():
            return self._failure(request, f"Image not found: {request.image_path}")
        if not self.model_loaded:
            return self._failure(request, "Model is not loaded.")

        try:
            raw_text = (
                self._placeholder_inference(request)
                if not self.adapter.loaded
                else self.adapter.generate(request)
            )
        except Exception as exc:
            return self._failure(request, str(exc))
        processed = apply_postprocessors(raw_text, request.postprocessor_ids)
        return GenerateResult(
            image_path=request.image_path,
            mode=request.mode,
            preset_id=request.preset_id,
            text=raw_text,
            postprocessed_text=processed,
            status=JobStatus.SUCCEEDED,
            metadata={"profile": self.profile.id},
        )

    def iter_batch_requests(self, job: BatchJob) -> list[GenerateRequest]:
        paths = job.input_dir.rglob("*") if job.include_subfolders else job.input_dir.iterdir()
        image_paths = [
            path
            for path in sorted(paths)
            if path.is_file() and path.suffix.lower() in job.image_extensions
        ]
        return [
            GenerateRequest(
                image_path=path,
                mode=job.mode,
                preset_id=job.preset_id,
                postprocessor_ids=job.postprocessor_ids,
                extra_options=dict(job.extra_options),
            )
            for path in image_paths
        ]

    def _placeholder_inference(self, request: GenerateRequest) -> str:
        custom_prompt = request.extra_options.get("custom_prompt")
        if custom_prompt:
            if request.mode == GenerationMode.TAGS:
                return f"{request.image_path.stem}, 사용자정의, 프롬프트, 테스트 결과"
            return f"사용자 정의 프롬프트: {request.image_path.name} 테스트 추론 결과"
        preset = BUILTIN_PRESETS[request.preset_id]
        if request.mode == GenerationMode.TAGS:
            return f"{request.image_path.stem}, 이미지, 테스트 추론 결과"
        return f"{preset.name}: {request.image_path.name} 테스트 추론 결과"

    def _failure(self, request: GenerateRequest, error: str) -> GenerateResult:
        return GenerateResult(
            image_path=request.image_path,
            mode=request.mode,
            preset_id=request.preset_id,
            text="",
            postprocessed_text="",
            status=JobStatus.FAILED,
            error=error,
            metadata={"profile": self.profile.id},
        )
