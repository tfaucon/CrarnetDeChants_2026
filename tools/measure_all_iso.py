#!/usr/bin/env python3
"""Measure all songs in 3 isolated compiles (one per col-count)."""
import json, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
MEAS_DIR = ROOT / "build_iso"
MEAS_DIR.mkdir(exist_ok=True)

tw, cs = 483.69687, 12.0
COLW = {n: (tw - (n-1)*cs)/n for n in (2, 3, 4)}
SP_PER_PT = 65536

def collect_songs_by_cols():
    """Return dict {col_count: [path, ...]}."""
    main = (ROOT/"main.tex").read_text()
    sections = []
    cur = 2
    for line in main.splitlines():
        m = re.match(r"\s*\\songcolumns\{(\d+)\}", line)
        if m: cur = int(m.group(1)); continue
        m = re.match(r"\s*\\input\{songs/(\w+)\}", line)
        if m: sections.append((m.group(1), cur))
    by_cols = {}
    for sec, default in sections:
        tex = (ROOT/"songs"/f"{sec}.tex").read_text()
        cols = default
        for line in tex.splitlines():
            m = re.match(r"\s*\\songcols\{(\d+)\}", line)
            if m: cols = int(m.group(1)); continue
            m = re.match(r"\s*\\input\{(songs/\w+/\w+)\}", line)
            if m:
                p = m.group(1)
                # Count beginsong occurrences
                content = (ROOT/f"{p}.tex").read_text()
                n = len(re.findall(r"\\beginsong\b", content))
                for _ in range(n):
                    by_cols.setdefault(cols, []).append(p)
    return by_cols

def run_for_cols(cols, paths):
    """Generate iso_all_{cols}.tex with all paths, compile twice, parse .iso.
    paths may contain duplicates (multi-song file) — input unique only."""
    tmpl = (ROOT/"tools"/"iso_all.tex").read_text()
    unique_paths = []
    for p in paths:
        if p not in unique_paths:
            unique_paths.append(p)
    inputs = []
    for p in unique_paths:
        inputs.append(f"\\input{{{ROOT}/{p}}}\\clearpage")
    tex = tmpl.replace("__COLW__", f"{COLW[cols]:.3f}").replace("__INPUTLIST__", "\n".join(inputs))
    jobname = f"iso_all_{cols}"
    (MEAS_DIR/f"{jobname}.tex").write_text(tex)
    for _ in range(2):
        r = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(MEAS_DIR), str(MEAS_DIR/f"{jobname}.tex")],
            capture_output=True, text=True, cwd=ROOT,
        )
    iso_path = MEAS_DIR/f"{jobname}.iso"
    return iso_path.read_text() if iso_path.exists() else ""

def parse_iso(text):
    """Parse lines: id by ey bp ep  (y values in sp). Return list of (id, by_sp, ey_sp, bp, ep)."""
    out = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5: continue
        try:
            sid = int(parts[0]); by = int(parts[1]); ey = int(parts[2]); bp = int(parts[3]); ep = int(parts[4])
            out.append((sid, by, ey, bp, ep))
        except ValueError: continue
    return out

def main():
    by_cols = collect_songs_by_cols()
    all_lengths = {}
    for cols in sorted(by_cols.keys()):
        paths = by_cols[cols]
        print(f"Measuring {len(paths)} songs at {cols}-col width ({COLW[cols]:.1f}pt)...")
        iso = run_for_cols(cols, paths)
        records = parse_iso(iso)
        print(f"  got {len(records)} measurement records")
        paperheight_sp = int(5000 * SP_PER_PT)
        # match by sequential order (songs appear in their input order)
        # For files with multiple \beginsong, both entries map to same path → sum lengths.
        for i, (sid, by, ey, bp, ep) in enumerate(records):
            if i >= len(paths): break
            path = paths[i]
            if bp == ep:
                L_sp = by - ey
            else:
                L_sp = by + (ep - bp - 1) * paperheight_sp + (paperheight_sp - ey)
            L_pt = L_sp / SP_PER_PT
            entry = all_lengths.setdefault(path, {})
            entry[cols] = entry.get(cols, 0.0) + L_pt
    (ROOT/"tools"/"iso_lengths.json").write_text(json.dumps(all_lengths, indent=2))
    print(f"Wrote iso_lengths.json with {len(all_lengths)} songs")

if __name__ == "__main__":
    main()
