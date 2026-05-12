from __future__ import annotations

from pathlib import Path
from threading import Thread

from joycaption_desktop.contracts import GenerateRequest, ModelProfile
from joycaption_desktop.presets.builtin import BUILTIN_PRESETS


class JoyCaptionAdapter:
    """Thin adapter for the real JoyCaption Transformers path.

    Heavy imports live inside this module so the desktop shell and setup wizard
    can run diagnostics without importing Torch/Transformers at startup.
    """

    def __init__(self, profile: ModelProfile, model_cache_dir: Path) -> None:
        self.profile = profile
        self.model_cache_dir = model_cache_dir
        self.processor = None
        self.model = None

    @property
    def loaded(self) -> bool:
        return self.processor is not None and self.model is not None

    def load(self) -> None:
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoProcessor, LlavaForConditionalGeneration
        try:
            from transformers import BitsAndBytesConfig
        except ImportError:
            BitsAndBytesConfig = None

        model_dir = snapshot_download(
            repo_id=self.profile.model_id,
            cache_dir=str(self.model_cache_dir),
        )

        model_kwargs = {
            "torch_dtype": self._torch_dtype(torch),
            "low_cpu_mem_usage": True,
            "device_map": "auto",
            "cache_dir": str(self.model_cache_dir),
        }
        if self.profile.precision == "4bit":
            if BitsAndBytesConfig is None:
                raise RuntimeError("4-bit profile requires transformers BitsAndBytesConfig.")
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                llm_int8_skip_modules=["vision_tower", "multi_modal_projector"],
            )
            model_kwargs["torch_dtype"] = "auto"

        self.processor = AutoProcessor.from_pretrained(
            model_dir,
            cache_dir=str(self.model_cache_dir),
        )
        self.model = LlavaForConditionalGeneration.from_pretrained(
            model_dir,
            **model_kwargs,
        )
        self.model.eval()

        if self.profile.precision != "4bit":
            self._try_apply_liger_kernel()

    def generate(self, request: GenerateRequest) -> str:
        if not self.loaded:
            raise RuntimeError("JoyCaption model is not loaded.")

        import torch
        from PIL import Image
        from transformers import TextIteratorStreamer

        try:
            image = Image.open(request.image_path).convert("RGB")
        except Exception as exc:
            raise RuntimeError(f"이미지를 열 수 없습니다: {request.image_path} ({exc})") from exc
        prompt = request.extra_options.get("custom_prompt")
        if not prompt:
            preset = BUILTIN_PRESETS[request.preset_id]
            prompt = preset.prompt
        if request.max_words:
            prompt = f"{prompt} Keep the result under {request.max_words} words."

        convo = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that describes images for "
                    "tagging, captioning, and dataset preparation."
                ),
            },
            {"role": "user", "content": prompt.strip()},
        ]
        convo_string = self.processor.apply_chat_template(
            convo,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.processor(
            text=[convo_string],
            images=[image],
            return_tensors="pt",
        ).to(self.model.device)
        inputs["pixel_values"] = inputs["pixel_values"].to(self.model.dtype)

        streamer = TextIteratorStreamer(
            self.processor.tokenizer,
            timeout=20.0,
            skip_prompt=True,
            skip_special_tokens=True,
        )
        generate_kwargs = dict(
            **inputs,
            max_new_tokens=int(request.extra_options.get("max_new_tokens", 512)),
            do_sample=True,
            use_cache=True,
            temperature=float(request.extra_options.get("temperature", 0.6)),
            top_p=float(request.extra_options.get("top_p", 0.9)),
            streamer=streamer,
        )

        with torch.no_grad():
            thread_error: list[BaseException] = []

            def run_generate() -> None:
                try:
                    self.model.generate(**generate_kwargs)
                except BaseException as exc:
                    thread_error.append(exc)

            thread = Thread(target=run_generate)
            thread.start()
            parts = [token for token in streamer if token]
            thread.join()
            if thread_error:
                raise RuntimeError(f"모델 추론 실패: {thread_error[0]}") from thread_error[0]

        return "".join(parts).strip()

    def _torch_dtype(self, torch):
        if self.profile.device == "cuda" and hasattr(torch, "bfloat16"):
            return torch.bfloat16
        if self.profile.device == "mps" and hasattr(torch, "float16"):
            return torch.float16
        return torch.float32

    def _try_apply_liger_kernel(self) -> None:
        try:
            from liger_kernel.transformers import apply_liger_kernel_to_llama
        except ImportError:
            return
        if self.model is not None and hasattr(self.model, "language_model"):
            apply_liger_kernel_to_llama(model=self.model.language_model)
