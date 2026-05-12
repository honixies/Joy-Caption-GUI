# Runtime Sandbox Specification

The app must not modify global Python, system site-packages, or user-managed ML
environments. All mutable runtime state belongs to an app-managed sandbox.

## Sandbox Layout

```text
<app-data>/JoyCaptionDesktop/
  runtime/
    python/
    venv/
    manifests/
  models/
    fancyfeast--llama-joycaption-beta-one-hf-llava/
  cache/
    huggingface/
    torch/
  plugins/
    presets/
    postprocessors/
  jobs/
    <job-id>/
      results.csv
      results.json
      manifest.json
  logs/
    app.log
    worker.log
    setup.log
  backups/
    settings-<timestamp>.json
  settings.json
```

## Setup Wizard Responsibilities

1. Detect OS, architecture, GPU backend, VRAM, driver hints, and available disk.
2. Select a runtime profile.
3. Create or repair the sandbox directories.
4. Install or verify the private Python environment.
5. Install profile-specific ML dependencies.
6. Download model files into the versioned model cache.
7. Run a smoke test with a bundled tiny image.
8. Save a setup report and make it exportable.

## Runtime Profiles

### Windows NVIDIA 4-bit

- Primary beta profile.
- Expected to target users with enough VRAM for the reference 4-bit path.
- Uses CUDA PyTorch wheels and `bitsandbytes` where compatible.

### Windows NVIDIA FP8 / BF16

- Optional high-VRAM profile.
- Requires stricter diagnostics because the reference README reports about
  17.4 GB VRAM for FP8.

### macOS Apple Silicon

- Gate profile.
- Must prove model loading, memory behavior, and generation correctness through
  a smoke test before beta inclusion.

## Repair Policy

The user-facing repair path should support:

- Re-check setup.
- Reinstall dependencies.
- Clear model cache.
- Re-download model.
- Export logs.
- Reset sandbox while preserving settings backup.

No repair action should require manual deletion of hidden directories.
