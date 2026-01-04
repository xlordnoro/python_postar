from datetime import date
import os, re, json, argparse, io
from pathlib import Path
from urllib.parse import quote
import requests, sys
import zlib, zipfile, shutil, tempfile, subprocess
import textwrap

try:
    from pymediainfo import MediaInfo
    HAVE_PYMEDIAINFO = True
except Exception:
    HAVE_PYMEDIAINFO = False

# ----------------------
# Application base directory (portable-safe, updater-safe)
# ----------------------
if "POSTAR_APP_DIR" in os.environ:
    APP_DIR = Path(os.environ["POSTAR_APP_DIR"]).resolve()
elif getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

# ----------------------
# Settings Loader
# ----------------------
SETTINGS_FILE = Path.cwd() / ".postar_settings.json"

DEFAULT_SETTINGS = {
    "B2_SHOWS_BASE": "",
    "B2_TORRENTS_BASE": "",
    "ENCODER_NAME": "",
    "AUTO_UPDATE": True  # <-- New setting to enable/disable auto-update
}

def load_settings(force_reconfigure=False):
    """Ensure postar_settings.json exists and load settings from it."""

    # If user passed --configure, force a new prompt
    if force_reconfigure:
        settings = prompt_for_settings()
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        print("[Settings] Settings updated.\n")
        return settings
    
    if not SETTINGS_FILE.exists():
        print("[Settings] No settings file found. Creating postar_settings.json...")
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")

        # Prompt user to fill in values
        print("\nPlease enter your Backblaze B2 URLs & encoder name:")
        shows = input("B2_SHOWS_BASE: ").strip()
        torrents = input("B2_TORRENTS_BASE: ").strip()
        encoder = input("ENCODER_NAME: ").strip()
        auto_update = input("Enable auto-update? [Y/n]: ").strip().lower() != "n"

        settings = {
            "B2_SHOWS_BASE": shows,
            "B2_TORRENTS_BASE": torrents,
            "ENCODER_NAME": encoder,
            "AUTO_UPDATE": auto_update
        }

        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        print("[Settings] Settings saved to .postar_settings.json\n")
        return settings

    # Load existing settings
    try:
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        print("[Settings] ERROR: Could not read .postar_settings.json — recreating...")
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
        return load_settings()

    # Validate keys (in case future versions add/remove settings)
    modified = False
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings:
            settings[k] = v
            modified = True
    if modified:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    return settings


# Re-prompt if a user wishes to change their postar settings via -configure instead of editing the .postar_settings.json
def prompt_for_settings():
    print("\n[Settings] Reconfigure postar settings:")
    shows = input("B2_SHOWS_BASE: ").strip()
    torrents = input("B2_TORRENTS_BASE: ").strip()
    encoder = input("ENCODER_NAME: ").strip()
    auto_update = input("Enable auto-update? [Y/n]: ").strip().lower() != "n"

    return {
        "B2_SHOWS_BASE": shows,
        "B2_TORRENTS_BASE": torrents,
        "ENCODER_NAME": encoder,
        "AUTO_UPDATE": auto_update
    }

# Load settings + override globals
SETTINGS = load_settings()
B2_SHOWS_BASE = SETTINGS["B2_SHOWS_BASE"]
B2_TORRENTS_BASE = SETTINGS["B2_TORRENTS_BASE"]
FC_LC_PREFIX = "https://fc.lc/st?api=3053afcd9e6bde75550be021b9d8aa183f18d5ae&url="
SPASTE_PREFIX = "https://www.spaste.com/r/LRZdw6?link="
OUO_PREFIX = "https://ouo.io/s/QgcGSmNw?s="
TORRENT_IMAGE = "http://i.imgur.com/CBig9hc.png"
DDL_IMAGE = "http://i.imgur.com/UjCePGg.png"
ENCODER_NAME = SETTINGS["ENCODER_NAME"]
VERSION = "0.43"

