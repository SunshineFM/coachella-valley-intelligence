# CoWork Brief Template — SunshineFM
Last updated: February 15, 2026

## Standing Instructions (Include in Every CoWork Session)

### Before any git operation:
```bash
rm -f ~/coachella-valley-intelligence/.git/*.lock
```

### Constraints (always apply):
* Read the relevant files before making any changes
* Make only the changes explicitly listed in the task
* Do NOT update `docs.json` or `mint.json` unless explicitly asked
* Do NOT migrate, rename, or move any `.mdx` files unless explicitly asked
* Do NOT create new files unless explicitly asked
* Do NOT modify the generation prompt or Claude API call unless explicitly asked
* Do NOT refactor anything not listed in the task
* Show exact lines changed after each task before moving to the next
* Do NOT commit or push until explicitly approved
* After approval, always run `git pull --rebase origin main && git push`

### Repo location:
`~/coachella-valley-intelligence/`

### Key files:
* `scripts/generate_mintlify_artifacts.py` — pipeline generation script
* `scripts/upload_to_assemblyai.py` — transcription trigger
* `docs.json` — Mintlify navigation (authoritative)
* `.mintignore` — excludes deprecated content from Mintlify
* `CANONICAL_MANUAL.md` — source of truth for all project decisions
