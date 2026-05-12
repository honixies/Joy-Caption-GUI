from __future__ import annotations

import importlib.util

from joycaption_desktop.contracts import GpuDiagnostic, ModelProfile, WorkerHealth


def dependency_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def dependency_report(profile: ModelProfile) -> dict[str, bool]:
    module_names = {
        "torch": "torch",
        "torchvision": "torchvision",
        "torchaudio": "torchaudio",
        "transformers": "transformers",
        "accelerate": "accelerate",
        "peft": "peft",
        "bitsandbytes": "bitsandbytes",
        "pillow": "PIL",
        "huggingface_hub": "huggingface_hub",
        "sentencepiece": "sentencepiece",
        "liger-kernel": "liger_kernel",
    }
    report: dict[str, bool] = {}
    for dependency in profile.dependencies:
        package_name = dependency.split("==", 1)[0].split(">=", 1)[0]
        module_name = module_names.get(package_name, package_name.replace("-", "_"))
        report[package_name] = dependency_available(module_name)
    return report


def detect_gpu() -> GpuDiagnostic:
    if not dependency_available("torch"):
        return GpuDiagnostic(
            backend="unknown",
            device_name=None,
            vram_gb=None,
            available=False,
            errors=("torch is not installed in this runtime.",),
        )

    import torch

    if torch.cuda.is_available():
        index = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(index)
        return GpuDiagnostic(
            backend="cuda",
            device_name=props.name,
            vram_gb=round(props.total_memory / (1024**3), 2),
            available=True,
        )

    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return GpuDiagnostic(
            backend="mps",
            device_name="Apple Silicon GPU",
            vram_gb=None,
            available=True,
            warnings=("MPS support must pass JoyCaption smoke tests before beta inclusion.",),
        )

    return GpuDiagnostic(
        backend="cpu",
        device_name=None,
        vram_gb=None,
        available=False,
        warnings=("No CUDA or MPS GPU backend detected.",),
    )


def build_worker_health(
    profile: ModelProfile,
    model_loaded: bool,
    *,
    use_real_model: bool,
) -> WorkerHealth:
    if not use_real_model:
        return WorkerHealth(
            ok=True,
            profile_id=profile.id,
            model_loaded=model_loaded,
            backend="test",
            device_name="테스트 모드",
            vram_gb=None,
            dependencies_available={},
            warnings=(),
            errors=(),
        )

    gpu = detect_gpu()
    dependencies = dependency_report(profile)
    missing = tuple(name for name, available in dependencies.items() if not available)
    errors = gpu.errors
    warnings = gpu.warnings
    if missing:
        warnings = warnings + (f"Missing dependencies: {', '.join(missing)}",)
    if profile.device != gpu.backend and gpu.backend != "unknown":
        warnings = warnings + (
            f"Selected profile expects {profile.device}, but detected {gpu.backend}.",
        )
    return WorkerHealth(
        ok=not errors,
        profile_id=profile.id,
        model_loaded=model_loaded,
        backend=gpu.backend,
        device_name=gpu.device_name,
        vram_gb=gpu.vram_gb,
        dependencies_available=dependencies,
        warnings=warnings,
        errors=errors,
    )
