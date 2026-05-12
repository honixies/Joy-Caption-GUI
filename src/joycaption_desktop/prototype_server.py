from __future__ import annotations

import argparse
import cgi
import io
import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, is_dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from joycaption_desktop.contracts import (
    BatchJob,
    GenerateRequest,
    GenerateResult,
    GenerationMode,
    JobStatus,
)
from joycaption_desktop.runtime.profiles import PROFILES, WINDOWS_NVIDIA_4BIT
from joycaption_desktop.runtime.sandbox import ensure_sandbox
from joycaption_desktop.worker.exports import (
    export_successful_sidecars,
    write_results_csv,
    write_results_json,
)
from joycaption_desktop.worker.protocol import json_ready
from joycaption_desktop.worker.service import JoyCaptionWorker

APP_DIR = Path(__file__).resolve().parents[2] / "app" / "prototype"
DEFAULT_SANDBOX = Path(__file__).resolve().parents[2] / ".sandbox-prototype"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
PREVIEW_SIZE = (720, 520)


class PrototypeState:
    def __init__(self, sandbox_root: Path, profile_id: str, use_real_model: bool) -> None:
        self.sandbox = ensure_sandbox(sandbox_root)
        self.worker = JoyCaptionWorker(
            PROFILES[profile_id],
            self.sandbox.models,
            use_real_model=use_real_model,
        )
        self.load_lock = threading.Lock()
        self.load_status: dict[str, Any] = {
            "state": "ready" if self.worker.model_loaded else "idle",
            "message": "모델이 아직 로드되지 않았습니다.",
            "started_at": None,
            "finished_at": None,
            "error": None,
        }
        self.current_image_lock = threading.Lock()
        self.static_file_cache: dict[Path, tuple[tuple[int, int], bytes, str]] = {}
        self.preview_cache: dict[tuple[str, int, int], tuple[bytes, str]] = {}
        self.cancel_event = threading.Event()
        self.current_image: dict[str, Any] = {
            "path": None,
            "label": "선택된 이미지 없음",
            "kind": "image",
            "index": 0,
            "total": 0,
            "state": "idle",
            "updated_at": None,
        }

    def start_model_load(self) -> dict[str, Any]:
        with self.load_lock:
            if self.worker.model_loaded:
                started_at = self.load_status.get("started_at") or time.time()
                self.load_status = {
                    "state": "ready",
                    "message": "모델이 이미 로드되어 있습니다.",
                    "started_at": started_at,
                    "finished_at": self.load_status.get("finished_at") or started_at,
                    "error": None,
                }
                return self.load_status
                self.load_status = {
                    "state": "ready",
                    "message": "모델이 이미 로드되어 있습니다.",
                    "started_at": self.load_status.get("started_at"),
                    "finished_at": time.time(),
                    "error": None,
                }
                return self.load_status
            if self.load_status.get("state") == "loading":
                return self.load_status
            self.load_status = {
                "state": "loading",
                "message": "모델 파일을 확인하고 GPU 메모리에 로드하는 중입니다.",
                "started_at": time.time(),
                "finished_at": None,
                "error": None,
            }
            thread = threading.Thread(target=self._load_model_background, daemon=True)
            thread.start()
            return self.load_status

    def _load_model_background(self) -> None:
        try:
            self.worker.load_model()
        except Exception as exc:
            with self.load_lock:
                self.load_status = {
                    **self.load_status,
                    "state": "error",
                    "message": "모델 로드에 실패했습니다.",
                    "finished_at": time.time(),
                    "error": str(exc),
                }
            return
        with self.load_lock:
            self.load_status = {
                **self.load_status,
                "state": "ready",
                "message": "모델 로드가 완료되었습니다.",
                "finished_at": time.time(),
                "error": None,
            }

    def get_load_status(self) -> dict[str, Any]:
        with self.load_lock:
            status = dict(self.load_status)
        started_at = status.get("started_at")
        finished_at = status.get("finished_at")
        now = finished_at or time.time()
        status["elapsed_seconds"] = round(now - started_at, 1) if started_at else 0
        status["model_loaded"] = self.worker.model_loaded
        return status

    def set_current_image(
        self,
        path: Path | None,
        label: str | None = None,
        kind: str = "image",
        index: int = 0,
        total: int = 0,
        state: str = "running",
    ) -> None:
        with self.current_image_lock:
            self.current_image = {
                "path": str(path.resolve()) if path else None,
                "label": label or (path.name if path else "선택된 이미지 없음"),
                "kind": kind,
                "index": index,
                "total": total,
                "state": state,
                "updated_at": time.time(),
            }

    def get_current_image(self) -> dict[str, Any]:
        with self.current_image_lock:
            return dict(self.current_image)

    def clear_cancel(self) -> None:
        self.cancel_event.clear()

    def request_cancel(self) -> dict[str, Any]:
        self.cancel_event.set()
        with self.current_image_lock:
            self.current_image = {
                **self.current_image,
                "state": "cancelled",
                "updated_at": time.time(),
            }
        return {"cancelled": True}

    def cancel_requested(self) -> bool:
        return self.cancel_event.is_set()


