#!/usr/bin/env python3
import os
import re
import json
import time
import subprocess
import urllib.request
from typing import List, Tuple

# Load API key from .env when running locally.
# In GitHub Actions the env var is already set by the secrets context.
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.env")
if os.path.exists(_env_path) and not os.environ.get("ANTHROPIC_API_KEY"):
    with open(_env_path) as _f:
        for _line in _f:
            if _line.startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = _line.strip().split("=", 1)[1]

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

TRANSCRIPTS_SOURCE_DIR = "transcripts/source"
TRANSCRIPTS_PAGES_DIR = "transcripts/pages"
EPISODES_DIR = os.path.join("intelligence", "episodes")
SIGNALS_DIR = "intelligence"
EPISODES_INDEX_PATH = os.path.join("intelligence", "episodes", "index.mdx")
SIGNALS_INDEX_PATH = os.path.join("intelligence", "index.mdx")

# Matches raw transcript paths like transcripts/source/2026-02-17-1459.txt
DATE_RE = re.compile(r"^transcripts/source/(\d{4}-\d{2}-\d{2}(?:-\d{4})?)\.txt$")
MAX_RETRIES = 3


def sh(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def claude_chat(system: str, user: str) -> str:
    if not API_KEY:
        raise RuntimeError("Missing ANTHROPIC_API_KEY secret in GitHub Actions.")
    payload = {
        "model": MODEL,
        "max_tokens": 8192,
        "system": system,
        "messages": [
            {"role": "user", "content": user}
        ],
        "temperature": 0.5,
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        content_blocks = data.get("content", [])
        if content_blocks and len(content_blocks) > 0:
            return content_blocks[0].get("text", "").strip()
        return ""



def sanitize_mdx(text: str) -> str:
    """Escape dollar signs in MDX body only, not in frontmatter."""
    if text.startswith("---"):
        # Split frontmatter from body
        parts = text.split("---", 2)
        if len(parts) >= 3:
            # parts[0] is empty, parts[1] is frontmatter, parts[2] is body
            body = re.sub(r"(?<!\\)\$", r"\\$", parts[2])
            return "---" + parts[1] + "---" + body
    return re.sub(r"(?<!\\)\$", r"\\$", text)

def ensure_dirs() -> None:
    os.makedirs(EPISODES_DIR, exist_ok=True)
    os.makedirs(SIGNALS_DIR, exist_ok=True)  # Creates "intelligence" dir
    os.makedirs(TRANSCRIPTS_SOURCE_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTS_PAGES_DIR, exist_ok=True)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(sanitize_mdx(content.rstrip()) + "\n")



def mdx_frontmatter(title: str, description: str, sidebarTitle: str = None) -> str:
    title = (title or "").replace("'", "''").strip()
    description = (description or "").replace("'", "''").strip()

    frontmatter = f"""---
title: '{title}'
"""

    if sidebarTitle:
        sidebarTitle = (sidebarTitle or "").replace("'", "''").strip()
        frontmatter += f"sidebarTitle: '{sidebarTitle}'\n"
        frontmatter += "author: 'Sat Singh'\n"
        frontmatter += "location: 'Rancho Mirage, California'\n"
        frontmatter += "geographic_scope: 'Coachella Valley'\n"

    frontmatter += f"description: '{description}'\n---\n"
    return frontmatter


def wrap_text(s: str, width: int = 110) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = s.split("\n")
    out: List[str] = []
    for line in lines:
        if len(line) <= width:
            out.append(line)
            continue
        chunk = line
        while len(chunk) > width:
            out.append(chunk[:width])
            chunk = chunk[width:]
        if chunk:
            out.append(chunk)
    return "\n".join(out).strip()


def format_display_date(date_str: str) -> str:
    """Format date string for display.
    Takes '2026-02-13-1500' and returns 'February 13 · 3:00pm'
    Falls back gracefully if no time component present.
    """
    from datetime import datetime

    # Check if timestamp is present
    if len(date_str) > 10 and '-' in date_str[10:]:
        # Format: YYYY-MM-DD-HHMM
        parts = date_str.split('-')
        if len(parts) == 4:
            year, month, day, time = parts
            try:
                dt = datetime(int(year), int(month), int(day))
                date_part = dt.strftime("%B %-d" if os.name != 'nt' else "%B %d").replace(' 0', ' ')
                hour = int(time[:2])
                minute = int(time[2:])
                period = "am" if hour < 12 else "pm"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                time_part = f"{display_hour}:{minute:02d}{period}" if minute > 0 else f"{display_hour}{period}"
                return f"{date_part} · {time_part}"
            except:
                pass

    # Fallback: just format date without time
    try:
        parts = date_str.split('-')
        year, month, day = parts[:3]
        dt = datetime(int(year), int(month), int(day))
        return dt.strftime("%B %-d" if os.name != 'nt' else "%B %d").replace(' 0', ' ')
    except:
        return date_str


def extract_tag(text: str, tag: str) -> str:
    pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
    m = pattern.search(text)
    if not m:
        raise ValueError(f"Could not find <{tag}> tag in model output.")
    return m.group(1).strip()


def gen_signals_with_retry(date_str: str, transcript: str) -> Tuple[str, str, str]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = gen_signals(date_str, transcript)
            return result
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = attempt * 2
                print(f"  ⚠ Signals attempt {attempt} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ✗ Signals failed after {MAX_RETRIES} attempts: {e}")
    raise last_error


def gen_signals(date_str: str, transcript: str) -> Tuple[str, str, str]:
    system = """You are SunshineFM's signals desk — the part of the operation that cuts through the noise and tells you exactly what moved today and why it matters.

Signals are not bullet point summaries. Each signal is a 2 to 4 sentence observation that includes:
- What specifically happened (with numbers, names, dates)
- Why it matters for Palm Springs Coachella or the people building here
- One implication or question worth sitting with

VOICE: Direct. Confident. Locally grounded. Slightly opinionated. No fluff, no hedging, no corporate language.

You are also a fact-checking editor. When you encounter proper nouns in the transcript — including names of executives, companies, products, and organizations — correct any misspellings or phonetic transcription errors based on your knowledge. For example: "Amadai" should be "Amodei", "Chachi PT" should be "ChatGPT", "Anthropik" should be "Anthropic". Do not invent facts, but do correct obvious transcription errors in names you recognize.

IF THE TRANSCRIPT IS TOO SHORT: If the transcript is under 500 words or lacks sufficient content to generate 6 signals, do NOT pad or invent content. Instead generate only as many signals as the transcript genuinely supports — even if that is just 1 or 2. Write a note at the top of the body: "Note: This brief is shorter than usual due to limited broadcast content." Do not hallucinate events, statistics, company names, local items, or dates that are not present in the transcript.

GROUNDING RULE: Every signal must be directly traceable to something said in the transcript. If you cannot point to a specific moment in the transcript that supports a claim, do not include it. The Local Radar section must only include events or items mentioned in the transcript — do not generate plausible-sounding local events from general knowledge.

SOURCE FIDELITY RULE: Generate this Intelligence Brief using ONLY information explicitly stated in the source content provided. Do not supplement, expand, or correct using external world knowledge. If you cannot trace a claim directly to the source content, do not include it. If the source content is ambiguous or incomplete on a point, omit that point entirely rather than filling in the gap. If the source content is too short to support 6 signals, generate only as many signals as the content genuinely supports — even if that is just 2 or 3. Do not pad.

ABSOLUTE RULE: Do not invent facts."""

    user = f"""
Intelligence Brief date: {date_str}

Create a SunshineFM Intelligence Brief from this transcript.

REQUIREMENTS:
- Title format: "{format_display_date(date_str)} — Intelligence Brief"
- Write 6 to 10 signals
- Each signal needs a bold one-line header that names the actual story (not a generic label)
- Each signal body is 2 to 4 sentences — specific, local, opinionated
- End with a "## Local Radar" section: 3 to 5 upcoming local events, opportunities, or things worth watching in the Valley this week. Be specific — names, dates, locations where available.
- After Local Radar, add a "## Citeable Claims" section: 6-10 specific verifiable facts as a bulleted list. Include dates, dollar figures, company names, named individuals, and specific metrics from the transcript. Each claim should be independently verifiable.
- After Citeable Claims, add a "## The Signal" section: 2-3 sentences synthesizing the day's signals into one coherent thesis about what's changing and why it matters to Coachella Valley founders, operators, and decision-makers.
- Do NOT invent facts
- Do NOT include an H1 or H2 title at the top of the body — the frontmatter title handles that automatically

FORMAT EXAMPLE:
**$285B Wiped From Software Stocks After Anthropic Cowork Launch**
Anthropic's 11 new Claude Cowork plugins spooked Wall Street this week, erasing $285 billion from software stocks in a single day. The fear: if AI can review legal contracts and manage sales pipelines autonomously, why pay for Salesforce or LegalZoom? For Valley businesses with heavy admin overhead — real estate, estate planning, hospitality back office — this is worth watching closely. The question isn't if this changes your software stack. It's when.

Return your response using EXACTLY these XML tags and nothing else outside them:

<title>{format_display_date(date_str)} — Intelligence Brief</title>
<description>One sentence description of today's dominant signal.</description>
<body_markdown>
Your full signals body markdown here.
</body_markdown>

TRANSCRIPT:
{transcript}
""".strip()

    raw = claude_chat(system, user)
    title = extract_tag(raw, "title")
    description = extract_tag(raw, "description")
    body = extract_tag(raw, "body_markdown")
    return title, description, body


def changed_transcripts() -> List[str]:
    files: List[str] = []

    try:
        diff = sh(["git", "diff", "--name-only", "HEAD~1", "HEAD"])
        for line in diff.splitlines():
            line = line.strip()
            if DATE_RE.match(line):
                files.append(line)
    except Exception:
        pass

    if files:
        return sorted(set(files))

    candidates = []
    for fn in os.listdir(TRANSCRIPTS_SOURCE_DIR):
        if re.match(r"\d{4}-\d{2}-\d{2}(?:-\d{4})?\.txt$", fn):
            full = os.path.join(TRANSCRIPTS_SOURCE_DIR, fn)
            candidates.append((os.path.getmtime(full), full))

    candidates.sort(reverse=True)
    return [c[1] for c in candidates]  # Return all unprocessed transcripts


def make_transcript_page(date_str: str, transcript: str) -> str:
    title = f"{date_str} Transcript"
    desc = "Raw transcript (source text)."
    header = "## Transcript"
    source_note = "> This is the source transcript from SunshineFM.\n"

    body = "\n".join([
        source_note,
        "",
        header,
        "",
        "```text",
        wrap_text(transcript, 110),
        "```",
    ])

    return mdx_frontmatter(title, desc) + "\n" + body + "\n"


def date_from_path(path: str) -> str:
    m = DATE_RE.match(path)
    return m.group(1) if m else ""


def update_docs_json(date_str: str) -> None:
    """Update docs.json with the new intelligence brief.

    Prepends the new brief to the appropriate month group.
    Creates the month group if it doesn't exist, and sets the previous month to expanded: false.
    """
    from datetime import datetime
    import calendar

    docs_path = "docs.json"

    # Read current docs.json
    with open(docs_path, 'r', encoding='utf-8') as f:
        docs = json.load(f)

    # Extract year and month from date_str
    parts = date_str.split('-')
    year = int(parts[0])
    month = int(parts[1])
    month_name = calendar.month_name[month]
    month_label = f"{month_name} {year}"

    # Find the Intelligence Briefs group
    intel_briefs_group = None
    for group in docs['navigation']['groups']:
        if group['group'] == 'Intelligence Briefs':
            intel_briefs_group = group
            break

    if not intel_briefs_group:
        raise ValueError("Could not find 'Intelligence Briefs' group in docs.json")

    # Find or create the month group
    # pages should be: ["intelligence/index", {...month groups...}]
    # Start from index 1 (after intelligence/index)
    pages = intel_briefs_group['pages']
    month_group_idx = None
    month_group = None

    for idx, page in enumerate(pages[1:], start=1):  # Skip the first item (intelligence/index)
        if isinstance(page, dict) and page.get('group') == month_label:
            month_group_idx = idx
            month_group = page
            break

    brief_path = f"intelligence/{date_str}"

    if month_group:
        # Month group exists, prepend the new brief if not already present
        if brief_path not in month_group['pages']:
            month_group['pages'].insert(0, brief_path)
            print(f"  → Added {brief_path} to existing '{month_label}' group")
    else:
        # Create new month group
        # First, set previous month (if any) to expanded: false
        if len(pages) > 1 and isinstance(pages[1], dict):
            pages[1]['expanded'] = False
            print(f"  → Set '{pages[1]['group']}' to expanded: false")

        # Create and insert new month group at position 1 (after intelligence/index)
        new_month_group = {
            "group": month_label,
            "pages": [brief_path]
        }
        pages.insert(1, new_month_group)
        print(f"  → Created new month group '{month_label}' with {brief_path}")

    # Write back to docs.json
    with open(docs_path, 'w', encoding='utf-8') as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)
        f.write('\n')  # Add trailing newline


def update_transcripts_nav(date_str: str) -> None:
    """No-op: Transcripts group has been removed from nav."""
    return


def write_outputs(date_str: str, transcript: str) -> None:
    sig_title, sig_desc, sig_body = gen_signals_with_retry(date_str, transcript)

    # Extract sidebarTitle by stripping " — Intelligence Brief" suffix
    sidebar_title = sig_title.replace(" — Intelligence Brief", "")

    signals_path = os.path.join(SIGNALS_DIR, f"{date_str}.mdx")
    transcript_page_path = os.path.join(TRANSCRIPTS_PAGES_DIR, f"{date_str}.mdx")

    write_text(signals_path, mdx_frontmatter(sig_title, sig_desc, sidebar_title) + "\n" + sig_body)
    write_text(transcript_page_path, make_transcript_page(date_str, transcript))

    # Update docs.json with the new brief and transcript nav
    update_docs_json(date_str)
    update_transcripts_nav(date_str)


def update_episodes_index(new_dates: List[str]) -> None:
    return


def update_signals_index(new_dates: List[str]) -> None:
    return



def write_today_index() -> None:
    return

def main() -> None:
    import sys
    ensure_dirs()

    # Support --date YYYY-MM-DD argument for targeted processing
    forced_date = None
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        if idx + 1 < len(sys.argv):
            forced_date = sys.argv[idx + 1]

    if forced_date:
        # Verify at least the raw source exists before queuing
        raw_path = os.path.join(TRANSCRIPTS_SOURCE_DIR, f"{forced_date}.txt")
        if not os.path.exists(raw_path):
            print(f"No transcript found for {forced_date}")
            return
        files = [f"transcripts/source/{forced_date}.txt"]
    else:
        files = changed_transcripts()

    if not files:
        print("No transcript files found to process.")
        return

    processed_dates = []
    failed_dates = []

    for path in files:
        date_str = date_from_path(path)
        if not date_str:
            continue

        raw_path = os.path.join(TRANSCRIPTS_SOURCE_DIR, f"{date_str}.txt")
        if not os.path.exists(raw_path):
            print(f"  ✗ Skipping {date_str}: transcript not found ({raw_path})")
            failed_dates.append(date_str)
            continue

        print(f"\nProcessing {date_str}  [{raw_path}]")

        transcript = read_text(raw_path)
        if not transcript:
            print(f"  ✗ Skipping {date_str}: transcript is empty")
            failed_dates.append(date_str)
            continue

        try:
            write_outputs(date_str, transcript)
            processed_dates.append(date_str)
            print(f"  ✓ Generated brief and transcript page for {date_str}")
        except Exception as e:
            failed_dates.append(date_str)
            print(f"  ✗ FAILED {date_str}: {e}")

    if processed_dates:
        update_episodes_index(processed_dates)
        update_signals_index(processed_dates)
        write_today_index()

    if failed_dates:
        print(f"\n⚠ FAILED DATES — rerun manually: {', '.join(failed_dates)}")
    else:
        print(f"\n✓ All dates processed successfully")



if __name__ == "__main__":
    main()

# Override entry point to support --date argument
