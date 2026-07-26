#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif

[Setup]
AppId={{6B5A3461-9A4C-4D08-A72A-6F7426F22C91}
AppName=All for Cabal Web
AppVersion={#MyAppVersion}
AppPublisher=All for Cabal
DefaultDirName={autopf}\All for Cabal Web
DefaultGroupName=All for Cabal Web
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\artifacts
OutputBaseFilename=All for Cabal Web Setup-{#MyAppVersion}
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\All for Cabal Web.exe
PrivilegesRequired=lowest
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "สร้างไอคอนบน Desktop"; GroupDescription: "ไอคอนเพิ่มเติม:"

[Files]
Source: "..\dist\All for Cabal Web\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\All for Cabal Web"; Filename: "{app}\All for Cabal Web.exe"
Name: "{autodesktop}\All for Cabal Web"; Filename: "{app}\All for Cabal Web.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\All for Cabal Web.exe"; Description: "เปิด All for Cabal Web"; Flags: nowait postinstall skipifsilent
