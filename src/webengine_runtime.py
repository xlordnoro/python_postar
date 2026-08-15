import os
import sys
from pathlib import Path

# ------------------------------------------------------------
# Locate portable application directory
# ------------------------------------------------------------

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

# External Qt WebEngine runtime:
#
# python_postar_portable/
# ├── python_postar_gui.exe
# └── webengine/
#
WEBENGINE_DIR = APP_DIR / "webengine"

if not WEBENGINE_DIR.is_dir():
    # Allow the application to start normally when WebEngine
    # is unavailable. Qt will report the actual WebEngine error
    # if/when the preview is used.
    return

# ------------------------------------------------------------
# Qt WebEngine process
# ------------------------------------------------------------

PROCESS_PATH = WEBENGINE_DIR / "QtWebEngineProcess.exe"

if PROCESS_PATH.is_file():
    os.environ["QTWEBENGINEPROCESS_PATH"] = str(WEBENGINE_DIR)

# ------------------------------------------------------------
# Chromium resources
# ------------------------------------------------------------

RESOURCES_DIR = WEBENGINE_DIR / "resources"

if RESOURCES_DIR.is_dir():
    os.environ["QTWEBENGINE_RESOURCES_PATH"] = str(RESOURCES_DIR)

# ------------------------------------------------------------
# Chromium locale files
# ------------------------------------------------------------

LOCALES_DIR = WEBENGINE_DIR / "qtwebengine_locales"

if LOCALES_DIR.is_dir():
    os.environ["QTWEBENGINE_LOCALES_PATH"] = str(LOCALES_DIR)

# ------------------------------------------------------------
# External Qt WebEngine DLLs
# ------------------------------------------------------------

if WEBENGINE_DIR.is_dir():

    # Windows DLL search path for the current process.
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(WEBENGINE_DIR))

    # Make the DLLs discoverable by child processes too,
    # particularly QtWebEngineProcess.exe.
    os.environ["PATH"] = (
        str(WEBENGINE_DIR)
        + os.pathsep
        + os.environ.get("PATH", "")
    )
