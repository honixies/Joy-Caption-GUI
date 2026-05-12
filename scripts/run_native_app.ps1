$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONPATH = "src"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:HF_HOME = (Resolve-Path -LiteralPath ".sandbox-prototype").Path + "\cache\huggingface"
$env:TRANSFORMERS_CACHE = $env:HF_HOME + "\transformers"

& ".sandbox-prototype\runtime\venv\Scripts\python.exe" `
  -m joycaption_desktop.native_app `
  --sandbox-root ".sandbox-prototype" `
  --profile "windows-nvidia-4bit" `
  --real-model
