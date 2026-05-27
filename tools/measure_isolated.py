#!/usr/bin/env python3
"""Compile each song alone at target column width; parse .iso sidecar to get intrinsic height."""
import json, re, subprocess, sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parent.parent
MEAS_DIR = ROOT / "build_iso"
MEAS_DIR.mkdir(exist_ok=True)

# Column widths for each column count
tw, cs = 483.69687, 12.0
COLW = {n: (tw - (n-1)*cs)/n for n in (2, 3, 4)}

TEMPLATE = (ROOT/"tools"/"iso_template.tex").read_text()

def song_paths_and_cols():
    """Build list of (cols, path) for every unique song file referenced in the current layout."""
    main = (ROOT/"main.tex").read_text()
    sections = []
    cur = 2
    for line in main.splitlines():
        m = re.match(r"\s*\\songcolumns\{(\d+)\}", line)
        if m: cur = int(m.group(1)); continue
        m = re.match(r"\s*\\input\{songs/(\w+)\}", line)
        if m: sections.append((m.group(1), cur))
    seen = {}
    for sec, default in sections:
        tex = (ROOT/"songs"/f"{sec}.tex").read_text()
        cols = default
        for line in tex.splitlines():
            m = re.match(r"\s*\\songcols\{(\d+)\}", line)
            if m: cols = int(m.group(1)); continue
            m = re.match(r"\s*\\input\{(songs/\w+/\w+)\}", line)
            if m:
                p = m.group(1)
                if p not in seen:
                    seen[p] = cols
    return seen

def compile_one(args):
    i, cols, path = args
    colw = COLW[cols]
    tex = TEMPLATE.replace("__COLW__", f"{colw:.3f}").replace("__SONGFILE__", f"{ROOT}/{path}")
    jobname = f"iso_{i:03d}"
    (MEAS_DIR/f"{jobname}.tex").write_text(tex)
    for _ in range(2):
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(MEAS_DIR), str(MEAS_DIR/f"{jobname}.tex")],
            capture_output=True, text=True, cwd=ROOT,
        )
    iso = MEAS_DIR/f"{jobname}.iso"
    if not iso.exists():
        return path, None, "no-iso"
    line = iso.read_text().strip()
    m = re.match(r"ABSP (\d+) STARTY ([-\d.]+)pt ENDY ([-\d.]+)pt PAPERH ([\d.]+)pt", line)
    if not m:
        return path, None, f"badline: {line}"
    absp = int(m.group(1)); sy = float(m.group(2)); ey = float(m.group(3)); ph = float(m.group(4))
    # Height = page-used content. Page is ultra-tall; if absp=1, just sy-ey.
    # If absp>1, song broke to page 2; add (absp-1)*ph (unlikely with 2500pt)
    L = sy - ey + (absp - 1) * ph
    return path, {"cols": cols, "length_pt": L, "absp": absp, "sy": sy, "ey": ey}, None

def main():
    paths = song_paths_and_cols()
    items = [(i, cols, p) for i, (p, cols) in enumerate(paths.items())]
    print(f"Measuring {len(items)} songs...")
    results = {}
    errors = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(compile_one, it): it for it in items}
        done = 0
        for fut in as_completed(futures):
            path, res, err = fut.result()
            done += 1
            if res:
                results[path] = res
            else:
                errors.append((path, err))
            if done % 20 == 0:
                print(f"  {done}/{len(items)}")
    (ROOT/"tools"/"iso_lengths.json").write_text(json.dumps(results, indent=2))
    print(f"OK: {len(results)}, errors: {len(errors)}")
    for p, e in errors[:10]:
        print(f"  FAIL {p}: {e}")

if __name__ == "__main__":
    main()
