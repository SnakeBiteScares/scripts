# scripts

A small collection of utility scripts.

## scan-ma-groups.py

Scans movie filenames for MA-tagged releases and counts them by release group.

Run:

    python3 scan-ma-groups.py

## scan-ma-audio.py

Scans movie filenames for MA-tagged releases and reports whether the filename audio tag is lossless or lossy.

Supported naming styles:

- Standard bracketed:
  - Movie (2025) - [MA][WEBDL-2160p][EAC3 5.1][h265]-Group.mkv
- P2P dot-separated:
  - Movie.2025.MA.WEBDL-2160p.EAC3.5.1.h265-Group.mkv

The script only parses filenames. It does not inspect media streams.

Run:

    python3 scan-ma-audio.py

## LLM disclosure

Some scripts in this repository are built, edited, or reviewed with help from large language models.

Review scripts before running them. Test against your own files before relying on the output.

## Disclaimer

Scripts are provided as-is. Use at your own risk.
