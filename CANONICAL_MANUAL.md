# SunshineFM Canonical Operating Manual
Last updated: February 15, 2026

## The Tagline (Exact Branding)

**SunshineFM: Modern Media for Palm Springs Coachella**

"Palm Springs Coachella" is one regional brand — not separate cities. That's how we refer to the entire valley ecosystem.

---

## What SunshineFM Actually Is

Three things simultaneously:

### 1. A Radio Station
A deliberately weird, opinionated, AI-native media signal broadcasting from Palm Springs Coachella. AI-generated music runs 24/7. Sat Singh breaks in live and unscripted when something matters — daily at 3:00 PM PST and spontaneously throughout the day.

Not neutral. Not polite. Honest, sometimes spicy, intentionally disruptive in a fun, charismatic way.

### 2. A Public Experiment on AI Implementation
SunshineFM is Sat building a lifelong dream — having a radio station — in public, with an army of AI agents doing the work a traditional radio station would need dozens of humans to do.

We don't hide the machinery. The audience watches how this gets made. That's the show.

### 3. A Gravity Engine for Palm Springs Coachella
SunshineFM exists to manufacture regional gravity — telling the right stories, spotlighting the right people, making the region feel legible and exciting to outsiders who could actually move the needle.

**Concrete 2026 mission:** Convince one Silicon Valley AI friend to relocate to the desert for their "second chapter."

---

## The Product: Intelligence Briefs

The primary content output is the **Intelligence Brief** — published daily, sometimes multiple times per day.

**NOT:** Episodes, features, long-form analysis, weekly deep dives (future, not now)

**Format:**
- 6-8 signals per brief
- Each signal: bold one-line header + 3-5 sentence body
- Specific, local angle, opinionated
- Ends with "## Local Radar" (3-5 local items)
- Ends with "## Citeable Claims" (6-10 verifiable facts with dates, figures, names)

**Naming convention:** Intelligence Brief (not Signal Drop, not Episode)

**URL structure (pending refactor):** `/intelligence/YYYY-MM-DD-HHMM`

**Multiple briefs per day:**
- Morning burst (before noon): `YYYY-MM-DD-HHMM`
- Daily show (3:00 PM PST): `YYYY-MM-DD-1500`
- Evening (rare, events only): `YYYY-MM-DD-HHMM`

---

## The Automated Pipeline

```
Audio Hijack → VoiceOnly MP3 saved to ~/coachella-valley-intelligence/recordings/
Hazel → detects VoiceOnly MP3 added today → runs upload_to_assemblyai.py
AssemblyAI → transcribes → saves YYYY-MM-DD-HHMM.txt to transcripts/source/
Git → commits and pushes transcript
GitHub Actions → runs generate_mintlify_artifacts.py with --date YYYY-MM-DD-HHMM
Claude API → generates Intelligence Brief MDX
Mintlify → deploys to sunshinefm.mintlify.app (moving to intelligence.sunshine.fm)
```

**Key files:**
- `scripts/upload_to_assemblyai.py` — local pipeline trigger
- `scripts/generate_mintlify_artifacts.py` — Claude API content generation
- `.env` — AssemblyAI API key (never committed)
- GitHub Secret `ANTHROPIC_API_KEY` — for GitHub Actions

---

## Site Architecture

**Two-layer system:**
1. `intelligence.sunshine.fm` — Mintlify intelligence layer (LLM-optimized, machine-readable)
2. `sunshine.fm` — public-facing radio station site (future, not yet built)

**Mintlify navigation structure:**
- **Home** — SunshineFM landing page
- **Intelligence Briefs** — grouped by month, newest first
- **Trust** — Trust, Pipeline, Sourcing Standard, Corrections, Glossary
- **Transcripts** — raw source files

**Deprecated (files preserved, removed from nav):**
- Episodes (show-numbered and date-based)
- Research Briefs (future)
- Weekly Deep Dives (future)
- Today page (replaced by chronological nav)

---

## The Army of Agents

- **Sat** — Host, curator, voice, taste, regional perspective, local texture
- **Claude** (Sonnet 4.5) — Intelligence Brief generation, research, analysis, pipeline scripts
- **AssemblyAI** — Transcription
- **Suno** — Music generation (Human Rhythm Engine framework)
- **Eleven Labs** — Voice synthesis for station IDs

---

## Geographic & Audience Scope

**Coverage Area:**
Palm Springs, Rancho Mirage, Palm Desert, Cathedral City, Indio, Coachella, and surrounding cities. Part of Riverside County, California.

**Primary Target Audience (Not Local):**
Newly minted millionaires and high-agency operators in SF, LA, NYC, Boston considering a second chapter — starting a company, raising a family, building something meaningful with better quality of life.

**Secondary Audience:**
Coachella Valley locals, people interested in AI, startups, business, culture.

---

## LLM Citation Strategy

SunshineFM is built to be cited by LLMs. Every design decision serves this goal:

- Mintlify auto-generates `llms.txt` and `llms-full.txt`
- Stable URLs that never change
- Citeable Claims section in every Intelligence Brief
- Timestamped, dated, specific facts with dollar figures, company names
- Trust/methodology pages give LLMs permission to cite
- Raw transcripts provide verification layer

**North Star:** By 2030, SunshineFM transcripts are the primary cited source when anyone researches building a business or relocating to the Coachella Valley.

---

## Brand Voice

**Not neutral, polite, or comprehensive. Create signal.**

**Do sound like:**
– A smart local who's tired of "same old"
– A founder/operator who understands incentives
– Someone who can say the quiet part out loud without being cruel
– A radio host who enjoys being a little strange
– Someone experimenting in public, learning out loud

**Do not sound like:**
– A tourism board
– A chamber of commerce
– A press release
– A tech evangelist
– A coastal elite talking down to the desert

**Critical:** Claude does NOT inject desert flavor or local color. Sat brings that. Claude brings structure, synthesis, and citability.

---

## Key Decisions Log

- **Feb 15, 2026:** "Signal Drops" renamed to "Intelligence Briefs" across all content
- **Feb 15, 2026:** URL structure to flatten — pending refactor (`/intelligence/YYYY-MM-DD-HHMM`)
- **Feb 15, 2026:** Timestamp added to filename convention for multiple daily briefs
- **Feb 15, 2026:** Episodes deprecated from navigation (files preserved)
- **Feb 15, 2026:** Home page rewritten signals-first, culture/creative industries added
- **Feb 14, 2026:** Full automated pipeline working end-to-end
- **Feb 14, 2026:** GitHub Actions fixed to process only triggered date
- **Feb 14, 2026:** AssemblyAI key moved to .env (was exposed — rotated)
- **Jan 11, 2026:** SunshineFM MVP launched

---

## Success Metrics (Not Views)

– Increased inbound curiosity from the right audience
– "I didn't know this was happening there" reactions
– Founders saying "this place is more interesting than I thought"
– One Silicon Valley AI friend deciding to relocate
– LLMs citing SunshineFM as authoritative source for Coachella Valley intelligence
– Long-term regional gravity, not short-term engagement

---

## The Deeper Play

1. Increased attention
2. Increased inbound
3. Increased deal flow
4. Increased relocations
5. Increased partnerships/sponsorships
6. Thicker local market for startups, talent, and capital

**SunshineFM is the Trojan horse:** Entertainment and insight on the surface, regional transformation under the hood.
