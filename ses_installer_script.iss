; -- SES Accounting Setup Script --

[Setup]
AppName=SES Accounting
AppVersion=1.0.0
AppPublisher=Your Company Name
DefaultDirName={autopf}\SES Accounting
DefaultGroupName=SES Accounting
OutputDir=Output
OutputBaseFilename=SES_Setup_v1.0.0
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=D:\SES_Accounting\logo.ico

[Files]
Source: "D:\SES_Accounting\dist\SES_Accounting\SES_Accounting.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\SES_Accounting\dist\SES_Accounting\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 👇 1. This copies your logo into the app's installation folder
Source: "D:\SES_Accounting\logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 👇 2. This forces the Desktop and Start Menu shortcuts to use your logo!
Name: "{autodesktop}\SES Accounting"; Filename: "{app}\SES_Accounting.exe"; IconFilename: "{app}\logo.ico"
Name: "{group}\SES Accounting"; Filename: "{app}\SES_Accounting.exe"; IconFilename: "{app}\logo.ico"