#!/usr/bin/env python3
"""
python_postar.py

v43.4:
- Tweaked the version info to include the latest version alongside the current version
- Put the version code into a startup banner as well.
"""

# --- Imports and constants ---
from datetime import date
import time
import sys
import os, re, json, argparse
from pathlib import Path
from helper import *

#ORIGINAL_ARGV = sys.argv.copy()
#if SETTINGS.get("AUTO_UPDATE", True):
    #check_for_github_update()

# -----------------------------
# BD / season block
# -----------------------------
def build_season_block(folder1080: Path, folder720: Path, heading_color: str, season_index: int, mal_id: str, bd_toggle=False, bd_images=None, is_airing=False, crc_enabled=False, kage=False):
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
        out_lines.extend(build_quality_table(folder1080, mal_info, heading_color, is_airing=is_airing, crc_enabled=crc_enabled, kage=kage))
        out_lines.append('</div>')
        out_lines.append(f'<div id="{season_id}_season_bd720pane">')
        out_lines.extend(build_quality_table(folder720, mal_info, heading_color, is_airing=is_airing, crc_enabled=crc_enabled, kage=kage))
        out_lines.append('</div>')
    else:
        # Non-BD normal table
        out_lines.extend(build_quality_table(folder1080, mal_info, heading_color, crc_enabled=crc_enabled, kage=kage))

    # -------------------------
    # REORDER: Batch table vs Button block
    # If bd_toggle/args.bd is True → batch table goes ABOVE the buttons
    # -------------------------
    if bd_toggle:  # or args.bd if passed in directly
        # Find first </table> (end of batch table)
        batch_end = None
        for i, line in enumerate(out_lines):
            if "</table>" in line:
                batch_end = i + 1
                break

        if batch_end:
            batch_block = out_lines[:batch_end]

            # Button block is always the next 2–3 lines (<p> + <div>)
            # We detect the <p> that contains the BD toggle button
            button_start = None
            for i in range(batch_end, len(out_lines)):
                if "<p" in out_lines[i] and "hide" in out_lines[i]:
                    button_start = i
                    break

            if button_start:
                # button block = <p>...</p> AND <div ...>
                button_block = out_lines[button_start:button_start + 2]
                episode_block = out_lines[button_start + 2:]

                # Rebuild in the new order
                out_lines[:] = batch_block + button_block + episode_block

    return "\n".join(out_lines)

# -----------------------------
# Non-BD block with MAL synopsis
# -----------------------------
def build_nonbd_block(folder_path: Path, heading_color: str, mal_id: str, is_airing=False, crc_enabled=False, kage=False):
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
    out_lines.extend(build_quality_table(folder_path, mal_info, heading_color, is_airing=is_airing, crc_enabled=crc_enabled, kage=kage))
    return "\n".join(out_lines)

