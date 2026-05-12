$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".sandbox-prototype\runtime\venv\Scripts\python.exe"
$Port = 8765
$Url = "http://127.0.0.1:$Port/"

if (-not (Test-Path -LiteralPath $VenvPython)) {
  throw "Sandbox Python was not found: $VenvPython"
}

Set-Location $Root

$listener = netstat -ano | Select-String "127\.0\.0\.1:$Port\s+0\.0\.0\.0:0\s+LISTENING" | Select-Object -First 1
if ($listener) {
  $existingPid = ($listener.ToString().Trim() -split "\s+")[-1]
  Write-Host "Existing JoyCaption server detected on port $Port (PID $existingPid). Reusing it."
} else {
  $env:PYTHONPATH = Join-Path $Root "src"
  $env:PYTHONDONTWRITEBYTECODE = "1"
  $env:HF_HOME = Join-Path $Root ".sandbox-prototype\cache\huggingface"
  $env:TRANSFORMERS_CACHE = Join-Path $Root ".sandbox-prototype\cache\huggingface\transformers"

  $server = Start-Process `
    -FilePath $VenvPython `
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
  Write-Host "Started JoyCaption server (PID $($server.Id))."
  Start-Sleep -Seconds 3
}

$edgeCandidates = @(
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
)
$edge = $edgeCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1

if ($edge) {
  Start-Process -FilePath $edge -ArgumentList @("--app=$Url", "--new-window")
} else {
  Start-Process $Url
}

Write-Host "JoyCaption web app opened: $Url"
