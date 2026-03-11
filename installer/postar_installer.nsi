;--------------------------------
; Postar Installer (Desktop Default)
;--------------------------------

!define APP_NAME "Postar"
!define APP_EXE "python_postar_gui.exe"
!define COMPANY_NAME "Postar"
!define INSTALL_DIR "$DESKTOP\Postar"   ; Default install location

Name "${APP_NAME}"
OutFile "python_postar_setup_${VERSION}.exe"
InstallDir "${INSTALL_DIR}"

; No admin rights needed
RequestExecutionLevel user

SetCompressor /SOLID lzma

Icon "..\icon.ico"
UninstallIcon "..\icon.ico"

;--------------------------------
; Pages
;--------------------------------

Page directory          ; Allow user to change install folder
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

;--------------------------------
; Install Section
;--------------------------------

Section "Install"

  ; Set output path
  SetOutPath "$INSTDIR"

  ; Copy all prepared files (includes _internal and EXEs)
  File /r "..\python_postar_windows\*"

  ; Optional Start Menu folder
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

  ; Registry entries for Add/Remove Programs (HKCU so no admin needed)
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "DisplayName" "Postar"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "DisplayIcon" "$INSTDIR\python_postar_gui.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "Publisher" "${COMPANY_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "DisplayVersion" "${VERSION}"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar" "NoRepair" 1

  ; Write uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

;--------------------------------
; Uninstall Section
;--------------------------------

Section "Uninstall"

  ; Delete shortcuts
  Delete "$DESKTOP\Postar GUI.lnk"
  Delete "$SMPROGRAMS\Postar\Postar GUI.lnk"
  Delete "$SMPROGRAMS\Postar\Uninstall Postar.lnk"
  RMDir "$SMPROGRAMS\Postar"

  ; Remove program files
  RMDir /r "$INSTDIR"

  ; Remove registry entries
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar"

SectionEnd
