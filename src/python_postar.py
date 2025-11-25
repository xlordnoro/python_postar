#!/usr/bin/env python3
"""
python_postar.py

v37.1:
- Fixed a regex issue which was causing the resolution to not be grabbed on folders with () for the resolution
"""

# --- Imports and constants ---
from datetime import date
import os, re, json, argparse
from pathlib import Path
from urllib.parse import quote
import requests, sys
import zlib
import re

try:
    from pymediainfo import MediaInfo
    HAVE_PYMEDIAINFO = True
except Exception:
    HAVE_PYMEDIAINFO = False

# ----------------------
# Settings Loader
# ----------------------
SETTINGS_FILE = Path.cwd() / ".postar_settings.json"

DEFAULT_SETTINGS = {
    "B2_SHOWS_BASE": "",
    "B2_TORRENTS_BASE": "",
    "ENCODER_NAME": ""
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

        settings = {
            "B2_SHOWS_BASE": shows,
            "B2_TORRENTS_BASE": torrents,
            "ENCODER_NAME": encoder
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

    return {
        "B2_SHOWS_BASE": shows,
        "B2_TORRENTS_BASE": torrents,
        "ENCODER_NAME": encoder
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
VERSION = "0.37.1"

KB = 1024
MB = KB * 1024
GB = MB * 1024
PROCESSED_FILE = Path(__file__).with_name("processed.json")

# ----------------------
# Auto-Updater
# ----------------------
VERSION_URL = "https://raw.githubusercontent.com/xlordnoro/python_postar/main/VERSION"
SCRIPT_URL  = "https://raw.githubusercontent.com/xlordnoro/python_postar/main/src/python_postar.py"

# Timestamp file stored next to the script
def get_timestamp_file():
    script_path = Path(__file__).resolve()
    return script_path.parent / ".postar_update_check"


def should_check_update():
    stamp_file = get_timestamp_file()

    if not stamp_file.exists():
        return True  # no file → check now

    try:
        last_date_str = stamp_file.read_text().strip()
        last_date = date.fromisoformat(last_date_str)
    except:
        return True  # corrupt file → check now

    # If it's a different day → check
    return last_date != date.today()


def update_timestamp():
    stamp_file = get_timestamp_file()
    stamp_file.write_text(date.today().isoformat())


def check_for_github_update():
    # Only run once per day
    if not should_check_update():
        return
    update_timestamp()

    print("[Update] Checking for updates...")

    try:
        resp = requests.get(VERSION_URL, timeout=5)
        resp.raise_for_status()
        remote_ver = resp.text.strip()
    except Exception as e:
        print(f"[Update] Could not get version info: {e}")
        return

    if remote_ver <= VERSION:
        return  # Already up to date

    print(f"[Update] New version {remote_ver} available (current: {VERSION})")
    print("[Update] Downloading updated script...")

    try:
        script_resp = requests.get(SCRIPT_URL, timeout=5)
        script_resp.raise_for_status()
    except Exception as e:
        print(f"[Update] Failed to download script: {e}")
        return

    script_path = Path(__file__).resolve()
    backup_path = script_path.with_suffix(".backup.py")

    try:
        script_path.replace(backup_path)
    except Exception as e:
        print(f"[Update] Backup failed: {e}")
        return

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_resp.text)
    except Exception as e:
        print(f"[Update] Writing new script failed: {e}")
        return

    print("[Update] Update complete — restart the script.")
    sys.exit(0)

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

# -----------------------------
# BD / season block
# -----------------------------
def build_season_block(folder1080: Path, folder720: Path, heading_color: str, season_index: int, mal_id: str, bd_toggle=False, bd_images=None, is_airing=False, crc_enabled=False):
    idx_name = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]
    season_id = idx_name[season_index] if season_index < len(idx_name) else f"season{season_index + 1}"
    out_lines = []

    mal_info = get_mal_info(mal_id)
    header_title = mal_info["full_title"]
    if mal_info["season_info"]:
        header_title += f" ({mal_info['season_info']})"

    if not globals().get("_s2if_opened", False):
        out_lines.append('[s2If is_user_logged_in()]')
        globals()["_s2if_opened"] = True

    # Synopsis table
    out_lines.append('<table class="kshowSynopsisTable"><thead><tr>')
    out_lines.append(
        f'<th colspan="1"><span style="color: {heading_color};">'
        f'<a style="color: {heading_color};" href="https://myanimelist.net/anime/{mal_id}" target="_blank" rel="noopener noreferrer">'
        f'<strong>{mal_info["short_title"]}</strong></a></span> | {header_title}</th></tr></thead>'
    )
    out_lines.append(f'<tbody><tr><td>{mal_info["synopsis"]}<!--more--></td></tr></tbody></table>')

    # BD toggle buttons
    if bd_toggle:
        bd1080_img = "https://imgur.com/Ho3EZDh.jpg"
        bd720_img = "https://imgur.com/BI8chCK.jpg"
        if bd_images and len(bd_images) > season_index*2:
            bd1080_img = bd_images[season_index*2]
        if bd_images and len(bd_images) > season_index*2 + 1:
            bd720_img = bd_images[season_index*2 + 1]
        out_lines.append('<div style="width: 100%; text-align: center;">')
        out_lines.append(
            f'<div style="margin: 0px 0px 25px 0px; display: infline-flex;">'
            f'<a id="{season_id}_season_bd1080" href="#"><img id="{season_id}_season_bd1080on" src="{bd1080_img}" alt="BD 1080p" style="width:50%;"></a>'
            f'<a id="{season_id}_season_bd720" href="#"><img id="{season_id}_season_bd720on" src="{bd720_img}" alt="BD 720p" style="width:50%;"></a>'
            '</div></div>'
        )
        out_lines.append(f'<div id="{season_id}_season_bd1080pane">')
        out_lines.extend(build_quality_table(folder1080, mal_info, heading_color, is_airing=is_airing, crc_enabled=crc_enabled))
        out_lines.append('</div>')
        out_lines.append(f'<div id="{season_id}_season_bd720pane">')
        out_lines.extend(build_quality_table(folder720, mal_info, heading_color, is_airing=is_airing, crc_enabled=crc_enabled))
        out_lines.append('</div>')
    else:
        # Non-BD normal table
        out_lines.extend(build_quality_table(folder1080, mal_info, heading_color, crc_enabled=crc_enabled))

    return "\n".join(out_lines)

# -----------------------------
# Non-BD block with MAL synopsis
# -----------------------------
def build_nonbd_block(folder_path: Path, heading_color: str, mal_id: str, is_airing=False, crc_enabled=False):
    out_lines = []
    mal_info = get_mal_info(mal_id)
    header_title = mal_info["full_title"]
    if mal_info["season_info"]:
        header_title += f" ({mal_info['season_info']})"

    if not globals().get("_s2if_opened", False):
        out_lines.append('[s2If is_user_logged_in()]')
        globals()["_s2if_opened"] = True

    # Synopsis table
    out_lines.append('<table class="kshowSynopsisTable"><thead><tr>')
    out_lines.append(
        f'<th colspan="1"><span style="color: {heading_color};">'
        f'<a style="color: {heading_color};" href="https://myanimelist.net/anime/{mal_id}" target="_blank" rel="noopener noreferrer">'
        f'<strong>{mal_info["short_title"]}</strong></a></span> | {header_title}</th></tr></thead>'
    )
    out_lines.append(f'<tbody><tr><td>{mal_info["synopsis"]}<!--more--></td></tr></tbody></table>')

    # Episode table
    out_lines.extend(build_quality_table(folder_path, mal_info, heading_color, is_airing=is_airing, crc_enabled=crc_enabled))
    return "\n".join(out_lines)

# -----------------------------
# Episode tables
# -----------------------------
def build_quality_table(folder_path: Path, mal_info=None, heading_color="#000000", is_airing=False, crc_enabled=False):
    mkv_files = [p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() in (".mkv", ".rar", ".zip")]
    episodes = []
    folder_basename = folder_path.name

    # --- Helper functions ---
    def is_op_ed(fname: str):
        return bool(re.search(r'(?<![A-Za-z0-9])(OP|ED)[ _-]?\d{1,2}(?![A-Za-z0-9])', fname, re.IGNORECASE))

    def op_ed_label(fname: str):
        m = re.search(r'(OP|ED)[ _-]?\d{1,2}', fname, re.IGNORECASE)
        return m.group(0).upper().replace("_", "").replace("-", "") if m else fname

    def is_special(name: str, tag: str):
        return bool(re.search(rf'(?<![A-Za-z0-9]){tag}(?:[ _\-]*?(\d{{1,3}}))?(?![A-Za-z0-9])', name, re.IGNORECASE))

    def special_label(name: str, tag: str):
        m = re.search(rf'(?<![A-Za-z0-9]){tag}(?:[ _\-]*?(\d{{1,3}}))?(?![A-Za-z0-9])', name, re.IGNORECASE)
        num = m.group(1) if m else None
        return tag.upper() + (num if num else "")

    def is_extras(name: str):
        return "extras" in name.lower()

    def extract_dash_label(name: str):
        # Original regex but we capture the label
        m = re.search(r'-_([A-Za-z0-9_]*[A-Za-z][A-Za-z0-9_]*)(?=_\(|$)', name)
        if not m:
            return None

        label = m.group(1).strip()

        # Reject things that start with a number → it's an episode, not dash label
        # Examples: 01, 01v2, 12, 24a
        if re.match(r'^\d', label):
            return None

        return label
        return None

    # --- Build episodes list ---
    for p in mkv_files:
        fname = p.name
        fsize = p.stat().st_size
        dash_label = extract_dash_label(fname)

        if is_op_ed(fname):
            raw = op_ed_label(fname)
            category = "op" if raw.startswith("OP") else "ed"
            label = raw
            epnum = None
        elif is_special(fname, "OVA"):
            category = "ova"
            label = special_label(fname, "OVA")
            epnum = None
        elif is_special(fname, "ONA"):
            category = "ona"
            label = special_label(fname, "ONA")
            epnum = None
        elif is_special(fname, "OAD"):
            category = "oad"
            label = special_label(fname, "OAD")
            epnum = None
        elif is_special(fname, "SP"):
            category = "sp"
            label = special_label(fname, "SP")
            epnum = None
        elif is_extras(fname):
            category = "extras"
            label = "Extras"
            epnum = None
        elif dash_label:
            category = "dash"
            label = dash_label.upper()
            epnum = None
        else:
            epnum = find_episode_number(fname)
            if isinstance(epnum, int):
                category = "episode"

                # Detect v2/v3/etc
                ver = extract_version_suffix(fname)

                if ver:
                    label = f"{epnum:02d}{ver}"
                else:
                    label = f"{epnum:02d}"
            else:
                category = "extras"
                label = fname
                epnum = None

        series_name = re.split(r'_-\s*\d{1,3}', fname)[0].strip()
        crc_in_name = extract_crc_from_filename(fname)
        crc_val = crc_in_name if crc_in_name else compute_crc32(p)

        episodes.append({
            "series": series_name,
            "filename": fname,
            "size_bytes": fsize,
            "size_human": human_size_bytes(fsize),
            "episode": epnum,
            "label": label,
            "category": category,
            "crc32": crc_val,
            "crc_from_name": bool(crc_in_name)
        })

    #for x in episodes:
        #print(x["filename"], "=>", x["category"])

    # --- Sorting ---
    def build_sorted_episodes(episodes, is_airing=False):
        if is_airing:
            def ep_sort_key(item):
                cat = item["category"].lower()
                if cat in ("ova", "oad", "ona", "sp"):
                    cat = "special"
                order = {"episode": 0, "special": 1, "ed": 2, "op": 3, "dash": 4, "extras": 5}
                cat_order = order.get(cat, 999)
                return (item["series"].lower(), cat_order, item.get("episode", 9999), item["filename"].lower())
            return sorted(episodes, key=ep_sort_key)
        else:
            def ep_sort_key(item):
                cat = item["category"].lower()
                if cat in ("ova", "oad", "ona", "sp"):
                    cat = "special"
                order = {"episode": 0, "special": 1, "ed": 2, "op": 3, "dash": 4, "extras": 5}
                cat_order = order.get(cat, 999)
                if cat == "episode":
                    return (cat_order, item.get("episode", 9999))
                else:
                    return (cat_order, item["filename"].lower())
            return sorted(episodes, key=ep_sort_key)

    episodes_sorted = build_sorted_episodes(episodes, is_airing=is_airing)

    # --- HTML Generation with proper indentation ---
    total_bytes = sum((p.stat().st_size for p in folder_path.rglob("*") if p.is_file()), 0)
    total_size_str = total_size_gb_str(total_bytes)
    batch_is_new = mark_new(folder_basename)
    batch_sup = "<sup>New</sup>" if batch_is_new else ""
    torrent_path_for_folder = torrent_url_for_folder(folder_basename)
    anime_title = mal_info["short_title"] if mal_info else sanitize_display_name_from_folder(folder_path.name)

    out_lines = []

    # Batch torrent table
    out_lines.append('<table class="batchLinksTable">')
    out_lines.append('    <thead>')
    out_lines.append(f'        <tr><th colspan="5"><span style="color: {heading_color};"><strong>{anime_title} Batch Torrent</strong></span></th></tr>')
    out_lines.append('    </thead>')
    out_lines.append('    <tbody>')
    out_lines.append('        <tr>')
    out_lines.append('            <th>Quality</th>')
    out_lines.append('            <th>Size</th>')
    out_lines.append('            <th>Spaste</th>')
    out_lines.append('            <th>Ouo.io</th>')
    out_lines.append('            <th>Fc.lc</th>')
    out_lines.append('        </tr>')
    out_lines.append('        <tr>')
    quality_label = (
        "BD 1080p" if "bd" in (re.search(r'[\(\[](.*?)[\)\]]$', folder_basename.lower()) or [None,""])[1].lower() 
                      and "1080" in (re.search(r'[\(\[](.*?)[\)\]]$', folder_basename.lower()) or [None,""])[1].lower() else
        "BD 720p"  if "bd" in (re.search(r'[\(\[](.*?)[\)\]]$', folder_basename.lower()) or [None,""])[1].lower() 
                      and "720" in (re.search(r'[\(\[](.*?)[\)\]]$', folder_basename.lower()) or [None,""])[1].lower() else
        "1080p"    if "1080" in (re.search(r'[\(\[](.*?)[\)\]]$', folder_basename.lower()) or [None,""])[1].lower() else
        "720p"     if "720"  in (re.search(r'[\(\[](.*?)[\)\]]$', folder_basename.lower()) or [None,""])[1].lower() else
        "Unknown Quality"
    )
    out_lines.append(f'            <td>{quality_label}{batch_sup}</td>')
    out_lines.append(f'            <td>{total_size_str}</td>')
    out_lines.append(f'            <td><a href="{SPASTE_PREFIX}{torrent_path_for_folder}"><img src="{TORRENT_IMAGE}"></a></td>')
    out_lines.append(f'            <td><a href="{OUO_PREFIX}{torrent_path_for_folder}"><img src="{TORRENT_IMAGE}"></a></td>')
    out_lines.append(f'            <td><a href="{FC_LC_PREFIX}{torrent_path_for_folder}"><img src="{TORRENT_IMAGE}"></a></td>')
    out_lines.append('        </tr>')
    out_lines.append('    </tbody>')
    out_lines.append('</table>')

    # Episodes table toggle
    out_lines.append(f'<p style="text-align:center;">')
    out_lines.append(f'    <button class="button1" title="Click to Show / Hide Links" type="button" onclick="var e=document.getElementById(\'{folder_basename}_hidden\'); e.style.display=(e.style.display==\'none\'?\'\':\'none\')">{anime_title}</button>')
    out_lines.append('</p>')
    out_lines.append(f'<div id="{folder_basename}_hidden" style="display:none; align:center">')
    out_lines.append('    <table class="showLinksTable">')
    out_lines.append('        <thead>')
    out_lines.append(f'            <tr><th colspan="6"><span style="color: {heading_color};"><strong>{anime_title}</strong></span></th></tr>')
    out_lines.append('        </thead>')
    out_lines.append('        <thead>')
    out_lines.append('            <tr>')
    out_lines.append('                <th>Episode</th>')
    out_lines.append('                <th>Size</th>')
    if crc_enabled:
        out_lines.append('                <th>CRC32</th>')
    out_lines.append('                <th>Spaste</th>')
    out_lines.append('                <th>Ouo.io</th>')
    out_lines.append('                <th>Fc.lc</th>')
    out_lines.append('            </tr>')
    out_lines.append('        </thead>')
    out_lines.append('        <tbody>')

    for e in episodes_sorted:
        #print(f"{e['filename']} -> CRC32: {e['crc32']}")
        label = e["label"]
        filename = e["filename"]
        if mark_new(folder_basename, label, filename):
            label += "<sup>New</sup>"
        file_url = url_for_show_file(folder_basename, filename)

        out_lines.append('            <tr>')
        out_lines.append(f'                <td>{label}</td>')
        out_lines.append(f'                <td>{e["size_human"]}</td>')
        if crc_enabled:
            out_lines.append(f'                <td>{e["crc32"]}</td>')
        out_lines.append(f'                <td><a href="{SPASTE_PREFIX}{file_url}"><img src="{DDL_IMAGE}"></a></td>')
        out_lines.append(f'                <td><a href="{OUO_PREFIX}{file_url}"><img src="{DDL_IMAGE}"></a></td>')
        out_lines.append(f'                <td><a href="{FC_LC_PREFIX}{file_url}"><img src="{DDL_IMAGE}"></a></td>')
        out_lines.append('            </tr>')

    out_lines.append('        </tbody>')
    out_lines.append('    </table>')
    out_lines.append('</div>')

    return out_lines

# -----------------------------
# Build HTML block (modified to use single s2If and add href to donations)
# Also integrated encoding table generation before cover images.
# -----------------------------
def build_html_block(folders1080, folders720, non_bd_folders, mal_ids, span_colors, airing_img, donate_imgs, bd_toggle, bd_images, is_airing=False, crc_enabled=False):
    out_lines = []

    # single s2If opens once for all show content
    s2if_opened = False

    # BD seasons
    for idx, folder1080 in enumerate(folders1080):
        folder720 = folders720[idx] if idx < len(folders720) else Path()
        mal_id = mal_ids[idx] if idx < len(mal_ids) else mal_ids[0]
        heading_color = span_colors[idx % len(span_colors)]
        airing_src = airing_img[idx] if isinstance(airing_img, list) and idx < len(airing_img) else airing_img[0] if isinstance(airing_img, list) else airing_img
        display_name = sanitize_display_name_from_folder(folder1080.name)

        # --- Cover image ---
        out_lines.append(f'<a class="coverImage"><img title="{display_name}" src="{airing_src}"></a>')

        # --- Full season block ---
        season_block = build_season_block(folder1080, folder720, heading_color, idx, mal_id, bd_toggle, bd_images, is_airing=is_airing, crc_enabled=crc_enabled)

        # --- 1080p encoding table ---
        enc_1080 = build_encoding_table(folder1080, display_name, heading_color)
        if enc_1080:
            season_block = season_block.replace(
                '<table class="showLinksTable">',
                f'{enc_1080}\n<table class="showLinksTable">', 1
            )

        # --- 720p encoding table inside bd720pane ---
        if folder720.exists():
            enc_720 = build_encoding_table(folder720, display_name, heading_color)
            if enc_720:
                def insert_720_table(match):
                    div_id = match.group(1)
                    div_content = match.group(2)
                    new_content = re.sub(
                        r'(<table class="showLinksTable">)',
                        f'{enc_720}\n\\1',
                        div_content,
                        count=1
                    )
                    return f'<div id="{div_id}">{new_content}</div>'

                season_block = re.sub(
                    r'<div id="([^"]*_bd720pane)">(.*?)</div>',
                    insert_720_table,
                    season_block,
                    flags=re.DOTALL
                )

        out_lines.append(season_block)

    # Non-BD folders
    for idx, folder in enumerate(non_bd_folders):
        heading_color = span_colors[idx % len(span_colors)]
        mal_id = mal_ids[idx % len(mal_ids)]
        airing_src = airing_img[idx] if isinstance(airing_img, list) and idx < len(airing_img) else airing_img
        display_name = sanitize_display_name_from_folder(folder.name)

        # --- Cover image ---
        out_lines.append(f'<a class="coverImage"><img title="{display_name}" src="{airing_src}"></a>')

        # --- Full non-BD block ---
        nonbd_block = build_nonbd_block(folder, heading_color, mal_id, is_airing=is_airing, crc_enabled=crc_enabled)

        # --- Encoding table for non-BD above episodes ---
        enc_table = build_encoding_table(folder, display_name, heading_color)
        if enc_table:
            nonbd_block = nonbd_block.replace(
                '<table class="showLinksTable">',
                f'{enc_table}\n<table class="showLinksTable">', 1
            )

        out_lines.append(nonbd_block)

    # Close single s2If before donations
    out_lines.append('[/s2If]')

    # Donation section
    if donate_imgs:
        out_lines.append(f'<a class="donateImage" href="https://hi10anime.com/?page_id=70"><img src="{donate_imgs[0]}" alt="Please Donate" title="Please Donate"></a>')
        if len(donate_imgs) > 1:
            donate_id = "Donate_Global"
            out_lines.append(
                f'<p style="text-align: center;"><button title="Click to show / hide Donate Banners" type="button" '
                f'onclick="if(document.getElementById(\'{donate_id}\').style.display==\'none\') '
                f'{{document.getElementById(\'{donate_id}\').style.display=\'\'}} '
                f'else{{document.getElementById(\'{donate_id}\').style.display=\'none\'}}">'
                'Donate</button></p>'
            )
            out_lines.append(f'<div id="{donate_id}" style="display:none; align:center">')
            for img in donate_imgs[1:]:
                out_lines.append(f'<a class="donateImage" href="https://hi10anime.com/?page_id=70"><img src="{img}" alt="Please Donate" title="Please Donate"></a>')
            out_lines.append("</div>")

    # JS include
    out_lines.append('<script type="text/javascript" src="https://xlordnoro.github.io/playcools_js_code.js"></script>')

    # Default output filename
    txt_name = safe_txt_filename(str(folders1080[0] if folders1080 else (non_bd_folders[0] if non_bd_folders else "output")))

    return "\n".join(out_lines), txt_name

# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate html posts for hi10anime")
    parser.add_argument("-p1080", nargs="+", help="Paths to BD 1080p anime folders")
    parser.add_argument("-p720", nargs="+", help="Paths to BD 720p anime folders")
    parser.add_argument("--paths", "-p", nargs="+", help="Paths to non-BD anime folders")
    parser.add_argument("--mal-id", "-m", nargs="+", required=True, help="MAL ID(s)")
    parser.add_argument("--span-color", "-c", nargs="+", required=True, help="List of colors for table headings")
    parser.add_argument("--bd", "-b", action="store_true", help="Enable BD 1080p/720p toggle")
    parser.add_argument("--bd-image", "-bi", nargs="+", metavar="BD_IMG", help="BD image URLs in pairs (1080p,720p) per season")
    parser.add_argument("--airing-image", "-a", nargs="+", required=True, help="URL to airing image")
    parser.add_argument("--seasonal", "-s", action="store_true", help="When set, group episodes by series (airing-style)")
    parser.add_argument("--donation-image", "-d", nargs="+", required=True, help="One or more donation image URLs")
    parser.add_argument("--output", "-o", help="Output TXT filename (optional)")
    parser.add_argument("--version", "-v", action="version", version=f"Version: {VERSION}", help="Shows the version of the script")
    parser.add_argument("--crc", "-crc", action="store_true", help="Show CRC32 column in the episode table")
    parser.add_argument("--configure", "-configure", action="store_true", help="Reconfigure postar settings and overwrite postar_settings.json")
    args = parser.parse_args()

    # ----------------------------------------
    # Load settings (with forced reconfigure)
    # ----------------------------------------
    SETTINGS = load_settings(force_reconfigure=args.configure)

    # Override globals after loading settings
    global B2_SHOWS_BASE, B2_TORRENTS_BASE, ENCODER_NAME
    B2_SHOWS_BASE = SETTINGS["B2_SHOWS_BASE"]
    B2_TORRENTS_BASE = SETTINGS["B2_TORRENTS_BASE"]
    ENCODER_NAME = SETTINGS["ENCODER_NAME"]

    # Runs auto-update check on runtime once per day
    check_for_github_update()
    
    # --- DEBUG ---
    #print("DEBUG: args.bd =", args.bd)
    print("DEBUG: --seasonal flag is set to:", args.seasonal)

    output_text, default_filename = build_html_block(
        [Path(p) for p in args.p1080] if args.p1080 else [],
        [Path(p) for p in args.p720] if args.p720 else [],
        [Path(p) for p in args.paths] if args.paths else [],
        args.mal_id,
        args.span_color,
        args.airing_image,
        args.donation_image,
        args.bd,
        args.bd_image,
        is_airing=args.seasonal,
        crc_enabled=args.crc
    )

    out_file = args.output or default_filename
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"TXT generated: {out_file}")

if __name__ == "__main__":
    main()
