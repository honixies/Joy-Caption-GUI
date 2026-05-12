$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".sandbox-prototype\runtime\venv\Scripts\python.exe"
$FallbackPython = "C:\Users\honix\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (Test-Path -LiteralPath $VenvPython) {
  $Python = $VenvPython
} else {
  Write-Warning "Sandbox venv not found. Falling back to Codex Python; real model dependencies may be missing."
  $Python = $FallbackPython
}

$env:PYTHONPATH = Join-Path $Root "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:HF_HOME = Join-Path $Root ".sandbox-prototype\cache\huggingface"
$env:TRANSFORMERS_CACHE = Join-Path $Root ".sandbox-prototype\cache\huggingface\transformers"

Set-Location $Root

& $Python -m joycaption_desktop.prototype_server `
  --host 127.0.0.1 `
  --port 8765 `
  --sandbox-root .sandbox-prototype `
  --profile windows-nvidia-4bit `
  --real-model
