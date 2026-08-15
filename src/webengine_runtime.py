import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent.parent

WEBENGINE_DIR = APP_DIR / "webengine"

if WEBENGINE_DIR.is_dir():
    # QtWebEngineProcess.exe
    os.environ["QTWEBENGINEPROCESS_PATH"] = str(WEBENGINE_DIR)

    # Chromium resources
    resources = WEBENGINE_DIR / "resources"
    if resources.is_dir():
        os.environ["QTWEBENGINE_RESOURCES_PATH"] = str(resources)

    # Chromium locale files
    locales = WEBENGINE_DIR / "qtwebengine_locales"
    if locales.is_dir():
        os.environ["QTWEBENGINE_LOCALES_PATH"] = str(locales)

    # Make external WebEngine DLLs discoverable.
    os.add_dll_directory(str(WEBENGINE_DIR))

    # Also make them available to subprocesses such as
    # QtWebEngineProcess.exe.
    os.environ["PATH"] = (
        str(WEBENGINE_DIR)
        + os.pathsep
        + os.environ.get("PATH", "")
    )