KB = 1024
MB = KB * 1024
GB = MB * 1024
PROCESSED_FILE = APP_DIR / "processed.json"
#print("[Debug] PROCESSED_FILE =", PROCESSED_FILE)

# ----------------------
# Auto-Updater via GitHub release ZIP with backup
# ----------------------
REPO_OWNER = "xlordnoro"
REPO_NAME  = "python_postar"
VERSION_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/VERSION"
ORIGINAL_ARGV = sys.argv.copy()  # Save original arguments for restart

# ----------------------
# Timestamp helpers
# ----------------------
def get_timestamp_file():
    """
    Return path to .postar_update_check file, works for script or PyInstaller.
    """
    return get_base_dir() / ".postar_update_check"

def should_check_update():
    stamp_file = get_timestamp_file()
    if not stamp_file.exists():
        return True
    try:
        last_date = date.fromisoformat(stamp_file.read_text().strip())
    except Exception:
        return True
    return last_date != date.today()

def update_timestamp():
    try:
        get_timestamp_file().write_text(date.today().isoformat())
    except Exception as e:
        print(f"[Update] Warning: could not write timestamp file: {e}")

# ----------------------
# Platform detection
# ----------------------
def detect_platform_zip():
    """Return platform string used in release ZIP naming."""
    if sys.platform.startswith("win"):
        return "windows"
    elif sys.platform.startswith("darwin"):
        return "macos"
    else:
        return "linux"

# ----------------------
# Backup helper
# ----------------------
def backup_file(target_path: Path):
    """Create a backup of the file if it exists."""
    if target_path.exists():
        backup_path = target_path.with_suffix(target_path.suffix + ".backup")
        shutil.copy2(target_path, backup_path)
        print(f"[Update] Backup created: {backup_path}")

# ----------------------
# Portable detection (FINAL)
# ----------------------
def is_portable():
    """
    Detect PyInstaller portable build (Windows / Linux / macOS).
    """
    return getattr(sys, "frozen", False)


def get_base_dir():
    """
    Directory where the app lives and should be updated from.
    """
    return Path(sys.executable).resolve().parent if is_portable() else Path(__file__).resolve().parent


def get_install_type():
    """
    Human-readable install type.
    """
    return "portable" if is_portable() else "source (.py)"

# ----------------------
# Release URL
# ----------------------
def get_release_url(remote_ver: str):
    platform = detect_platform_zip()
    suffix = "_portable" if is_portable() else ""
    zip_name = f"{REPO_NAME}_{platform}_v{remote_ver}{suffix}.zip"
    return f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest/download/{zip_name}"

