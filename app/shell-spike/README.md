# Desktop Shell Spike

This folder is reserved for the Tauri/Electron comparison spike.

The spike must use the Python worker contracts under `src/joycaption_desktop`
and should not import JoyCaption model code directly in the UI layer.

## Required Checks

- Start the Python worker from the shell.
- Send a health request.
- Send a placeholder generation request.
- Keep the worker alive over the JSONL protocol in `docs/worker-jsonl-protocol.md`.
- Stream batch progress.
- Open the sandbox folder from app settings.
- Export logs.
- Package a Windows test build.

## Decision Output

Write the final shell decision to `docs/adr/0002-select-desktop-shell.md`.
