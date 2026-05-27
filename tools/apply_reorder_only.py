#!/usr/bin/env python3
"""Write section .tex files using packer order but WITHOUT \\clearpage markers."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
order = json.loads((ROOT/"tools"/"packed_order.json").read_text())

# group by section, preserving col block order
# order keys: 'sgdf_2col', 'sgdf_3col', etc.
from collections import defaultdict
sec_blocks = defaultdict(list)
for key, songs_list in order.items():
    sec, col = key.rsplit("_", 1)
    col = int(col.replace("col",""))
    sec_blocks[sec].append((col, songs_list))

for sec, blocks in sec_blocks.items():
    default_col = 4 if sec == "benedicite" else 2
    # sort blocks: default_col first, then others
    blocks.sort(key=lambda x: (x[0] != default_col, x[0]))
    lines = []
    for i, (col, songs) in enumerate(blocks):
        if i > 0:
            lines.append(f"\\songcols{{{col}}}")
        for s in songs:
            lines.append(f"\\input{{{s}}}")
    # restore default col at end (if last block wasn't default)
    if blocks and blocks[-1][0] != default_col:
        lines.append(f"\\songcols{{{default_col}}}")
    (ROOT/"songs"/f"{sec}.tex").write_text("\n".join(lines)+"\n")
print("reorder applied (no clearpage)")
