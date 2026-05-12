from __future__ import annotations

import argparse
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from joycaption_desktop.contracts import BatchJob, GenerateRequest, GenerationMode, JobStatus
from joycaption_desktop.postprocessors.builtin import apply_postprocessors
from joycaption_desktop.runtime.profiles import PROFILES, WINDOWS_NVIDIA_4BIT
from joycaption_desktop.runtime.sandbox import ensure_sandbox
from joycaption_desktop.worker.exports import (
    export_successful_sidecars,
    write_results_csv,
    write_results_json,
)
from joycaption_desktop.worker.service import JoyCaptionWorker

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
MODE_OPTIONS = {
    "태그 목록": (GenerationMode.TAGS, "tags-dataset", ("normalize-commas", "dedupe-tags", "strip-tag-period")),
    "짧은 캡션": (GenerationMode.SHORT_CAPTION, "caption-short", ()),
    "긴 설명": (GenerationMode.LONG_DESCRIPTION, "description-long", ()),
}


class NativeJoyCaptionApp:
    def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
        self.root = root
        self.root.title("JoyCaption Desktop")
        self.root.geometry("1180x760")
        self.root.minsize(980, 640)

        self.sandbox = ensure_sandbox(Path(args.sandbox_root).resolve())
        self.worker = JoyCaptionWorker(
            PROFILES[args.profile],
            self.sandbox.models,
            use_real_model=args.real_model,
        )
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.target_path: Path | None = None
        self.target_kind = "image"
        self.preview_photo: ImageTk.PhotoImage | None = None

        self.mode_var = tk.StringVar(value="태그 목록")
        self.target_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="모델을 먼저 로드하세요.")
        self.progress_var = tk.DoubleVar(value=0)
        self.write_sidecar_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._poll_events()
        self._set_model_state("대기 중", 0, "모델이 아직 로드되지 않았습니다.")

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(18, 14, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="JoyCaption Desktop", font=("Malgun Gothic", 22, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, text="원본 파일 또는 폴더 경로에서 이미지 태그와 캡션을 생성합니다.").grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )
        ttk.Button(header, text="모델 로드", command=self.load_model).grid(row=0, column=1, rowspan=2, padx=(10, 0))

        body = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=10)

        left = ttk.Frame(body, padding=12)
        right = ttk.Frame(body, padding=12)
        body.add(left, weight=3)
        body.add(right, weight=2)

        left.columnconfigure(0, weight=1)
        left.rowconfigure(4, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        target = ttk.LabelFrame(left, text="작업 대상", padding=12)
        target.grid(row=0, column=0, sticky="ew")
        target.columnconfigure(0, weight=1)
        ttk.Entry(target, textvariable=self.target_var).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        ttk.Button(target, text="파일 열기", command=self.open_file).grid(row=1, column=0, sticky="w")
        ttk.Button(target, text="폴더 열기", command=self.open_folder).grid(row=1, column=0, padx=(96, 0), sticky="w")
        ttk.Button(target, text="드래그로 지정", command=self.open_drop_window).grid(
            row=1, column=0, padx=(196, 0), sticky="w"
        )
        ttk.Button(target, text="경로 적용", command=self.apply_typed_path).grid(row=1, column=1, padx=(12, 0), sticky="w")

        options = ttk.LabelFrame(left, text="프리셋", padding=12)
        options.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="생성 방식").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            options,
            textvariable=self.mode_var,
            values=list(MODE_OPTIONS),
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Checkbutton(options, text="이미지 옆에 .txt 저장", variable=self.write_sidecar_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

        actions = ttk.Frame(left)
        actions.grid(row=2, column=0, sticky="ew", pady=12)
        ttk.Button(actions, text="생성하기", command=self.generate).pack(side=tk.LEFT)
        ttk.Button(actions, text="결과 지우기", command=self.clear_result).pack(side=tk.LEFT, padx=(8, 0))

        progress_box = ttk.LabelFrame(left, text="작업 상황", padding=12)
        progress_box.grid(row=3, column=0, sticky="ew")
        progress_box.columnconfigure(0, weight=1)
        ttk.Label(progress_box, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Progressbar(progress_box, variable=self.progress_var, maximum=100).grid(
            row=1, column=0, sticky="ew", pady=(8, 0)
        )

        result_box = ttk.LabelFrame(left, text="생성 결과", padding=12)
        result_box.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
        result_box.rowconfigure(0, weight=1)
        result_box.columnconfigure(0, weight=1)
        self.result_text = tk.Text(result_box, wrap="word", height=12)
        self.result_text.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(result_box, orient="vertical", command=self.result_text.yview).grid(row=0, column=1, sticky="ns")
        self.result_text.configure(yscrollcommand=lambda *args: None)

        preview_box = ttk.LabelFrame(right, text="현재 이미지", padding=12)
        preview_box.grid(row=0, column=0, sticky="nsew")
        preview_box.columnconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview_box, text="이미지를 선택하면 여기에 표시됩니다.", anchor="center")
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        log_box = ttk.LabelFrame(right, text="작업 기록", padding=12)
        log_box.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        log_box.rowconfigure(0, weight=1)
        log_box.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_box, wrap="word", height=10)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(log_box, orient="vertical", command=self.log_text.yview).grid(row=0, column=1, sticky="ns")

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="이미지 파일 열기",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.bmp"), ("All files", "*.*")],
        )
        if path:
            self.set_target(Path(path), "image")

    def open_folder(self) -> None:
        path = filedialog.askdirectory(title="이미지 폴더 열기")
        if path:
            self.set_target(Path(path), "folder")

    def open_drop_window(self) -> None:
        if os.name != "nt":
            messagebox.showinfo("드래그 지정", "현재 최소 앱에서는 Windows 드롭 창만 지원합니다. 파일 열기 또는 폴더 열기를 사용하세요.")
            return
        try:
            path = self._run_windows_drop_window()
        except Exception as exc:
            messagebox.showerror("드래그 지정 실패", str(exc))
            return
        if path:
            selected = Path(path)
            self.set_target(selected, "folder" if selected.is_dir() else "image")

    def _run_windows_drop_window(self) -> str | None:
        script = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$selectedPath = $null
