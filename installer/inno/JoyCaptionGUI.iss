#define MyAppName "JoyCaption GUI"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "honixies"
#define MyAppExeName "JoyCaptionShell.exe"
#define MyAppId "{{6B3989F9-8E63-45E1-B328-4FD5D70DF141}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\JoyCaptionGUI
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\..\dist\inno
OutputBaseFilename=JoyCaptionGUI-Setup-Inno
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\..\app\webview-shell\Assets\JoyCaption.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=JoyCaption GUI Windows Installer

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "runtime"; Description: "Python 런타임과 ML 패키지를 설치합니다. 실사용에 필요하며 첫 설치에는 시간이 오래 걸릴 수 있습니다."; GroupDescription: "런타임 준비"

[Files]
Source: "..\..\dist\win-x64-single\JoyCaptionShell.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\joy-caption-desktop-beta.seed.yaml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"
Source: "..\..\scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\app\prototype\*"; DestDir: "{app}\app\prototype"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\app\webview-shell\Assets\*"; DestDir: "{app}\app\webview-shell\Assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\app\webview-shell\*.csproj"; DestDir: "{app}\app\webview-shell"; Flags: ignoreversion
Source: "..\..\app\webview-shell\Program.cs"; DestDir: "{app}\app\webview-shell"; Flags: ignoreversion
Source: "..\..\samples\images\*.jpg"; DestDir: "{app}\samples\images"; Flags: ignoreversion
Source: "..\..\samples\images\*.png"; DestDir: "{app}\samples\images"; Flags: ignoreversion
Source: "..\..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\.sandbox-prototype"
Name: "{app}\.sandbox-prototype\cache"
Name: "{app}\.sandbox-prototype\jobs"
Name: "{app}\.sandbox-prototype\logs"
Name: "{app}\.sandbox-prototype\models"
Name: "{app}\.sandbox-prototype\runtime"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\setup_real_runtime.ps1"""; WorkingDir: "{app}"; Description: "Python 런타임과 ML 패키지 설치"; Flags: postinstall skipifsilent runhidden; Tasks: runtime
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.sandbox-prototype\jobs"
Type: filesandordirs; Name: "{app}\.sandbox-prototype\logs"