# ----------------------
# Main auto-update function
# ----------------------
def check_for_github_update(force=False):
    """
    Auto-update for portable EXE or source .py
    - Downloads latest GitHub release ZIP
    - Extracts to temp folder
    - If portable EXE, launches updater batch and exits
    - If source, overwrites files directly and restarts
    """
    global VERSION

    print(f"Installed version : {get_install_type()}")
    print(f"Running from      : {get_base_dir()}")
    print(f"Current version   : {VERSION}")

    if not force:
        if not should_check_update():
            return

    # Always stamp when a check actually runs
    update_timestamp()

    print("[Update] Checking for updates...")

    # ---- Get latest version ----
    try:
        resp = requests.get(VERSION_URL, timeout=5)
        resp.raise_for_status()
        remote_ver = resp.text.strip()
    except Exception as e:
        print(f"[Update] Could not get version info: {e}")
        return

    if remote_ver <= VERSION:
        print("[Update] Already up to date.")
        return

    print(f"[Update] New version {remote_ver} available (current: {VERSION})")

    # ---- Download ZIP ----
    zip_url = get_release_url(remote_ver)
    print(f"[Update] Downloading release ZIP from {zip_url} ...")
    try:
        resp = requests.get(zip_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[Update] Failed to download release ZIP: {e}")
        return

    # ---- Extract to temporary folder ----
    temp_dir = Path(tempfile.mkdtemp())
    print(f"[Update] Preparing to update files in temporary folder {temp_dir} ...")
    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            z.extractall(temp_dir)
    except Exception as e:
        print(f"[Update] Failed to extract ZIP: {e}")
        return

    base_dir = get_base_dir()

    # ---- Portable EXE handling ----
    if is_portable():
        print("[Update] Portable updater launched. Exiting current program...")

        updater_py = base_dir / "update_portable.py"
        python_exe = Path(sys.executable).name
        temp_dir_str = str(temp_dir)
        base_dir_str = str(base_dir)
        original_args = ORIGINAL_ARGV[1:]

        py_text = textwrap.dedent(f'''
            import os
            import sys
            import time
            import shutil
            import subprocess
            from pathlib import Path

            python_exe = "{python_exe}"
            temp_dir = Path(r"{temp_dir_str}")
            base_dir = Path(r"{base_dir_str}")
            original_args = {original_args}

            print(f"[Updater] Waiting for {{python_exe}} to exit...")

            # ---- wait for main EXE to exit ----
            while True:
                try:
                    result = subprocess.run(
                        ["tasklist"],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    if python_exe.lower() not in result.stdout.lower():
                        break
                except Exception:
                    break
                time.sleep(1)

            # ---- detect correct extraction root ----
            entries = list(temp_dir.iterdir())
            if len(entries) == 1 and entries[0].is_dir():
                source_root = entries[0]
            else:
                source_root = temp_dir

            print(f"[Updater] Copying files from {{source_root}}")

            # ---- helper: backup files ----
            def backup_path(p: Path):
                if p.exists():
                    backup = p.with_suffix(p.suffix + ".backup")
                    try:
                        shutil.copy2(p, backup)
                        print(f"[Updater] Backup created: {{backup}}")
                    except Exception as e:
                        print(f"[Updater] Backup failed for {{p}}: {{e}}")

            # ---- BACKUP EXE FIRST ----
            exe_path = base_dir / python_exe
            backup_path(exe_path)

            # ---- copy updated files ----
            for item in source_root.iterdir():
                dest = base_dir / item.name
                try:
                    # Skip EXE (already backed up)
                    if dest.name.lower() == python_exe.lower():
                        print(f"[Updater] Skipping backup for {{dest}} (already done)")
                    elif item.is_file():
                        backup_path(dest)

                    # ---- COPY ----
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)

                except Exception as e:
                    print("[Updater] Copy failed:", e)

            # ---- relaunch app ----
            print("[Updater] Relaunching application...")
            env = os.environ.copy()
            env["POSTAR_APP_DIR"] = str(base_dir)

            subprocess.Popen(
                ["cmd", "/c", "python", str(updater_py)],
                cwd=str(base_dir),
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
            )

            # ---- cleanup ----
            time.sleep(2)
            shutil.rmtree(temp_dir, ignore_errors=True)

            # ---- self delete ----
            updater = Path(sys.argv[0]).resolve()
            subprocess.Popen(
                ["cmd", "/c", "ping 127.0.0.1 -n 2 >nul & del", str(updater)],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        ''')

        # Write updater script
        with open(updater_py, "w", encoding="utf-8") as f:
            f.write(py_text)
            f.flush()
            os.fsync(f.fileno())

        # Launch updater via cmd so python resolves correctly
        subprocess.Popen(
            ["cmd", "/c", "python", str(updater_py)],
            cwd=str(base_dir),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
        )

        sys.exit(0)

    # ---- Source (.py) handling ----
    else:
        base_dir = Path(sys.executable).parent if is_portable() else Path(__file__).resolve().parent
        print(f"[Update] Extracting files directly to {base_dir} ...")
        try:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                for member in z.namelist():
                    if member.endswith("/"):
                        continue  # skip directories

                    parts = Path(member).parts
                    # Remove top-level folder in ZIP
                    relative_path = Path(*parts[1:]) if len(parts) > 1 else Path(*parts)
                    target_path = base_dir / relative_path

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    backup_file(target_path)

                    with z.open(member) as src, open(target_path, "wb") as dst:
                        dst.write(src.read())
                    print(f"[Update] Updated: {target_path}")

            print("[Update] Update complete — restarting with original command...")
            # Restart the main script/exe
            python = sys.executable
            script = Path(sys.executable).resolve() if is_portable() else Path(__file__).resolve().parent / "python_postar.py"
            os.execv(python, [python, str(script), *ORIGINAL_ARGV[1:]])

        except Exception as e:
            print(f"[Update] Failed to extract ZIP: {e}")
            return

# -----------------------------
# Processed tracking
# -----------------------------
def load_processed():
    if PROCESSED_FILE.exists():
        try:
            return json.load(open(PROCESSED_FILE, "r", encoding="utf-8"))
        except:
            return {}
    return {}

def save_processed(data):
    try:
        open(PROCESSED_FILE, "w", encoding="utf-8").write(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Warning: could not save processed file ({e})")

def mark_new(folder_basename, episode_label=None, filename=None):
    """
    Tracks processed episodes by filename and label.
    Handles old entries (strings) for backward compatibility.
    
    folder_basename: str, name of the series/folder
    episode_label: str, episode code like '01', 'SP1', 'ED', etc.
    filename: str, actual filename of the file being processed
    """
    data = load_processed()
    show_entry = data.setdefault(folder_basename, {"episodes": [], "batch": False})

    # Migrate old entries if they are just strings
    for i, ep in enumerate(show_entry["episodes"]):
        if isinstance(ep, str):
            show_entry["episodes"][i] = {"label": ep, "filename": None}

    # Batch marker
    if episode_label is None:
        if not show_entry.get("batch", False):
            show_entry["batch"] = True
            save_processed(data)
            return True
        return False

    if filename is None:
        raise ValueError("mark_new must be called with 'filename' for episodes")

    # Check if this exact filename has already been processed
    already = any(ep.get("filename") == filename for ep in show_entry["episodes"])

    if not already:
        show_entry["episodes"].append({
            "label": episode_label,
            "filename": filename
        })
        save_processed(data)
        return True

    return False

# -----------------------------
# Helpers
# -----------------------------
def human_size_bytes(num_bytes): return f"{num_bytes/GB:.2f} GB" if num_bytes>=GB else f"{int(round(num_bytes/MB))} MB"
def total_size_gb_str(num_bytes): return f"{num_bytes/GB:.2f} GB"
def sanitize_display_name_from_folder(folder_name: str) -> str:
    s = re.sub(r'[\[\(\{][^\]\)\}]*[\]\)\}]', ' ', folder_name)
    s = s.replace('_', ' ').replace('.', ' ')
    return re.sub(r'\s+', ' ', s).strip()

def find_episode_number(filename: str):
    """
    Extract the episode number from the filename.
    Ignores series numbering, resolution numbers (720/1080), CRC hashes, 
    release group tags, and properly handles v1/v2 suffixes.
    """
    ignore_numbers = {720, 1080}

    # Remove all parentheses blocks (CRC, resolution, release group)
    filename_clean = re.sub(r'\([^\)]*\)', '', filename)

    # Focus on part after the last dash
    last_dash_index = filename_clean.rfind('-')
    search_str = filename_clean[last_dash_index + 1:] if last_dash_index != -1 else filename_clean

    # Search for first number (episode) with optional v1/v2
    match = re.search(r'(\d{1,3})(v\d)?', search_str)
    if match:
        val = int(match.group(1))
        if val not in ignore_numbers and val < 1000:
            return val

    # Fallback: last valid number in the whole filename
    matches = re.findall(r'(\d{1,3})(v\d)?', filename_clean)
    for number_str, _ in reversed(matches):
        val = int(number_str)
        if val not in ignore_numbers and val < 1000:
            return val

    return None

def url_for_show_file(folder_basename: str, filename: str) -> str:
    return B2_SHOWS_BASE + quote(f"{folder_basename}/{filename}", safe="/[]()")
def torrent_url_for_folder(folder_basename: str) -> str:
    return B2_TORRENTS_BASE + quote(f"{folder_basename}.torrent", safe="/[]()")
def safe_txt_filename(folder_path: str) -> str:
    s = sanitize_display_name_from_folder(Path(folder_path).name)
    s = re.sub(r'[<>:"/\\|?*]+', '', s).strip()
    return (s if s else "output") + ".txt"

# ----------------------------
# CRC32 Hash Extractor
# ----------------------------
def compute_crc32(path: Path) -> str:
    """Return uppercase 8-digit CRC32."""
    crc = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            crc = zlib.crc32(chunk, crc)
    return f"{crc & 0xffffffff:08X}"   # <-- uppercase

def extract_crc_from_filename(fname: str) -> str | None:
    """
    Match CRC inside brackets: [A1B2C3D4] or [a1b2c3d4]
    """
    m = re.search(r'\[([0-9A-Fa-f]{8})\]', fname)
    return m.group(1).upper() if m else None   # <-- normalize to uppercase

# ----------------------------
# Version Extractor
# ----------------------------
def extract_version_suffix(name: str):
    # Matches 01v2, 05v3, 12v10 etc.
    m = re.search(r'(\d{1,3})(v\d{1,3})', name, re.IGNORECASE)
    return m.group(2).lower() if m else ""

# -----------------------------
# Helper for HTML indentation
# -----------------------------
def append_html(out_lines, line, level=0):
    """Append HTML line with indentation based on nesting level."""
    indent = "    " * level  # 4 spaces per level
    out_lines.append(f"{indent}{line}")

# -----------------------------
# MediaInfo / Encoding Table
# -----------------------------
def detect_source_from_foldername(folder_name: str) -> str:
    tokens = re.findall(r'[\[\(]([^)\]]+)[\]\)]', folder_name)
    groups = []
    for t in tokens:
        for part in re.split(r'[ _\.-]+', t):
            part_clean = part.strip()
            if not part_clean: continue
            if re.search(r'hi10', part_clean, re.I): groups.append('Hi10')
            elif re.search(r'scy', part_clean, re.I): groups.append('SCY')
            elif re.search(r'playcool', part_clean, re.I): groups.append('Playcool')
            elif re.search(r'bd|blu[- ]?ray', part_clean, re.I): groups.append('BD')
            elif re.search(r'eng|jpn|jap|japanese|english', part_clean, re.I): groups.append(part_clean)
            elif re.fullmatch(r'[A-Z0-9]{2,6}', part_clean): groups.append(part_clean)
    seen=[]
    for g in groups:
        if g not in seen: seen.append(g)
    if not seen: return "Unknown"
    if len(seen)==1: return seen[0]
    if len(seen)==2: return f"{seen[0]} from {seen[1]}"
    return f"{seen[0]} from {seen[1]} via {' '.join(seen[2:])}"

def _kbps_from_bitrate(br):
    if not br: return None
    try: return int(int(br)/1000)
    except: 
        try: return int(int(str(br))/1000)
        except: return None

def extract_encoding_info(folder: Path):
    if not HAVE_PYMEDIAINFO:
        return {"source": "Unknown", "video": "Unknown", "audio": [], "crfs": []}  # changed to list

    mkvs = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".mkv"], key=lambda p: p.name.lower())
    if not mkvs:
        return {"source": "Unknown", "video": "Unknown", "audio": [], "crfs": []}

    crfs = set()  # use a set to automatically remove duplicates

    try:
        # Extract CRFs for each MKV
        for mkv in mkvs:
            media_info = MediaInfo.parse(str(mkv))
            video_tracks = [t for t in media_info.tracks if getattr(t, "track_type", "").lower() == "video"]
            v = video_tracks[0] if video_tracks else None
            if v and getattr(v, "encoding_settings", None):
                for part in v.encoding_settings.split(" / "):
                    if part.startswith("crf="):
                        crfs.add(part.split("=")[1])
    except Exception:
        pass

    crfs_sorted = sorted(
    crfs,
    key=lambda x: float(x) if x.replace('.', '', 1).isdigit() else 0,
    reverse=True  # sort descending
    )

    # Video
    v = None
    try:
        media_info = MediaInfo.parse(str(mkvs[0]))
        video_tracks = [t for t in media_info.tracks if getattr(t, "track_type", "").lower() == "video"]
        v = video_tracks[0] if video_tracks else None
    except Exception:
        pass
    codec = getattr(v, "format", None) or getattr(v, "codec", None) if v else None
    depth = getattr(v, "bit_depth", None) if v else None
    video_str = " ".join([f"{depth}-bit" if depth else "", f"via {codec}" if codec else ""]).strip() or "Unknown"

    # Audio
    audio_tracks = []
    try:
        audio_tracks_all = [t for t in media_info.tracks if getattr(t, "track_type", "").lower() == "audio"]
        for a in audio_tracks_all:
            codec = getattr(a, "format", None) or getattr(a, "codec", None) or "Audio"
            lang = getattr(a, "language", None) or getattr(a, "language_string", None) or "und"
            br = getattr(a, "bit_rate", None)
            kbps = _kbps_from_bitrate(br)
            audio_tracks.append({"lang": lang.upper(), "codec": codec, "kbps": kbps})
    except Exception:
        pass

    # Source
    source = extract_subgroup_from_filenames(mkvs[0].name) if mkvs else "Unknown"

    return {"source": source, "video": video_str, "audio": audio_tracks, "crfs": crfs_sorted}

