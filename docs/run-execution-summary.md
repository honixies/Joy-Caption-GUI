# JoyCaption Desktop Beta Run Summary

This run starts the Seed execution for a beta-quality desktop app that turns
images into tags, short captions, and long descriptions using JoyCaption.

## Reference Findings

- Reference repo: `reference/joy-caption-beta-one-gui-mod`
- Current UI/runtime style: single-file PyQt app (`Run_GUI.py`) plus a 4-bit variant.
- Model path used by the reference app: `fancyfeast/llama-joycaption-beta-one-hf-llava`.
- Core dependencies include `torch`, `torchvision`, `torchaudio`, `transformers`,
  `huggingface_hub`, `accelerate`, `peft`, `bitsandbytes`, `PyQt5`, `pillow`,
  and `liger-kernel`.
- The reference app already supports sidecar `.txt` saving and batch caption
  saving, but model loading, UI, prompts, inference, and persistence are tightly
  coupled inside the GUI file.

## Execution Direction

The first implementation slice extracts product contracts and backend structure
without committing to Tauri or Electron yet. The desktop shell remains a spike
until worker startup, sandbox access, IPC, and packaging behavior are validated.

## Current Slice Deliverables

- Seed file saved at `joy-caption-desktop-beta.seed.yaml`.
- Architecture decision record for shell selection.
- Runtime sandbox specification.
- Python worker contracts for model profiles, generation requests, batch jobs,
  diagnostics, exports, and setup state.
- Built-in preset and post-processing modules that can be reused by the future UI.

## Known Gate

The Ouroboros MCP execution tools registered in the local log, but they were not
exposed to this Codex session through tool search. The CLI orchestrator dry-run
created session `orch_d85447d003e1` and execution `exec_6a7b11b9b64a`, then
exited with code 137. Legacy non-orchestrator dry-run validated the Seed file.
