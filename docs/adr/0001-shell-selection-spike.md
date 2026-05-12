# ADR 0001: Defer Desktop Shell Choice Until Worker Packaging Spike

## Status

Accepted for beta planning.

## Context

The product must be a general-user desktop app for Windows and possibly macOS,
but the hardest risk is not the UI shell. The main risk is packaging a Python ML
runtime, GPU-specific dependencies, model downloads, and a repairable sandbox.

The reference implementation is a PyQt app where UI, model loading, prompts,
generation, batch processing, and sidecar saving live together. The beta target
requires a cleaner split:

- Desktop shell for setup, queue management, previews, settings, and logs.
- Python worker for JoyCaption model loading and inference.
- App-managed sandbox for runtime, dependencies, models, cache, logs, and
  plugin resources.

## Decision

Do not choose Tauri or Electron yet. Build a shell spike that compares both
against the same worker and sandbox contract.

The spike must validate:

- Launching and supervising the Python worker.
- Local IPC request/response and progress streaming.
- Access to the app-managed sandbox.
- Installer/update behavior on Windows.
- macOS Apple Silicon feasibility if dependency validation passes.
- Bundle size and developer workflow complexity.

## Consequences

- UI code should depend on contracts, not direct JoyCaption imports.
- Worker API shape should be stable enough for either shell.
- The first beta can choose the shell after evidence, rather than preference.

## Decision Criteria

Prefer the shell that best satisfies:

- Reliable worker lifecycle management.
- Low-friction Windows packaging.
- Clear sandbox file permissions.
- Reasonable app size.
- Straightforward log export and diagnostics.
- Maintainable build pipeline for a small project.
