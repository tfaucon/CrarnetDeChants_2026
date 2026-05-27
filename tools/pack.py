#!/usr/bin/env python3
"""Bin-pack songs per block to minimize pages.
Rule:
  - song with L > C must start at top-left (occupies ceil(L/C) pages)
  - song with L <= C must fit entirely on one page (may start mid-page OR top-left)
  - inter-song gap = intersong_gap, added between songs on same page/column
"""
import json, math, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT/"tools"/"songs_meta.json").read_text())
songs = data["songs"]
# Use iso lengths if available (per-column-width intrinsic measurements)
iso = json.loads((ROOT/"tools"/"iso_lengths.json").read_text()) if (ROOT/"tools"/"iso_lengths.json").exists() else {}
# Override length_pt from iso
# Calibration factor: iso measurements are ~25% larger than real layout lengths
# (real doc uses tighter spacing / font metrics than our minimal iso template)
ISO_CAL = 0.78
for s in songs:
    if s["path"] in iso:
        col_key = str(s["cols"])
        if col_key in iso[s["path"]]:
            s["length_pt"] = iso[s["path"]][col_key] * ISO_CAL
textheight = data["textheight"]
intersong_gap = 40.0  # empirically measured ~37pt median, ~49pt max → use 40pt
versesep = data["versesep"]

# Group by (section, cols)
blocks = defaultdict(list)
for s in songs:
    blocks[(s["section"], s["cols"])].append(s)

# For current ordering comparison, compute current pages per block
current_pages_per_block = {}
for key, grp in blocks.items():
    ps = [g["begin"][0] for g in grp] + [g["end"][0] for g in grp]
    current_pages_per_block[key] = (min(ps), max(ps), max(ps)-min(ps)+1)

def pack_block(songs_in_block, ncols):
    """Return (ordered_song_list, estimated_pages).
    Approach:
      - C = ncols * textheight (page capacity as linear length)
      - long: L > C  → each takes ceil(L/C) pages, last page has leftover = span*C - L
      - short: L <= C → bin-pack into leftover bins + fresh bins
    Strategy to place in final order: interleave longs with short fills.
    """
    C = ncols * textheight
    longs = sorted([s for s in songs_in_block if s["length_pt"] > C], key=lambda s: -s["length_pt"])
    shorts = sorted([s for s in songs_in_block if s["length_pt"] <= C], key=lambda s: -s["length_pt"])

    # Compute leftover after each long song (last page remainder)
    long_info = []
    for s in longs:
        L = s["length_pt"]
        span = math.ceil(L/C)
        leftover = span*C - L
        # Any song packed after needs gap first: usable = leftover - intersong_gap if >0
        long_info.append({"song": s, "span": span, "leftover": leftover})

    # Bins to pack into: one bin of size (leftover - intersong_gap) per long song,
    # plus as many fresh bins of size C as needed.
    # We'll use best-fit-decreasing on shorts.

    # Create initial bins list: one per long (with attached "parent_long" reference).
    # Plus we always allow adding fresh bins.
    bins = []
    # Fresh-start bin for block beginning? First song of block should be at top-left.
    # That's naturally enforced by fresh bin = C with no parent.
    # Initial: one fresh bin (first page of block).
    bins.append({"type": "fresh", "remaining": C, "songs": []})

    for li in long_info:
        # each long creates a "long-tail" bin after it
        # we represent a "long" as a pseudo-song placed into its own bin, with remaining = leftover
        bins.append({"type": "long_tail", "long": li, "remaining": li["leftover"], "songs": []})

    # Best-fit-decreasing for shorts
    for s in shorts:
        L = s["length_pt"]
        # find bin with smallest remaining that can fit (L + gap if bin non-empty)
        best_idx = -1
        best_rem = 1e18
        for i, b in enumerate(bins):
            need = L if not b["songs"] else L + intersong_gap
            if b["remaining"] >= need - 0.1:  # small tolerance
                if b["remaining"] < best_rem:
                    best_rem = b["remaining"]
                    best_idx = i
        if best_idx < 0:
            # open a new fresh bin
            bins.append({"type": "fresh", "remaining": C - L, "songs": [s]})
        else:
            b = bins[best_idx]
            gap = intersong_gap if b["songs"] else 0
            b["remaining"] -= L + gap
            b["songs"].append(s)

    # Now linearize: we need a single ordered list of song inputs representing pages.
    # Order: bins in current order (fresh-first, then longs with their trailing shorts),
    # but the first bin must be fresh (block start).
    # Merge: first bin (fresh) with its songs; then for each long-tail bin: output the long song, then its trailing shorts.
    ordered = []
    # first fresh bin
    first = bins[0]
    ordered.extend(first["songs"])
    # long bins in order of longs (as input sorted by -L)
    for i, li in enumerate(long_info):
        b = bins[1+i]
        ordered.append(li["song"])
        ordered.extend(b["songs"])

    # If no longs and no fresh, place any orphaned shorts (shouldn't happen since we added fresh first)
    # Handle extra fresh bins we created during packing (beyond the initial one)
    extra_fresh = [b for b in bins[1+len(long_info):] if b["type"] == "fresh"]
    for b in extra_fresh:
        ordered.extend(b["songs"])

    # Count pages used
    # Pages = fresh bins used + sum of long.span for each long
    fresh_bins_used = sum(1 for b in bins if b["type"] == "fresh" and b["songs"])
    if not fresh_bins_used and not long_info:
        fresh_bins_used = 1  # at least one page
    long_pages = sum(li["span"] for li in long_info)
    total_pages = fresh_bins_used + long_pages

    return ordered, total_pages, bins

