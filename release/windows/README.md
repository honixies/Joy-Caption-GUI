# Windows Release Files

- `JoyCaptionGUI-Setup-Inno.exe`: Inno Setup based Windows installer. This is the preferred installer.
- `JoyCaptionGUI-Setup.exe`: Legacy bootstrap installer.
- `JoyCaptionGUI-Payload.zip`: Local source payload used by the legacy bootstrap installer when placed beside it.

The Inno installer installs the desktop app, source server files, scripts, sample images, and shortcuts. During installation you can optionally run the Python/ML runtime setup step; otherwise run `scripts\setup_real_runtime.ps1` later from the install folder.
