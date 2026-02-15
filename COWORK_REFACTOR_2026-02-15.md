# SunshineFM CoWorks Project — Intelligence Brief Refactor
Created: February 15, 2026

---

## Context

Read these files first before doing anything:
- `~/coachella-valley-intelligence/MEMORY.md`
- `~/coachella-valley-intelligence/CANONICAL_MANUAL.md`
- `~/coachella-valley-intelligence/OPERATING_INSTRUCTIONS.md`

---

## What We're Doing

Renaming and restructuring the content pipeline from "Signal Drops" to "Intelligence Briefs" with timestamp-based filenames and flat URL structure.

**Current state:**
- Files named: `2026-02-13-signals.mdx`
- URLs: `/intelligence/signals/2026-02-13-signals`
- Content called: "Signal Drop"
- Transcripts named: `2026-02-13.txt` (no time)

**Target state:**
- Files named: `2026-02-13-1500.mdx`
- URLs: `/intelligence/2026-02-13-1500`
- Content called: "Intelligence Brief"
- Transcripts named: `2026-02-13-1500.txt` (with time)

---

## PROJECT 1: Update upload_to_assemblyai.py

**File:** `~/coachella-valley-intelligence/scripts/upload_to_assemblyai.py`

**Change:** Extract HHMM from Audio Hijack filename and include in transcript filename.

Audio Hijack saves files as: `16 20260216 1500 VoiceOnly.mp3`
Currently the script extracts date only and saves as: `2026-02-13.txt`
It needs to extract date AND time and save as: `2026-02-13-1500.txt`

**The regex to extract time:** The filename format is `DD YYYYMMDD HHMM VoiceOnly.mp3`
- Date is at positions 3-10: `YYYYMMDD`
- Time is at positions 12-15: `HHMM`

Update the script so:
1. Extract HHMM from filename
2. Save transcript as `YYYY-MM-DD-HHMM.txt` instead of `YYYY-MM-DD.txt`
3. Git commit message becomes: `transcript: YYYY-MM-DD-HHMM`

**Test:** Run the script on an existing VoiceOnly MP3 and confirm the output filename includes the time.

---

## PROJECT 2: Update generate_mintlify_artifacts.py

**File:** `~/coachella-valley-intelligence/scripts/generate_mintlify_artifacts.py`

### Change 1: Handle timestamp filenames
The script currently expects `YYYY-MM-DD.txt` and generates `YYYY-MM-DD-signals.mdx`.
It needs to handle `YYYY-MM-DD-HHMM.txt` and generate `YYYY-MM-DD-HHMM.mdx`.

Update the date extraction regex to match both formats:
- `YYYY-MM-DD` (existing files)
- `YYYY-MM-DD-HHMM` (new files)

### Change 2: Rename "Signal Drop" to "Intelligence Brief"
Find every instance of "Signal Drop" or "signal drop" in the prompts and replace with "Intelligence Brief" or "intelligence brief".

Specifically update:
- The signals generation prompt
- Title format: change `"{date_str}: Signal Drop"` to `"{date_str}: Intelligence Brief"`
- Any display strings

### Change 3: Flatten URL structure
Currently generates files to: `intelligence/signals/2026-02-13-signals.mdx`
Should generate to: `intelligence/2026-02-13-1500.mdx`

Update:
- `SIGNALS_DIR` path from `intelligence/signals/` to `intelligence/`
- Output filename from `{date_str}-signals.mdx` to `{date_str}.mdx`
- Any index update functions that reference the old path

### Change 4: Update display format for timestamps
When displaying dates in titles and nav, format `2026-02-13-1500` as `February 13, 2026 3:00pm`.

Write a helper function `format_display_date(date_str)` that:
- Takes `2026-02-13-1500`
- Returns `February 13, 2026 3:00pm`
- Falls back gracefully if no time component present

---

## PROJECT 3: Update GitHub Actions workflow

**File:** `~/coachella-valley-intelligence/.github/workflows/generate-mintlify-artifacts.yml`

The workflow trigger watches: `transcripts/source/*.txt`
The date extraction line currently does: `DATE=$(basename "$CHANGED" .txt)`

This already works for `2026-02-13-1500.txt` — it will extract `2026-02-13-1500` correctly.

**Verify** this works correctly by reading the workflow file and confirming the basename extraction handles the timestamp format.

---

## PROJECT 4: Migrate existing signal files

Move all existing signal files from `/intelligence/signals/` to `/intelligence/`:

