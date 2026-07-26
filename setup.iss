; Inno Setup Installer Script for PennyBook
; To compile this script, use the Inno Setup Compiler (GUI or ISCC.exe command line tool)

#define MyAppName "PennyBook"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Sudeep Mullaguri"
#define MyAppURL "https://github.com/pennybook"
#define MyAppExeName "PennyBook.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{509E9623-CD2A-4FDF-A460-DF29B963557A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Allow the user to choose between installing for all users (Admin required) or current user (no Admin required)
PrivilegesRequiredOverridesAllowed=dialog
PrivilegesRequired=lowest
OutputBaseFilename=PennyBookSetup
SetupIconFile=static\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy all build files except the database (which we handle separately to avoid overwriting user data) and the receipts folder contents
Source: "dist\PennyBook\*"; DestDir: "{app}"; Excludes: "pennybook.db,receipts\*"; Flags: ignoreversion recursesubdirs createallsubdirs
; Copy the template database if it doesn't already exist, and grant write permissions
Source: "dist\PennyBook\pennybook.db"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall; Permissions: users-modify

[Dirs]
; Ensure the installation directory and the receipts storage folder have write/modify permissions for standard users
Name: "{app}"; Permissions: users-modify
Name: "{app}\receipts"; Permissions: users-modify

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
