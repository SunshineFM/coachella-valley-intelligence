#!/usr/bin/env python3
import os
import re
import json
import time
import subprocess
import urllib.request
from typing import List, Tuple

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

TRANSCRIPTS_SOURCE_DIR = "transcripts/source"
TRANSCRIPTS_PAGES_DIR = "transcripts/pages"
EPISODES_DIR = os.path.join("intelligence", "episodes")
SIGNALS_DIR = "intelligence"
EPISODES_INDEX_PATH = os.path.join("intelligence", "episodes", "index.mdx")
SIGNALS_INDEX_PATH = os.path.join("intelligence", "index.mdx")

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


def mdx_frontmatter(title: str, description: str) -> str:
    title = (title or "").replace("'", "''").strip()
    description = (description or "").replace("'", "''").strip()
    return f"""---
title: '{title}'
description: '{description}'
---
"""


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
    Takes '2026-02-13-1500' and returns 'February 13, 2026 3:00pm'
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
                date_part = dt.strftime("%B %-d, %Y" if os.name != 'nt' else "%B %d, %Y").replace(' 0', ' ')
                hour = int(time[:2])
                minute = int(time[2:])
                period = "am" if hour < 12 else "pm"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                time_part = f"{display_hour}:{minute:02d}{period}" if minute > 0 else f"{display_hour}{period}"
                return f"{date_part} {time_part}"
            except:
                pass

    # Fallback: just format date without time
    try:
        parts = date_str.split('-')
        year, month, day = parts[:3]
        dt = datetime(int(year), int(month), int(day))
        return dt.strftime("%B %-d, %Y" if os.name != 'nt' else "%B %d, %Y").replace(' 0', ' ')
    except:
        return date_str


def extract_tag(text: str, tag: str) -> str:
    pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
    m = pattern.search(text)
    if not m:
        raise ValueError(f"Could not find <{tag}> tag in model output.")
    return m.group(1).strip()


def gen_episode_with_retry(date_str: str, transcript: str) -> Tuple[str, str, str]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = gen_episode(date_str, transcript)
            return result
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = attempt * 2
                print(f"  ⚠ Episode attempt {attempt} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ✗ Episode failed after {MAX_RETRIES} attempts: {e}")
    raise last_error


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


def gen_episode(date_str: str, transcript: str) -> Tuple[str, str, str]:
    system = """You are the editorial voice of SunshineFM — a sharp, opinionated intelligence platform broadcasting from Palm Springs Coachella.

You write like a founder who reads everything and has opinions about all of it. Not a journalist. Not a summarizer. Someone who was in the room, heard the show, and is now telling you what actually mattered and why.

VOICE RULES:
- Lead with the most important thing. Don't warm up slowly.
- Be specific. Exact dollar figures, company names, dates, local references.
- Have a point of view. If something is significant, say why. If something is overhyped, say that.
- Connect stories to Palm Springs Coachella specifically — which local sectors, which kinds of businesses, which people building here.
- Write in flowing prose, not template sections. Let the content determine the structure.
- Short punchy sentences when something lands hard. Longer sentences when you're building an argument.
- Never use: "delves into", "explores", "discusses", "in this episode", "Sat talks about"
- Never describe the show. Just say the thing.
- First person is fine where it fits naturally.

STRUCTURE:
- Do not include an H1 title in the body — the frontmatter title handles that.
- Open strong. The first paragraph should be the most important thing from the show — stated directly, with specifics.
- Use H2 headings only when a genuine topic shift happens, not on a schedule.
- Every major story gets its own space — don't compress a rich topic into two sentences because you're moving to the next section.
- End with something worth sitting with — a question, an implication, a local observation that lingers.

LENGTH: 900 to 1400 words of body content. This is a full intelligence report. Every story in the transcript deserves real treatment.

ABSOLUTE RULE: Do not invent facts, names, numbers, or claims not in the transcript."""

    user = f"""
Episode date: {date_str}

Write a full SunshineFM intelligence report from this transcript.

The report should flow like excellent longform writing — not like a filled-in template. Let the most important story lead. Give each major topic the space it deserves. Connect everything to what it means for people building or living in Palm Springs Coachella.

End with a "## Citeable Claims" section — 6 to 10 specific, verifiable facts from this episode with exact figures, names, and dates. These are for researchers and LLMs to cite directly.

Return your response using EXACTLY these XML tags and nothing else outside them:

<title>Your sharp, specific title here</title>
<description>Two sentence max description, specific enough to stand alone as a cited summary.</description>
<body_markdown>
Your full episode body markdown here, 900-1400 words.
</body_markdown>

TRANSCRIPT:
{transcript}
""".strip()

    raw = claude_chat(system, user)
    title = extract_tag(raw, "title")
    description = extract_tag(raw, "description")
    body = extract_tag(raw, "body_markdown")
    return title, description, body