# -----------------------------
# Episode tables
# -----------------------------
def build_quality_table(folder_path: Path, mal_info=None, heading_color="#000000", is_airing=False, crc_enabled=False, kage=False):
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

    def is_movie(name: str):
        return bool(re.search(r'(?<![A-Za-z0-9])movie(?![A-Za-z0-9])', name, re.IGNORECASE))

    def extract_special_label(name: str):
        """
        Extracts full special label for OVA / ONA / OAD / SP
        only when it appears after the '_-_' separator.
        """

        m = re.search(
            r'_-_(?P<label>'
            r'(?P<tag>OVA|ONA|OAD|SP)'
            r'(?:[ _\-]*\d{1,3}(?:\.\d)?)?'
            r'(?:_[^()]+)?'
            r')',
            name,
            re.IGNORECASE
        )

        if not m:
            return None

        return m.group("label").rstrip('_')

    def extract_movie_label(name: str):
        """
        Extracts full movie label, including decimals:
        Movie_08.5_vs_Detective_Conan_Special
        """

        m = re.search(
            r'-_\s*(Movie(?:[ _\-]?\d{1,2}(?:\.\d)?)?(?:_[^_()]+)*)',
            name,
            re.IGNORECASE
        )
        if not m:
            return None

        return m.group(1).rstrip('_')

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
            label = extract_special_label(fname) or "OVA"
            epnum = None
        elif is_special(fname, "ONA"):
            category = "ona"
            label = extract_special_label(fname) or "ONA"
            epnum = None
        elif is_special(fname, "OAD"):
            category = "oad"
            label = extract_special_label(fname) or "OAD"
            epnum = None
        elif is_special(fname, "SP"):
            category = "sp"
            label = extract_special_label(fname) or "SP"
            epnum = None
        elif is_extras(fname):
            category = "extras"
            label = "Extras"
            epnum = None
        elif is_movie(fname):
            category = "dash"
            movie_dash = extract_movie_label(fname)
            if movie_dash:
                label = movie_dash
            else:
                label = "MOVIE"
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

    # Episodes table (toggle unless -kage is used)
    if not kage:
        out_lines.append('<p style="text-align:center;">')
        out_lines.append(
            f'    <button class="button1" title="Click to Show / Hide Links" '
            f'type="button" '
            f'onclick="var e=document.getElementById(\'{folder_basename}_hidden\'); '
            f'e.style.display=(e.style.display==\'none\'?\'\':\'none\')">'
            f'{anime_title}</button>'
        )
        out_lines.append('</p>')
        out_lines.append(f'<div id="{folder_basename}_hidden" style="display:none; align:center">')
    else:
        # No toggle, no hidden div
        out_lines.append('<div style="align:center">')

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
def build_html_block(folders1080, folders720, non_bd_folders, mal_ids, span_colors, airing_img, donate_imgs, bd_toggle, bd_images, is_airing=False, crc_enabled=False, kage=False):
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
        season_block = build_season_block(folder1080, folder720, heading_color, idx, mal_id, bd_toggle, bd_images, is_airing=is_airing, crc_enabled=crc_enabled, kage=kage)

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

        # ----------------------------------------------------------
        # Build single batch table with BD 1080p and BD 720p
        # ----------------------------------------------------------
        if bd_toggle:
            # Remove any existing batch table for this season
            start_tag = '<table class="batchLinksTable">'
            end_tag = '</table>'
            start_idx = season_block.find(start_tag)
            while start_idx != -1:
                end_idx = season_block.find(end_tag, start_idx)
                if end_idx == -1:
                    break
                season_block = season_block[:start_idx] + season_block[end_idx + len(end_tag):]
                start_idx = season_block.find(start_tag)

            # Build new batch table
            batch_lines = []
            batch_lines.append('<table class="batchLinksTable">')
            batch_lines.append('    <thead>')
            batch_lines.append(f'        <tr><th colspan="5"><span style="color: {heading_color};"><strong>{display_name} Batch Torrent</strong></span></th></tr>')
            batch_lines.append('    </thead>')
            batch_lines.append('    <tbody>')
            batch_lines.append('        <tr>')
            batch_lines.append('            <th>Quality</th>')
            batch_lines.append('            <th>Size</th>')
            batch_lines.append('            <th>Spaste</th>')
            batch_lines.append('            <th>Ouo.io</th>')
            batch_lines.append('            <th>Fc.lc</th>')
            batch_lines.append('        </tr>')
            batch_lines.append('    </tbody>')
            batch_lines.append('    <tbody>')

            # 1080p row
            total_bytes_1080 = sum((p.stat().st_size for p in folder1080.rglob("*") if p.is_file()), 0)
            total_size_1080 = total_size_gb_str(total_bytes_1080)
            torrent_path_1080 = torrent_url_for_folder(folder1080.name)
            batch_lines.append(f'        <tr>')
            batch_lines.append(f'            <td>BD 1080p<sup>{"New" if mark_new(folder1080.name) else ""}</sup></td>')
            batch_lines.append(f'            <td>{total_size_1080}</td>')
            batch_lines.append(f'            <td><a href="{SPASTE_PREFIX}{torrent_path_1080}"><img src="{TORRENT_IMAGE}"></a></td>')
            batch_lines.append(f'            <td><a href="{OUO_PREFIX}{torrent_path_1080}"><img src="{TORRENT_IMAGE}"></a></td>')
            batch_lines.append(f'            <td><a href="{FC_LC_PREFIX}{torrent_path_1080}"><img src="{TORRENT_IMAGE}"></a></td>')
            batch_lines.append(f'        </tr>')

            # 720p row (only if exists)
            if folder720.exists():
                total_bytes_720 = sum((p.stat().st_size for p in folder720.rglob("*") if p.is_file()), 0)
                total_size_720 = total_size_gb_str(total_bytes_720)
                torrent_path_720 = torrent_url_for_folder(folder720.name)
                batch_lines.append(f'        <tr>')
                batch_lines.append(f'            <td>BD 720p<sup>{"New" if mark_new(folder720.name) else ""}</sup></td>')
                batch_lines.append(f'            <td>{total_size_720}</td>')
                batch_lines.append(f'            <td><a href="{SPASTE_PREFIX}{torrent_path_720}"><img src="{TORRENT_IMAGE}"></a></td>')
                batch_lines.append(f'            <td><a href="{OUO_PREFIX}{torrent_path_720}"><img src="{TORRENT_IMAGE}"></a></td>')
                batch_lines.append(f'            <td><a href="{FC_LC_PREFIX}{torrent_path_720}"><img src="{TORRENT_IMAGE}"></a></td>')
                batch_lines.append(f'        </tr>')

            batch_lines.append('    </tbody>')
            batch_lines.append('</table>')

            batch_table = "\n".join(batch_lines)

            # Insert **once** after the synopsis but before the BD buttons
            insert_pos = season_block.find('<div style="width: 100%; text-align: center;">')
            season_block = season_block[:insert_pos] + batch_table + "\n" + season_block[insert_pos:]
                
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
        nonbd_block = build_nonbd_block(folder, heading_color, mal_id, is_airing=is_airing, crc_enabled=crc_enabled, kage=kage)

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

    # ----------------------------------------
    # Donation section (disabled when kage)
    # ----------------------------------------
    if donate_imgs and not kage:
        out_lines.append(
            f'<a class="donateImage" href="https://hi10anime.com/?page_id=70">'
            f'<img src="{donate_imgs[0]}" alt="Please Donate" title="Please Donate">'
            f'</a>'
        )

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
                out_lines.append(
                    f'<a class="donateImage" href="https://hi10anime.com/?page_id=70">'
                    f'<img src="{img}" alt="Please Donate" title="Please Donate">'
                    f'</a>'
                )
            out_lines.append("</div>")

    # ----------------------------------------
    # Kage Discord widget (end of post)
    # ----------------------------------------
    if kage:
        banner_html = ""
        donate_img_html = ""

        if donate_imgs:
            if len(donate_imgs) > 1:
                # First donation image becomes the banner
                banner_html = (
                    '<div style="margin-left: auto; margin-right: auto;">'
                    f'<img src="{donate_imgs[0]}">'
                    '</div>'
                )
                donate_img = donate_imgs[1]
            else:
                # Single donation image stays inside widget
                donate_img = donate_imgs[0]

            donate_img_html = (
                f'<a class="donateImage" href="https://hi10anime.com/?page_id=70">'
                f'<img src="{donate_img}" alt="Please Donate" title="Please Donate" />'
                f'</a>'
            )

        if banner_html:
            out_lines.append(banner_html)

        out_lines.append(
            '<div style="margin-left: auto; margin-right: auto; text-align: center;'
            'padding-top: 10px; padding-bottom: 10px; background-color: #7289da;'
            'border-radius: 10px; color: white; font-weight: 600;'
            'letter-spacing: 1px; font-variant: all-petite-caps;">'
            f'{donate_img_html}'
            'Join us at Discord!'
            '<iframe title="Discord" '
            'src="https://discordapp.com/widget?id=155549815466491904&amp;theme=dark" '
            'style="margin-bottom: -10px" width="100%" height="250"></iframe>'
            '</div>'
        )

    # JS include
    out_lines.append('<script type="text/javascript" src="https://xlordnoro.github.io/playcools_js_code.js"></script>')

    # Default output filename
    txt_name = safe_txt_filename(str(folders1080[0] if folders1080 else (non_bd_folders[0] if non_bd_folders else "output")))

    return "\n".join(out_lines), txt_name

