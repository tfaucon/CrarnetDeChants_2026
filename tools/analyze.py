#!/usr/bin/env python3
"""Parse .smeas to compute per-song linear column length, then bin-pack."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMEAS = ROOT / "build" / "main.smeas"
MAIN = ROOT / "main.tex"
SP_PER_PT = 65536

def pt(sp): return sp / SP_PER_PT

# --- Parse smeas ---
meta = {}
begs, ends = {}, {}
for line in SMEAS.read_text().splitlines():
    parts = line.split("|")
    if parts[0] == "META":
        meta[parts[1]] = parts[2]
    elif parts[0] == "BEG":
        sid, x, y, p = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
        begs[sid] = (p, pt(x), pt(y))
    elif parts[0] == "END":
        sid, x, y, p = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
        ends[sid] = (p, pt(x), pt(y))

def parse_pt(s):
    # "330.05199pt" or "3.0pt plus 2.0pt minus 1.0pt"
    m = re.match(r"([-\d.]+)pt", s.strip())
    return float(m.group(1)) if m else 0.0

textheight = parse_pt(meta["textheight"])
textwidth  = parse_pt(meta["textwidth"])
columnsep  = parse_pt(meta["columnsep"])
paperheight= parse_pt(meta["paperheight"])
versesep   = parse_pt(meta["versesep"])

print(f"# textheight={textheight:.2f}pt textwidth={textwidth:.2f}pt colsep={columnsep:.2f}pt versesep={versesep:.2f}pt")

# --- Parse main.tex + section files to get ordered list of (section, col_count, song_path) ---
main = MAIN.read_text()

# Sections in order with their default column count
# Format: (section_name, tex_file, default_cols)
# parse by scanning main.tex for \input{songs/X} with preceding \songcolumns{N}
sections = []
cur_cols = 2
for line in main.splitlines():
    m = re.match(r"\s*\\songcolumns\{(\d+)\}", line)
    if m:
        cur_cols = int(m.group(1))
        continue
    m = re.match(r"\s*\\input\{songs/(\w+)\}", line)
    if m:
        sections.append((m.group(1), cur_cols))

print(f"# sections: {sections}")

# Now build full song list: for each section, parse songs/{section}.tex
songs = []  # list of (section, col_count, song_path)
for (sec, default_cols) in sections:
    sec_tex = (ROOT / "songs" / f"{sec}.tex").read_text()
    cols = default_cols
    for line in sec_tex.splitlines():
        m = re.match(r"\s*\\songcols\{(\d+)\}", line)
        if m:
            cols = int(m.group(1)); continue
        m = re.match(r"\s*\\songcolumns\{(\d+)\}", line)
        if m:
            cols = int(m.group(1)); continue
        m = re.match(r"\s*\\input\{(songs/\w+/\w+)\}", line)
        if m:
            path = m.group(1)
            # count actual \beginsong occurrences in this file
            content = (ROOT / f"{path}.tex").read_text()
            n = len(re.findall(r"\\beginsong\b", content))
            for _ in range(n):
                songs.append((sec, cols, path))

print(f"# total songs: {len(songs)}")
print(f"# songs per section:")
from collections import Counter
sec_counts = Counter((s[0], s[1]) for s in songs)
for k, v in sec_counts.items(): print(f"#   {k}: {v}")
print(f"# smeas has {len(begs)} BEGs, {len(ends)} ENDs")

# --- Determine page text-area bounds ---
# Text top y = highest observed BEG y on any page
# (we assume first song on a page starts near the top)
# Actually need left_edge per page parity. Observe min x across all begs/ends.
all_x = [x for (p,x,y) in list(begs.values())+list(ends.values())]
all_y = [y for (p,x,y) in list(begs.values())+list(ends.values())]
# Per-page parity left edge
page_min_x = {}
page_max_y = {}
page_min_y = {}
for (p,x,y) in list(begs.values())+list(ends.values()):
    page_min_x[p] = min(page_min_x.get(p, 1e9), x)
    page_max_y[p] = max(page_max_y.get(p, -1e9), y)
    page_min_y[p] = min(page_min_y.get(p, 1e9), y)

# Each page parity gets its own left_edge
odd_lefts = [x for p, x in page_min_x.items() if p % 2 == 1]
even_lefts= [x for p, x in page_min_x.items() if p % 2 == 0]
print(f"# odd-page min x = {min(odd_lefts) if odd_lefts else None}")
print(f"# even-page min x = {min(even_lefts) if even_lefts else None}")

# top_y: highest y seen (across all) → text top
# bottom_y: textheight below top_y
text_top_y = max(all_y)
print(f"# max observed y = {text_top_y:.2f}pt (≈text top)")

def col_layout(ncols, left_edge):
    col_w = (textwidth - (ncols-1)*columnsep) / ncols
    positions = [left_edge + i*(col_w + columnsep) for i in range(ncols)]
    return col_w, positions

def col_index(x, positions, col_w):
    # which column does x belong to?
    for i, px in enumerate(positions):
        if x < px + col_w + columnsep/2 + 1:
            return i
    return len(positions)-1

# Compute linear length per song
song_meta = []  # list of dicts
for i, (sec, ncols, path) in enumerate(songs, start=1):
    if i not in begs or i not in ends:
        print(f"# WARN song {i} {path}: missing BEG/END"); continue
    bp, bx, by = begs[i]
    ep, ex, ey = ends[i]
    # Determine left edge for each page
    bleft = page_min_x.get(bp, bx)
    eleft = page_min_x.get(ep, ex)
    col_w_b, pos_b = col_layout(ncols, bleft)
    col_w_e, pos_e = col_layout(ncols, eleft)
    b_col = col_index(bx, pos_b, col_w_b)
    e_col = col_index(ex, pos_e, col_w_e)

    # top and bottom y per page (approx from observed; use global max y as top, top-textheight as bottom)
    top_y = text_top_y
    bot_y = top_y - textheight

    if bp == ep:
        if b_col == e_col:
            L = by - ey
        else:
            L = (by - bot_y) + (e_col - b_col - 1)*textheight + (top_y - ey)
    else:
        # start page: partial col + remaining full cols on that page
        start_partial = (by - bot_y) + (ncols - 1 - b_col)*textheight
        # full middle pages
        middle = (ep - bp - 1) * ncols * textheight
        # end page: full cols before end_col + partial of end_col
        end_partial = e_col * textheight + (top_y - ey)
        L = start_partial + middle + end_partial

    song_meta.append({
        "id": i, "section": sec, "cols": ncols, "path": path,
        "begin": (bp, b_col, by), "end": (ep, e_col, ey),
        "length_pt": L,
    })

# Print sorted per block
from itertools import groupby
key = lambda d: (d["section"], d["cols"])
song_meta.sort(key=key)
for (sec, ncols), grp in groupby(song_meta, key=key):
    grp = list(grp)
    print(f"\n## Block: {sec} / {ncols}-col, {len(grp)} songs, page_capacity={ncols*textheight:.2f}pt")
    for s in sorted(grp, key=lambda d: -d["length_pt"]):
        frac = s["length_pt"] / (ncols*textheight)
        print(f"  {s['path']:60s}  L={s['length_pt']:7.2f}pt  ({frac*100:5.1f}% of page)")

# Merge consecutive same-path entries (for files containing multiple \beginsong)
merged = []
for s in song_meta:
    if merged and merged[-1]["path"] == s["path"]:
        # extend previous: use earlier begin, later end; add gap + this L
        prev = merged[-1]
        bp, bc, by = prev["begin"]
        ep, ec, ey = s["end"]
        # sum lengths + intersong gap (37pt median)
        prev["length_pt"] = prev["length_pt"] + 37.0 + s["length_pt"]
        prev["end"] = (ep, ec, ey)
        prev["id_end"] = s["id"]
    else:
        s["id_end"] = s["id"]
        merged.append(s)
print(f"# merged song entries: {len(merged)}")
song_meta = merged

# Save for later
import json
(ROOT/"tools"/"songs_meta.json").write_text(json.dumps({
    "meta": meta,
    "textheight": textheight,
    "textwidth": textwidth,
    "columnsep": columnsep,
    "versesep": versesep,
    "songs": song_meta,
}, indent=2))
print(f"\n# wrote tools/songs_meta.json")
