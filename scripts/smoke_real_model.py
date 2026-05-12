from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8765"
SAMPLE_IMAGE = ROOT / "samples" / "images" / "sample-one.jpg"


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
    with urllib.request.urlopen(req, timeout=900) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    config = request("GET", "/api/config")
    assert config["real_model"] is True, "server must be started with --real-model"

    health = request("GET", "/api/health")["health"]
    assert health["ok"] is True, health
    assert health["backend"] == "cuda", health

    load = request("POST", "/api/load-model", {})
    assert load["model_loaded"] is True

    result = request(
        "POST",
        "/api/generate",
        {
            "image_path": str(SAMPLE_IMAGE),
            "mode": "tags",
            "preset_id": "tags-dataset",
            "postprocessor_ids": ["normalize-commas", "dedupe-tags", "strip-tag-period"],
            "write_sidecar": True,
            "extra_options": {"max_new_tokens": 96, "temperature": 0.2, "top_p": 0.9},
        },
    )
    assert result["result"]["status"] == "succeeded", result
    assert "테스트 추론 결과" not in result["result"]["postprocessed_text"]
    assert Path(result["sidecar_path"]).exists()
    print("real model smoke ok")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
