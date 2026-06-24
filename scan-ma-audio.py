#!/usr/bin/env python3

from pathlib import Path
import argparse
import re
import sys
from collections import defaultdict

DEFAULT_SCAN_DIR = "/data/media/movies-uhd"
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".m4v", ".avi", ".mov"}
CHANNEL_PATTERN = r"\d+(?:\.\d+)+"

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

CODECS = sorted(
    [(codec, "LOSSLESS") for codec in LOSSLESS_CODECS]
    + [(codec, "LOSSY") for codec in LOSSY_CODECS],
    key=lambda item: len(item[0]),
    reverse=True,
)


def die(message, code=2):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scan MA releases and group them by lossless/lossy audio."
    )

    parser.add_argument("scan_dir", nargs="?")
    parser.add_argument("--scheme", choices=("1", "2", "standard", "p2p"))
    parser.add_argument("--output", choices=("summary", "full", "results"))

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
    print("     Example: Movie (2025) - [MA][WEBDL-2160p][EAC3 5.1][h265]-RlsGrp.mkv")
    print()
    print("  2) P2P (Dot separated)")
    print("     Example: Movie.2025.MA.WEBDL-2160p.EAC3.5.1.h265-RlsGrp.mkv")
    print()

    choice = input("Select scheme [1]: ").strip() or "1"

    if choice == "1":
        return "standard"

    if choice == "2":
        return "p2p"

    die(f"Invalid scheme selection: {choice}")


def choose_output(value):
    if value:
        return value

    print()
    print("Which output do you want?")
    print("  1) Summary only")
    print("  2) Results followed by summary")
    print("  3) Results only")
    print()

    choice = input("Select output [1]: ").strip() or "1"

    if choice == "1":
        return "summary"

    if choice == "2":
        return "full"

    if choice == "3":
        return "results"

    die(f"Invalid output selection: {choice}")


def bracket_tags(path):
    return re.findall(r"\[([^\]]+)\]", path.name)


def p2p_stem(path):
    return re.sub(r"-[^.-]+$", "", path.stem)


def is_ma_release(path, scheme):
    if scheme == "standard":
        return "MA" in bracket_tags(path)

    return re.search(r"(^|\.)MA(\.|-|$)", p2p_stem(path)) is not None


def classify_audio_tag(text):
    for codec, group in CODECS:
        match = re.search(
            rf"^{re.escape(codec)} (?P<channels>{CHANNEL_PATTERN})$",
            text,
        )

        if match:
            return f"{codec} {match.group('channels')}", group

        if codec.endswith(" Atmos"):
            base_codec = codec.removesuffix(" Atmos")

            match = re.search(
                rf"^{re.escape(base_codec)} (?P<channels>{CHANNEL_PATTERN}) Atmos$",
                text,
            )

            if match:
                return f"{codec} {match.group('channels')}", group

    return None, None


def classify_standard_audio(path):
    for tag in bracket_tags(path):
        audio, group = classify_audio_tag(tag)

        if audio:
            return audio, group

    return None, None


def classify_p2p_audio(path):
    stem = p2p_stem(path)

    for codec, group in CODECS:
        dot_codec = codec.replace(" ", ".")

        match = re.search(
            rf"(^|\.){re.escape(dot_codec)}\.(?P<channels>{CHANNEL_PATTERN})(\.|-|$)",
            stem,
        )

        if match:
            return f"{codec} {match.group('channels')}", group

        if codec.endswith(" Atmos"):
            base_codec = codec.removesuffix(" Atmos")
            dot_base_codec = base_codec.replace(" ", ".")

            match = re.search(
                rf"(^|\.){re.escape(dot_base_codec)}\.(?P<channels>{CHANNEL_PATTERN})\.Atmos(\.|-|$)",
                stem,
            )

            if match:
                return f"{codec} {match.group('channels')}", group

    return None, None


def classify_audio(path, scheme):
    if scheme == "standard":
        return classify_standard_audio(path)

    return classify_p2p_audio(path)


def movie_row(path):
    folder = path.parent.name

    tmdb_match = re.search(r"\{tmdb-(\d+)\}", folder)
    tmdb = tmdb_match.group(1) if tmdb_match else "UNKNOWN"

    movie = re.sub(r"\s*\{tmdb-\d+\}\s*$", "", folder)

    return movie, tmdb, path.name


def count_section(grouped, section):
    return sum(len(entries) for entries in grouped[section].values())


