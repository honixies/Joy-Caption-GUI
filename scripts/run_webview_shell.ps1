$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Port = 8765
$Url = "http://127.0.0.1:$Port/"
$Python = Join-Path $Root ".sandbox-prototype\runtime\venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
  throw "Sandbox Python was not found: $Python"
}

Set-Location $Root

$listener = netstat -ano | Select-String "127\.0\.0\.1:$Port\s+0\.0\.0\.0:0\s+LISTENING" | Select-Object -First 1
if (-not $listener) {
  $env:PYTHONPATH = Join-Path $Root "src"
  $env:PYTHONDONTWRITEBYTECODE = "1"
  $env:HF_HOME = Join-Path $Root ".sandbox-prototype\cache\huggingface"
  $env:TRANSFORMERS_CACHE = Join-Path $Root ".sandbox-prototype\cache\huggingface\transformers"

  $server = Start-Process `
    -FilePath $Python `
    -ArgumentList @(
      "-m", "joycaption_desktop.prototype_server",
      "--host", "127.0.0.1",
      "--port", "$Port",
      "--sandbox-root", ".sandbox-prototype",
      "--profile", "windows-nvidia-4bit",
      "--real-model"
    ) `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -PassThru
  $server.Id | Set-Content -LiteralPath (Join-Path $Root ".prototype-server.pid")
  Start-Sleep -Seconds 3
}

dotnet run --project (Join-Path $Root "app\webview-shell\JoyCaptionShell.csproj") -- $Url
