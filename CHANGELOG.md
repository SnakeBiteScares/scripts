# Changelog

## scan-ma-groups-v0.1.0 - 2026-06-24

### Added

- Scan MA-tagged movie filenames.
- Support standard bracketed naming.
- Support P2P dot-separated naming.
- Count MA releases by release group.
- Show release group counts and percentages.
- Report files without a release group as NO-GROUP.

## scan-ma-audio-v0.1.0 - 2026-06-24

### Added

- Scan MA-tagged movie filenames.
- Support standard bracketed naming.
- Support P2P dot-separated naming.
- Classify filename audio tags as lossless or lossy.
- Group detailed results by audio format.
- Add summary output with totals and percentages.
- Add output selection: summary only, results followed by summary, or results only.
- Fail when an MA release has an unrecognised audio tag.
- Parse flexible channel layouts such as 5.1, 7.1, and 7.1.4.

### Changed

- Replaced fixed channel matching with flexible channel pattern matching.
- Removed duplicated lossy output.
- Improved output headings and summary alignment.
- Improved naming scheme prompts and examples.

### Notes

- The script only parses filenames.
- The script does not inspect media streams.
- Results depend on accurate filename tags.
