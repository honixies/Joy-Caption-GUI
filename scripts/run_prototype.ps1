$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\honix\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$env:PYTHONPATH = Join-Path $Root "src"
$env:PYTHONDONTWRITEBYTECODE = "1"

Set-Location $Root

& $Python -m joycaption_desktop.prototype_server `
  --host 127.0.0.1 `
  --port 8765 `
  --sandbox-root .sandbox-prototype
