import sys
import json
import requests
import platform
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPalette
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QComboBox, QProgressBar, 
    QDialog, QMessageBox, QListWidget, QListWidgetItem, QInputDialog, QSizePolicy, QColorDialog
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

# ---------------------------
# PyInstaller-safe app dir
# ---------------------------
def app_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

# ---------------------------
# CLI command helper
# ---------------------------
def get_cli_command(args_list):
    folder = app_dir()
    exe_path = folder / "python_postar.exe"
    py_path = folder / "python_postar.py"

    if exe_path.exists():
        return [str(exe_path)] + args_list
    elif py_path.exists():
        if getattr(sys, "frozen", False):
            return ["python", str(py_path)] + args_list
        else:
            return [sys.executable, str(py_path)] + args_list
    else:
        raise FileNotFoundError("Neither python_postar.exe nor python_postar.py found")

# ---------------------------
# File constants
# ---------------------------
PROFILE_FILE = Path("postar_profiles.json")
SETTINGS_FILE = Path("postar_last_profile.json")
QUEUE_FILE = Path("postar_job_queue.json")

APP_NAME = "Postar GUI"
APP_AUTHOR = "XLordnoro"
APP_WEBSITE = "https://github.com/xlordnoro/python_postar/releases"
REPO_OWNER = "xlordnoro"
REPO_NAME = "python_postar"
VERSION = "0.47.0"
RELEASE_NAME = "Erina"

# ----------------------
# GitHub release metadata
# ----------------------
def get_latest_github_release():
    """
    Returns (version_tag, release_title) from GitHub
    """
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

    try:
        resp = requests.get(api_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        tag = data.get("tag_name", "").lstrip("v")
        title = data.get("name") or data.get("tag_name", "Unknown Release")

        return tag, title

    except Exception as e:
        print(f"[Update] Failed to fetch release info: {e}")
        return None, None

# --------------------------
# Settings Menu Prompt
# --------------------------
POSTAR_SETTINGS_FILE = Path(".postar_settings.json")
DEFAULT_POSTAR_SETTINGS = {
    "B2_SHOWS_BASE": "",
    "B2_TORRENTS_BASE": "",
    "ENCODER_NAME": "",
    "AUTO_UPDATE": True,
    "BACKGROUND_IMAGE": "",
    "DARK_MODE": False
}
REQUIRED_POSTAR_KEYS = ("B2_SHOWS_BASE", "B2_TORRENTS_BASE", "ENCODER_NAME")

def load_postar_settings():
    if not POSTAR_SETTINGS_FILE.exists():
        POSTAR_SETTINGS_FILE.write_text(json.dumps(DEFAULT_POSTAR_SETTINGS, indent=2), encoding="utf-8")
        return DEFAULT_POSTAR_SETTINGS.copy()
    try:
        data = json.loads(POSTAR_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_POSTAR_SETTINGS.copy()
    for k, v in DEFAULT_POSTAR_SETTINGS.items():
        data.setdefault(k, v)
    return data

def save_postar_settings(settings: dict):
    POSTAR_SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")

def postar_settings_complete(settings: dict) -> bool:
    return all(settings.get(k, "").strip() for k in REQUIRED_POSTAR_KEYS)

# ---------------------------
# Storing UI states
# ---------------------------
UI_STATE_FILE = Path("postar_ui_state.json")
DEFAULT_UI_STATE = {
    "cmd_preview": True,
    "process_output": True,
    "html_preview": True,
}

def load_ui_state():
    if UI_STATE_FILE.exists():
        try:
            data = json.loads(UI_STATE_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_UI_STATE, **data}
        except Exception:
            pass
    return DEFAULT_UI_STATE.copy()

def save_ui_state(state: dict):
    UI_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

# Store unfinished jobs in the queue
def save_queue(job_queue):
    """Save the full unfinished job queue."""
    jobs_to_save = [
        {"args": args, "output": str(out_path)}
        for args, out_path in job_queue
    ]
    QUEUE_FILE.write_text(json.dumps(jobs_to_save, indent=2), encoding="utf-8")

def load_queue():
    if QUEUE_FILE.exists():
        try:
            data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            queue = [(job["args"], Path(job["output"])) for job in data]
            return queue
        except Exception:
            return []
    return []

# ---------------------------
# About Dialog
# ---------------------------
class AboutDialog(QDialog):
    def __init__(self, parent=None, dark_mode=False, version="Unknown", release_title="Unknown"):
        super().__init__(parent)

        self.setWindowTitle(f"About {APP_NAME}")
        self.setWindowIcon(QIcon("icon.ico"))
        self.setFixedSize(420, 260)

        layout = QVBoxLayout(self)
        title = QLabel(f"<h2>{APP_NAME}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        link_color = "white" if dark_mode else "black"

        info = QLabel(
            f"""
            <b>Version:</b> {version}<br>
            <b>Release:</b> {release_title}<br><br>
            <b>Author:</b> {APP_AUTHOR}<br>
            <b>Website:</b> <a style="color:{link_color};" href="{APP_WEBSITE}">{APP_WEBSITE}</a>
            """
        )
        info.setOpenExternalLinks(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(info)
        layout.addStretch()
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

# ---------------------------
# Drag & Drop LineEdit
# ---------------------------
class DragDropLineEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        if paths:
            current = self.text().strip()
            if current:
                current += ","
            self.setText(current + ",".join(paths))

class UpdateWorker(QThread):
    finished = pyqtSignal(str)
    output = pyqtSignal(str)

    def __init__(self, force=False, display_delay=2.0):
        super().__init__()
        self.force = force
        self.display_delay = display_delay

    def run(self):
        try:
            base_dir = app_dir()
            system = platform.system().lower()

            updater = None

            # -------- Windows --------
            if system == "windows":
                updater = base_dir / "updater.exe"

            # -------- Linux --------
            elif system == "linux":
                updater = base_dir / "updater"

            # -------- macOS --------
            elif system == "darwin":
                app = base_dir / "updater.app"
                if app.exists():
                    updater = ["open", "-a", str(app)]
                else:
                    updater = base_dir / "updater"

            if not updater:
                self.finished.emit("Unsupported platform")
                return

            if isinstance(updater, Path):
                if not updater.exists():
                    self.finished.emit(f"Updater not found: {updater}")
                    return
                cmd = [str(updater)]
            else:
                cmd = updater

            if self.force:
                cmd.append("--force")

            self.output.emit("[Update] Launching updater and closing GUI...\n")

            if system == "windows":
                subprocess.Popen(
                    cmd,
                    cwd=base_dir,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP |
                                  subprocess.DETACHED_PROCESS
                )
            else:
                subprocess.Popen(cmd, cwd=base_dir)

            # Exit GUI so files are unlocked
            QTimer.singleShot(500, QApplication.instance().quit)

            self.finished.emit("done")

        except Exception as e:
            self.finished.emit(str(e))           

# ---------------------------
# MAL Search Worker
# ---------------------------
class MalSearchWorker(QThread):
    finished = pyqtSignal(list)  # List of (title, mal_id)
    error = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        import requests
        try:
            url = f"https://api.jikan.moe/v4/anime?q={self.query}&limit=5"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                self.error.emit(f"HTTP {resp.status_code} error")
                return
            data = resp.json()
            results = []
            for item in data.get("data", []):
                title = item.get("title")
                mal_id = str(item.get("mal_id"))
                results.append((title, mal_id))
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class MalSearchByIdWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, mal_id):
        super().__init__()
        self.mal_id = mal_id

    def run(self):
        import requests
        try:
            url = f"https://api.jikan.moe/v4/anime/{self.mal_id}"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                self.error.emit(f"HTTP {resp.status_code} error")
                return

            data = resp.json().get("data")
            if not data:
                self.error.emit("No data found for that MAL ID")
                return

            title = data.get("title")
            self.finished.emit([(title, self.mal_id)])
        except Exception as e:
            self.error.emit(str(e))

# ---------------------------
# Worker Thread
# ---------------------------
class HtmlWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, args_list):
        super().__init__()
        self.args_list = args_list

    def run(self):
        try:
            cmd = get_cli_command(self.args_list)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1
            )
            for line in process.stdout:
                self.log.emit(line.rstrip())
            process.wait()
            if process.returncode != 0:
                self.error.emit(f"Process exited with code {process.returncode}")
            else:
                self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

# ---------------------------
# Postar Settings Dialog
# ---------------------------
class PostarSettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Postar – First-Time Setup")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(500, 250)
        self.settings = settings

        layout = QVBoxLayout(self)
        self.shows_edit = QLineEdit(settings["B2_SHOWS_BASE"])
        self.torrents_edit = QLineEdit(settings["B2_TORRENTS_BASE"])
        self.encoder_edit = QLineEdit(settings["ENCODER_NAME"])
        self.auto_update_check = QCheckBox("Enable auto-update")
        self.auto_update_check.setChecked(settings["AUTO_UPDATE"])

        layout.addWidget(QLabel("Backblaze B2 Shows Base URL"))
        layout.addWidget(self.shows_edit)
        layout.addWidget(QLabel("Backblaze B2 Torrents Base URL"))
        layout.addWidget(self.torrents_edit)
        layout.addWidget(QLabel("Encoder Name"))
        layout.addWidget(self.encoder_edit)
        layout.addWidget(self.auto_update_check)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.on_save)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def on_save(self):
        if not all((
            self.shows_edit.text().strip(),
            self.torrents_edit.text().strip(),
            self.encoder_edit.text().strip()
        )):
            QMessageBox.warning(self, "Missing values", "All fields are required.")
            return
        self.settings.update({
            "B2_SHOWS_BASE": self.shows_edit.text().strip(),
            "B2_TORRENTS_BASE": self.torrents_edit.text().strip(),
            "ENCODER_NAME": self.encoder_edit.text().strip(),
            "AUTO_UPDATE": self.auto_update_check.isChecked()
        })
        self.accept()

class JobQueueWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.gui = parent
        self.setWindowTitle("Job Queue")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(500, 350)

        layout = QVBoxLayout(self)

        self.queue_list = QListWidget()
        layout.addWidget(self.queue_list)

        self.timer_label = QLabel("Elapsed Time: 00:00:00")
        layout.addWidget(self.timer_label)

        btn_row = QHBoxLayout()

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.gui.remove_selected_job)
        btn_row.addWidget(self.remove_btn)

        self.run_btn = QPushButton("Run Queue")
        self.run_btn.clicked.connect(self.gui.start_queue)
        btn_row.addWidget(self.run_btn)

        layout.addLayout(btn_row)

    def sync_from_main(self):
        """Sync queue list from main GUI"""
        self.queue_list.clear()
        for args, out_path in self.gui.job_queue:
            self.queue_list.addItem(out_path.name)

BASE_SANDBOX_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy"
          content="
            default-src * data: blob: filesystem: about: ws: wss: 'unsafe-inline' 'unsafe-eval';
            img-src * data: blob: https: http:;
            media-src * data: blob: https: http:;
            connect-src *;
            style-src * 'unsafe-inline' https: http: file:;
            script-src * 'unsafe-inline' 'unsafe-eval' https: http:;
            font-src * data: blob: https: http: file:;
          ">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Live Preview Sandbox</title>
</head>
<body>
    <div id="container"></div>
