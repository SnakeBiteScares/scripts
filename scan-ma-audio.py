#!/usr/bin/env python3

from pathlib import Path
import argparse
import re
import sys
from collections import defaultdict

DEFAULT_SCAN_DIR = "/data/media/movies-uhd"

VIDEO_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".m4v",
    ".avi",
    ".mov",
}

CHANNELS = (
    "1.0",
    "2.0",
    "3.0",
    "4.0",
    "5.1",
    "6.1",
    "7.1",
)

LOSSLESS_CODECS = (
    "TrueHD Atmos",
    "TrueHD",
    "DTS-HD MA",
    "DTS-X",
    "DTS:X",
    "FLAC",
    "PCM",
    "LPCM",
    "MLP",
)

LOSSY_CODECS = (
    "EAC3 Atmos",
    "EAC3",
    "DDP Atmos",
    "DDP",
    "DD+ Atmos",
    "DD+",
    "DTS-HD HRA",
    "DTS-ES",
    "AC3",
    "DD",
    "AAC",
    "DTS",
    "Opus",
    "MP3",
)

def build_formats(codecs, group):
    formats = []

    for codec in codecs:
        for channel in CHANNELS:
            formats.append((f"{codec} {channel}", group))

        if "Atmos" in codec:
            base_codec = codec.replace(" Atmos", "")
            for channel in CHANNELS:
                formats.append((f"{base_codec} {channel} Atmos", group))

    return formats

ALL_FORMATS = tuple(
    sorted(
        build_formats(LOSSLESS_CODECS, "LOSSLESS") + build_formats(LOSSY_CODECS, "LOSSY"),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Scan MA releases and group them by lossless/lossy audio."
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
    print("     Example: Movie Name (2024) {tmdb-123} - [MA][WEBDL-2160p][EAC3 Atmos 5.1][DV HDR10][h265]-GROUP.mkv")
    print()
    print("  2) P2P dot scheme")
    print("     Example: Movie.Title.2024.MA.WEBDL-2160p.EAC3.Atmos.5.1.DV.HDR10.h265-GROUP.mkv")
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

def audio_bracket(path):
    blocks = bracket_blocks(path.name)

    for block in blocks:
        for audio_format, group in ALL_FORMATS:
            if block == audio_format or block.startswith(audio_format + " "):
                return block, group

    return None, None

def dot_stem(path):
    stem = path.stem
    return re.sub(r"-[^.-]+$", "", stem)

def is_ma_dot(path):
    stem = dot_stem(path)
    return re.search(r"(^|\.)MA(\.|-|$)", stem) is not None

def audio_dot(path):
    stem = dot_stem(path)

    for audio_format, group in ALL_FORMATS:
        dot_format = audio_format.replace(" ", ".")
        regex = rf"(^|\.){re.escape(dot_format)}(\.|-|$)"

        if re.search(regex, stem):
            return audio_format, group

    return None, None

def is_ma_release(path, scheme):
    if scheme == "1":
        return is_ma_bracket(path)

    return is_ma_dot(path)

def audio_format(path, scheme):
    if scheme == "1":
        return audio_bracket(path)

    return audio_dot(path)

def movie_info(path):
    folder = path.parent.name
    filename = path.name

    tmdb_match = re.search(r"\{tmdb-(\d+)\}", folder)
    tmdb = tmdb_match.group(1) if tmdb_match else "UNKNOWN"

    movie = re.sub(r"\s*\{tmdb-\d+\}\s*$", "", folder)

    return movie, tmdb, filename

def print_entries(entries):
    movie_width = max([len("MOVIE NAME")] + [len(e[0]) for e in entries])
    tmdb_width = max([len("TMDB")] + [len(e[1]) for e in entries])

    print(f"    {'MOVIE NAME':<{movie_width}}  {'TMDB':<{tmdb_width}}  FILENAME")
    print(f"    {'-' * movie_width}  {'-' * tmdb_width}  {'-' * 100}")

    for movie, tmdb, filename in entries:
        print(f"    {movie:<{movie_width}}  {tmdb:<{tmdb_width}}  {filename}")

def print_section(section, grouped):
    section_count = sum(len(v) for v in grouped[section].values())

    if section_count == 0:
        return

    print(f"{section}: {section_count}")

    for audio in sorted(grouped[section]):
        entries = sorted(grouped[section][audio], key=lambda x: x[0].lower())
        print(f"  {audio}: {len(entries)}")
        print_entries(entries)
        print()

    print()

def print_summary(files, grouped):
    total = len(files)
    lossless_count = sum(len(v) for v in grouped["LOSSLESS"].values())
    lossy_count = sum(len(v) for v in grouped["LOSSY"].values())

    print("SUMMARY")
    print("-------")

    if total == 0:
        print("Total MA releases: 0")
        return

    print(f"Total MA releases:     {total}")
    print(f"Lossless MA releases:  {lossless_count:>4} ({lossless_count / total * 100:>5.1f}%)")
    print(f"Lossy MA releases:     {lossy_count:>4} ({lossy_count / total * 100:>5.1f}%)")
    print()

    if grouped["LOSSLESS"]:
        print("Lossless formats:")
        for audio in sorted(grouped["LOSSLESS"]):
            count = len(grouped["LOSSLESS"][audio])
            print(f"  {audio:<24} {count:>4} ({count / total * 100:>5.1f}%)")
        print()

    if grouped["LOSSY"]:
        print("Lossy formats:")
        for audio in sorted(grouped["LOSSY"]):
            count = len(grouped["LOSSY"][audio])
            print(f"  {audio:<24} {count:>4} ({count / total * 100:>5.1f}%)")
        print()

def main():
    args = parse_args()

    scan_dir = choose_scan_dir(args.scan_dir)
    scheme = choose_scheme(args.scheme)
    root = validate_scan_dir(scan_dir)

    files = sorted(
        p for p in root.glob("*/*")
        if is_video_file(p) and is_ma_release(p, scheme)
    )

    grouped = {
        "LOSSLESS": defaultdict(list),
        "LOSSY": defaultdict(list),
    }

    unrecognised = []

    for path in files:
        audio, group = audio_format(path, scheme)

        if audio is None:
            unrecognised.append(str(path))
            continue

        grouped[group][audio].append(movie_info(path))

    if unrecognised:
        print()
        print("ERROR: Unrecognised audio format in these MA releases:")
        print()
        for entry in unrecognised:
            print(entry)
        raise SystemExit(1)

    lossy_count = sum(len(v) for v in grouped["LOSSY"].values())

    scheme_label = "Normal Radarr bracket scheme" if scheme == "1" else "P2P dot scheme"

    print()
    print(f"SCAN DIR: {root}")
    print(f"SCHEME:   {scheme_label}")
    print()
    print(f"ALL MA RELEASES: {len(files)}")
    print()

    for section in ("LOSSLESS", "LOSSY"):
        print_section(section, grouped)

    print(f"LOSSY MA RELEASES: {lossy_count}")
    print()

    print_section("LOSSY", grouped)

    print_summary(files, grouped)

if __name__ == "__main__":
    main()
