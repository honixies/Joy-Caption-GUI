from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxPaths:
    root: Path
    runtime: Path
    models: Path
    cache: Path
    plugins: Path
    jobs: Path
    logs: Path
    backups: Path
    settings: Path


def build_sandbox_paths(root: Path) -> SandboxPaths:
    return SandboxPaths(
        root=root,
        runtime=root / "runtime",
        models=root / "models",
        cache=root / "cache",
        plugins=root / "plugins",
        jobs=root / "jobs",
        logs=root / "logs",
        backups=root / "backups",
        settings=root / "settings.json",
    )


def ensure_sandbox(root: Path) -> SandboxPaths:
    paths = build_sandbox_paths(root)
    for directory in (
        paths.runtime,
        paths.models,
        paths.cache,
        paths.plugins,
        paths.jobs,
        paths.logs,
        paths.backups,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return paths
