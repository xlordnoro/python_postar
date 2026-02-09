import sys
import json
from pathlib import Path
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QComboBox, QProgressBar, 
    QDialog, QMessageBox, QListWidget, QListWidgetItem, QInputDialog
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from datetime import datetime
import subprocess

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
APP_VERSION = "0.44.0"
APP_VERSION_NAME = "Emilia"
APP_AUTHOR = "XLordnoro"
APP_WEBSITE = "https://github.com/xlordnoro/python_postar/releases"

# --------------------------
# Settings Menu Prompt
# --------------------------
POSTAR_SETTINGS_FILE = Path(".postar_settings.json")
DEFAULT_POSTAR_SETTINGS = {
    "B2_SHOWS_BASE": "",
    "B2_TORRENTS_BASE": "",
    "ENCODER_NAME": "",
    "AUTO_UPDATE": True
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
    "queue_visible": True
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
    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setWindowIcon(QIcon("icon.ico"))
        self.setFixedSize(420, 260)

        layout = QVBoxLayout(self)
        title = QLabel(f"<h2>{APP_NAME}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set link color depending on dark mode
        link_color = "white" if dark_mode else "black"

        info = QLabel(
            f"""
            <b>Version:</b> {APP_VERSION}<br>
            <b>Release:</b> {APP_VERSION_NAME}<br><br>
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

# ---------------------------
# Main GUI
# ---------------------------
class PostarGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("icon.ico"))
        self.setWindowTitle(APP_NAME)
        self.resize(1050, 950)
        self.worker = None

        # Queue
        self.job_queue = load_queue()  # Load unfinished jobs
        self.current_job_index = 0 if self.job_queue else -1
        self.timer = QTimer()
        self.elapsed_seconds = 0

        self.ui_state = load_ui_state()

        # Central widget
        central = QWidget(self)
        self.setCentralWidget(central)
        self.layout = QVBoxLayout(central)

        # Menu bar
        menubar = self.menuBar()
        about_action = menubar.addAction("About")
        about_action.setShortcut("F1")
        about_action.triggered.connect(self.show_about)

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

            else:
                # Regular inputs
                widget = self.add_input(label)
                widget.setFixedWidth(input_width)
                self.inputs[label] = widget

        # Checkboxes
        self.bd_checkbox = QCheckBox("Enable BD toggle")
        self.seasonal_checkbox = QCheckBox("Seasonal / Airing style")
        self.crc_checkbox = QCheckBox("Include CRC32 column")
        self.kage_checkbox = QCheckBox("Kage Layout")
        self.dark_checkbox = QCheckBox("Dark Mode")
        self.update_checkbox = QCheckBox("Manually check for updates (-u)")
        self.disable_auto_update_checkbox = QCheckBox("Disable auto-update (-du)")
        self.configure_checkbox = QCheckBox("Re-run setup (-configure)")
        for cb in (
            self.bd_checkbox,
            self.seasonal_checkbox,
            self.crc_checkbox,
            self.kage_checkbox,
            self.dark_checkbox,
            self.update_checkbox,
            self.disable_auto_update_checkbox,
            self.configure_checkbox,
        ):
            self.layout.addWidget(cb)

        # ---------------------------
        # Apply dark/light mode colors to menu
        # ---------------------------
        def apply_menu_colors():
            if self.dark_checkbox.isChecked():
                menubar.setStyleSheet("""
                    QMenuBar {
                        background-color: #1e1e1e;
                        color: #e0e0e0;
                    }
                    QMenuBar::item {
                        background-color: #1e1e1e;
                        color: #e0e0e0;
                    }
                    QMenuBar::item:selected {
                        background-color: #444444;
                        color: #ffffff;
                    }
                    QMenu {
                        background-color: #1e1e1e;
                        color: #e0e0e0;
                    }
                    QMenu::item:selected {
                        background-color: #444444;
                        color: #ffffff;
                    }
                """)
            else:
                menubar.setStyleSheet("")  # reset to default

        # Connect to checkbox after it exists
        self.dark_checkbox.stateChanged.connect(apply_menu_colors)

        # Initial apply (in case dark mode is already checked)
        apply_menu_colors()
        self.dark_checkbox.stateChanged.connect(self.toggle_dark)
        self.configure_checkbox.stateChanged.connect(self.open_reconfigure_dialog)

        # Output file
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output HTML File"))
        self.output_file = QLineEdit("output.txt")
        out_row.addWidget(self.output_file)
        self.layout.addLayout(out_row)

        # Profiles
        prof_row = QHBoxLayout()
        self.profile_name = QLineEdit()
        self.profile_name.setPlaceholderText("Profile name")
        self.profile_box = QComboBox()
        self.load_profiles()
        save_btn = QPushButton("Save")
        load_btn = QPushButton("Load")
        del_btn = QPushButton("Delete")
        save_btn.clicked.connect(self.save_profile)
        load_btn.clicked.connect(self.load_selected_profile)
        del_btn.clicked.connect(self.delete_profile)
        prof_row.addWidget(QLabel("Profile"))
        prof_row.addWidget(self.profile_name)
        prof_row.addWidget(self.profile_box)
        prof_row.addWidget(save_btn)
        prof_row.addWidget(load_btn)
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

        # ---------------------------
        # Job Queue & Timer with toggle
        # ---------------------------
        queue_row = QVBoxLayout()

        # Header with toggle button
        queue_header = QHBoxLayout()
        queue_label = QLabel("Job Queue")
        self.queue_toggle_btn = QPushButton("Hide")
        self.queue_toggle_btn.setMaximumWidth(60)
        queue_header.addWidget(queue_label)
        queue_header.addStretch()
        queue_header.addWidget(self.queue_toggle_btn)
        queue_row.addLayout(queue_header)

        # Container for queue elements
        self.queue_container = QWidget()
        queue_container_layout = QVBoxLayout(self.queue_container)
        queue_container_layout.setContentsMargins(0, 0, 0, 0)

        self.queue_list = QListWidget()
        queue_container_layout.addWidget(self.queue_list)

        self.timer_label = QLabel("Elapsed Time: 00:00:00")
        queue_container_layout.addWidget(self.timer_label)

        remove_btn = QPushButton("Remove Selected Job")
        remove_btn.clicked.connect(self.remove_selected_job)
        queue_container_layout.addWidget(remove_btn)

        queue_row.addWidget(self.queue_container)
        self.layout.addLayout(queue_row)

        # Connect toggle button and remember state
        self.queue_toggle_btn.clicked.connect(
            lambda: self.toggle_widget(self.queue_container, self.queue_toggle_btn, state_key="queue_visible")
        )

        # Apply saved visibility
        visible = self.ui_state.get("queue_visible", True)
        self.queue_container.setVisible(visible)
        self.queue_toggle_btn.setText("Hide" if visible else "Show")

        # Generate / Queue Controls
        btn_row = QHBoxLayout()
        self.add_queue_btn = QPushButton("Add To Queue")
        self.add_queue_btn.clicked.connect(self.add_job_to_queue)
        self.start_queue_btn = QPushButton("Run Queue")
        self.start_queue_btn.clicked.connect(self.start_queue)
        self.generate_btn = QPushButton("Generate HTML (Immediate)")
        self.generate_btn.clicked.connect(self.generate_html)
        btn_row.addWidget(self.add_queue_btn)
        btn_row.addWidget(self.start_queue_btn)
        btn_row.addWidget(self.generate_btn)
        self.layout.addLayout(btn_row)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.layout.addWidget(self.progress)

        self.load_last_profile()

        # Store the UI states
        self.ui_state = load_ui_state()
        self.apply_ui_state()

        # Populate queue list if jobs were loaded
        for args, out_path in self.job_queue:
            self.queue_list.addItem(str(out_path.name))

        # Timer updates
        self.timer.timeout.connect(self.update_timer)

    def closeEvent(self, event):
        # Save the current job queue regardless of current_job_index
        if self.job_queue:
            save_queue(self.job_queue)
        else:
            QUEUE_FILE.write_text("[]", encoding="utf-8")
        event.accept()

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
        if self.update_checkbox.isChecked(): args_list.append("-u")
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
        self.queue_list.addItem(job_name)
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
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            item.setBackground(QColor("white"))
            item.setForeground(QColor("black"))

        # Highlight current job with border / color
        if self.queue_list.count() > self.current_job_index:
            item = self.queue_list.item(self.current_job_index)
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
            self.html_preview.setPlainText(self.current_output_file.read_text(encoding="utf-8"))

        # Highlight job in green
        if 0 <= self.current_job_index < self.queue_list.count():
            item = self.queue_list.item(self.current_job_index)
            item.setBackground(QColor("#4CAF50"))  # green flash

            # Remove from queue after 700ms
            QTimer.singleShot(700, lambda idx=self.current_job_index: self.remove_job_from_list(idx))

        self.cleanup_worker()

    def on_queue_job_error(self, err):
        self.process_output.append(f"ERROR: {err}")
        if 0 <= self.current_job_index < self.queue_list.count():
            self.queue_list.item(self.current_job_index).setBackground(QColor("red"))
            # Remove errored job after short delay
            QTimer.singleShot(700, lambda idx=self.current_job_index: self.remove_job_from_list(idx))
        self.cleanup_worker()

    def remove_job_from_list(self, index):
        if index < len(self.job_queue):
            self.job_queue.pop(index)
        if index < self.queue_list.count():
            self.queue_list.takeItem(index)
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
        if 0 <= self.current_job_index < self.queue_list.count():
            self.queue_list.item(self.current_job_index).setBackground(QColor("red"))
        self.cleanup_worker()
        self.current_job_index += 1
        self.run_next_job()

    def remove_selected_job(self):
        selected_items = self.queue_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            row = self.queue_list.row(item)
            self.queue_list.takeItem(row)
            # Remove corresponding job from job_queue
            if row < len(self.job_queue):
                self.job_queue.pop(row)
        self.statusBar().showMessage("Selected job(s) removed", 3000)

    def on_error(self, err):
        self.process_output.append(f"ERROR: {err}")
        if 0 <= self.current_job_index < self.queue_list.count():
            self.queue_list.item(self.current_job_index).setBackground(Qt.GlobalColor.red)
        self.cleanup_worker()
        self.current_job_index += 1
        self.run_next_job()

    def update_timer(self):
        self.elapsed_seconds += 1
        h, rem = divmod(self.elapsed_seconds, 3600)
        m, s = divmod(rem, 60)
        self.timer_label.setText(f"Elapsed Time: {h:02}:{m:02}:{s:02}")

    def cleanup_worker(self):
        self.progress.hide()
        self.generate_btn.setEnabled(True)
        self.worker = None
        self.timer.stop()

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
            self.html_preview.setPlainText(self.current_output_file.read_text(encoding="utf-8"))
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

        # Only keep results with valid titles
        items = [f"{title} — ID: {mal_id}" for title, mal_id in results if title]
        if not items:
            QMessageBox.information(self, "No Results", "No matching anime found on MAL.")
            return

        # Show selection dialog
        item, ok = QInputDialog.getItem(
            self,
            "Select Anime",
            "Select anime to use MAL ID:",
            items,
            0,
            False
        )
        if ok and item:
            mal_id = item.split("ID:")[-1].strip()
            # Replace the input field entirely with the selected MAL ID
            self.mal_input.setText(mal_id)

    def on_mal_search_error(self, err):
        self.mal_search_btn.setEnabled(True)
        self.mal_search_btn.setText("Search MAL ID")
        QMessageBox.warning(self, "Search Error", f"Failed to search MAL:\n{err}")


    # ---------------------------
    # UI / Dark Mode / Toggle
    # ---------------------------
    def toggle_dark(self):
        if self.dark_checkbox.isChecked():
            self.setStyleSheet("""
                QWidget { background:#121212; color:#e0e0e0; }
                QLineEdit, QTextEdit { background:#1e1e1e; border:1px solid #444; }
                QPushButton { background:#2a2a2a; padding:6px; }
            """)
        else:
            self.setStyleSheet("")

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
        self.ui_state["queue_visible"] = self.queue_container.isVisible()
        save_ui_state(self.ui_state)

    def apply_ui_state(self):
        self.set_preview_state(self.cmd_preview, self.cmd_toggle_btn, self.ui_state["cmd_preview"])
        self.set_preview_state(self.process_output, self.output_toggle_btn, self.ui_state["process_output"])
        self.set_preview_state(self.html_preview, self.html_toggle_btn, self.ui_state["html_preview"])
        self.set_preview_state(self.queue_container, self.queue_toggle_btn, self.ui_state["queue_visible"])

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
                "dark": self.dark_checkbox.isChecked(),
                "update": self.update_checkbox.isChecked(),
                "disable_auto_update": self.disable_auto_update_checkbox.isChecked(),
            },
            "output_file": self.output_file.text().strip() or "output.txt"
        }

    def write_state(self, state):
        for k, v in state.get("inputs", {}).items():
            self.inputs[k].setText(v)
        self.bd_checkbox.setChecked(state["checks"].get("bd", False))
        self.seasonal_checkbox.setChecked(state["checks"].get("seasonal", False))
        self.crc_checkbox.setChecked(state["checks"].get("crc", False))
        self.kage_checkbox.setChecked(state["checks"].get("kage", False))
        self.dark_checkbox.setChecked(state["checks"].get("dark", False))
        self.update_checkbox.setChecked(state["checks"].get("update", False))
        self.disable_auto_update_checkbox.setChecked(state["checks"].get("disable_auto_update", False))
        self.output_file.setText(state.get("output_file", "output.txt"))

    def show_about(self):
        dark = self.dark_checkbox.isChecked()
        AboutDialog(self, dark_mode=dark).exec()

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
