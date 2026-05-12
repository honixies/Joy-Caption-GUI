# Worker JSONL Protocol

The desktop shell should launch `joycaption_desktop.worker_cli` as a long-lived
child process inside the app-managed Python sandbox.

Each request is one JSON object on stdin. Each response is one JSON object on
stdout.

## Start Command

```text
python -m joycaption_desktop.worker_cli --profile windows-nvidia-4bit --model-cache-dir <sandbox>/models
```

Use `--real-model` only after the setup wizard has installed dependencies and
downloaded/validated the model profile. Without `--real-model`, the worker uses
placeholder inference for UI and packaging smoke tests.

## Commands

### Health

```json
{"command":"health"}
```

### Load Model

```json
{"command":"load_model"}
```

### Generate

```json
{
  "command": "generate",
  "request": {
    "image_path": "C:/path/to/image.jpg",
    "mode": "tags",
    "preset_id": "tags-dataset",
    "postprocessor_ids": ["normalize-commas", "dedupe-tags"],
    "extra_options": {"temperature": 0.6, "top_p": 0.9}
  }
}
```

### Shutdown

```json
{"command":"shutdown"}
```

## Shell Spike Requirement

The Tauri/Electron comparison must prove that the selected shell can:

- Start this process.
- Send `health`.
- Send `load_model` in placeholder mode.
- Send `generate` for a local image.
- Display errors from failed requests.
- Shut the worker down cleanly.
