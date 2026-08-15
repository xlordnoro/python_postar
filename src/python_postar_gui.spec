from pathlib import Path

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
# Remove Qt WebEngine runtime from the onefile executable.
#
# The Python bindings remain inside python_postar_gui.exe.
# The large Chromium/Qt WebEngine runtime is supplied from:
#
#     <portable folder>\webengine\
#
# This dramatically reduces the size of the GUI executable.
# ------------------------------------------------------------

WEBENGINE_FILES = {
    "qt6webenginecore.dll",
    "qt6webengine.dll",
    "qt6webenginewidgets.dll",
    "qtwebengineprocess.exe",
    "icudtl.dat",
    "v8_context_snapshot.bin",
    "qtwebengine_resources.pak",
    "qtwebengine_resources_100p.pak",
    "qtwebengine_resources_200p.pak",
    "qtwebengine_devtools_resources.pak",
}

def is_webengine_file(entry):
    source, destination, typecode = entry

    source_name = Path(source).name.lower()
    destination = str(destination).replace("\\", "/").lower()

    # Explicit WebEngine runtime files
    if source_name in WEBENGINE_FILES:
        return True

    # WebEngine locale directory
    if "qtwebengine_locales/" in destination:
        return True

    # WebEngine resources
    if source_name.startswith("qtwebengine_"):
        return True

    return False

# Remove WebEngine binaries
a.binaries = [
    entry
    for entry in a.binaries
    if not is_webengine_file(entry)
]

# Remove WebEngine data/resources
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
