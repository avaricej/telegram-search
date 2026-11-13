; Optional installer: compile with Inno Setup 6 after scripts/build.ps1.
[Setup]
AppId={{E5836D5C-1443-466D-91A0-88F90AE6226B}
AppName=Chat Scout
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\ChatScout
DefaultGroupName=Chat Scout
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=ChatScout-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE

[Files]
Source: "..\dist\ChatScout\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Chat Scout"; Filename: "{app}\ChatScout.exe"
Name: "{autodesktop}\Chat Scout"; Filename: "{app}\ChatScout.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\ChatScout.exe"; Description: "Launch Chat Scout"; Flags: nowait postinstall skipifsilent
