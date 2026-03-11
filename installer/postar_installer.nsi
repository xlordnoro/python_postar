;--------------------------------
; Postar Installer
;--------------------------------

!define APP_NAME "Postar"
!define APP_EXE "python_postar_gui.exe"
!define COMPANY_NAME "Postar"
;!define VERSION "${VERSION}"
!define INSTALL_DIR "$PROGRAMFILES\Postar"

Name "${APP_NAME}"
OutFile "postar_setup_${VERSION}.exe"
InstallDir "${INSTALL_DIR}"

RequestExecutionLevel admin

SetCompressor /SOLID lzma

Icon "..\icon.ico"
UninstallIcon "..\icon.ico"

;--------------------------------
; Pages
;--------------------------------

Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

;--------------------------------
; Install
;--------------------------------

Section "Install"

SetOutPath "$INSTDIR"

; Copy entire prepared release folder
File /r "..\python_postar_windows\*"

; Start Menu folder
CreateDirectory "$SMPROGRAMS\Postar"

CreateShortcut \
"$SMPROGRAMS\Postar\Postar GUI.lnk" \
"$INSTDIR\python_postar_gui.exe"

CreateShortcut \
"$SMPROGRAMS\Postar\Uninstall Postar.lnk" \
"$INSTDIR\uninstall.exe"

; Desktop shortcut
CreateShortcut \
"$DESKTOP\Postar GUI.lnk" \
"$INSTDIR\python_postar_gui.exe"

; Registry for Add/Remove Programs
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "DisplayName" "Postar"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "UninstallString" "$INSTDIR\uninstall.exe"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "DisplayIcon" "$INSTDIR\python_postar_gui.exe"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "Publisher" "${COMPANY_NAME}"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "DisplayVersion" "${VERSION}"
WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "NoModify" 1
WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "NoRepair" 1

; Write uninstaller
WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

;--------------------------------
; Uninstall
;--------------------------------

Section "Uninstall"

Delete "$DESKTOP\Postar GUI.lnk"

Delete "$SMPROGRAMS\Postar\Postar GUI.lnk"
Delete "$SMPROGRAMS\Postar\Uninstall Postar.lnk"
RMDir "$SMPROGRAMS\Postar"

; Remove program files
RMDir /r "$INSTDIR"

; Remove registry entries
DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar"

SectionEnd