print(f"# intersong_gap={intersong_gap}pt  textheight={textheight}pt\n")
total_new = 0
total_current = 0
results = {}
for key in sorted(blocks.keys()):
    sec, ncols = key
    grp = blocks[key]
    ordered, pages, bins = pack_block(grp, ncols)
    cur = current_pages_per_block[key][2]
    total_new += pages
    total_current += cur
    results[f"{sec}_{ncols}col"] = [s["path"] for s in ordered]
    print(f"{sec} / {ncols}-col: {len(grp)} songs  current≈{cur} pages  packed={pages} pages  (Δ={pages-cur:+d})")

print(f"\nTOTAL: current≈{total_current}  packed={total_new}  (Δ={total_new-total_current:+d})")

# Build structured plan per section: list of "pages" each containing songs.
# Between pages, emit \clearpage. Multi-page long songs are represented as
# (long_song, [tail_songs]).
plan = {}
for key in sorted(blocks.keys()):
    sec, ncols = key
    _, _, bins = pack_block(blocks[key], ncols)
    long_info = [b for b in bins if b["type"] == "long_tail"]
    fresh_bins = [b for b in bins if b["type"] == "fresh"]
    # Order: first fresh bin, then interleave long_tails, then extra fresh bins
    items = []  # each item is {"kind": "fresh"|"long", "songs":[...], "long":song|None}
    if fresh_bins and fresh_bins[0]["songs"]:
        items.append({"kind": "fresh", "songs": fresh_bins[0]["songs"]})
    for lt in long_info:
        items.append({"kind": "long", "long": lt["long"]["song"], "songs": lt["songs"]})
    for fb in fresh_bins[1:]:
        if fb["songs"]:
            items.append({"kind": "fresh", "songs": fb["songs"]})
    plan.setdefault(sec, {})[ncols] = items

# Generate new section .tex files
for sec in plan:
    # preserve order of 2-col then 3-col (matching original)
    # Read original to find column order
    orig = (ROOT/"songs"/f"{sec}.tex").read_text().splitlines()
    col_order = []
    seen = set()
    # start col from main.tex default
    if sec == "benedicite":
        cur = 4
    else:
        cur = 2
    if cur not in seen: col_order.append(cur); seen.add(cur)
    for line in orig:
        import re
        m = re.match(r"\s*\\songcols\{(\d+)\}", line)
        if m:
            c = int(m.group(1))
            if c not in seen: col_order.append(c); seen.add(c)

    lines = []
    for idx, ncols in enumerate(col_order):
        if idx > 0:
            lines.append(f"\\songcols{{{ncols}}}")
        items = plan[sec].get(ncols, [])
        first_in_block = True
        for item in items:
            if not first_in_block:
                lines.append("\\clearpage")
            first_in_block = False
            if item["kind"] == "fresh":
                for s in item["songs"]:
                    lines.append(f"\\input{{{s['path']}}}")
            else:  # long
                lines.append(f"\\input{{{item['long']['path']}}}")
                for s in item["songs"]:
                    lines.append(f"\\input{{{s['path']}}}")
    # if original ended with \songcols{2}, preserve that
    if col_order and col_order[-1] != (4 if sec=="benedicite" else 2):
        lines.append(f"\\songcols{{{4 if sec=='benedicite' else 2}}}")
    out_path = ROOT/"songs"/f"{sec}.tex"
    (ROOT/"songs"/f"{sec}.new.tex").write_text("\n".join(lines)+"\n")
print("\n# wrote songs/*.new.tex")
(ROOT/"tools"/"packed_order.json").write_text(json.dumps(results, indent=2))
