from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from joycaption_desktop.runtime.profiles import PROFILES, WINDOWS_NVIDIA_4BIT
from joycaption_desktop.worker.protocol import json_ready, request_from_payload
from joycaption_desktop.worker.service import JoyCaptionWorker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JoyCaption Desktop worker JSONL process.")
    parser.add_argument(
        "--profile",
        default=WINDOWS_NVIDIA_4BIT.id,
        choices=sorted(PROFILES),
        help="Runtime profile id.",
    )
    parser.add_argument(
        "--model-cache-dir",
        required=True,
        help="App-managed model cache directory.",
    )
    parser.add_argument(
        "--real-model",
        action="store_true",
        help="Load the real JoyCaption model instead of placeholder inference.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    worker = JoyCaptionWorker(
        PROFILES[args.profile],
        Path(args.model_cache_dir),
        use_real_model=args.real_model,
    )

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = handle_command(worker, line)
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        if response.get("exit"):
            break
    return 0


def handle_command(worker: JoyCaptionWorker, raw_line: str) -> dict[str, Any]:
    try:
        message = json.loads(raw_line)
        command = message.get("command")
        if command == "health":
            return ok("health", worker.health())
        if command == "load_model":
            worker.load_model()
            return ok("load_model", {"model_loaded": worker.model_loaded})
        if command == "generate":
            request = request_from_payload(message["request"])
            return ok("generate", worker.generate(request))
        if command == "shutdown":
            return {"ok": True, "command": "shutdown", "exit": True}
        return error(command or "unknown", f"Unknown command: {command}")
    except Exception as exc:
        return error("error", str(exc))


def ok(command: str, payload: Any) -> dict[str, Any]:
    return {"ok": True, "command": command, "payload": json_ready(payload)}


def error(command: str, message: str) -> dict[str, Any]:
    return {"ok": False, "command": command, "error": message}


if __name__ == "__main__":
    raise SystemExit(main())
