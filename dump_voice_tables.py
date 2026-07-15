r"""Regenerate voice_mapping.json from the game exe's embedded voice tables.

The exe stores one filename table per voice group (v002..v913, rv001..rv013) as
fixed 24-byte string slots, in REVERSE playback order. PLAY_VOICE (0x41) args are
(group_id, index) with index 0-based into the reversed (i.e. alphabetical) table.

Usage:  python dump_voice_tables.py [path\to\ch.exe]
Writes voice_mapping.json next to this script (the editor serves it from there).
"""
import re
import os
import sys
import json
import collections

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_EXE = r"E:\ch\1\ch.exe"


def extract(exe_path):
    with open(exe_path, 'rb') as f:
        data = f.read()

    # per-group tables: vNNN\vNNN_xxx_yy.mp3 (24-byte slots, reverse order)
    pat = re.compile(rb'(v\d{3}a?)\\((?:v\d{3}a?)_[0-9a-z_]+\.mp3)', re.I)
    groups = collections.defaultdict(dict)   # folder -> {filename: max offset}
    for m in pat.finditer(data):
        folder = m.group(1).decode().lower()
        fn = m.group(2).decode().lower()
        # dedupe strays (full-path strings elsewhere in the exe): keep max offset,
        # the table region sits above the loose strings
        prev = groups[folder].get(fn, -1)
        if m.start() > prev:
            groups[folder][fn] = m.start()

    # rv tables: full data\sound\voice\rvNNN\... paths, also reverse order
    rvpat = re.compile(rb'data\\sound\\voice\\(rv\d{3})\\((?:rv\d{3})_[0-9a-z_]+\.mp3)', re.I)
    for m in rvpat.finditer(data):
        folder = m.group(1).decode().lower()
        fn = m.group(2).decode().lower()
        prev = groups[folder].get(fn, -1)
        if m.start() > prev:
            groups[folder][fn] = m.start()

    mapping = {}
    warnings = []
    for folder, entries in sorted(groups.items()):
        # playback order = exe offset DESCENDING (tables are stored reversed)
        ordered = [fn for fn, off in sorted(entries.items(), key=lambda kv: -kv[1])]
        if ordered != sorted(ordered):
            warnings.append(folder)
        if folder.startswith('rv'):
            key = folder                          # rv001 .. rv013
        elif folder[-1] == 'a':
            key = str(int(folder[1:-1])) + 'a'    # v002a -> "2a"
        else:
            key = str(int(folder[1:]))            # v003  -> "3"
        mapping[key] = ordered
    return mapping, warnings


def main():
    exe = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXE
    if not os.path.exists(exe):
        print(f"exe not found: {exe}")
        sys.exit(1)
    mapping, warnings = extract(exe)
    out = os.path.join(BASE_DIR, 'voice_mapping.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=1)
    total = sum(len(v) for v in mapping.values())
    print(f"Wrote {out}: {len(mapping)} groups, {total} voice files")
    if warnings:
        print(f"note: {len(warnings)} group(s) whose exe order is not plain alphabetical "
              f"(kept exe order, which is what the game uses): {', '.join(warnings)}")


if __name__ == '__main__':
    main()
