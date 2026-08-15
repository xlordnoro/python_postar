import os
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

WEBENGINE_DIR = APP_DIR / "webengine"

if not WEBENGINE_DIR.is_dir():
    raise RuntimeError(
        f"Qt WebEngine runtime not found:\n{WEBENGINE_DIR}\n\n"
        "The 'webengine' folder must be present beside "
        "python_postar_gui.exe."
    )

# QtWebEngineProcess.exe
PROCESS_PATH = WEBENGINE_DIR / "QtWebEngineProcess.exe"

if not PROCESS_PATH.is_file():
    raise RuntimeError(
        f"QtWebEngineProcess.exe not found:\n{PROCESS_PATH}"
    )

os.environ["QTWEBENGINEPROCESS_PATH"] = str(WEBENGINE_DIR)

# Chromium resources
RESOURCES_DIR = WEBENGINE_DIR / "resources"

if not RESOURCES_DIR.is_dir():
    raise RuntimeError(
        f"Qt WebEngine resources not found:\n{RESOURCES_DIR}"
    )

os.environ["QTWEBENGINE_RESOURCES_PATH"] = str(RESOURCES_DIR)

# Chromium locales
LOCALES_DIR = WEBENGINE_DIR / "qtwebengine_locales"

if not LOCALES_DIR.is_dir():
    raise RuntimeError(
        f"Qt WebEngine locales not found:\n{LOCALES_DIR}"
    )

os.environ["QTWEBENGINE_LOCALES_PATH"] = str(LOCALES_DIR)

# External Qt WebEngine DLLs
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(str(WEBENGINE_DIR))

# Make DLLs available to child processes.
os.environ["PATH"] = (
    str(WEBENGINE_DIR)
    + os.pathsep
    + os.environ.get("PATH", "")
)
