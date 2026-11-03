; 도형그리기 설치 파일 (Inno Setup 6)
; GitHub Actions 에서: iscc /DMyAppVersion=1.9 installer\mdraw.iss

#ifndef MyAppVersion
  #define MyAppVersion "1.0"
#endif
#define MyAppName "도형그리기"
#define MyAppExe "도형그리기.exe"

[Setup]
AppId={{6B1D5C7E-3F2A-4C1B-9E7D-4A5B8C9D2E10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=mathkt
AppPublisherURL=https://github.com/mathkt/mathboard
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; 관리자 권한 없이 설치 (학교 PC에서도 설치되도록)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=mdraw-setup
SetupIconFile=..\icon\mdraw.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
WizardStyle=modern
WizardImageFile=wizard.bmp,wizard@2x.bmp
WizardSmallImageFile=small.bmp,small@2x.bmp
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
ChangesAssociations=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"
Name: "assoc"; Description: "도형 파일(.dhg)을 더블클릭하면 이 프로그램으로 열기"; GroupDescription: "추가 작업:"

[Files]
Source: "..\dist\도형그리기\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\{#MyAppName} 지우기"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.dhg"; ValueType: string; ValueName: ""; ValueData: "Dohyeong.File"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\Dohyeong.File"; ValueType: string; ValueName: ""; ValueData: "도형그리기 파일"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\Dohyeong.File\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExe},0"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\Dohyeong.File\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExe}"" ""%1"""; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\.dhg\OpenWithProgids"; ValueType: string; ValueName: "Dohyeong.File"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assoc
; '연결 프로그램' 목록의 '도형그리기' 를 지금 설치한 프로그램으로 (예전에 지운 폴더의 도형그리기.exe 를 가리키던 것을 바로잡음)
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExe}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExe},0"
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExe}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExe}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExe}\SupportedTypes"; ValueType: string; ValueName: ".dhg"; ValueData: ""

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "도형그리기 실행하기"; Flags: nowait postinstall skipifsilent