def extract_subgroup_from_filenames(filenames: list[str]) -> str:
    """
    Extract primary sources and all unique subgroups from multiple filenames.
    Returns a string like: "XLordnoro from Hi10 via Cunnysaurus | SCY | Asakura"
    """
    sources = []
    subgroups = []

    for fname in filenames:
        tokens = re.findall(r'\(([^)]+)\)', fname)
        if not tokens:
            continue

        primary_source = tokens[0].strip()
        if primary_source not in sources:
            sources.append(primary_source)

        for t in reversed(tokens[1:]):
            t_clean = t.strip()
            if re.fullmatch(r'BD(_1080p)?|1080p|720p', t_clean, re.I):
                continue
            if re.fullmatch(r'[0-9A-F]{4,8}', t_clean, re.I):
                continue
            if t_clean.lower() in ("duala"):
                continue
            if t_clean not in subgroups:
                subgroups.append(t_clean)
            break  # only take the last valid subgroup in each filename

    source_str = " | ".join(sources) if sources else "Unknown"
    if subgroups:
        return f"{source_str} via {' | '.join(subgroups)}"
    return source_str


def build_encoding_table(folder_path: Path, display_name: str, heading_color: str):
    info = extract_encoding_info(folder_path)
    mkvs = sorted([p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() == ".mkv"], key=lambda p: p.name.lower())
    subgroup_str = extract_subgroup_from_filenames([m.name for m in mkvs]) if mkvs else "Unknown"

    # Video
    video_str = info.get("video", "Unknown").replace("HEVC", "x265")

    # Add CRF list
    crfs = info.get("crfs", [])
    if crfs:
        video_str += " @ crf " + " | ".join(crfs)

    # Audio
    audio_tracks = info.get("audio", [])
    if not audio_tracks:
        audio_str = "Unknown"
        audio_label = "Single Audio"
    else:
        audio_label = "Single Audio" if len(audio_tracks) == 1 else "Dual Audio"
        audio_entries = []
        for t in audio_tracks:
            kbps_str = f"{t['kbps']} kbps" if t['kbps'] else "~? kbps"
            audio_entries.append(f"{t['lang']} {t['codec']} @ {kbps_str}")
        audio_str = f"{audio_label} via " + " | ".join(audio_entries)

    # --- Quality Detection ---
    folder_lower = folder_path.name.lower()
    mkv_names = " ".join([m.name.lower() for m in mkvs]) if mkvs else ""

    # --- Tag-based BD detection ---
    m = re.search(r'[\(\[](?P<val>.*?)[\)\]]$', folder_lower)
    tag = m.group(1) if m else ""
    tag = tag.lower()

    is_bd     = "bd" in tag
    has_1080  = "1080" in tag
    has_720   = "720" in tag

    #print("BT-QUALITY CHECK:", folder_lower, "BD?", is_bd)  # <-- here, inside processing

    if is_bd and has_1080:
        quality_label = "BD 1080p"
    elif is_bd and has_720:
        quality_label = "BD 720p"
    elif has_1080:
        quality_label = "1080p"
    elif has_720:
        quality_label = "720p"
    else:
        quality_label = "Unknown Quality"

    #print("Quality label:", quality_label)  # optional

    title_extra = f"{quality_label}, {audio_label}"
    source_str = f"{ENCODER_NAME} from {subgroup_str}"

    return (
        '<table class="showInfoTable">\n'
        '<thead>\n'
        '<tr>\n'
        f'<th colspan="2"><span style="color:{heading_color};"><strong>Encoding Settings - {display_name} [{title_extra}]</strong></span></th>\n'
        '</tr>\n'
        '</thead>\n'
        '<tbody>\n'
        f'<tr>\n<td>Source</td>\n<td>{source_str}</td>\n</tr>\n'
        f'\t<tr>\n\t<td>Video</td>\n\t<td>{video_str}</td>\n\t</tr>\n'
        f'\t<tr>\n\t<td>Audio</td>\n\t<td>{audio_str}</td>\n\t</tr>\n'
        '</tbody>\n'
        '</table>'
    )