**Date-based files to move and rename:**
- `intelligence/signals/2026-02-13-signals.mdx` → `intelligence/2026-02-13-1500.mdx`
- `intelligence/signals/2026-02-12-signals.mdx` → `intelligence/2026-02-12-1500.mdx`
- `intelligence/signals/2026-02-11-signals.mdx` → `intelligence/2026-02-11-1500.mdx`
- `intelligence/signals/2026-02-10-signals.mdx` → `intelligence/2026-02-10-1500.mdx`
- `intelligence/signals/2026-02-09-signals.mdx` → `intelligence/2026-02-09-1500.mdx`
- `intelligence/signals/2026-02-06-signals.mdx` → `intelligence/2026-02-06-1500.mdx`
- `intelligence/signals/2026-02-05-signals.mdx` → `intelligence/2026-02-05-1500.mdx`
- `intelligence/signals/2026-02-04-signals.mdx` → `intelligence/2026-02-04-1500.mdx`
- `intelligence/signals/2026-02-03-signals.mdx` → `intelligence/2026-02-03-1500.mdx`
- `intelligence/signals/2026-02-02-signals.mdx` → `intelligence/2026-02-02-1500.mdx`
- `intelligence/signals/2026-01-30-signals.mdx` → `intelligence/2026-01-30-1500.mdx`
- `intelligence/signals/2026-01-29-signals.mdx` → `intelligence/2026-01-29-1500.mdx`
- `intelligence/signals/2026-01-28-signals.mdx` → `intelligence/2026-01-28-1500.mdx`
- `intelligence/signals/2026-01-27-signals.mdx` → `intelligence/2026-01-27-1500.mdx`
- `intelligence/signals/2026-01-26-signals.mdx` → `intelligence/2026-01-26-1500.mdx`
- `intelligence/signals/2026-01-23-signals.mdx` → `intelligence/2026-01-23-1500.mdx`
- `intelligence/signals/2026-01-22-signals.mdx` → `intelligence/2026-01-22-1500.mdx`
- `intelligence/signals/2026-01-21-signals.mdx` → `intelligence/2026-01-21-1500.mdx`
- `intelligence/signals/2026-01-20-signals.mdx` → `intelligence/2026-01-20-1500.mdx`
- `intelligence/signals/2026-01-19-signals.mdx` → `intelligence/2026-01-19-1500.mdx`
- `intelligence/signals/2026-01-16-signals.mdx` → `intelligence/2026-01-16-1500.mdx`
- `intelligence/signals/2026-01-15-signals.mdx` → `intelligence/2026-01-15-1500.mdx`
- `intelligence/signals/2026-01-14-signals.mdx` → `intelligence/2026-01-14-1500.mdx`
- `intelligence/signals/2026-01-13-signals.mdx` → `intelligence/2026-01-13-1500.mdx`
- `intelligence/signals/2026-01-12-signals.mdx` → `intelligence/2026-01-12-1500.mdx`
- `intelligence/signals/2026-01-11-signals.mdx` → `intelligence/2026-01-11-1500.mdx`

**Show-numbered files — leave in place:**
- `intelligence/signals/show-XX-signals.mdx` files stay where they are
- They are legacy content, not part of the new structure

**Update frontmatter** in each moved file:
- Change title from `"{date}: Signal Drop"` to `"{date} 3:00pm — Intelligence Brief"`

---

## PROJECT 5: Update Signals Index page

**File:** `~/coachella-valley-intelligence/intelligence/signals/index.mdx`

Update this page to reflect new naming and structure. Change:
- Title: "Signals Index" → "Intelligence Briefs"
- Description: update to reference Intelligence Briefs not Signal Drops
- All links to point to new `/intelligence/YYYY-MM-DD-HHMM` paths

---

## PROJECT 6: Update mint.json navigation

**File:** `~/coachella-valley-intelligence/mint.json`

Note: Mintlify dashboard also manages navigation. Update mint.json to match.

Update navigation to reflect new structure:
- Group name: "Intelligence Briefs" (not "Signals")
- All page paths: `intelligence/2026-02-13-1500` (not `intelligence/signals/2026-02-13-signals`)
- Remove show-numbered signal files from navigation (keep files, remove from nav)

Target navigation structure:
```json
{
  "group": "Intelligence Briefs",
  "pages": [
    "intelligence/2026-02-13-1500",
    "intelligence/2026-02-12-1500",
    ... all date-based briefs newest first ...
  ]
}
```

---

## PROJECT 7: Commit everything

After all changes are made:

```bash
cd ~/coachella-valley-intelligence
git add -A
git commit -m "Refactor: Signal Drops → Intelligence Briefs, flatten URL structure, add timestamps"
git push
```

Then verify on GitHub Actions that the workflow still triggers correctly on new transcript commits.

---

## Success Criteria

- [ ] New VoiceOnly MP3 processed by Hazel produces `YYYY-MM-DD-HHMM.txt` transcript
- [ ] GitHub Actions generates `intelligence/YYYY-MM-DD-HHMM.mdx` (not in signals subfolder)
- [ ] Generated page title says "Intelligence Brief" not "Signal Drop"
- [ ] All existing date-based signal files moved to new location
- [ ] mint.json navigation updated with new paths
- [ ] Site deploys without errors on Mintlify

---

## Key Constraints

- Do NOT delete show-numbered files (`show-XX-signals.mdx`) — leave them in place
- Do NOT change the `/transcripts/` folder structure
- Do NOT change the `/methodology/` or `/trust.mdx` files
- Do NOT modify the episodes folder
- Keep `.env` file untouched — contains API keys
- Run `git pull --rebase` before pushing if push is rejected
