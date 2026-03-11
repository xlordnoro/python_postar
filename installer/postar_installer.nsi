;--------------------------------
; Postar Installer (Desktop Install)
;--------------------------------

!define APP_NAME "Postar"
!define APP_EXE "python_postar_gui.exe"
!define COMPANY_NAME "Postar"
!define INSTALL_DIR "$DESKTOP\Postar"   ; Install on Desktop

Name "${APP_NAME}"
OutFile "postar_setup_${VERSION}.exe"
InstallDir "${INSTALL_DIR}"

; No admin rights needed for Desktop install
RequestExecutionLevel user

SetCompressor /SOLID lzma

Icon "..\icon.ico"
UninstallIcon "..\icon.ico"

;--------------------------------
; Pages
;--------------------------------

Page instfiles

; No directory page needed since we fixed Desktop install
;Page directory  

UninstPage uninstConfirm
UninstPage instfiles

;--------------------------------
; Install
;--------------------------------

Section "Install"

  SetOutPath "$INSTDIR"

  ; Copy entire prepared release folder
  File /r "..\python_postar_windows\*"

  ; Start Menu folder (optional)
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

  ; Registry for Add/Remove Programs (still optional, may fail without admin)
  ; Using HKCU instead of HKLM so admin rights not needed
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
; Uninstall
;--------------------------------

Section "Uninstall"

  Delete "$DESKTOP\Postar GUI.lnk"

  Delete "$SMPROGRAMS\Postar\Postar GUI.lnk"
  Delete "$SMPROGRAMS\Postar\Uninstall Postar.lnk"
  RMDir "$SMPROGRAMS\Postar"

  ; Remove program files from Desktop
  RMDir /r "$INSTDIR"

  ; Remove registry entries from HKCU
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Postar"

SectionEnd
