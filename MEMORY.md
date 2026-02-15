# SunshineFM — Project Memory & Context
Last updated: February 15, 2026

## Purpose & Strategic Intent

SunshineFM is a radio station and intelligence operation broadcasting from the Coachella Valley. The concrete mission for 2026: convince one Silicon Valley friend working at or running an AI company to relocate to the desert for their "second chapter." This personal objective drives all content decisions.

The project serves dual purposes:
1. Warning locals about AI-driven economic disruption
2. Attracting relocating tech founders to build a startup ecosystem in the desert

**Primary audience:** Newly minted, high-agency founders and operators in SF, LA, NYC, Boston considering a second chapter. NOT locals first — outsiders who could move the needle.

**Content filter:** Always ask "Would this make an outsider more curious about building a life or company here?"

## What SunshineFM Actually Is

Three things simultaneously:
1. **A radio station** — AI-generated music runs 24/7. Sat breaks in live, unscripted, when something matters.
2. **An intelligence operation** — every broadcast transcribed, analyzed, published as structured citable intelligence
3. **A gravity engine** — manufacturing regional gravity by making the Coachella Valley legible and exciting to outsiders

**The product is Intelligence Briefs** — not episodes, not signal drops. Daily timestamped intelligence published to `intelligence.sunshine.fm` (currently at `sunshinefm.mintlify.app`).

## Current Infrastructure

**Broadcasting:**
- Radio.co platform for 24/7 broadcast
- Daily show at 3:00 PM PST (Mon-Fri)
- Spontaneous break-ins throughout the day when news breaks
- Suno for AI-generated music (Human Rhythm Engine framework)
- Eleven Labs for voice synthesis

**Recording & Transcription Pipeline:**
- Audio Hijack records shows → saves MP3s to `~/coachella-valley-intelligence/recordings/`
- Filename format: `DD YYYYMMDD HHMM VoiceOnly.mp3` (e.g., `16 20260216 1500 VoiceOnly.mp3`)
- Hazel watches recordings folder → detects VoiceOnly MP3s added today → triggers `upload_to_assemblyai.py`
- AssemblyAI transcribes → saves to `~/coachella-valley-intelligence/transcripts/source/`
- Git commits transcript → pushes to GitHub → triggers GitHub Actions
- GitHub Actions runs `generate_mintlify_artifacts.py` → generates Intelligence Brief MDX
- Mintlify deploys updated site automatically

**Key scripts:**
- `~/coachella-valley-intelligence/scripts/upload_to_assemblyai.py` — Hazel trigger, handles MP3 → transcript → git push
- `~/coachella-valley-intelligence/scripts/generate_mintlify_artifacts.py` — Claude API → generates Intelligence Brief and transcript page
- AssemblyAI API key stored in `~/coachella-valley-intelligence/.env` (never committed to GitHub)
- Anthropic API key stored as GitHub Secret `ANTHROPIC_API_KEY`

## Repository Structure

**Primary repo:** `~/coachella-valley-intelligence/` (GitHub: SunshineFM/coachella-valley-intelligence)
**Deployed at:** `sunshinefm.mintlify.app` (moving to `intelligence.sunshine.fm` — DNS pending)

```
coachella-valley-intelligence/
├── index.mdx                          # Home page
├── mint.json                          # Mintlify config (managed via dashboard)
├── trust.mdx                          # Trust/methodology landing page
├── intelligence/
│   ├── today.mdx                      # STALE — to be removed or replaced
│   ├── signals/                       # Intelligence Briefs (TO BE REFACTORED)
│   │   ├── index.mdx                  # Signals index
│   │   ├── 2026-02-13-signals.mdx     # Individual briefs
│   │   └── show-XX-signals.mdx        # Legacy show-numbered briefs
│   └── episodes/                      # DEPRECATED — removed from nav, files stay
├── transcripts/
│   ├── source/                        # Raw .txt transcripts (not published)
│   └── pages/                         # Published transcript MDX pages
├── methodology/
│   ├── pipeline.mdx
│   ├── sourcing-standard.mdx
│   ├── corrections.mdx
│   └── glossary.mdx
├── scripts/
│   ├── generate_mintlify_artifacts.py
│   └── upload_to_assemblyai.py
├── recordings/                        # MP3 files (gitignored)
└── .github/workflows/
    └── generate-mintlify-artifacts.yml
```

## PENDING REFACTOR — DO THIS NEXT

This is the most important pending work. Decisions made February 15, 2026:

### Content renamed: Signal Drops → Intelligence Briefs
- Old name: "Signal Drop" 
- New name: "Intelligence Brief"
- URLs stay the same (don't break existing citations)
- Update in: generation prompt, nav labels, page titles, index pages

### URL structure to flatten
- Current: `/intelligence/signals/2026-02-13-signals`
- Target: `/intelligence/2026-02-13-1500` (date + time, no subfolder)
- Reason: "signals" subfolder is redundant if Intelligence Briefs are the only content type

### Filename convention to add timestamps
- Current: `2026-02-13.txt` → generates `2026-02-13-signals.mdx`
- Target: `2026-02-13-1500.txt` → generates `2026-02-13-1500.mdx`
- Why: Sat publishes multiple briefs per day (morning burst + 3pm show + occasional evening)
- Audio Hijack filename already contains time: `16 20260216 1500 VoiceOnly.mp3`
- `upload_to_assemblyai.py` needs to extract HHMM from filename and include in output filename

### Nav structure target
```
Home (SunshineFM — Coachella Valley Intelligence)
Intelligence Briefs
  February 2026
    Feb 16, 2026 3:00pm — Intelligence Brief
    Feb 13, 2026 3:00pm — Intelligence Brief
    Feb 12, 2026 3:00pm — Intelligence Brief
    [collapsed: older February briefs]
  January 2026
    [collapsed]
Trust
  Trust
  Pipeline
  Sourcing Standard
  Corrections
  Glossary
Transcripts
  [raw source files]
```

### Files to update for refactor:
1. `scripts/upload_to_assemblyai.py` — extract HHMM from filename, save as `YYYY-MM-DD-HHMM.txt`
2. `scripts/generate_mintlify_artifacts.py` — update prompt ("Signal Drop" → "Intelligence Brief"), handle timestamp filenames, flatten URL structure
3. `mint.json` — update navigation groups and page paths
4. `intelligence/signals/index.mdx` — update description
5. Remove/redirect `intelligence/today.mdx` — stale, being replaced by chronological nav

## Site Navigation (Current State as of Feb 15, 2026)

Managed via Mintlify dashboard (not mint.json directly):
- **Start Here:** Home, Signals Index, Today
- **Trust:** Trust, Pipeline, Sourcing Standard, Corrections, Glossary
- Episodes removed from nav (files remain at their URLs)
- Research section removed (doesn't exist yet)

## Content Strategy

**Intelligence Briefs are the product.** Not episodes. Not long-form features.

Format:
- 6-8 signals per brief (bold one-line header + 3-5 sentence body each)
- Each signal: specific, local angle, opinionated
- End with "## Local Radar" section (3-5 local items)
- End with "## Citeable Claims" section (6-10 specific verifiable facts with dates, figures, names)
- NO H1 or H2 title at top of body (frontmatter handles that)
- Do NOT inject desert flavor — Sat brings local texture, Claude brings structure and synthesis

**Do not generate:** Long-form episodes, weekly deep dives, research briefs (not yet)

**Voice rules:**
- Curious but skeptical
- Optimistic but not hype-drunk  
- Local but outward-facing
- Playful on surface, serious underneath
- Never sound like: tourism board, chamber of commerce, press release, tech evangelist

## Key Decisions Log

- **Feb 15, 2026:** Renamed "Signal Drops" to "Intelligence Briefs"
- **Feb 15, 2026:** Decided to flatten URL structure (pending refactor)
- **Feb 15, 2026:** Added timestamp to filename convention for multiple daily briefs
- **Feb 15, 2026:** Removed episodes from nav (deprecated but files preserved)
- **Feb 15, 2026:** Removed Research section (future, not yet)
- **Feb 15, 2026:** Home page rewritten to signals-first, culture and creative industries added
- **Feb 14, 2026:** Full pipeline working: Audio Hijack → Hazel → AssemblyAI → GitHub → Mintlify
- **Feb 14, 2026:** GitHub Actions fixed to process only triggered date (not all transcripts)
- **Feb 14, 2026:** AssemblyAI key moved to .env file (was exposed in git history — rotated)

## Outstanding Work

**High priority:**
- Execute URL/filename refactor (see PENDING REFACTOR above)
- Set up `intelligence.sunshine.fm` DNS
- Add Hazel "Date Added is today" condition ✅ Done Feb 15
- Bulk move old SunshineFM recordings to coachella-valley-intelligence/recordings/
- Archive ~/SunshineFM/ folder

**Medium priority:**
- Purge old AssemblyAI key from git history (key already rotated, lower urgency)
- Reprocess show-11 through show-30 with new Intelligence Brief format
- Build `sunshine.fm` public-facing landing page (separate from intelligence layer)

**Future:**
- Weekly Intelligence Brief (deeper research, separate from daily)
- `intelligence.sunshine.fm` as the machine-readable layer
- CoWorks access to coachella-valley-intelligence repo
