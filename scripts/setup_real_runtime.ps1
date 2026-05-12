$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $Root ".sandbox-prototype\runtime\venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"
$SandboxCache = Join-Path $Root ".sandbox-prototype\cache"
$PipCache = Join-Path $SandboxCache "pip"
$HuggingFaceCache = Join-Path $SandboxCache "huggingface"

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
      $version = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
      if ($LASTEXITCODE -eq 0 -and [version]$version -ge [version]"3.11") {
        return $candidate
      }
    }
  }

  throw "Python 3.11+ was not found. Install Python first or set the PYTHON environment variable."
}

New-Item -ItemType Directory -Path $PipCache -Force | Out-Null
New-Item -ItemType Directory -Path $HuggingFaceCache -Force | Out-Null

if (-not (Test-Path -LiteralPath $Python)) {
  $BasePython = Find-BasePython
  & $BasePython -m venv $VenvDir
}

$resolvedPython = (Resolve-Path -LiteralPath $Python).Path
$resolvedVenv = (Resolve-Path -LiteralPath $VenvDir).Path
if (-not $resolvedPython.StartsWith($resolvedVenv, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Refusing to install packages outside the app-managed virtual environment: $resolvedPython"
}

$venvCheck = & $Python -c "import sys; print('venv' if sys.prefix != sys.base_prefix else 'global')"
if ($venvCheck -ne "venv") {
  throw "Refusing to install packages because Python is not running inside a virtual environment: $Python"
}

$env:PIP_REQUIRE_VIRTUALENV = "true"
$env:PIP_CACHE_DIR = $PipCache
$env:HF_HOME = $HuggingFaceCache
$env:TRANSFORMERS_CACHE = Join-Path $HuggingFaceCache "transformers"

& $Python -m pip --disable-pip-version-check install --upgrade pip
& $Python -m pip --disable-pip-version-check install --force-reinstall `
  --index-url https://download.pytorch.org/whl/cu121 `
  torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121

& $Python -m pip --disable-pip-version-check install --upgrade `
  huggingface_hub transformers sentencepiece `
  peft==0.12.0 accelerate==1.0.0 `
  bitsandbytes pillow

& $Python -m pip --disable-pip-version-check install --upgrade accelerate

Write-Host "Real runtime ready: $Python"