def scan(root, scheme):
    grouped = {
        "LOSSLESS": defaultdict(list),
        "LOSSY": defaultdict(list),
    }

    ma_count = 0
    unrecognised = []

    for path in sorted(root.glob("*/*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        if not is_ma_release(path, scheme):
            continue

        ma_count += 1

        audio, group = classify_audio(path, scheme)

        if not audio:
            unrecognised.append(path)
            continue

        grouped[group][audio].append(movie_row(path))

    return ma_count, grouped, unrecognised


def print_entries(entries):
    movie_width = max([len("MOVIE NAME")] + [len(row[0]) for row in entries])
    tmdb_width = max([len("TMDB")] + [len(row[1]) for row in entries])

    print(f"    {'MOVIE NAME':<{movie_width}}  {'TMDB':<{tmdb_width}}  FILENAME")
    print(f"    {'-' * movie_width}  {'-' * tmdb_width}  {'-' * 100}")

    for movie, tmdb, filename in entries:
        print(f"    {movie:<{movie_width}}  {tmdb:<{tmdb_width}}  {filename}")


def print_section(section, grouped):
    total = count_section(grouped, section)

    if total == 0:
        return

    print(f"{section}: {total}")

    for audio in sorted(grouped[section]):
        entries = sorted(grouped[section][audio], key=lambda row: row[0].lower())

        print(f"  {audio}: {len(entries)}")
        print_entries(entries)
        print()

    print()


def print_results(grouped):
    print_section("LOSSLESS", grouped)
    print_section("LOSSY", grouped)


def print_summary(ma_count, grouped):
    lossless_count = count_section(grouped, "LOSSLESS")
    lossy_count = count_section(grouped, "LOSSY")

    labels = [
        "Total MA releases:",
        "Lossless MA releases:",
        "Lossy MA releases:",
    ]

    for section in ("LOSSLESS", "LOSSY"):
        labels.extend(f"  {audio}" for audio in grouped[section])

    label_width = max(len(label) for label in labels)

    def print_count(label, count, percent=None):
        if percent is None:
            print(f"{label:<{label_width}} {count:>4}")
            return

        print(f"{label:<{label_width}} {count:>4} ({percent:.1f}%)")

    print("SUMMARY")
    print("-------")

    print_count("Total MA releases:", ma_count)

    if ma_count == 0:
        return

    print_count("Lossless MA releases:", lossless_count, lossless_count / ma_count * 100)
    print_count("Lossy MA releases:", lossy_count, lossy_count / ma_count * 100)
    print()

    if grouped["LOSSLESS"]:
        print("Lossless formats:")
        for audio in sorted(grouped["LOSSLESS"]):
            count = len(grouped["LOSSLESS"][audio])
            print_count(f"  {audio}", count, count / ma_count * 100)
        print()

    if grouped["LOSSY"]:
        print("Lossy formats:")
        for audio in sorted(grouped["LOSSY"]):
            count = len(grouped["LOSSY"][audio])
            print_count(f"  {audio}", count, count / ma_count * 100)
        print()


def main():
    args = parse_args()

    root = Path(choose_scan_dir(args.scan_dir)).expanduser().resolve()
    scheme = choose_scheme(args.scheme)
    output = choose_output(args.output)

    if not root.exists():
        die(f"Scan directory does not exist: {root}")

    if not root.is_dir():
        die(f"Scan path is not a directory: {root}")

    ma_count, grouped, unrecognised = scan(root, scheme)

    if unrecognised:
        print()
        print("ERROR: Unrecognised audio format in these MA releases:")
        print()
        print("The script only parses filenames. It does not inspect media streams.")
        print("Check the naming scheme or add the missing codec to the script.")
        print()

        for path in unrecognised:
            print(path)

        raise SystemExit(1)

    scheme_label = "Standard (Bracketed)" if scheme == "standard" else "P2P (Dot separated)"

    print()
    print(f"SCAN DIR: {root}")
    print(f"SCHEME:   {scheme_label}")
    print(f"OUTPUT:   {output}")
    print()
    print(f"ALL MA RELEASES: {ma_count}")
    print(f"LOSSLESS: {count_section(grouped, 'LOSSLESS')}")
    print(f"LOSSY:    {count_section(grouped, 'LOSSY')}")
    print()

    if output in {"full", "results"}:
        print_results(grouped)

    if output in {"summary", "full"}:
        print_summary(ma_count, grouped)


if __name__ == "__main__":
    main()
