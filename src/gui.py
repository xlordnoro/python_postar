import sys
import json
from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QComboBox, QProgressBar,
    QDialog, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import subprocess

PROFILE_FILE = Path("postar_profiles.json")
SETTINGS_FILE = Path("postar_last_profile.json")

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
# About Dialog
# ---------------------------
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setWindowIcon(QIcon("icon.ico"))
        self.setFixedSize(420, 260)

        layout = QVBoxLayout(self)
        title = QLabel(f"<h2>{APP_NAME}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info = QLabel(
            f"""
            <b>Version:</b> {APP_VERSION}<br>
            <b>Release:</b> {APP_VERSION_NAME}<br><br>
            <b>Author:</b> {APP_AUTHOR}<br>
            <b>Website:</b> <a href="{APP_WEBSITE}">{APP_WEBSITE}</a>
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
            folder = Path(__file__).parent
            exe_path = folder / "python_postar.exe"
            py_path = folder / "python_postar.py"
            if exe_path.exists():
                main_cmd = [str(exe_path)]
            elif py_path.exists():
                main_cmd = [sys.executable, str(py_path)]
            else:
                raise FileNotFoundError("Neither python_postar.exe nor python_postar.py was found.")
            cmd = main_cmd + self.args_list
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
            self.inputs[label] = self.add_input(label)

        # Checkboxes
        self.bd_checkbox = QCheckBox("Enable BD toggle")
        self.seasonal_checkbox = QCheckBox("Seasonal / Airing style")
        self.crc_checkbox = QCheckBox("Include CRC32 column")
        self.kage_checkbox = QCheckBox("Kage Layout")
        self.dark_checkbox = QCheckBox("Dark Mode")
        self.update_checkbox = QCheckBox("Manually check for updates (-u)")
        self.disable_auto_update_checkbox = QCheckBox("Disable auto-update (-du)")
        for cb in (
            self.bd_checkbox,
            self.seasonal_checkbox,
            self.crc_checkbox,
            self.kage_checkbox,
            self.dark_checkbox,
            self.update_checkbox,
            self.disable_auto_update_checkbox,
        ):
            self.layout.addWidget(cb)
        self.dark_checkbox.stateChanged.connect(self.toggle_dark)

        # Output file
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output HTML File"))
        self.output_file = QLineEdit("output.txt")
        out_row.addWidget(self.output_file)
        self.layout.addLayout(out_row)

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

        # Generate
        self.generate_btn = QPushButton("Generate HTML")
        self.generate_btn.clicked.connect(self.generate_html)
        self.layout.addWidget(self.generate_btn)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.layout.addWidget(self.progress)

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
        html_header.addWidget(html_label)
        html_header.addStretch()
        html_header.addWidget(self.html_toggle_btn)
        html_row.addLayout(html_header)
        html_row.addWidget(self.html_preview)
        self.layout.addLayout(html_row)

        self.load_last_profile()

    # ---------------------------
    # Toggle helper
    # ---------------------------
    def toggle_widget(self, widget, button):
        if widget.isVisible():
            widget.hide()
            button.setText("Show")
        else:
            widget.show()
            button.setText("Hide")

    # ---------------------------
    # UI helpers
    # ---------------------------
    def add_input(self, label):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        edit = DragDropLineEdit()
        row.addWidget(edit)
        self.layout.addLayout(row)
        return edit

    # ---------------------------
    # HTML generation
    # ---------------------------
    def generate_html(self):
        self.generate_btn.setEnabled(False)
        self.progress.show()
        self.process_output.clear()
        self.html_preview.clear()

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

        out_path = Path(self.output_file.text().strip() or "output.txt")
        args_list += ["-o", str(out_path)]
        self.current_output_file = out_path

        # Determine main command for preview
        folder = Path(__file__).parent
        exe_path = folder / "python_postar.exe"
        py_path = folder / "python_postar.py"
        if exe_path.exists():
            main_cmd_preview = ["python_postar.exe"]
        elif py_path.exists():
            main_cmd_preview = ["python", str(py_path)]
        else:
            main_cmd_preview = ["python", "python_postar.py"]

        self.cmd_preview.setPlainText(
            " ".join(f'"{c}"' if " " in c else c for c in main_cmd_preview + args_list)
        )

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
    # Dark mode
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
        AboutDialog(self).exec()

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