class PrototypeHandler(BaseHTTPRequestHandler):
    state: PrototypeState

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_file(APP_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/static/"):
            rel = parsed.path.removeprefix("/static/")
            self._send_file(APP_DIR / rel)
            return
        if parsed.path == "/api/health":
            self._json({"health": json_ready(self.state.worker.health())})
            return
        if parsed.path == "/api/load-status":
            self._json(self.state.get_load_status())
            return
        if parsed.path == "/api/current-image":
            self._json(self.state.get_current_image())
            return
        if parsed.path == "/api/preview-image":
            image_path = Path(parse_qs(parsed.query).get("path", [""])[0]).expanduser()
            self._send_preview(image_path)
            return
        if parsed.path == "/api/folder-preview-image":
            folder_path = Path(parse_qs(parsed.query).get("path", [""])[0]).expanduser()
            self._send_folder_preview(folder_path)
            return
        if parsed.path == "/api/folder-images":
            folder_path = Path(parse_qs(parsed.query).get("path", [""])[0]).expanduser()
            include_subfolders = parse_qs(parsed.query).get("recursive", ["false"])[0].lower() == "true"
            self._json(json_ready(self._folder_images(folder_path, include_subfolders=include_subfolders)))
            return
        if parsed.path == "/api/config":
            self._json(
                {
                    "sample_image": str((Path.cwd() / "samples" / "images" / "sample-one.jpg").resolve()),
                    "sample_folder": str((Path.cwd() / "samples" / "images").resolve()),
                    "sandbox_root": str(self.state.sandbox.root),
                    "real_model": self.state.worker.use_real_model,
                    "profile": self.state.worker.profile.id,
                }
            )
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/upload":
                self._json(self._upload_files())
                return
            payload = self._read_json()
            if parsed.path == "/api/load-model":
                self.state.start_model_load()
                while self.state.get_load_status()["state"] == "loading":
                    time.sleep(0.25)
                status = self.state.get_load_status()
                if status["state"] == "error":
                    raise RuntimeError(status["error"])
                self._json({"model_loaded": self.state.worker.model_loaded})
                return
            if parsed.path == "/api/start-load-model":
                self._json(self.state.start_model_load())
                return
            if parsed.path == "/api/cancel-job":
                self._json(self.state.request_cancel())
                return
            if parsed.path == "/api/pick-file":
                self._json(self._pick_file())
                return
            if parsed.path == "/api/pick-folder":
                self._json(self._pick_folder())
                return
            if parsed.path == "/api/drop-path":
                self._json(self._drop_path())
                return
            if parsed.path == "/api/open-path":
                self._json(self._open_path(payload))
                return
            if parsed.path == "/api/generate":
                self._json(json_ready(self._generate(payload)))
                return
            if parsed.path == "/api/batch":
                self._json(json_ready(self._batch(payload)))
                return
        except PermissionError as exc:
            self._json(
                {"error": f"선택한 폴더에 txt 파일을 저장할 권한이 없습니다: {exc}"},
                status=400,
            )
            return
        except Exception as exc:
            self._json({"error": str(exc)}, status=400)
            return
        self._json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[prototype] {self.address_string()} - {format % args}")

    def _generate(self, payload: dict[str, Any]):
        image_path = Path(payload["image_path"]).expanduser()
        if not self.state.worker.use_real_model and not payload.get("allow_test_output"):
            raise RuntimeError("테스트 모드에서는 실제 이미지 설명을 생성하거나 저장할 수 없습니다. 실제 모델 런타임을 준비한 뒤 앱으로 실행하세요.")
        self.state.clear_cancel()
        self.state.set_current_image(image_path, image_path.name, "image", 0, 1, "running")
        request = GenerateRequest(
            image_path=image_path,
            mode=GenerationMode(payload["mode"]),
            preset_id=payload["preset_id"],
            postprocessor_ids=tuple(payload.get("postprocessor_ids", ())),
            max_words=payload.get("max_words"),
            extra_options=dict(payload.get("extra_options", {})),
        )
        result = self.state.worker.generate(request)
        if self.state.cancel_requested():
            result = self._cancelled_result(request)
        self.state.set_current_image(image_path, image_path.name, "image", 1, 1, result.status.value)
        sidecar = None
        save_warning = None
        if payload.get("write_sidecar") and result.status == JobStatus.SUCCEEDED:
            sidecar = export_successful_sidecars(
                [result],
                mode=payload.get("sidecar_mode", "beside"),
                source_dir=image_path.parent,
                combined_include_filenames=payload.get("combined_include_filenames", True),
            )[0]
            save_warning = self._save_warning([sidecar], image_path.parent)
        return {"result": result, "sidecar_path": sidecar, "save_warning": save_warning}

    def _batch(self, payload: dict[str, Any]) -> dict[str, Any]:
        input_dir = Path(payload["input_dir"]).expanduser()
        if not self.state.worker.use_real_model and not payload.get("allow_test_output"):
            raise RuntimeError("테스트 모드에서는 실제 이미지 설명을 생성하거나 저장할 수 없습니다. 실제 모델 런타임을 준비한 뒤 앱으로 실행하세요.")
        if not input_dir.exists():
            raise FileNotFoundError(f"Input folder not found: {input_dir}")
        self.state.clear_cancel()
        job_id = f"job-{uuid.uuid4().hex[:10]}"
        job_dir = self.state.sandbox.jobs / job_id
        job = BatchJob(
            id=job_id,
            input_dir=input_dir,
            output_dir=job_dir,
            mode=GenerationMode(payload["mode"]),
            preset_id=payload["preset_id"],
            postprocessor_ids=tuple(payload.get("postprocessor_ids", ())),
            extra_options=dict(payload.get("extra_options", {})),
            include_subfolders=bool(payload.get("include_subfolders", False)),
        )
        requests = self.state.worker.iter_batch_requests(job)
        results = []
        total = len(requests)
        for index, request in enumerate(requests, start=1):
            if self.state.cancel_requested():
                results.extend(self._cancelled_result(pending) for pending in requests[index - 1 :])
                break
            self.state.set_current_image(
                request.image_path,
                f"{index}/{total} {request.image_path.name}",
                "batch",
                index,
                total,
                "running",
            )
            results.append(self.state.worker.generate(request))
            if self.state.cancel_requested():
                if index < total:
                    results.extend(self._cancelled_result(pending) for pending in requests[index:])
                break
        if requests:
            last_request = requests[-1]
            final_state = "cancelled" if self.state.cancel_requested() else "succeeded"
            self.state.set_current_image(
                last_request.image_path,
                f"{total}/{total} {last_request.image_path.name}",
                "batch",
                total,
                total,
                final_state,
            )
        sidecars = (
            export_successful_sidecars(
                results,
                mode=payload.get("sidecar_mode", "beside"),
                source_dir=input_dir,
                combined_include_filenames=payload.get("combined_include_filenames", True),
            )
            if payload.get("write_sidecars", True)
            else []
        )
        save_warning = self._save_warning(sidecars, input_dir)
        csv_path = job_dir / "results.csv"
        json_path = job_dir / "results.json"
        write_results_csv(results, csv_path)
        write_results_json(results, json_path)
        return {
            "job_id": job_id,
            "total": len(results),
            "succeeded": sum(1 for result in results if result.status == JobStatus.SUCCEEDED),
            "failed": sum(1 for result in results if result.status == JobStatus.FAILED),
            "cancelled": sum(1 for result in results if result.status == JobStatus.CANCELLED),
            "sidecar_paths": sidecars,
            "save_warning": save_warning,
            "csv_path": csv_path,
            "json_path": json_path,
            "results": results,
        }

    def _cancelled_result(self, request: GenerateRequest) -> GenerateResult:
        return GenerateResult(
            image_path=request.image_path,
            mode=request.mode,
            preset_id=request.preset_id,
            text="",
            postprocessed_text="",
            status=JobStatus.CANCELLED,
            error="사용자가 작업을 중지했습니다.",
            metadata={"profile": self.state.worker.profile.id},
        )

    def _save_warning(self, paths: list[Path], intended_dir: Path) -> str | None:
        if not paths:
            return None
        intended = intended_dir.resolve()
        for path in paths:
            try:
                path.resolve().relative_to(intended)
            except ValueError:
                return (
                    "요청한 위치와 다른 곳에 저장되었습니다. "
                    "저장 위치를 확인하세요."
                )
        return None

    def _folder_images(self, folder_path: Path, include_subfolders: bool = False) -> dict[str, Any]:
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Not a folder: {folder_path}")
        paths = folder_path.rglob("*") if include_subfolders else folder_path.iterdir()
        images = [
            {
                "name": path.name,
                "relative_path": str(path.relative_to(folder_path)),
                "path": str(path.resolve()),
            }
            for path in sorted(paths)
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ]
        return {
            "folder": str(folder_path.resolve()),
            "count": len(images),
            "include_subfolders": include_subfolders,
            "images": images,
        }

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _open_path(self, payload: dict[str, Any]) -> dict[str, Any]:
        target = Path(payload["path"]).expanduser()
        if target.is_file():
            target = target.parent
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {target}")
        if sys.platform.startswith("win"):
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return {"opened": str(target.resolve())}

    def _upload_files(self) -> dict[str, Any]:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        kind = form.getfirst("kind", "image")
        fields = form["files"] if "files" in form else []
        if not isinstance(fields, list):
            fields = [fields]

        upload_dir = self.state.sandbox.root / "uploads" / f"upload-{uuid.uuid4().hex[:10]}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: list[Path] = []
        for index, field in enumerate(fields, start=1):
            filename = Path(field.filename or f"image-{index}.png").name
            suffix = Path(filename).suffix.lower()
            if suffix not in IMAGE_EXTENSIONS:
                continue
            target = upload_dir / filename
            if target.exists():
                target = upload_dir / f"{target.stem}-{index}{target.suffix}"
            data = field.file.read()
            target.write_bytes(data)
            saved_paths.append(target)

        if not saved_paths:
            raise ValueError("업로드된 이미지 파일이 없습니다.")
        if kind == "folder" or len(saved_paths) > 1:
            return {"kind": "folder", "path": str(upload_dir.resolve()), "count": len(saved_paths)}
        return {"kind": "image", "path": str(saved_paths[0].resolve()), "count": 1}

    def _pick_file(self) -> dict[str, Any]:
        if sys.platform.startswith("win"):
            return self._run_windows_picker("file")
        script = """
import json
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
path = filedialog.askopenfilename(
    title="이미지 파일 열기",
    filetypes=[
        ("Image files", "*.jpg *.jpeg *.png *.webp *.bmp"),
    ],
)
root.destroy()
print(json.dumps({"path": path or None}, ensure_ascii=False))
"""
        return self._run_picker_script(script)

    def _pick_folder(self) -> dict[str, Any]:
        if sys.platform.startswith("win"):
            return self._run_windows_picker("folder")
        script = """
import json
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
path = filedialog.askdirectory(title="이미지 폴더 열기")
root.destroy()
print(json.dumps({"path": path or None}, ensure_ascii=False))
"""
        return self._run_picker_script(script)

    def _drop_path(self) -> dict[str, Any]:
        if not sys.platform.startswith("win"):
            raise RuntimeError("Native drag path selection is currently available on Windows only.")
        script = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$selectedPath = $null
$form = New-Object System.Windows.Forms.Form
$form.Text = '파일 또는 폴더를 여기에 드래그'
$form.Width = 560
$form.Height = 260
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true
$form.AllowDrop = $true

$label = New-Object System.Windows.Forms.Label
$label.Text = "원본 경로에서 작업할 이미지 파일이나 폴더를`r`n이 창 안으로 드래그하세요."
$label.Dock = 'Fill'
$label.TextAlign = 'MiddleCenter'
$label.Font = New-Object System.Drawing.Font('Malgun Gothic', 13)
$form.Controls.Add($label)

$button = New-Object System.Windows.Forms.Button
$button.Text = '취소'
$button.Width = 88
$button.Height = 34
$button.Left = 452
$button.Top = 182
$button.Anchor = 'Right,Bottom'
$button.Add_Click({ $form.Close() })
$form.Controls.Add($button)

$form.Add_DragEnter({
  if ($_.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
    $_.Effect = [System.Windows.Forms.DragDropEffects]::Copy
  } else {
    $_.Effect = [System.Windows.Forms.DragDropEffects]::None
  }
})

$form.Add_DragDrop({
  $paths = [string[]]$_.Data.GetData([System.Windows.Forms.DataFormats]::FileDrop)
  if ($paths.Length -gt 0) {
    $script:selectedPath = $paths[0]
    $form.Close()
  }
})

[void]$form.ShowDialog()
if ($selectedPath) {
  [Console]::WriteLine($selectedPath)
}
$form.Dispose()
"""
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        path = completed.stdout.strip()
        if not path:
            return {"path": None, "kind": None}
        selected = Path(path)
        kind = "folder" if selected.is_dir() else "image"
        if kind == "image" and selected.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError("Selected file is not a supported image.")
        return {"path": str(selected.resolve()), "kind": kind}

    def _run_picker_script(self, script: str) -> dict[str, Any]:
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return json.loads(completed.stdout or '{"path": null}')

    def _run_windows_picker(self, picker_type: str) -> dict[str, Any]:
        if picker_type == "file":
            dialog_script = r"""
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = '이미지 파일 열기'
$dialog.Filter = '이미지 파일 (*.jpg;*.jpeg;*.png;*.webp;*.bmp)|*.jpg;*.jpeg;*.png;*.webp;*.bmp'
$dialog.CheckFileExists = $true
$dialog.CheckPathExists = $true
$dialog.FilterIndex = 1
$dialog.Title = 'JoyCaption 파일 열기'
$dialog.RestoreDirectory = $true
$dialog.Multiselect = $false
"""
        else:
            dialog_script = r"""
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = '이미지 폴더 열기'
$dialog.ShowNewFolderButton = $false
$dialog.Description = 'JoyCaption 폴더 열기'
"""
        script = f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
{dialog_script}
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
  if ($dialog.PSObject.Properties.Name -contains 'FileName') {{
    [Console]::WriteLine($dialog.FileName)
  }} else {{
    [Console]::WriteLine($dialog.SelectedPath)
  }}
}}
"""
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        path = completed.stdout.strip()
        return {"path": path or None}

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(json_ready(payload), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self._json({"error": "not found"}, status=404)
            return
        stat = path.stat()
        cache_key = (stat.st_mtime_ns, stat.st_size)
        cached = self.state.static_file_cache.get(path)
        if cached and cached[0] == cache_key:
            _, body, guessed = cached
        else:
            body = path.read_bytes()
            guessed = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self.state.static_file_cache[path] = (cache_key, body, guessed)
        self.send_response(200)
        self.send_header("Content-Type", guessed)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_folder_preview(self, folder_path: Path) -> None:
        if not folder_path.exists() or not folder_path.is_dir():
            self._json({"error": "folder not found"}, status=404)
            return
        image_path = next(
            (
                path
                for path in sorted(folder_path.iterdir())
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ),
            None,
        )
        if image_path is None:
            self._json({"error": "image not found"}, status=404)
            return
        self._send_preview(image_path)

    def _send_preview(self, image_path: Path) -> None:
        if not image_path.exists() or not image_path.is_file():
            self._json({"error": "image not found"}, status=404)
            return
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            self._json({"error": "unsupported image"}, status=400)
            return
        stat = image_path.stat()
        cache_key = (str(image_path.resolve()), stat.st_mtime_ns, stat.st_size)
        cached = self.state.preview_cache.get(cache_key)
        if cached:
            body, content_type = cached
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        try:
            from PIL import Image

            with Image.open(image_path) as image:
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGB")
                scale = min(PREVIEW_SIZE[0] / image.width, PREVIEW_SIZE[1] / image.height)
                resized_size = (
                    max(1, round(image.width * scale)),
                    max(1, round(image.height * scale)),
                )
                image = image.resize(resized_size)
                canvas = Image.new("RGB", PREVIEW_SIZE, (255, 255, 255))
                if image.mode == "RGBA":
                    background = Image.new("RGBA", PREVIEW_SIZE, (255, 255, 255, 255))
                    offset = (
                        (PREVIEW_SIZE[0] - image.width) // 2,
                        (PREVIEW_SIZE[1] - image.height) // 2,
                    )
                    background.alpha_composite(image, offset)
                    canvas = background.convert("RGB")
                else:
                    offset = (
                        (PREVIEW_SIZE[0] - image.width) // 2,
                        (PREVIEW_SIZE[1] - image.height) // 2,
                    )
                    canvas.paste(image, offset)
                buffer = io.BytesIO()
                canvas.save(buffer, format="PNG")
                body = buffer.getvalue()
                content_type = "image/png"
        except Exception:
            body = image_path.read_bytes()
            content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        if len(self.state.preview_cache) > 64:
            self.state.preview_cache.clear()
        self.state.preview_cache[cache_key] = (body, content_type)

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the JoyCaption Desktop local prototype.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--sandbox-root", default=str(DEFAULT_SANDBOX))
    parser.add_argument("--profile", default=WINDOWS_NVIDIA_4BIT.id, choices=sorted(PROFILES))
    parser.add_argument("--real-model", action="store_true")
    args = parser.parse_args(argv)

    PrototypeHandler.state = PrototypeState(
        Path(args.sandbox_root),
        args.profile,
        use_real_model=args.real_model,
    )
    server = ThreadingHTTPServer((args.host, args.port), PrototypeHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"JoyCaption Desktop prototype running at {url}")
    print(f"Sandbox: {PrototypeHandler.state.sandbox.root}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