$form = New-Object System.Windows.Forms.Form
$form.Text = 'JoyCaption 드래그 경로 지정'
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
        return completed.stdout.strip() or None

    def apply_typed_path(self) -> None:
        raw = self.target_var.get().strip().strip('"')
        if not raw:
            return
        path = Path(raw)
        kind = "folder" if path.is_dir() else "image"
        self.set_target(path, kind)

    def set_target(self, path: Path, kind: str) -> None:
        self.target_path = path.expanduser().resolve()
        self.target_kind = kind
        self.target_var.set(str(self.target_path))
        self.log(f"선택: {self.target_path}")
        preview_path = self._first_image(self.target_path) if kind == "folder" else self.target_path
        if preview_path:
            self.show_preview(preview_path)

    def show_preview(self, path: Path) -> None:
        try:
            image = Image.open(path)
            image.thumbnail((420, 320), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self.preview_photo, text="")
        except Exception as exc:
            self.preview_label.configure(image="", text=f"미리보기 실패: {exc}")

    def load_model(self) -> None:
        if self.worker.model_loaded:
            self._set_model_state("로드 완료", 100, "모델이 이미 로드되었습니다.")
            return
        self._set_model_state("로드 중", 10, "모델을 GPU 메모리에 로드하는 중입니다.")
        threading.Thread(target=self._load_model_worker, daemon=True).start()

    def _load_model_worker(self) -> None:
        started = time.time()
        try:
            self.worker.load_model()
            self.events.put(("model_loaded", time.time() - started))
        except Exception as exc:
            self.events.put(("error", f"모델 로드 실패: {exc}"))

    def generate(self) -> None:
        if not self.target_path:
            messagebox.showwarning("작업 대상 없음", "파일 또는 폴더를 먼저 선택하세요.")
            return
        if not self.worker.model_loaded:
            messagebox.showwarning("모델 필요", "모델을 먼저 로드하세요.")
            return
        self.result_text.delete("1.0", tk.END)
        self._set_model_state("생성 중", 5, "이미지 생성 작업을 시작했습니다.")
        threading.Thread(target=self._generate_worker, daemon=True).start()

    def _generate_worker(self) -> None:
        try:
            if self.target_kind == "folder":
                self._run_batch(self.target_path)
            else:
                self._run_single(self.target_path)
        except Exception as exc:
            self.events.put(("error", f"생성 실패: {exc}"))

    def _run_single(self, image_path: Path) -> None:
        result = self.worker.generate(self._request(image_path))
        sidecar = None
        if self.write_sidecar_var.get() and result.status == JobStatus.SUCCEEDED:
            sidecar = export_successful_sidecars([result])[0]
        self.events.put(("single_done", (result, sidecar)))

    def _run_batch(self, folder: Path) -> None:
        mode, preset_id, postprocessors = MODE_OPTIONS[self.mode_var.get()]
        job_id = f"job-{int(time.time())}"
        job_dir = self.sandbox.jobs / job_id
        job = BatchJob(
            id=job_id,
            input_dir=folder,
            output_dir=job_dir,
            mode=mode,
            preset_id=preset_id,
            postprocessor_ids=postprocessors,
        )
        requests = self.worker.iter_batch_requests(job)
        results = []
        total = len(requests)
        for index, request in enumerate(requests, start=1):
            self.events.put(("progress", (index - 1, total, request.image_path)))
            results.append(self.worker.generate(request))
        if self.write_sidecar_var.get():
            export_successful_sidecars(results)
        csv_path = job_dir / "results.csv"
        json_path = job_dir / "results.json"
        write_results_csv(results, csv_path)
        write_results_json(results, json_path)
        self.events.put(("batch_done", (results, csv_path, json_path)))

    def _request(self, image_path: Path) -> GenerateRequest:
        mode, preset_id, postprocessors = MODE_OPTIONS[self.mode_var.get()]
        return GenerateRequest(
            image_path=image_path,
            mode=mode,
            preset_id=preset_id,
            postprocessor_ids=postprocessors,
        )

    def _poll_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "model_loaded":
                self._set_model_state("로드 완료", 100, f"모델 로드 완료 · {payload:.1f}초")
                self.log(f"모델 로드 완료: {payload:.1f}초")
            elif event == "progress":
                index, total, path = payload
                percent = int((index / max(total, 1)) * 100)
                self._set_model_state("생성 중", percent, f"{index + 1}/{total} 처리 중: {path.name}")
                self.show_preview(path)
            elif event == "single_done":
                result, sidecar = payload
                self._set_model_state("완료", 100, "한 장 생성이 완료되었습니다.")
                self._render_result(result.postprocessed_text or result.error or "")
                self.log(f"완료: {result.image_path}")
                if sidecar:
                    self.log(f"저장: {sidecar}")
            elif event == "batch_done":
                results, csv_path, json_path = payload
                succeeded = sum(1 for result in results if result.status == JobStatus.SUCCEEDED)
                self._set_model_state("완료", 100, f"배치 완료: {succeeded}/{len(results)} 성공")
                self._render_result("\n\n".join(result.postprocessed_text or result.error or "" for result in results))
                self.log(f"CSV: {csv_path}")
                self.log(f"JSON: {json_path}")
            elif event == "error":
                self._set_model_state("오류", 0, payload)
                self.log(payload)
                messagebox.showerror("오류", payload)
        self.root.after(150, self._poll_events)

    def _set_model_state(self, title: str, progress: int, message: str) -> None:
        self.progress_var.set(progress)
        self.status_var.set(f"{title} · {message}")

    def _render_result(self, text: str) -> None:
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)

    def clear_result(self) -> None:
        self.result_text.delete("1.0", tk.END)

    def log(self, message: str) -> None:
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')}  {message}\n")
        self.log_text.see(tk.END)

    def _first_image(self, folder: Path) -> Path | None:
        if not folder.exists() or not folder.is_dir():
            return None
        return next((path for path in sorted(folder.iterdir()) if path.suffix.lower() in IMAGE_EXTENSIONS), None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JoyCaption native desktop app")
    parser.add_argument("--sandbox-root", default=".sandbox-prototype")
    parser.add_argument("--profile", default=WINDOWS_NVIDIA_4BIT)
    parser.add_argument("--real-model", action="store_true")
    return parser.parse_args()


def main() -> None:
    if os.name == "nt":
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    args = parse_args()
    root = tk.Tk()
    NativeJoyCaptionApp(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()
