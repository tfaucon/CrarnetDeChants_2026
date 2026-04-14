#!/usr/bin/env python3
"""Split each *.tex file in songs/ into one file per song inside a subdirectory."""
import os
import re
import unicodedata

SONGS_DIR = "songs"
SOURCES = [
    "sgdf.tex",
    "benedicite.tex",
    "coindufeu.tex",
    "coindufeu_anglais.tex",
    "tempsspi.tex",
]


def slugify(text: str) -> str:
    # Strip LaTeX escapes like \oe, \'e, {}, etc.
    text = re.sub(r"\\[a-zA-Z]+\s*", "", text)
    text = text.replace("{", "").replace("}", "")
    # Normalize accents
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text or "song"


SONG_TITLE_RE = re.compile(r"\\beginsong\{([^}]*)\}")


def split_file(src_path: str, out_dir: str) -> list[str]:
    with open(src_path, encoding="utf-8") as f:
        content = f.read()

    # Find all \beginsong ... \endsong blocks (greedy-safe via lazy between matching delims)
    pattern = re.compile(r"(\\beginsong.*?\\endsong)", re.DOTALL)
    matches = list(pattern.finditer(content))
    if not matches:
        return []

    os.makedirs(out_dir, exist_ok=True)
    slugs = []
    used = {}
    for i, m in enumerate(matches, 1):
        block = m.group(1)
        title_match = SONG_TITLE_RE.search(block)
        title = title_match.group(1) if title_match else f"song{i}"
        slug = slugify(title)
        # Prefix with index for stable order
        filename = f"{i:02d}_{slug}.tex"
        # Avoid collisions
        if filename in used:
            filename = f"{i:02d}_{slug}_{used[filename]}.tex"
            used[filename] = used.get(filename, 0) + 1
        used[filename] = 1
        out_path = os.path.join(out_dir, filename)
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(block.rstrip() + "\n")
        slugs.append(filename)
    return slugs


def main():
    for src in SOURCES:
        src_path = os.path.join(SONGS_DIR, src)
        if not os.path.exists(src_path):
            print(f"SKIP (missing): {src_path}")
            continue
        section = os.path.splitext(src)[0]
        out_dir = os.path.join(SONGS_DIR, section)
        files = split_file(src_path, out_dir)
        print(f"{src}: {len(files)} songs -> {out_dir}/")
        # Write an index file that inputs every song
        index_path = os.path.join(SONGS_DIR, section + ".tex")
        with open(index_path, "w", encoding="utf-8") as idx:
            for fn in files:
                base = os.path.splitext(fn)[0]
                idx.write(f"\\input{{songs/{section}/{base}}}\n")


if __name__ == "__main__":
    main()
