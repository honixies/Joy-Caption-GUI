$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $Root ".sandbox-prototype\runtime\venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"

Set-Location $Root

function Find-BasePython {
  $candidates = @()
  if ($env:PYTHON) {
    $candidates += $env:PYTHON
  }
  $commands = @("py", "python")
  foreach ($command in $commands) {
    $cmd = Get-Command $command -ErrorAction SilentlyContinue
    if ($cmd) {
      $candidates += $cmd.Source
    }
  }
  $candidates += "C:\Users\honix\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

  foreach ($candidate in $candidates | Where-Object { $_ } | Select-Object -Unique) {
    if (Test-Path -LiteralPath $candidate) {
      return $candidate
    }
  }

  throw "Python 3.11+ was not found. Install Python first or set the PYTHON environment variable."
}

if (-not (Test-Path -LiteralPath $Python)) {
  $BasePython = Find-BasePython
  & $BasePython -m venv $VenvDir
}

& $Python -m pip install --upgrade pip
& $Python -m pip install --force-reinstall `
  --index-url https://download.pytorch.org/whl/cu121 `
  torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121

& $Python -m pip install --upgrade `
  huggingface_hub transformers sentencepiece `
  peft==0.12.0 accelerate==1.0.0 `
  bitsandbytes pillow

& $Python -m pip install --upgrade accelerate

Write-Host "Real runtime ready: $Python"