# -----------------------------
# MAL retrieval
# -----------------------------
def get_mal_info(mal_id: str) -> dict:
    try:
        r = requests.get(f"https://api.jikan.moe/v4/anime/{mal_id}")
        r.raise_for_status()
        data = r.json().get("data", {})
        title = data.get("title", "Unknown Title")
        title_jp = data.get("title_japanese", "")
        full_title = f"{title}" if not title_jp else f"{title}"
        season = data.get("season", "")
        year = data.get("year", "")
        season_info = f"{season.capitalize()} {year}" if season and year else ""
        synopsis = data.get("synopsis", "No synopsis available.").replace("\n", " ").strip()
        return {
            "short_title": title,
            "full_title": full_title,
            "season_info": season_info,
            "synopsis": synopsis
        }
    except Exception as e:
        print(f"Warning: Could not fetch MAL {mal_id}: {e}")
        return {
            "short_title": f"Anime {mal_id}",
            "full_title": f"Anime {mal_id}",
            "season_info": "",
            "synopsis": "No synopsis available."
        }

# Export all functions to the main file
__all__ = [
    # Version / constants
    "VERSION",
    "KB", "MB", "GB",
    "FC_LC_PREFIX", "SPASTE_PREFIX", "OUO_PREFIX",
    "TORRENT_IMAGE", "DDL_IMAGE",
    "ENCODER_NAME",

    # Settings
    "load_settings",
    "prompt_for_settings",
    "SETTINGS",
    "B2_SHOWS_BASE",
    "B2_TORRENTS_BASE",

    # Update system
    "check_for_github_update",

    # Process tracking
    "load_processed",
    "save_processed",
    "mark_new",

    # Generic helpers
    "human_size_bytes",
    "total_size_gb_str",
    "sanitize_display_name_from_folder",
    "find_episode_number",
    "extract_version_suffix",
    "extract_crc_from_filename",
    "safe_txt_filename",
    "append_html",

    # URLs
    "url_for_show_file",
    "torrent_url_for_folder",

    # CRC
    "compute_crc32",

    # Encoding / MediaInfo
    "detect_source_from_foldername",
    "extract_encoding_info",
    "build_encoding_table",

    # MAL
    "get_mal_info",
]
