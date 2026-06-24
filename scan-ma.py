#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
import argparse
import re
import sys

DEFAULT_SCAN_DIR = "/data/media/movies-uhd"

VIDEO_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".m4v",
    ".avi",
    ".mov",
}

def parse_args():
    parser = argparse.ArgumentParser(
        description="Count MA releases by release group."
    )
    parser.add_argument(
        "scan_dir",
        nargs="?",
        help="Movie root directory to scan. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--scheme",
        choices=("1", "2"),
        help="Naming scheme: 1 = normal bracket Radarr, 2 = P2P dot. If omitted, you will be prompted.",
    )
    return parser.parse_args()

def choose_scan_dir(cli_scan_dir):
    if cli_scan_dir:
        return cli_scan_dir

    entered = input(f"Enter movie path [{DEFAULT_SCAN_DIR}]: ").strip()

    if entered == "":
        return DEFAULT_SCAN_DIR

    return entered

def choose_scheme(cli_scheme):
    if cli_scheme:
        return cli_scheme

    print()
    print("Which naming scheme do you use?")
    print("  1) Normal Radarr bracket scheme")
    print("     Example: Movie Name (2024) {tmdb-123} - [MA][WEBDL-2160p][EAC3 5.1][h265]-GROUP.mkv")
    print()
    print("  2) P2P dot scheme")
    print("     Example: Movie.Title.2024.MA.WEBDL-2160p.EAC3.5.1.h265-GROUP.mkv")
    print()

    choice = input("Select scheme [1]: ").strip()

    if choice == "":
        return "1"

    if choice not in {"1", "2"}:
        print(f"ERROR: Invalid scheme selection: {choice}", file=sys.stderr)
        raise SystemExit(2)

    return choice

def validate_scan_dir(scan_dir):
    root = Path(scan_dir).expanduser().resolve()

    if not root.exists():
        print(f"ERROR: Scan directory does not exist: {root}", file=sys.stderr)
        raise SystemExit(2)

    if not root.is_dir():
        print(f"ERROR: Scan path is not a directory: {root}", file=sys.stderr)
        raise SystemExit(2)

    return root

def is_video_file(path):
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS

def bracket_blocks(name):
    return re.findall(r"\[([^\]]+)\]", name)

def is_ma_bracket(path):
    return "MA" in bracket_blocks(path.name)

def is_ma_dot(path):
    stem = path.stem
    return re.search(r"(^|\.)MA(\.|-|$)", stem) is not None

def is_ma_release(path, scheme):
    if scheme == "1":
        return is_ma_bracket(path)

    return is_ma_dot(path)

def release_group_bracket(path):
    stem = path.stem

    match = re.search(r"\]-([^-]+)$", stem)
    if match:
        return match.group(1)

    match = re.search(r"-([A-Za-z0-9_.]+)$", stem)
    if match:
        return match.group(1)

    return "NO-GROUP"

def release_group_dot(path):
    stem = path.stem

    match = re.search(r"-([A-Za-z0-9_.]+)$", stem)
    if match:
        return match.group(1)

    return "NO-GROUP"

def release_group(path, scheme):
    if scheme == "1":
        return release_group_bracket(path)

    return release_group_dot(path)

def print_counts(counts, root, scheme):
    total = sum(counts.values())
    scheme_label = "Normal Radarr bracket scheme" if scheme == "1" else "P2P dot scheme"

    print()
    print("MA RELEASES BY RELEASE GROUP")
    print(f"SCAN DIR: {root}")
    print(f"SCHEME:   {scheme_label}")
    print(f"TOTAL:    {total}")
    print()

    if not counts:
        print("No MA releases found.")
        return

    group_width = max([len("RELEASE GROUP")] + [len(group) for group in counts])
    count_width = max(len("COUNT"), len(str(max(counts.values()))))
    percent_width = len("PERCENT")

    print(f"{'RELEASE GROUP':<{group_width}}  {'COUNT':>{count_width}}  {'PERCENT':>{percent_width}}")
    print(f"{'-' * group_width}  {'-' * count_width}  {'-' * percent_width}")

    for group, count in counts.most_common():
        percent = count / total * 100
        print(f"{group:<{group_width}}  {count:>{count_width}}  {percent:>6.1f}%")

def main():
    args = parse_args()

    scan_dir = choose_scan_dir(args.scan_dir)
    scheme = choose_scheme(args.scheme)
    root = validate_scan_dir(scan_dir)

    counts = Counter()

    for path in root.glob("*/*"):
        if not is_video_file(path):
            continue

        if not is_ma_release(path, scheme):
            continue

        counts[release_group(path, scheme)] += 1

    print_counts(counts, root, scheme)

if __name__ == "__main__":
    main()
