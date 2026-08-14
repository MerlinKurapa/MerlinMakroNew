[Setup]
AppName=Merlin Makro
AppVersion=5.1
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
Source: "MerlinGuard_Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "MerlinGuard_Launcher.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "MerlinGuard_Code.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "MerlinMakro.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "merlinmakroauth-firebase-adminsdk-fbsvc-df7571c065.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Merlin Makro"; Filename: "{app}\Launcher.exe"; IconFilename: "{app}\MerlinMakro.ico"
Name: "{commondesktop}\Merlin Makro"; Filename: "{app}\Launcher.exe"; IconFilename: "{app}\MerlinMakro.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\Launcher.exe"; Description: "Launch Merlin Makro"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"