</body>
</html>
"""

class LivePreviewWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Live HTML Preview")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(1200, 900)

        layout = QVBoxLayout(self)

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Reload Preview")
        refresh_btn.clicked.connect(self.reload_preview)

        self.dark_mode_cb = QCheckBox("Dark Mode")
        self.dark_mode_cb.stateChanged.connect(self._inject_pending_html)

        toolbar.addWidget(QLabel("Live HTML Preview"))
        toolbar.addStretch()
        toolbar.addWidget(self.dark_mode_cb)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # --- Webview ---
        self.webview = QWebEngineView()
        settings = self.webview.settings()
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.webview.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.webview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.webview)

        self.pending_html = ""

        # Base URL for images / local files
        self.base_url = QUrl.fromLocalFile(
            str(Path(__file__).parent.resolve()) + "/"
        )

        self.webview.setHtml(BASE_SANDBOX_HTML, self.base_url)
        self.webview.loadFinished.connect(self._inject_pending_html)

        # --- Local CSS directory ---
        if getattr(sys, 'frozen', False):
            # Running in a PyInstaller bundle
            base_path = Path(sys._MEIPASS)
        else:
            # Running as normal script
            base_path = Path(__file__).parent
            
        css_dir = base_path / "css"
        self.local_css_files = [
            p.resolve().as_uri().replace("\\", "\\\\")
            for p in css_dir.glob("*.css")
        ]

        if not self.local_css_files:
            print("Warning: No local CSS files found!")

    def set_html(self, html: str):
        self.pending_html = html
        self._inject_pending_html()

    def _inject_pending_html(self):
        if not self.pending_html:
            return

        # Escape HTML for JS injection
        html = (
            self.pending_html
            .replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("</script>", "<\\/script>")
        )

        # Toggle dark mode state
        dark_mode_enabled = self.dark_mode_cb.isChecked()

        # Build JS array for local CSS files
        local_css_js_array = ",".join(f"'{css}'" for css in self.local_css_files)

        js = f"""
        (function() {{
            const container = document.getElementById('container');
            if (!container) return;
            container.innerHTML = "";

            // --- Remove old injected CSS ---
            document.querySelectorAll('link[data-live-css]').forEach(e => e.remove());

            // --- Toggle dark mode class ---
            document.body.classList.toggle('dark-mode', {str(dark_mode_enabled).lower()});

            // --- Optional: enforce body background / text color ---
            let dm = document.getElementById('live-preview-dark-mode');
            if (!dm) {{
                dm = document.createElement('style');
                dm.id = 'live-preview-dark-mode';
                document.head.appendChild(dm);
            }}
            dm.textContent = `
                body.dark-mode {{
                    background-color: #121212 !important;
                    color: #e4e4e4 !important;
                }}
                body.dark-mode table,
                body.dark-mode td,
                body.dark-mode th {{
                    background: #222 !important;
                    border-color: #444 !important;
                    color: #e4e4e4 !important;
                }}
            `;

            // --- Inject local CSS files ---
            const cssFiles = [{local_css_js_array}];
            cssFiles.forEach(url => {{
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.dataset.liveCss = "1";
                link.href = url + "?v=" + Date.now(); // cache bust
                document.head.appendChild(link);
            }});

            // --- Insert HTML content ---
            const temp = document.createElement('div');
            temp.innerHTML = `{html}`;

            // Move any style/link tags from HTML to <head>
            temp.querySelectorAll('link[rel="stylesheet"], style').forEach(node => {{
                document.head.appendChild(node);
            }});

            // Append remaining HTML nodes to container
            Array.from(temp.childNodes).forEach(node => {{
                if (!['SCRIPT','LINK','STYLE'].includes(node.tagName)) {{
                    container.appendChild(node);
                }}
            }});

            // --- Load external JS files ---
            const jsFiles = [
                'https://ajax.googleapis.com/ajax/libs/jquery/3.7.1/jquery.min.js',
                'https://xlordnoro.github.io/playcools_js_code.js'
            ];
            jsFiles.forEach(url => {{
                const s = document.createElement('script');
                s.type = 'text/javascript';
                s.async = false;
                s.src = url;
                document.head.appendChild(s);
            }});

            // --- Inline scripts from HTML ---
            temp.querySelectorAll('script').forEach(script => {{
                const s = document.createElement('script');
                if (script.src) s.src = script.src;
                else s.textContent = script.textContent;
                s.type = script.type || 'text/javascript';
                s.async = false;
                document.head.appendChild(s);
            }});
        }})();
        """

        self.webview.page().runJavaScript(js)

    def reload_preview(self):
        self.webview.setHtml(BASE_SANDBOX_HTML, self.base_url)

# ---------------------------
# Main GUI
# ---------------------------
class PostarGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("icon.ico"))
        self.setWindowTitle(APP_NAME)
        self.resize(900, 750)
        self.worker = None

        # Queue
        self.job_queue = load_queue()  # Load unfinished jobs
        self.current_job_index = 0 if self.job_queue else -1
        self.timer = QTimer()
        self.elapsed_seconds = 0

        self.ui_state = load_ui_state()
        self.postar_settings = load_postar_settings()

        # Central widget
        central = QWidget(self)
        self.setCentralWidget(central)
        self.layout = QVBoxLayout(central)
        self.setAutoFillBackground(True)

        self.bg_label = QLabel(self.centralWidget())
        self.bg_label.setScaledContents(True)
        self.bg_label.lower()  # send to back
        self.bg_label.hide()

        # Background Settings
        self.postar_settings = load_postar_settings()
        bg_path = self.postar_settings.get("BACKGROUND_IMAGE", "")
        if bg_path:
            # defer applying until window is fully shown
            QTimer.singleShot(0, lambda: self.apply_background_image(bg_path))

        # Menu bar
        menubar = self.menuBar()
        about_action = menubar.addAction("About")
        about_action.setShortcut("F1")
        about_action.triggered.connect(self.show_about)

        # Job Queue Menu
        self.queue_window = JobQueueWindow(self)
        self.live_preview = LivePreviewWindow(self)
        queue_menu = menubar.addMenu("Job Queue")

        open_queue_action = queue_menu.addAction("Jobs")
        open_queue_action.setShortcut("F2")
        open_queue_action.triggered.connect(self.show_queue_window)
        clear_queue_action = queue_menu.addAction("Clear Entire Queue", self.clear_job_queue)
        clear_queue_action.setShortcut("F3")

        # Background Dropdown
        view_menu = menubar.addMenu("Custom Background")
        bg_action = view_menu.addAction("Set Background")
        bg_action.setShortcut("F4")
        bg_action.triggered.connect(self.select_background_image)

        clear_bg_action = view_menu.addAction("Clear Background")
        clear_bg_action.setShortcut("F5")
        clear_bg_action.triggered.connect(self.clear_background_image)

        # Live Preview
        preview_action = menubar.addAction("Live Preview")
        preview_action.setShortcut("F6")
        preview_action.triggered.connect(self.show_live_preview)

        # ---- Help / Update menu ----
        update_action = menubar.addAction("Check for Updates")
        update_action.setShortcut("F12")
        update_action.triggered.connect(self.manual_update_check)

        # Inputs
        self.inputs = {}

        # Optional: compute a uniform width for all input fields
        input_width = 900  # pixels, adjust as needed
        button_width = 120  # MAL search button width

        for label in (
            "BD 1080p Folders",
            "BD 720p Folders",
            "Non-BD Folders",
            "MAL IDs",
            "Heading Colors",
            "Airing Images",
            "Donation Images",
            "BD Resolution Images",
        ):
            if label == "MAL IDs":
                # Create a horizontal layout for the input + button
                row = QHBoxLayout()
                row.addWidget(QLabel(label))

                # Line edit width = total input width minus button width minus spacing
                mal_input = DragDropLineEdit()
                mal_input.setFixedWidth(input_width - button_width - 10)  # 10px spacing
                row.addWidget(mal_input)

                # Add the search button
                self.mal_search_btn = QPushButton("Search For MAL ID")
                self.mal_search_btn.setFixedWidth(button_width)
                self.mal_search_btn.clicked.connect(self.search_mal_id)
                row.addWidget(self.mal_search_btn)

                self.layout.addLayout(row)
                self.mal_input = mal_input
                self.inputs[label] = mal_input

            elif label == "Heading Colors":
                row = QHBoxLayout()
                row.addWidget(QLabel(label))

                color_input = DragDropLineEdit()
                color_input.setFixedWidth(input_width - button_width - 10)  # 10px spacing
                row.addWidget(color_input)

                pick_btn = QPushButton("Color Picker")
                pick_btn.setFixedWidth(button_width)
                pick_btn.clicked.connect(lambda _, e=color_input: self.pick_color(e))
                row.addWidget(pick_btn)

                self.layout.addLayout(row)
                self.inputs[label] = color_input

            else:
                # Regular inputs
                widget = self.add_input(label)
                widget.setFixedWidth(input_width)
                self.inputs[label] = widget

        # ---------------------------
        # Options / Checkboxes Section
        # ---------------------------
        self.options_container = QWidget()
        self.options_container.setObjectName("optionsPanel")
        options_layout = QVBoxLayout(self.options_container)
        options_layout.setContentsMargins(0, 0, 0, 0)

        self.bd_checkbox = QCheckBox("Enable BD toggle")
        self.seasonal_checkbox = QCheckBox("Seasonal / Airing style")
        self.crc_checkbox = QCheckBox("Include CRC32 column")
        self.kage_checkbox = QCheckBox("Kage Layout")
        self.dark_checkbox = QCheckBox("Dark Mode")
        #self.update_checkbox = QCheckBox("Manually check for updates (-u)")
        self.disable_auto_update_checkbox = QCheckBox("Disable auto-update (-du)")
        self.configure_checkbox = QCheckBox("Re-run setup (-configure)")

        for cb in (
            self.bd_checkbox,
            self.seasonal_checkbox,
            self.crc_checkbox,
            self.kage_checkbox,
            self.dark_checkbox,
            #self.update_checkbox,
            self.disable_auto_update_checkbox,
            self.configure_checkbox,
        ):
            cb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            options_layout.addWidget(cb)

        # Toggle button row
        options_toggle_row = QHBoxLayout()
        options_label = QLabel("Options")
        self.options_toggle_btn = QPushButton("Hide")
        self.options_toggle_btn.setMaximumWidth(60)
        options_toggle_row.addWidget(options_label)
        options_toggle_row.addStretch()
        options_toggle_row.addWidget(self.options_toggle_btn)

        self.layout.addLayout(options_toggle_row)
        self.layout.addWidget(self.options_container)

        # Connect the toggle
        self.options_toggle_btn.clicked.connect(
            lambda: self.toggle_widget(self.options_container, self.options_toggle_btn, state_key="options_visible")
        )

        # Remember state
        self.ui_state.setdefault("options_visible", True)
        visible = self.ui_state["options_visible"]
        self.options_container.setVisible(visible)
        self.options_toggle_btn.setText("Hide" if visible else "Show")

        # Checks github version & release title
        QTimer.singleShot(200, self.fetch_release_metadata)

        # ---------------------------
        # Apply dark/light mode colors to menu
        # ---------------------------
        def apply_menu_colors():
            if self.dark_checkbox.isChecked():
                menubar.setStyleSheet("""
                    QMenuBar {
                        background-color: #1e1e1e;
                        color: #ffffff;
                        border-bottom: 1px solid #444;
                    }
                    QMenuBar::item {
                        background-color: #1e1e1e;
                        color: #ffffff;
                        padding: 6px 12px;
                    }
                    QMenuBar::item:selected {
                        background-color: #333333;
                        color: #ffffff;
                    }
                    QMenu {
                        background-color: #1e1e1e;
                        color: #ffffff;
                    }
                    QMenu::item:selected {
                        background-color: #333333;
                        color: #ffffff;
                    }
                """)
            else:
                menubar.setStyleSheet("""
                    QMenuBar {
                        background-color: #f0f0f0;
                        color: #000000;
                    }
                    QMenuBar::item {
                        background-color: #f0f0f0;
                        color: #000000;
                        padding: 6px 12px;
                    }
                    QMenuBar::item:selected {
                        background-color: #dcdcdc;
                    }
                """)

        # Connect to checkbox after it exists
        self.dark_checkbox.stateChanged.connect(apply_menu_colors)

        # Initial apply (in case dark mode is already checked)
        apply_menu_colors()
        self.dark_checkbox.stateChanged.connect(self.toggle_dark)
        self.dark_checkbox.setChecked(self.postar_settings.get("DARK_MODE", False))
        self.toggle_dark()
        self.configure_checkbox.stateChanged.connect(self.open_reconfigure_dialog)

        # Output file
        input_width = 900  # same width used for BD 1080p Folders
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output HTML File"))
        self.output_file = QLineEdit("output.txt")
        self.output_file.setFixedWidth(input_width) 
        out_row.addWidget(self.output_file)
        self.layout.addLayout(out_row)

        # Profiles
        prof_row = QHBoxLayout()

        label_width = 23      # approximate width for "Profile" label
        total_width = 900     # total width for the row
        button_width = 80     # each button width
        spacing = 0          # spacing between widgets

        # Compute remaining width for QLineEdit + QComboBox
        remaining_width = total_width - label_width - (3 * button_width) - (4 * spacing)
        profile_name_width = int(remaining_width * 0.5)  # half for name
        profile_box_width = remaining_width - profile_name_width  # rest for dropdown

        # Label
        prof_row.addWidget(QLabel("Profile"))

        # Profile Name
        self.profile_name = QLineEdit()
        self.profile_name.setPlaceholderText("Profile name")
        self.profile_name.setFixedWidth(profile_name_width)
        prof_row.addWidget(self.profile_name)

        # Profile Dropdown
        self.profile_box = QComboBox()
        self.profile_box.setObjectName("profileDropdown")
        self.profile_box.setFixedWidth(profile_box_width)
        self.load_profiles()
        prof_row.addWidget(self.profile_box)

        # Buttons
        save_btn = QPushButton("Save")
        save_btn.setFixedWidth(button_width)
        save_btn.clicked.connect(self.save_profile)
        prof_row.addWidget(save_btn)

        load_btn = QPushButton("Load")
        load_btn.setFixedWidth(button_width)
        load_btn.clicked.connect(self.load_selected_profile)
        prof_row.addWidget(load_btn)

        del_btn = QPushButton("Delete")
        del_btn.setFixedWidth(button_width)
        del_btn.clicked.connect(self.delete_profile)
        prof_row.addWidget(del_btn)

        self.layout.addLayout(prof_row)

        # Command Preview with toggle
        self.cmd_preview = QTextEdit()
        self.cmd_preview.setReadOnly(True)
        cmd_row = QVBoxLayout()
        cmd_header = QHBoxLayout()
        cmd_label = QLabel("Command Preview")
        self.cmd_toggle_btn = QPushButton("Hide")
        self.cmd_toggle_btn.setMaximumWidth(60)
        self.cmd_toggle_btn.clicked.connect(lambda: self.toggle_widget(self.cmd_preview, self.cmd_toggle_btn))
        cmd_header.addWidget(cmd_label)
        cmd_header.addStretch()
        cmd_header.addWidget(self.cmd_toggle_btn)
        cmd_row.addLayout(cmd_header)
        cmd_row.addWidget(self.cmd_preview)
        self.layout.addLayout(cmd_row)

        # Process Output with toggle
        self.process_output = QTextEdit()
        self.process_output.setReadOnly(True)
        output_row = QVBoxLayout()
        output_header = QHBoxLayout()
        output_label = QLabel("Process Output")
        self.output_toggle_btn = QPushButton("Hide")
        self.output_toggle_btn.setMaximumWidth(60)
        self.output_toggle_btn.clicked.connect(lambda: self.toggle_widget(self.process_output, self.output_toggle_btn))
        output_header.addWidget(output_label)
        output_header.addStretch()
        output_header.addWidget(self.output_toggle_btn)
        output_row.addLayout(output_header)
        output_row.addWidget(self.process_output)
        self.layout.addLayout(output_row)

        # HTML Preview with toggle
        self.html_preview = QTextEdit()
        self.html_preview.textChanged.connect(self.live_render_html)
        self.html_preview.setReadOnly(True)
        html_row = QVBoxLayout()
        html_header = QHBoxLayout()
        html_label = QLabel("HTML Preview")
        self.html_toggle_btn = QPushButton("Hide")
        self.html_toggle_btn.setMaximumWidth(60)
        self.html_toggle_btn.clicked.connect(lambda: self.toggle_widget(self.html_preview, self.html_toggle_btn))
        self.html_edit_btn = QPushButton("Edit")
        self.html_edit_btn.setMaximumWidth(60)
        self.html_edit_btn.clicked.connect(self.toggle_html_edit_mode)
        html_header.addWidget(html_label)
        html_header.addStretch()
        html_header.addWidget(self.html_edit_btn)
        html_header.addWidget(self.html_toggle_btn)
        html_row.addLayout(html_header)
        html_row.addWidget(self.html_preview)
        self.layout.addLayout(html_row)
        self.current_html_file = None

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.layout.addWidget(self.progress)

        self.load_last_profile()

        # Generate / Queue Controls
        btn_row = QHBoxLayout()
        self.add_queue_btn = QPushButton("Add To Queue")
        self.add_queue_btn.clicked.connect(self.add_job_to_queue)
        self.start_queue_btn = QPushButton("Run Queue")
        self.start_queue_btn.clicked.connect(self.start_queue)
        self.generate_btn = QPushButton("Generate HTML (Single)")
        self.generate_btn.clicked.connect(self.generate_html)
        btn_row.addWidget(self.add_queue_btn)
        btn_row.addWidget(self.start_queue_btn)
        btn_row.addWidget(self.generate_btn)
        self.layout.addLayout(btn_row)

        # Store the UI states
        self.ui_state = load_ui_state()
        self.apply_ui_state()

        # Populate queue list if jobs were loaded
        for args, out_path in self.job_queue:
            self.queue_window.queue_list.addItem(str(out_path.name))

        # Timer updates
        self.timer.timeout.connect(self.update_timer)

    def closeEvent(self, event):
        # Save the current job queue regardless of current_job_index
        if self.job_queue:
            save_queue(self.job_queue)
        else:
            QUEUE_FILE.write_text("[]", encoding="utf-8")
        event.accept()

    def clear_job_queue(self):
        if not self.job_queue:
            return

        reply = QMessageBox.question(
            self,
            "Clear Queue",
            "Are you sure you want to remove all jobs from the queue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.job_queue.clear()
            self.queue_window.queue_list.clear()
            self.statusBar().showMessage("Job queue cleared", 3000)

    def show_queue_window(self):
        self.queue_window.sync_from_main()
        self.queue_window.show()
        self.queue_window.raise_()
        self.queue_window.activateWindow()

    # Update/Version Check
    def fetch_release_metadata(self):
        def worker():
            try:
                version, title = get_latest_github_release()
                if version:
                    self.remote_version = version
                    self.release_title = title
                else:
                    self.remote_version = "Unknown"
                    self.release_title = "Unknown Release"
            except Exception:
                self.remote_version = "Unknown"
                self.release_title = "Unknown Release"

        threading.Thread(target=worker, daemon=True).start()

    def show_live_preview(self):
        self.live_preview.show()
        self.live_preview.raise_()
        self.live_preview.activateWindow()
        
        self.live_preview.set_html(self.html_preview.toPlainText())

    def live_render_html(self):
        if self.live_preview.isVisible():
            self.live_preview.set_html(self.html_preview.toPlainText())

    # ---------------------------
    # HTML Edit Mode
    # ---------------------------
    def toggle_html_edit_mode(self):
        if self.html_preview.isReadOnly():
            self.html_preview.setReadOnly(False)
            self.html_edit_btn.setText("Lock")
            self.html_preview.setStyleSheet("border: 2px solid #ff9800;")
            self.statusBar().showMessage("HTML edit mode enabled", 3000)
        else:
            self.html_preview.setReadOnly(True)
            self.html_edit_btn.setText("Edit")
            if self.current_html_file:
                try:
                    self.current_html_file.write_text(self.html_preview.toPlainText(), encoding="utf-8")
                    ts = datetime.now().strftime("%H:%M:%S")
                    self.statusBar().showMessage(f"HTML changes saved successfully at {ts}", 5000)
                    self.html_preview.setStyleSheet("border: 2px solid #4caf50;")
                    QTimer.singleShot(800, lambda: self.html_preview.setStyleSheet(""))
                except Exception as e:
                    QMessageBox.warning(self, "Save Error", f"Failed to write HTML file:\n{e}")

    # ---------------------------
    # Queue & Worker Logic
    # ---------------------------
    def build_args_list(self):
        folders1080 = [p.strip() for p in self.inputs["BD 1080p Folders"].text().split(",") if p.strip()]
        folders720 = [p.strip() for p in self.inputs["BD 720p Folders"].text().split(",") if p.strip()]
        non_bd = [p.strip() for p in self.inputs["Non-BD Folders"].text().split(",") if p.strip()]
        mal_ids = [p.strip() for p in self.inputs["MAL IDs"].text().split(",") if p.strip()]
        span_colors = [p.strip() for p in self.inputs["Heading Colors"].text().split(",") if p.strip()]
        airing_imgs = [p.strip() for p in self.inputs["Airing Images"].text().split(",") if p.strip()]
        donation_imgs = [p.strip() for p in self.inputs["Donation Images"].text().split(",") if p.strip()]
        bd_images = [p.strip() for p in self.inputs["BD Resolution Images"].text().split(",") if p.strip()]
        args_list = []
        def add_flag(flag, values):
            if values:
                args_list.append(flag)
                args_list.extend(values)
        add_flag("-p1080", folders1080)
        add_flag("-p720", folders720)
        add_flag("-p", non_bd)
        add_flag("-m", mal_ids)
        add_flag("-c", span_colors)
        add_flag("-a", airing_imgs)
        add_flag("-d", donation_imgs)
        add_flag("-bi", bd_images)
        if self.bd_checkbox.isChecked(): args_list.append("-b")
        if self.seasonal_checkbox.isChecked(): args_list.append("-s")
        if self.crc_checkbox.isChecked(): args_list.append("-crc")
        if self.kage_checkbox.isChecked(): args_list.append("-kage")
        #if self.update_checkbox.isChecked(): args_list.append("-u")
        if self.disable_auto_update_checkbox.isChecked(): args_list.append("-du")
        if self.configure_checkbox.isChecked(): args_list.append("-configure")
        out_path = Path(self.output_file.text().strip() or "output.txt")
        args_list += ["-o", str(out_path)]
        return args_list, out_path

    # ---------------------------
    # Queue & Worker Logic (Fixed)
    # ---------------------------
    def add_job_to_queue(self):
        args, out_path = self.build_args_list()
        job_name = str(out_path.name)
        self.job_queue.append((args, out_path))
        self.queue_window.queue_list.addItem(job_name)
        self.statusBar().showMessage(f"Added job to queue — {len(self.job_queue)} total", 4000)

    def start_queue(self):
        if not self.job_queue:
            QMessageBox.information(self, "Queue Empty", "No jobs in queue.")
            return
        if self.worker:
            return  # Already running
        self.current_job_index = 0
        self.run_next_job()

    def run_next_job(self):
        if self.current_job_index >= len(self.job_queue):
            self.statusBar().showMessage("Queue completed successfully", 6000)
            self.current_job_index = -1
            self.progress.hide()
            self.timer.stop()
            return

        args_list, out_path = self.job_queue[self.current_job_index]
        self.current_output_file = out_path
        self.current_html_file = out_path

        # Remove highlight from all items
        for i in range(self.queue_window.queue_list.count()):
            item = self.queue_window.queue_list.item(i)
            item.setBackground(QColor("white"))
            item.setForeground(QColor("black"))

        # Highlight current job with border / color
        if self.queue_window.queue_list.count() > self.current_job_index:
            item = self.queue_window.queue_list.item(self.current_job_index)
            item.setForeground(QColor("black"))
            item.setBackground(QColor("#FFD700"))  # temporary highlight (gold)
        
        self.progress.show()
        self.generate_btn.setEnabled(False)
        self.process_output.append(f"\n--- Running job ({self.current_job_index+1}/{len(self.job_queue)}) ---\n")
        self.worker = HtmlWorker(args_list)
        self.worker.log.connect(self.process_output.append)
        self.worker.finished.connect(self.on_queue_job_finished)
        self.worker.error.connect(self.on_queue_job_error)
        self.worker.start()

        # Start timer
        self.elapsed_seconds = 0
        self.timer.start(1000)

    def on_queue_job_finished(self):
        # Load HTML into preview
        if self.current_output_file.exists():
            html = self.current_output_file.read_text(encoding="utf-8")
            self.html_preview.setPlainText(html)

            if self.live_preview.isVisible():
                self.live_preview.set_html(html)

        # Highlight job in green
        if 0 <= self.current_job_index < self.queue_window.queue_list.count():
            item = self.queue_window.queue_list.item(self.current_job_index)
            item.setBackground(QColor("#4CAF50"))  # green flash

            # Remove from queue after 700ms
            QTimer.singleShot(700, lambda idx=self.current_job_index: self.remove_job_from_list(idx))

        self.cleanup_worker()

    def on_queue_job_error(self, err):
        self.process_output.append(f"ERROR: {err}")
        if 0 <= self.current_job_index < self.queue_window.queue_list.count():
            self.queue_window.queue_list.item(self.current_job_index).setBackground(QColor("red"))
            # Remove errored job after short delay
            QTimer.singleShot(700, lambda idx=self.current_job_index: self.remove_job_from_list(idx))
        self.cleanup_worker()

    def remove_job_from_list(self, index):
        if index < len(self.job_queue):
            self.job_queue.pop(index)
        if index < self.queue_window.queue_list.count():
            self.queue_window.queue_list.takeItem(index)
        # run next job if any left
        if self.job_queue:
            # current_job_index already points to next job, just run it
            self.run_next_job()
        else:
            self.statusBar().showMessage("Queue completed successfully", 6000)
            self.current_job_index = -1
            self.progress.hide()
            self.timer.stop()

    def on_queue_job_error(self, err):
        self.process_output.append(f"ERROR: {err}")
        if 0 <= self.current_job_index < self.queue_window.queue_list.count():
            self.queue_window.queue_list.item(self.current_job_index).setBackground(QColor("red"))
        self.cleanup_worker()
        self.current_job_index += 1
        self.run_next_job()

    def remove_selected_job(self):
        selected_items = self.queue_window.queue_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            row = self.queue_window.queue_list.row(item)
            self.queue_window.queue_list.takeItem(row)
            # Remove corresponding job from job_queue
            if row < len(self.job_queue):
                self.job_queue.pop(row)
        self.statusBar().showMessage("Selected job(s) removed", 3000)

    def on_error(self, err):
        self.process_output.append(f"ERROR: {err}")
        if 0 <= self.current_job_index < self.queue_window.queue_list.count():
            self.queue_window.queue_list.item(self.current_job_index).setBackground(Qt.GlobalColor.red)
        self.cleanup_worker()
        self.current_job_index += 1
        self.run_next_job()

    def update_timer(self):
        self.elapsed_seconds += 1
        h, rem = divmod(self.elapsed_seconds, 3600)
        m, s = divmod(rem, 60)
        self.queue_window.timer_label.setText(
            f"Elapsed Time: {h:02}:{m:02}:{s:02}"
        )

    def cleanup_worker(self):
        self.progress.hide()
        self.generate_btn.setEnabled(True)
        self.worker = None
        self.timer.stop()

    def manual_update_check(self):
        reply = QMessageBox.question(
            self,
            "Check for Updates",
            "Check GitHub for updates now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.statusBar().showMessage("Checking for updates...")

        self.process_output.clear()
        self.process_output.append("[Update] Launching updater...\n")

        self.update_worker = UpdateWorker(force=True)
        self.update_worker.output.connect(self.process_output.append)
        self.update_worker.finished.connect(self.on_update_finished)
        self.update_worker.start()

    def auto_update_check(self):
        if not self.postar_settings.get("AUTO_UPDATE", True):
            return

        self.update_worker = UpdateWorker(force=False)
        self.update_worker.output.connect(self.process_output.append)
        self.update_worker.finished.connect(self.on_update_finished)
        self.update_worker.start()

    def on_update_finished(self, result):
        #self.statusBar().showMessage("Update Complete!", 3000)
        self.statusBar().clearMessage()

        if result != "done":
            QMessageBox.warning(self, "Update Error", result)

    # Color picker function
    def pick_color(self, line_edit: QLineEdit):
        color = QColorDialog.getColor(
            parent=self,
            title="Select Color"
        )

        if not color.isValid():
            return

        hex_color = color.name()  # "#RRGGBB"

        existing = [c.strip() for c in line_edit.text().split(",") if c.strip()]

        if hex_color not in existing:
            existing.append(hex_color)

        line_edit.setText(", ".join(existing))

    # ---------------------------
    # Single job generation
    # ---------------------------
    def generate_html(self):
        args_list, out_path = self.build_args_list()
        self.current_output_file = out_path
        self.current_html_file = out_path
        try:
            main_cmd_preview = get_cli_command([])
        except FileNotFoundError:
            main_cmd_preview = ["python", "python_postar.py"]
        self.cmd_preview.setPlainText(" ".join(f'"{c}"' if " " in c else c for c in main_cmd_preview + args_list))
        self.progress.show()
        self.generate_btn.setEnabled(False)
        self.process_output.clear()
        self.html_preview.clear()
        self.worker = HtmlWorker(args_list)
        self.worker.log.connect(self.process_output.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_finished(self):
        if self.current_output_file.exists():
            html = self.current_output_file.read_text(encoding="utf-8")
            self.html_preview.setPlainText(html)

            if self.live_preview.isVisible():
                self.live_preview.set_html(html)
        self.cleanup_worker()

    def on_error(self, err):
        self.process_output.append(f"ERROR: {err}")
        self.cleanup_worker()

    def cleanup_worker(self):
        self.progress.hide()
        self.generate_btn.setEnabled(True)
        self.worker = None

    # ---------------------------
    # MAL Search Functions
    # ---------------------------
    def search_mal_id(self):
        query = self.mal_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Input Required", "Please enter a series name or MAL ID to search.")
            return

        self.mal_search_btn.setEnabled(False)
        self.mal_search_btn.setText("Searching...")

        # If the input is purely numeric, treat it as an ID
        if query.isdigit():
            self.mal_worker = MalSearchByIdWorker(query)
        else:
            self.mal_worker = MalSearchWorker(query)

        self.mal_worker.finished.connect(self.on_mal_search_finished)
        self.mal_worker.error.connect(self.on_mal_search_error)
        self.mal_worker.start()

    def on_mal_search_finished(self, results):
        self.mal_search_btn.setEnabled(True)
        self.mal_search_btn.setText("Search MAL ID")

        if not results:
            QMessageBox.information(self, "No Results", "No matching anime found on MAL.")
            return

        items = [f"{title} — ID: {mal_id}" for title, mal_id in results]
        item, ok = QInputDialog.getItem(self, "Select Anime", "Select anime to use MAL ID:", items, 0, False)
        if ok and item:
            selected_mal_id = item.split("ID:")[-1].strip()

            # Split existing text into parts (comma separated)
            current_ids = [x.strip() for x in self.mal_input.text().split(",") if x.strip()]

            # If user typed a name that was just replaced, remove it
            # We'll assume anything non-numeric in the field is a "name" that should be replaced
            current_ids = [x for x in current_ids if x.isdigit()]

            # Append new ID
            if selected_mal_id not in current_ids:
                current_ids.append(selected_mal_id)

            self.mal_input.setText(", ".join(current_ids))

    def on_mal_search_error(self, err):
        self.mal_search_btn.setEnabled(True)
        self.mal_search_btn.setText("Search MAL ID")
        QMessageBox.warning(self, "Search Error", f"Failed to search MAL:\n{err}")

    def apply_background_image(self, image_path):
        if image_path and Path(image_path).exists():
            pixmap = QPixmap(image_path)
            self.bg_label.setPixmap(pixmap)
            self.bg_label.show()
            self.resizeEvent(None)  # force rescale
        else:
            self.bg_label.hide()

    def select_background_image(self):
        from PyQt6.QtWidgets import QFileDialog

        file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )

        if file:
            settings = load_postar_settings()
            settings["BACKGROUND_IMAGE"] = file
            save_postar_settings(settings)
            self.apply_background_image(file)

    def clear_background_image(self):
        settings = load_postar_settings()
        settings["BACKGROUND_IMAGE"] = ""
        save_postar_settings(settings)
        self.apply_background_image("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.bg_label.isVisible():
            self.bg_label.setGeometry(self.centralWidget().rect())

    # ---------------------------
    # UI / Dark Mode / Toggle
    # ---------------------------
    def toggle_dark(self):
        dark = self.dark_checkbox.isChecked()
        self.postar_settings["DARK_MODE"] = dark
        save_postar_settings(self.postar_settings)

        has_background = hasattr(self, "background_image") and self.background_image is not None

        style = ""

        # Only set QWidget background if:
        # - dark mode ON
        # - NO custom background image
        if dark and not has_background:
            style += "QWidget { background:#2a2a2a; color:#e0e0e0; border: 1px solid #555; border-radius:3px; }\n"
        elif not dark:
            style += "QWidget { background:#f0f0f0; color:#000000; border:1px solid #555; border-radius:3px; }\n"

        if dark:
            style += """
                QLineEdit, QTextEdit { background: #1e1e1e; color: #ffffff; border: 1px solid #444; }
                QLabel { color: #ffffff; }
                QPushButton { background: #2a2a2a; color: #ffffff; border: 1px solid #555; padding:6px; border-radius:3px; }
                QPushButton:hover { background: #3a3a3a; }
                QCheckBox { color: #e0e0e0; }
                QComboBox { background: #2a2a2a; color: #e0e0e0; }
                QListWidget { background: #2a2a2a; color: #e0e0e0; }
                QProgressBar { background: #2a2a2a; color: #e0e0e0; }

                #profileDropdown {
                    border: 1px solid #555; 
                    background: #2a2a2a; 
                    color: #ffffff;
                }
                #profileDropdown QAbstractItemView {
                    background: #2a2a2a;
                    color: #ffffff;
                    selection-background-color: #3a3a3a;
                }
                QWidget#optionsPanel {
                    background: transparent;
                    border: none;
                }
                QMenuBar, QMenu {
                    background: transparent;
                    border: none;
                }
                QMenuBar::item {
                    background: transparent;
                    border: none;
                    padding: 4px 10px;
                }
                QMenuBar::item:selected {
                    background: rgba(255, 255, 255, 0.12);
                }
            """
        else:
            style += """
                QLineEdit, QTextEdit { background: #ffffff; color: #000000; border: 1px solid #ccc; }
                QLabel { color: #000000; }
                QPushButton { background: #f0f0f0; color: #000000; border:1px solid #555; padding:6px; border-radius:3px; }
                QPushButton:hover { background: #d0d0d0; }
                QCheckBox { color: #000000; }
                QComboBox { background: #ffffff; color: #000000; }
                QListWidget { background: #ffffff; color: #000000; }
                QProgressBar { background: #f0f0f0; color: #000000; }

                QWidget#optionsPanel {
                    background: transparent;
                    border: none;
                }
                QMenuBar, QMenu {
                    background: #f0f0f0;
                    border: none;
                }
            """

        self.setStyleSheet(style)

    def toggle_widget(self, widget, button, state_key=None):
        """Toggle visibility of a widget and update the corresponding button and UI state."""
        visible = not widget.isVisible()
        widget.setVisible(visible)
        button.setText("Hide" if visible else "Show")
        if state_key:
            self.ui_state[state_key] = visible
            save_ui_state(self.ui_state)

    def save_preview_state(self):
        """Save all toggleable sections."""
        self.ui_state["cmd_preview"] = self.cmd_preview.isVisible()
        self.ui_state["process_output"] = self.process_output.isVisible()
        self.ui_state["html_preview"] = self.html_preview.isVisible()
        save_ui_state(self.ui_state)

    def apply_ui_state(self):
        self.set_preview_state(self.cmd_preview, self.cmd_toggle_btn, self.ui_state["cmd_preview"])
        self.set_preview_state(self.process_output, self.output_toggle_btn, self.ui_state["process_output"])
        self.set_preview_state(self.html_preview, self.html_toggle_btn, self.ui_state["html_preview"])
        
    def set_preview_state(self, widget, button, visible):
        widget.setVisible(visible)
        button.setText("Hide" if visible else "Show")

    # ---------------------------
    # Inputs
    # ---------------------------
    def add_input(self, label):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = DragDropLineEdit()
        row.addWidget(edit)
        self.layout.addLayout(row)
        return edit

    # ---------------------------
    # Reconfigure Settings
    # ---------------------------
    def open_reconfigure_dialog(self):
        if not self.configure_checkbox.isChecked():
            return
        settings = load_postar_settings()
        dlg = PostarSettingsDialog(settings, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            save_postar_settings(settings)
            QMessageBox.information(self, "Settings Updated", "Postar configuration updated successfully.")
        self.configure_checkbox.setChecked(False)

    # ---------------------------
    # Profiles
    # ---------------------------
    def load_profiles(self):
        self.profile_box.clear()
        if PROFILE_FILE.exists():
            self.profile_box.addItems(json.loads(PROFILE_FILE.read_text(encoding="utf-8")).keys())

    def save_profile(self):
        name = self.profile_name.text().strip()
        if not name:
            return
        profiles = json.loads(PROFILE_FILE.read_text(encoding="utf-8")) if PROFILE_FILE.exists() else {}
        state = self.read_state()
        profiles[name] = state
        PROFILE_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
        SETTINGS_FILE.write_text(json.dumps({"last": name}), encoding="utf-8")
        self.load_profiles()
        self.profile_box.setCurrentText(name)

    def load_selected_profile(self):
        if not PROFILE_FILE.exists():
            return
        name = self.profile_box.currentText()
        profiles = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        if name in profiles:
            self.write_state(profiles[name])
            SETTINGS_FILE.write_text(json.dumps({"last": name}), encoding="utf-8")

    def delete_profile(self):
        if not PROFILE_FILE.exists():
            return
        name = self.profile_box.currentText()
        profiles = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        profiles.pop(name, None)
        PROFILE_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
        self.load_profiles()

    def load_last_profile(self):
        if SETTINGS_FILE.exists():
            last = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("last")
            if last:
                self.profile_box.setCurrentText(last)
                self.load_selected_profile()

    def read_state(self):
        return {
            "inputs": {k: v.text() for k, v in self.inputs.items()},
            "checks": {
                "bd": self.bd_checkbox.isChecked(),
                "seasonal": self.seasonal_checkbox.isChecked(),
                "crc": self.crc_checkbox.isChecked(),
                "kage": self.kage_checkbox.isChecked(),
                #"update": self.update_checkbox.isChecked(),
                "disable_auto_update": self.disable_auto_update_checkbox.isChecked(),
            },
            "output_file": self.output_file.text().strip() or "output.txt",
            "previews": {
                "cmd_preview": self.cmd_preview.isVisible(),
                "process_output": self.process_output.isVisible(),
                "html_preview": self.html_preview.isVisible(),
            }
        }

    def write_state(self, state):
        for k, v in state.get("inputs", {}).items():
            self.inputs[k].setText(v)
        self.bd_checkbox.setChecked(state["checks"].get("bd", False))
        self.seasonal_checkbox.setChecked(state["checks"].get("seasonal", False))
        self.crc_checkbox.setChecked(state["checks"].get("crc", False))
        self.kage_checkbox.setChecked(state["checks"].get("kage", False))
        #self.update_checkbox.setChecked(state["checks"].get("update", False))
        self.disable_auto_update_checkbox.setChecked(state["checks"].get("disable_auto_update", False))
        self.output_file.setText(state.get("output_file", "output.txt"))

        # Apply preview visibility
        previews = state.get("previews", {})
        self.set_preview_state(self.cmd_preview, self.cmd_toggle_btn, previews.get("cmd_preview", True))
        self.set_preview_state(self.process_output, self.output_toggle_btn, previews.get("process_output", True))
        self.set_preview_state(self.html_preview, self.html_toggle_btn, previews.get("html_preview", True))

    def show_about(self):
        dark = self.dark_checkbox.isChecked()
        AboutDialog(
            self,
            dark_mode=dark,
            version=VERSION,
            release_title=RELEASE_NAME
        ).exec()

# ---------------------------
# App Entry
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    postar_settings = load_postar_settings()
    if not postar_settings_complete(postar_settings):
        dlg = PostarSettingsDialog(postar_settings)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        save_postar_settings(postar_settings)
    win = PostarGUI()
    win.show()
    sys.exit(app.exec())
