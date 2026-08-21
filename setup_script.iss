[Setup]
AppName=Merlin Makro
AppVersion=6.1
DefaultDirName={commonpf}\MerlinMakro
DefaultGroupName=Merlin Makro
OutputBaseFilename=MerlinMakro_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableDirPage=no
DisableProgramGroupPage=yes
DisableFinishedPage=no
DisableWelcomePage=no
AllowNoIcons=yes
LicenseFile=
UninstallDisplayIcon={app}\Launcher.exe
SetupIconFile=MerlinMakro.ico
OutputDir=Output

[Files]
Source: "Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "MerlinMakro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "MerlinMakro.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Merlin Makro"; Filename: "{app}\Launcher.exe"; IconFilename: "{app}\MerlinMakro.ico"
Name: "{commondesktop}\Merlin Makro"; Filename: "{app}\Launcher.exe"; IconFilename: "{app}\MerlinMakro.ico"



[Run]
Filename: "{app}\Launcher.exe"; Description: "Launch Merlin Makro"; Flags: nowait postinstall

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{commondesktop}\Merlin Makro.lnk"
Type: filesandordirs; Name: "{userdesktop}\Merlin Makro.lnk"