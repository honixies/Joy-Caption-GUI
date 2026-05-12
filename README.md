# JoyCaption GUI

Windows desktop GUI for JoyCaption image tagging and caption generation.

The app uses a local WebView shell, a local Python server, and an app-managed
sandbox for the Python runtime, model cache, logs, and generated job metadata.
Generated `.txt` files are saved in the selected image/folder location.

## Windows App

Build the desktop shell:

```powershell
dotnet publish app\webview-shell\JoyCaptionShell.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true -o dist\win-x64-single
```

Run:

```powershell
.\dist\win-x64-single\JoyCaptionShell.exe
```

Opening the app automatically starts the local server. Closing the app stops the
server it started.

## Installer

Build the Windows bootstrap installer:

```powershell
dotnet publish installer\windows\JoyCaptionGUI.Setup.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true -o dist\installer
```

Installer output:

```text
dist\installer\JoyCaptionGUI-Setup.exe
```

The installer downloads this repository, prepares the Python runtime, builds the
desktop shell if needed, and creates Desktop/Start Menu shortcuts.

## Runtime Setup

Prepare the real-model runtime manually:

```powershell
.\scripts\setup_real_runtime.ps1
```

Then run the real-model desktop app:

```powershell
.\dist\win-x64-single\JoyCaptionShell.exe
```

The first real model load can take a long time because it downloads model
weights into `.sandbox-prototype/models`.

## Features

- Runtime health check
- Real JoyCaption model loading status
- Single image generation
- Folder batch generation with optional subfolders
- Sidecar `.txt`, `text_out`, and combined folder `.txt` exports
- Custom prompt preset builder and saved presets
- Compact Korean UI for generation status and work history

## Tests

Static checks:

```powershell
.\.sandbox-prototype\runtime\venv\Scripts\python.exe -m compileall src
node --check app\prototype\app.js
dotnet build app\webview-shell\JoyCaptionShell.csproj -c Release
```

Smoke test with the server running:

```powershell
.\.sandbox-prototype\runtime\venv\Scripts\python.exe .\scripts\smoke_real_model.py
```
