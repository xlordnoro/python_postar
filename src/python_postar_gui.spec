from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

block_cipher = None

a = Analysis(
    ["gui.pyw"],
    pathex=[],
    binaries=[],
    datas=[
        ("../css", "css"),
        ("../translations/*.qm", "translations"),
        ("../qt_translations", "qt_translations"),
        ("../themes", "themes"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["webengine_runtime.py"],
    excludes=[],
    noarchive=False,
)


# ------------------------------------------------------------
# Remove WebEngine runtime from the onefile executable.
#
# PyQt6-WebEngine's Python bindings remain available, but the
# large Chromium runtime is supplied externally.
# ------------------------------------------------------------

WEBENGINE_NAMES = {
    "Qt6WebEngineCore.dll",
    "Qt6WebEngine.dll",
    "Qt6WebEngineWidgets.dll",
    "QtWebEngineProcess.exe",
    "icudtl.dat",
    "v8_context_snapshot.bin",
    "qtwebengine_resources.pak",
    "qtwebengine_resources_100p.pak",
    "qtwebengine_resources_200p.pak",
    "qtwebengine_devtools_resources.pak",
}


def is_webengine_file(entry):
    source, destination, typecode = entry

    filename = Path(source).name.lower()

    if filename in {name.lower() for name in WEBENGINE_NAMES}:
        return True

    normalized = str(destination).replace("\\", "/").lower()

    if "qtwebengine_locales/" in normalized:
        return True

    if normalized.startswith("resources/"):
        if "qtwebengine" in filename:
            return True

    return False


a.binaries = [
    entry
    for entry in a.binaries
    if not is_webengine_file(entry)
]

a.datas = [
    entry
    for entry in a.datas
    if not is_webengine_file(entry)
]


pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)


exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="python_postar_gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="../icon.ico",
)