def gen_signals(date_str: str, transcript: str) -> Tuple[str, str, str]:
    system = """You are SunshineFM's signals desk — the part of the operation that cuts through the noise and tells you exactly what moved today and why it matters.

Signals are not bullet point summaries. Each signal is a 2 to 4 sentence observation that includes:
- What specifically happened (with numbers, names, dates)
- Why it matters for Palm Springs Coachella or the people building here
- One implication or question worth sitting with

VOICE: Direct. Confident. Locally grounded. Slightly opinionated. No fluff, no hedging, no corporate language.

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
    title = f"{date_str} Raw Transcript"
    desc = "Raw transcript (source text)."

    body = "\n".join([
        "## Raw transcript",
        "",
        "```text",
        wrap_text(transcript, 110),
        "```",
    ])

    return mdx_frontmatter(title, desc) + "\n" + body + "\n"


def date_from_path(path: str) -> str:
    m = DATE_RE.match(path)
    return m.group(1) if m else ""


def write_outputs(date_str: str, transcript: str) -> None:
    sig_title, sig_desc, sig_body = gen_signals_with_retry(date_str, transcript)

    signals_path = os.path.join(SIGNALS_DIR, f"{date_str}.mdx")
    transcript_page_path = os.path.join(TRANSCRIPTS_PAGES_DIR, f"{date_str}.mdx")

    write_text(signals_path, mdx_frontmatter(sig_title, sig_desc) + "\n" + sig_body)
    write_text(transcript_page_path, make_transcript_page(date_str, transcript))


def update_episodes_index(new_dates: List[str]) -> None:
    return


def update_signals_index(new_dates: List[str]) -> None:
    return



def write_today_index() -> None:
    episode_files = sorted([
        f for f in os.listdir(EPISODES_DIR)
        if f.endswith(".mdx") and f != "index.mdx"
    ], reverse=True)
    signal_files = sorted([
        f for f in os.listdir(SIGNALS_DIR)
        if f.endswith(".mdx") and f != "index.mdx"
    ], reverse=True)
    latest_episode_link = ""
    if episode_files:
        slug = episode_files[0].replace(".mdx", "")
        ep_path = os.path.join(EPISODES_DIR, episode_files[0])
        title = slug
        with open(ep_path) as fh:
            for line in fh:
                if line.startswith("title:"):
                    title = line.split("title:", 1)[1].strip().strip('"')
                    break
        latest_episode_link = f"- [{slug}: {title}](/intelligence/episodes/{slug})"
    latest_signal_link = ""
    if signal_files:
        slug = signal_files[0].replace(".mdx", "")
        display_date = format_display_date(slug)
        latest_signal_link = f"- [{display_date} — Intelligence Brief](/intelligence/{slug})"
    transcript_links = ""
    if os.path.exists(TRANSCRIPTS_PAGES_DIR):
        tfiles = sorted([
            f for f in os.listdir(TRANSCRIPTS_PAGES_DIR)
            if f.endswith(".mdx")
        ], reverse=True)[:3]
        transcript_links = "\n".join([
            "- [" + f.replace(".mdx","").replace("-raw","") + " Raw Transcript](/transcripts/" + f.replace(".mdx","") + ")"
            for f in tfiles
        ])
    today_content = (
        "---\n"
        'title: "Today"\n'
        'description: "The latest SunshineFM intelligence for Palm Springs Coachella."\n'
        "---\n\n"
        "This page is updated daily. Tracking **Palm Springs Coachella**: AI, business, startups, and the local operator economy.\n\n"
        "## Latest flagship\n"
        + latest_episode_link + "\n\n"
        "## Latest signals\n"
        + latest_signal_link + "\n\n"
        "## Sources (raw transcripts)\n"
        + transcript_links + "\n"
    )
    today_path = os.path.join("intelligence", "today.mdx")
    with open(today_path, "w") as fh:
        fh.write(today_content)
    print("  today.mdx updated")

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
        path = os.path.join(TRANSCRIPTS_SOURCE_DIR, f"{forced_date}.txt")
        if not os.path.exists(path):
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

        transcript = read_text(path)
        if not transcript:
            continue

        print(f"\nProcessing {date_str}...")
        try:
            write_outputs(date_str, transcript)
            processed_dates.append(date_str)
            print(f"✓ Generated episode and signals for {date_str}")
        except Exception as e:
            failed_dates.append(date_str)
            print(f"✗ FAILED {date_str}: {e}")

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
