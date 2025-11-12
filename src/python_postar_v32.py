#!/usr/bin/env python3
"""
python_postar_v32.py

v32 extended with:
- Added MediaInfo encoding info above episode tables which was missing before
- Fixed the OP/ED filename bug
- Added naming support for extra folders
- Ensured that the sort order is respected and files are labeled correctly
- Added -seasonal to enable a toggle for the sorting order (group vs non-group)
"""

# --- Imports and constants ---
import os, re, json, argparse
from pathlib import Path
from urllib.parse import quote
import requests

try:
    from pymediainfo import MediaInfo
    HAVE_PYMEDIAINFO = True
except Exception:
    HAVE_PYMEDIAINFO = False

B2_SHOWS_BASE = "https://f005.backblazeb2.com/file/noro-27be5839/Shows/"
B2_TORRENTS_BASE = "https://f005.backblazeb2.com/file/noro-27be5839/Torrents/"
FC_LC_PREFIX = "https://fc.lc/st?api=3053afcd9e6bde75550be021b9d8aa183f18d5ae&url="
SPASTE_PREFIX = "https://www.spaste.com/r/LRZdw6?link="
OUO_PREFIX = "https://ouo.io/s/QgcGSmNw?s="
TORRENT_IMAGE = "http://i.imgur.com/CBig9hc.png"
DDL_IMAGE = "http://i.imgur.com/UjCePGg.png"
ENCODER_NAME = "XLordnoro"

KB = 1024
MB = KB * 1024
GB = MB * 1024
PROCESSED_FILE = Path(__file__).with_name("processed.json")

# -----------------------------
# Processed tracking
# -----------------------------
def load_processed():
    if PROCESSED_FILE.exists():
        try: return json.load(open(PROCESSED_FILE, "r", encoding="utf-8"))
        except: return {}
    return {}
def save_processed(data):
    try: open(PROCESSED_FILE, "w", encoding="utf-8").write(json.dumps(data, indent=2))
    except Exception as e: print(f"Warning: could not save processed file ({e})")