# --------------------
# Metadata Version
# --------------------
def print_version_and_exit():
    tag, title = get_latest_github_release()

    print(f"Current Version   : v{VERSION}")

    if tag and title:
        print(f"Latest Version    : v{tag}")
        print(f"Release Name      : {title}")

    sys.exit(0)

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
    parser.add_argument("--version", "-v", action="store_true", help="Shows the version of the script")
    parser.add_argument("--crc", "-crc", action="store_true", help="Show CRC32 column in the episode table")
    parser.add_argument("--configure", "-configure", action="store_true", help="Reconfigure postar settings and overwrite postar_settings.json")
    parser.add_argument("--kage", "-kage", action="store_true", help="Modifies the post layout to include the discord widget and various minor changes in the layout")
    parser.add_argument("--update", "-u", action="store_true", help="Manually checks updates for postar")
    parser.add_argument("--disable-auto-update", "-du", action="store_true", help="Disable automatic updates permanently")
    args = parser.parse_args()

    # ---- HANDLE UPDATE FIRST ----
    if args.update:
        print("[Update] Manually checking updates...")
        check_for_github_update(force=True)

    # ---- Print Release Version With Metadata ----
    if args.version:
        print_version_and_exit()

    # ----------------------------------------
    # Load settings (with forced reconfigure)
    # ----------------------------------------
    SETTINGS = load_settings(force_reconfigure=args.configure)

    # Daily Auto Update Check
    if SETTINGS.get("AUTO_UPDATE", True) and not args.update and not args.version:
        ORIGINAL_ARGV = sys.argv.copy()
        check_for_github_update()

    # Print the version info of the script on startup    
    print_startup_banner()

    # Override globals after loading settings
    global B2_SHOWS_BASE, B2_TORRENTS_BASE, ENCODER_NAME, AUTO_UPDATE
    B2_SHOWS_BASE = SETTINGS["B2_SHOWS_BASE"]
    B2_TORRENTS_BASE = SETTINGS["B2_TORRENTS_BASE"]
    ENCODER_NAME = SETTINGS["ENCODER_NAME"]
    AUTO_UPDATE = SETTINGS["AUTO_UPDATE"]

    # ---- DISABLE AUTO UPDATES ----
    if args.disable_auto_update:
        SETTINGS["AUTO_UPDATE"] = False
        Path.cwd().joinpath(".postar_settings.json").write_text(
            json.dumps(SETTINGS, indent=2), encoding="utf-8"
        )
        print("[Settings] Auto-update has been disabled.")
    
    # --- DEBUG ---
    #print("DEBUG: args.bd =", args.bd)
    print("DEBUG: --seasonal flag is set to:", args.seasonal)
    start_time = time.perf_counter()

    # Progress message BEFORE writing
    early_out = args.output if args.output else "insert_something_here.txt"
    print(f"Processing TXT: {early_out}")

    def expand_paths(paths):
        folders = []
        for p in paths:
            root = Path(p)
            if root.is_dir():
                folders.extend(discover_media_folders(root))
        return folders

    folders_1080 = expand_paths(args.p1080) if args.p1080 else []
    folders_720  = expand_paths(args.p720) if args.p720 else []
    non_bd       = expand_paths(args.paths) if args.paths else []

    output_text, default_filename = build_html_block(
        folders_1080,
        folders_720,
        non_bd,
        args.mal_id,
        args.span_color,
        args.airing_image,
        args.donation_image,
        args.bd,
        args.bd_image,
        is_airing=args.seasonal,
        crc_enabled=args.crc,
        kage=args.kage
    )

    out_file = args.output or default_filename    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(output_text)

    # Records the time taken to build the html code
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    print(f"{out_file} completed in {elapsed:.3f} seconds")

if __name__ == "__main__":
    main()
