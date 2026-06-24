#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
import argparse
import re
import sys

DEFAULT_SCAN_DIR = "/data/media/movies-uhd"
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".avi", ".mov"}


def die(message, code=2):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scan MA releases and count them by release group."
    )

    parser.add_argument("scan_dir", nargs="?")
    parser.add_argument("--scheme", choices=("1", "2", "standard", "p2p"))

    return parser.parse_args()


def choose_scan_dir(value):
    if value:
        return value

    entered = input(f"Enter movie path [{DEFAULT_SCAN_DIR}]: ").strip()
    return entered or DEFAULT_SCAN_DIR


def choose_scheme(value):
    if value in {"1", "standard"}:
        return "standard"

    if value in {"2", "p2p"}:
        return "p2p"

    print()
    print("Which naming scheme do you use?")
    print("  1) Standard (Bracketed)")
    print("     Example: Movie (2025) - [MA][WEBDL-2160p][EAC3 5.1][h265]-Group.mkv")
    print()
    print("  2) P2P (Dot separated)")
    print("     Example: Movie.2025.MA.WEBDL-2160p.EAC3.5.1.h265-Group.mkv")
    print()

    choice = input("Select scheme [1]: ").strip() or "1"

    if choice == "1":
        return "standard"

    if choice == "2":
        return "p2p"

    die(f"Invalid scheme selection: {choice}")


def bracket_tags(path):
    return re.findall(r"\[([^\]]+)\]", path.name)


def p2p_stem(path):
    return re.sub(r"-[^.-]+$", "", path.stem)


def is_ma_release(path, scheme):
    if scheme == "standard":
        return "MA" in bracket_tags(path)

    return re.search(r"(^|\.)MA(\.|-|$)", p2p_stem(path)) is not None


def extract_release_group(path):
    stem = path.stem

    match = re.search(r"-([A-Za-z0-9_.]+)$", stem)

    if match:
        return match.group(1)

    return "NO-GROUP"


def scan(root, scheme):
    counts = Counter()

    for path in sorted(root.glob("*/*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        if not is_ma_release(path, scheme):
            continue

        counts[extract_release_group(path)] += 1

    return counts


def print_results(root, scheme, counts):
    total = sum(counts.values())
    scheme_label = "Standard (Bracketed)" if scheme == "standard" else "P2P (Dot separated)"

    print()
    print("MA RELEASES BY RELEASE GROUP")
    print(f"SCAN DIR: {root}")
    print(f"SCHEME:   {scheme_label}")
    print(f"TOTAL:    {total}")
    print()

    if total == 0:
        print("No MA releases found.")
        return

    group_width = max([len("RELEASE GROUP")] + [len(group) for group in counts])
    count_width = max(len("COUNT"), len(str(max(counts.values()))))

    print(f"{'RELEASE GROUP':<{group_width}}  {'COUNT':>{count_width}}  PERCENT")
    print(f"{'-' * group_width}  {'-' * count_width}  {'-' * 7}")

    for group, count in counts.most_common():
        percent = count / total * 100
        print(f"{group:<{group_width}}  {count:>{count_width}}  {percent:>6.1f}%")


def main():
    args = parse_args()

    root = Path(choose_scan_dir(args.scan_dir)).expanduser().resolve()
    scheme = choose_scheme(args.scheme)

    if not root.exists():
        die(f"Scan directory does not exist: {root}")

    if not root.is_dir():
        die(f"Scan path is not a directory: {root}")

    counts = scan(root, scheme)
    print_results(root, scheme, counts)


if __name__ == "__main__":
    main()