def mark_new(folder_basename, episode_label=None):
    data = load_processed()
    show_entry = data.setdefault(folder_basename, {"episodes": [], "batch": False})
    if episode_label is None:
        if not show_entry.get("batch", False):
            show_entry["batch"] = True
            save_processed(data)
            return True
        return False
    else:
        if episode_label not in show_entry["episodes"]:
            show_entry["episodes"].append(episode_label)
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
    Try several patterns to find a real episode number.
    Ignore numbers that are part of release tags or adjacent to letters (e.g. 'Hi10').
    """
    patterns = [
        r'[_\-]\s*(\d{1,3})(?=[_\s\)\[]|$)',                 # -01_ or - 01
        r'episode[ _\-\.]?(\d{1,3})(?=[_\s\)\[]|$)',         # episode01
        r'ep[ _\-\.]?(\d{1,3})(?=[_\s\)\[]|$)',              # ep01
        r'[_\(\[\s](\d{1,3})[_\]\)\s]',                      # (01) or _01_
        r'-(\d{1,3})-',                                      # -01-
        r's?(\d{1,2})e(\d{1,2})'                             # S01E01 or 1E01
    ]
    for p in patterns:
        m = re.search(p, filename, re.IGNORECASE)
        if not m:
            continue
        # find the group index containing digits
        for gi in range(1, len(m.groups()) + 1):
            try:
                span = m.span(gi)
            except:
                continue
            if span == (-1, -1):
                continue
            start = span[0]
            val_str = m.group(gi)
            if not val_str or not val_str.isdigit():
                continue
            # if the char before the matched digits is a letter, skip (handles Hi10 etc)
            if start > 0 and filename[start - 1].isalpha():
                continue
            try:
                val = int(val_str)
            except:
                continue
            if val in (720, 1080) or val >= 1000:
                continue
            return val
    # fallback: look for standalone digit groups but skip ones adjacent to letters
    for mo in re.finditer(r'(\d{1,3})', filename):
        start = mo.start(1)
        if start > 0 and filename[start - 1].isalpha():
            continue
        v = int(mo.group(1))
        if v in (720, 1080) or v >= 1000:
            continue
        return v
    return None
def url_for_show_file(folder_basename: str, filename: str) -> str:
    return B2_SHOWS_BASE + quote(f"{folder_basename}/{filename}", safe="/[]()")
def torrent_url_for_folder(folder_basename: str) -> str:
    return B2_TORRENTS_BASE + quote(f"{folder_basename}.torrent", safe="/[]()")
def safe_txt_filename(folder_path: str) -> str:
    s = sanitize_display_name_from_folder(Path(folder_path).name)
    s = re.sub(r'[<>:"/\\|?*]+', '', s).strip()
    return (s if s else "output") + ".txt"

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

    # Flexible BD detection
    is_bd = bool(re.search(r'bd|blu[-_ ]?ray', folder_lower, re.I)) or \
        bool(re.search(r'bd|blu[-_ ]?ray', mkv_names, re.I))

    has_1080 = "1080" in folder_lower or "1080" in mkv_names
    has_720  = "720" in folder_lower or "720" in mkv_names

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

    title_extra = f"{quality_label}, {audio_label}"
    source_str = f"{ENCODER_NAME} from {subgroup_str}"

    return (
        '<table class="showInfoTable">'
        '<thead>'
        f'<tr><th colspan="2"><span style="color:{heading_color};"><strong>Encoding Settings - {display_name} [{title_extra}]</strong></span></th></tr>'
        '</thead>'
        '<tbody>'
        f'<tr><td>Source</td><td>{source_str}</td></tr>'
        f'<tr><td>Video</td><td>{video_str}</td></tr>'
        f'<tr><td>Audio</td><td>{audio_str}</td></tr>'
        '</tbody></table>'
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
def build_season_block(folder1080: Path, folder720: Path, heading_color: str, season_index: int, mal_id: str, bd_toggle=False, bd_images=None, is_airing=False):
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
        out_lines.extend(build_quality_table(folder1080, mal_info, heading_color, is_airing=is_airing))
        out_lines.append('</div>')
        out_lines.append(f'<div id="{season_id}_season_bd720pane">')
        out_lines.extend(build_quality_table(folder720, mal_info, heading_color, is_airing=is_airing))
        out_lines.append('</div>')
    else:
        # Non-BD normal table
        out_lines.extend(build_quality_table(folder1080, mal_info, heading_color))

    return "\n".join(out_lines)

# -----------------------------
# Non-BD block with MAL synopsis
# -----------------------------
def build_nonbd_block(folder_path: Path, heading_color: str, mal_id: str, is_airing=False):
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
    out_lines.extend(build_quality_table(folder_path, mal_info, heading_color, is_airing=is_airing))
    return "\n".join(out_lines)

# -----------------------------
# Episode tables
# -----------------------------
def build_quality_table(folder_path: Path, mal_info=None, heading_color="#000000", is_airing=False):
    mkv_files = [p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() in (".mkv", ".rar", ".zip")]

    episodes = []
    folder_basename = folder_path.name

    # OP/ED detection
    def is_op_ed(fname: str):
        return bool(re.search(r'(?<![A-Za-z0-9])(OP|ED)[ _-]?\d{1,2}(?![A-Za-z0-9])', fname, re.IGNORECASE))

    def op_ed_label(fname: str):
        m = re.search(r'(OP|ED)[ _-]?\d{1,2}', fname, re.IGNORECASE)
        return m.group(0).upper().replace("_", "").replace("-", "") if m else fname

    # Special detection
    def is_special(name: str, tag: str):
        return bool(re.search(rf'(?<![A-Za-z0-9]){tag}(?:[ _\-]*?(\d{{1,3}}))?(?![A-Za-z0-9])', name, re.IGNORECASE))

    def special_label(name: str, tag: str):
        m = re.search(rf'(?<![A-Za-z0-9]){tag}(?:[ _\-]*?(\d{{1,3}}))?(?![A-Za-z0-9])', name, re.IGNORECASE)
        num = m.group(1) if m else None
        return tag.upper() + (num if num else "")

    def is_extras(name: str):
        return "extras" in name.lower()

    # Generic label extractor that allows full underscore names
    def extract_dash_label(name: str):
        # Capture everything after "-_" up to the next "_(" or end
        # Example: "-_fujimaru_S1_(BD_1080p)" -> "fujimaru_S1"
        # Require at least one letter in the label so pure numeric parts like "-_01" don't match
        m = re.search(r'-_([A-Za-z0-9_]*[A-Za-z][A-Za-z0-9_]*)(?=_\(|$)', name)
        if m:
            label = m.group(1).strip()
            if label:
                return label
        return None

    # Build episodes list
    for p in mkv_files:
        fname = p.name
        fsize = p.stat().st_size

        # Compute dash_label early
        dash_label = extract_dash_label(fname)

        # OP/ED detection first
        if is_op_ed(fname):
            raw = op_ed_label(fname)  # ex: OP1, ED2
            category = "op" if raw.startswith("OP") else "ed"
            label = raw
            epnum = None

        # Specials (OVA/ONA/OAD/SP)
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

        # Extras explicit
        elif is_extras(fname):
            category = "extras"
            label = "Extras"
            epnum = None

        # IMPORTANT: prefer dash_label (when it contains letters) over numeric-episode detection
        elif dash_label:
            # dash_label contains a letter (per extract_dash_label), treat as dash file
            category = "dash"
            label = dash_label.upper()
            epnum = None

        else:
            # Fallback: try numeric episode detection
            epnum = find_episode_number(fname)
            if isinstance(epnum, int):
                category = "episode"
                label = f"{epnum:02d}"
            else:
                category = "extras"
                label = fname
                epnum = None

        # Extract series name for alphabetical grouping
        series_name = re.split(r'_-\s*\d{1,3}', fname)[0].strip()

        episodes.append({
            "series": series_name,
            "filename": fname,
            "size_bytes": fsize,
            "size_human": human_size_bytes(fsize),
            "episode": epnum,
            "label": label,
            "category": category
        })

    # debug print (you can remove this later)
    #for x in episodes:
        #print(x["filename"], "=>", x["category"])

    # --- Sorting logic (switches based on --airing flag) ---
    def build_sorted_episodes(episodes, is_airing=False):
        #print("DEBUG: build_sorted_episodes called with is_airing =", is_airing)
        """
        Sorts episode entries based on whether --airing mode is active.
        Airing mode: group by series, then sort by category and episode number.
        Default: sort all episodes flat by category/episode number only.
        """

        if is_airing:
            #print("DEBUG: Using SERIES-GROUPED sorting")
            # --- Airing mode: grouped by series ---
            def ep_sort_key(item):
                cat = item["category"].lower()
                if cat in ("ova", "oad", "ona", "sp"):
                    cat = "special"

                order = {
                    "episode": 0,   # main episodes first
                    "special": 1,   # then specials
                    "ed": 2,
                    "op": 3,
                    "dash": 4,
                    "extras": 5,
                }

                cat_order = order.get(cat, 999)

                return (
                    item["series"].lower(),
                    cat_order,
                    item.get("episode", 9999),
                    item["filename"].lower(),
                )

            return sorted(episodes, key=ep_sort_key)

        else:
            #print("DEBUG: Using DEFAULT sorting")
            # --- Default mode: not grouped by series ---
            def ep_sort_key(item):
                cat = item["category"].lower()
                if cat in ("ova", "oad", "ona", "sp"):
                    cat = "special"

                order = {
                    "episode": 0,
                    "special": 1,
                    "ed": 2,
                    "op": 3,
                    "dash": 4,
                    "extras": 5,
                }

                cat_order = order.get(cat, 999)

                if cat == "episode":
                    return (cat_order, item.get("episode", 9999))
                else:
                    return (cat_order, item["filename"].lower())

            return sorted(episodes, key=ep_sort_key)

    # --- Sort episodes using airing flag ---
    episodes_sorted = build_sorted_episodes(episodes, is_airing=is_airing)

    # --- HTML generation (unchanged) ---
    total_bytes = sum((p.stat().st_size for p in folder_path.rglob("*") if p.is_file()), 0)
    total_size_str = total_size_gb_str(total_bytes)
    batch_is_new = mark_new(folder_basename)
    batch_sup = "<sup>New</sup>" if batch_is_new else ""
    torrent_path_for_folder = torrent_url_for_folder(folder_basename)
    out_lines = []

    # Batch torrent row
    out_lines.append('<table class="batchLinksTable">')
    out_lines.append(f'<thead><tr><th colspan="5"><span style="color: {heading_color};"><strong>{sanitize_display_name_from_folder(folder_basename)} Batch Torrent</strong></span></th></tr></thead>')
    out_lines.append('<tbody><tr><th>Quality</th><th>Size</th><th>Spaste</th><th>Ouo.io</th><th>Fc.lc</th></tr></tbody>')
    out_lines.append('<tbody><tr>')
    quality_label = "1080p" if "1080" in folder_basename else "720p"
    out_lines.append(f'<td>{quality_label}{batch_sup}</td>')
    out_lines.append(f'<td>{total_size_str}</td>')
    out_lines.append(f'<td><a href="{SPASTE_PREFIX}{torrent_path_for_folder}"><img src="{TORRENT_IMAGE}"></a></td>')
    out_lines.append(f'<td><a href="{OUO_PREFIX}{torrent_path_for_folder}"><img src="{TORRENT_IMAGE}"></a></td>')
    out_lines.append(f'<td><a href="{FC_LC_PREFIX}{torrent_path_for_folder}"><img src="{TORRENT_IMAGE}"></a></td>')
    out_lines.append('</tr></tbody></table>')

    anime_title = mal_info["short_title"] if mal_info else sanitize_display_name_from_folder(folder_path.name)

    # --- BD / Airing button ---
    is_bd = bool(re.search(r'[\(\[]BD_[0-9]{3,4}p[\)\]]', folder_basename, re.IGNORECASE))
    button_title = anime_title if is_bd else f"{anime_title} Airing_BUTTON"

    out_lines.append(f'<p style="text-align:center;">')
    out_lines.append(
        f'<button class="button1" title="Click to Show / Hide Links" type="button" '
        f'onclick="var e=document.getElementById(\'{folder_basename}_hidden\'); e.style.display=(e.style.display==\'none\'?\'\':\'none\')">'
        f'{button_title}</button></p>'
    )
    out_lines.append(f'<div id="{folder_basename}_hidden" style="display:none; align:center">')
    out_lines.append('<table class="showLinksTable"><thead>')
    out_lines.append(f'<tr><th colspan="5"><span style="color: {heading_color};"><strong>{anime_title}</strong></span></th></tr></thead>')
    out_lines.append('<thead><tr><th>Episode</th><th>Size</th><th>Spaste</th><th>Ouo.io</th><th>Fc.lc</th></tr></thead><tbody>')

    for e in episodes_sorted:  # <-- use sorted list
        label = e["label"]
        if mark_new(folder_basename, label):
            label += "<sup>New</sup>"
        file_url = url_for_show_file(folder_basename, e["filename"])
        out_lines.append('<tr>')
        out_lines.append(f'<td>{label}</td>')
        out_lines.append(f'<td>{e["size_human"]}</td>')
        out_lines.append(f'<td><a href="{SPASTE_PREFIX}{file_url}"><img src="{DDL_IMAGE}"></a></td>')
        out_lines.append(f'<td><a href="{OUO_PREFIX}{file_url}"><img src="{DDL_IMAGE}"></a></td>')
        out_lines.append(f'<td><a href="{FC_LC_PREFIX}{file_url}"><img src="{DDL_IMAGE}"></a></td>')
        out_lines.append('</tr>')

    out_lines.append('</tbody></table></div>')
    return out_lines

# -----------------------------
# Build HTML block (modified to use single s2If and add href to donations)
# Also integrated encoding table generation before cover images.
# -----------------------------
def build_html_block(folders1080, folders720, non_bd_folders, mal_ids, span_colors, airing_img, donate_imgs, bd_toggle, bd_images, is_airing=False):
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
        season_block = build_season_block(folder1080, folder720, heading_color, idx, mal_id, bd_toggle, bd_images, is_airing=is_airing)

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
                import re
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
        nonbd_block = build_nonbd_block(folder, heading_color, mal_id, is_airing=is_airing)

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
    parser.add_argument("-o", "--output", help="Output TXT filename (optional)")
    args = parser.parse_args()

    
    # --- DEBUG ---
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
        is_airing=args.seasonal
    )

    out_file = args.output or default_filename
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"TXT generated: {out_file}")

if __name__ == "__main__":
    main()
