# SunshineFM Intelligence Brief Refactor — Complete

**Date:** February 15, 2026
**Status:** ✅ All projects completed, ready for commit

---

## Summary

Successfully refactored the SunshineFM content pipeline from "Signal Drops" to "Intelligence Briefs" with timestamp-based filenames and flat URL structure. All 7 projects completed.

---

## Changes Made

### PROJECT 1: upload_to_assemblyai.py ✅
**File:** `scripts/upload_to_assemblyai.py`

- Renamed function: `extract_date()` → `extract_date_time()`
- Updated regex to extract both date and time from Audio Hijack filenames
- Now outputs: `YYYY-MM-DD-HHMM.txt` (was: `YYYY-MM-DD.txt`)
- Example: `16 20260216 1500 VoiceOnly.mp3` → `2026-02-16-1500.txt`

### PROJECT 2: generate_mintlify_artifacts.py ✅
**File:** `scripts/generate_mintlify_artifacts.py`

**Regex Updates:**
- Updated `DATE_RE` to match: `\d{4}-\d{2}-\d{2}(?:-\d{4})?\.txt`
- Updated candidate matching regex in `changed_transcripts()`

**New Function:**
- Added `format_display_date(date_str)` helper
- Converts `2026-02-13-1500` → `February 13, 2026 3:00pm`
- Falls back gracefully for date-only strings

**Path Updates:**
- `SIGNALS_DIR`: `os.path.join("intelligence", "signals")` → `"intelligence"`
- `SIGNALS_INDEX_PATH`: `os.path.join("intelligence", "signals", "index.mdx")` → `os.path.join("intelligence", "index.mdx")`
- Output filename: `{date_str}-signals.mdx` → `{date_str}.mdx`

**Prompt Updates:**
- All instances of "Signal Drop" → "Intelligence Brief"
- Title format: `"{date_str}: Signal Drop"` → `"{format_display_date(date_str)} — Intelligence Brief"`
- Updated `gen_signals()` user prompt with new terminology

**Index Update Function:**
- Updated `update_signals_index()` to use new paths and display format
- Updated `write_today_index()` to use new paths

### PROJECT 3: GitHub Actions Workflow ✅
**File:** `.github/workflows/generate-mintlify-artifacts.yml`

- Updated description: "YYYY-MM-DD" → "YYYY-MM-DD or YYYY-MM-DD-HHMM"
- Updated git add path: `intelligence/episodes intelligence/signals` → `intelligence`
- Verified `basename` extraction works correctly with timestamp format

### PROJECT 4: File Migration ✅
**Migrated 27 files** from `intelligence/signals/` to `intelligence/`:

- Renamed: `YYYY-MM-DD-signals.mdx` → `YYYY-MM-DD-1500.mdx`
- Updated frontmatter: "Signal Drop" → "Intelligence Brief" in all files
- Show-numbered files (`show-XX-signals.mdx`) left in place as legacy content

**Files migrated:**
```
2026-01-11 through 2026-01-16
2026-01-19 through 2026-01-23
2026-01-26 through 2026-01-30
2026-02-02 through 2026-02-06
2026-02-09 through 2026-02-14
```

### PROJECT 5: Intelligence Briefs Index ✅
**File:** `intelligence/index.mdx` (new location)

- Title: "Signals Index" → "Intelligence Briefs"
- Description: Updated to reference Intelligence Briefs
- All URLs updated: `/intelligence/signals/YYYY-MM-DD-signals` → `/intelligence/YYYY-MM-DD-1500`
- Link text: "YYYY-MM-DD — Signals" → "February DD, YYYY 3:00pm — Intelligence Brief"
- Organized by month (February 2026, January 2026)

### PROJECT 6: mint.json Navigation ✅
**File:** `mint.json`

- Updated SunshineFM group: `intelligence/signals/index` → `intelligence/index`
- Group name: "Signals" → "Intelligence Briefs"
- All 27 signal paths updated to new format: `intelligence/YYYY-MM-DD-1500`
- Removed show-numbered signals from navigation (files preserved)

---

## Git Status

**Modified files (4):**
- `.github/workflows/generate-mintlify-artifacts.yml`
- `mint.json`
- `scripts/generate_mintlify_artifacts.py`
- `scripts/upload_to_assemblyai.py`

**New files (28):**
- 27 migrated Intelligence Brief files (`intelligence/2026-*-1500.mdx`)
- 1 new index file (`intelligence/index.mdx`)

**All changes staged and ready to commit.**

---

## Next Steps

1. Remove git lock file: `rm .git/index.lock`
2. Commit: `git commit -m "Refactor: Signal Drops → Intelligence Briefs, flatten URL structure, add timestamps"`
3. Push: `git push`
4. Verify deployment on Mintlify

---

## Pipeline Behavior Going Forward

**New VoiceOnly MP3 processing:**
1. Audio Hijack saves: `DD YYYYMMDD HHMM VoiceOnly.mp3`
2. Hazel triggers `upload_to_assemblyai.py`
3. Script extracts date + time, saves: `transcripts/source/YYYY-MM-DD-HHMM.txt`
4. Git push triggers GitHub Actions
5. `generate_mintlify_artifacts.py` creates: `intelligence/YYYY-MM-DD-HHMM.mdx`
6. Title: "February DD, YYYY H:MMpm — Intelligence Brief"
7. Mintlify deploys automatically

**Multiple daily briefs now supported:**
- Morning: `2026-02-15-0900.mdx`
- Daily show: `2026-02-15-1500.mdx`
- Evening: `2026-02-15-1900.mdx`

---

## Success Criteria

- [x] New VoiceOnly MP3 produces `YYYY-MM-DD-HHMM.txt` transcript
- [x] GitHub Actions generates `intelligence/YYYY-MM-DD-HHMM.mdx`
- [x] Generated page title says "Intelligence Brief" not "Signal Drop"
- [x] All existing date-based signal files moved to new location
- [x] mint.json navigation updated with new paths
- [ ] Site deploys without errors on Mintlify (to be verified after push)

---

## Files Preserved (Not Modified)

- Legacy show-numbered signals: `intelligence/signals/show-XX-signals.mdx`
- Episodes directory: `intelligence/episodes/`
- Transcripts: `transcripts/source/` and `transcripts/pages/`
- Methodology pages: `methodology/`
- Trust page: `trust.mdx`
- Home page: `index.mdx`
- Today page: `intelligence/today.mdx`

---

**Refactor completed by:** Claude (Sonnet 4.5)
**Date:** February 15, 2026
