from __future__ import annotations

from joycaption_desktop.contracts import ModelProfile

JOYCAPTION_MODEL_ID = "fancyfeast/llama-joycaption-beta-one-hf-llava"

WINDOWS_NVIDIA_4BIT = ModelProfile(
    id="windows-nvidia-4bit",
    name="Windows NVIDIA 4-bit",
    model_id=JOYCAPTION_MODEL_ID,
    device="cuda",
    precision="4bit",
    min_vram_gb=10.0,
    dependencies=(
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "accelerate==1.0.0",
        "peft==0.12.0",
        "bitsandbytes",
        "pillow",
        "huggingface_hub",
        "sentencepiece",
    ),
    notes="Primary beta target; mirrors the reference 4-bit path.",
)

WINDOWS_NVIDIA_BF16 = ModelProfile(
    id="windows-nvidia-bf16",
    name="Windows NVIDIA BF16/FP8-capable",
    model_id=JOYCAPTION_MODEL_ID,
    device="cuda",
    precision="bf16",
    min_vram_gb=17.4,
    dependencies=WINDOWS_NVIDIA_4BIT.dependencies + ("liger-kernel==0.5.9",),
    notes="High-VRAM profile based on reference README guidance.",
)

MACOS_APPLE_SILICON_GATE = ModelProfile(
    id="macos-apple-silicon-gate",
    name="macOS Apple Silicon gate",
    model_id=JOYCAPTION_MODEL_ID,
    device="mps",
    precision="float16",
    min_vram_gb=None,
    dependencies=(
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "accelerate==1.0.0",
        "peft==0.12.0",
        "pillow",
        "huggingface_hub",
        "sentencepiece",
    ),
    notes="Must pass model-load and smoke-test validation before beta inclusion.",
)

PROFILES = {
    profile.id: profile
    for profile in (
        WINDOWS_NVIDIA_4BIT,
        WINDOWS_NVIDIA_BF16,
        MACOS_APPLE_SILICON_GATE,
    )
}
