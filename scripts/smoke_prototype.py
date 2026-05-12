from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8765"
SAMPLE_DIR = ROOT / "samples" / "images"
SAMPLE_IMAGE = SAMPLE_DIR / "sample-one.jpg"


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    health = request("GET", "/api/health")
    assert "health" in health

    load = request("POST", "/api/load-model", {})
    assert load["model_loaded"] is True

    single = request(
        "POST",
        "/api/generate",
        {
            "image_path": str(SAMPLE_IMAGE),
            "mode": "tags",
            "preset_id": "tags-dataset",
            "postprocessor_ids": ["normalize-commas", "dedupe-tags"],
            "write_sidecar": True,
        },
    )
    assert single["result"]["status"] == "succeeded"
    assert Path(single["sidecar_path"]).exists()

    batch = request(
        "POST",
        "/api/batch",
        {
            "input_dir": str(SAMPLE_DIR),
            "mode": "tags",
            "preset_id": "tags-dataset",
            "postprocessor_ids": ["normalize-commas", "dedupe-tags"],
            "write_sidecars": True,
        },
    )
    assert batch["total"] >= 2
    assert batch["failed"] == 0
    assert Path(batch["csv_path"]).exists()
    assert Path(batch["json_path"]).exists()

    print("prototype smoke ok")
    print(json.dumps({"single": single, "batch": batch}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
