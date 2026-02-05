#!/usr/bin/env python3
import os
import re
import json
import subprocess
import urllib.request
from typing import List, Tuple

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

TRANSCRIPTS_DIR = "transcripts"
EPISODES_DIR = os.path.join("intelligence", "episodes")
SIGNALS_DIR = os.path.join("intelligence", "signals")

# Matches: transcripts/2026-02-04-raw.txt
DATE_RE = re.compile(r"^transcripts/(\d{4}-\d{2}-\d{2})-raw\.txt$")


def sh(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def openai_chat(system: str, user: str) -> str:
    if not API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY secret in GitHub Actions.")
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.5,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


def ensure_dirs() -> None:
    os.makedirs(EPISODES_DIR, exist_ok=True)
    os.makedirs(SIGNALS_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n")


def mdx_frontmatter(title: str, description: str) -> str:
    title = (title or "").replace('"', '\\"').strip()
    description = (description or "").replace('"', '\\"').strip()
    return f"""---
title: "{title}"
description: "{description}"
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


def extract_json(text: str) -> str:
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("Could not find JSON object in model output.")
    return m.group(0)


def safe_json_loads(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        repaired = re.sub(r",\s*([}\]])", r"\1", raw)
        return json.loads(repaired)


def gen_episode(date_str: str, transcript: str) -> Tuple[str, str, str]:
    system = (
        "You are SunshineFM's lead editor. Write in Sat's voice: human, sharp, slightly witty, "
        "reflective, and locally grounded in Palm Springs Coachella. "
        "Output must be clean Markdown/MDX with headings and bullet clarity. "
        "ABSOLUTE RULE: Do not invent facts, names, events, or claims not present in the transcript."
    )

    user = f"""
Episode date: {date_str}

TASK:
Create a flagship episode page from the transcript.

REQUIREMENTS:
- Create a strong, human title (not just the date).
- Use H2 headings for these sections:
  1) What happened (fast summary)
  2) The local angle (Palm Springs Coachella)
  3) What to do next (operators / founders)
  4) AI lens (where it's real vs overhyped)
  5) Quotes (3–6 short verbatim lines)
- Add a "Key claims (copy/paste citeable)" bullet list (5–9 bullets).
- Do NOT invent names, meetings, releases, stats, or news.

Return STRICT JSON only:
{{
  "title": "...",
  "description": "...",
  "body_markdown": "..."
}}

TRANSCRIPT:
{transcript}
""".strip()

    raw = openai_chat(system, user)
    data = safe_json_loads(extract_json(raw))
    return (
        str(data.get("title", "")).strip(),
        str(data.get("description", "")).strip(),
        str(data.get("body_markdown", "")).strip(),
    )


def gen_signals(date_str: str, transcript: str) -> Tuple[str, str, str]:
    system = (
        "You are SunshineFM's signals desk. Tone: crisp, operational, local-first. "
        "Short sentences. Clear actions. No fluff. "
        "ABSOLUTE RULE: Do not invent facts, names, events, or claims not present in the transcript."
    )

    user = f"""
Signal date: {date_str}

TASK:
Create a Signals page based on the transcript.

REQUIREMENTS:
- Title format exactly: "{date_str}: Signal Drop"
- Include 5–10 signals. Each signal must follow this exact mini-template:

### Signal N: <short name>
- What changed:
- Why it matters (Palm Springs Coachella):
- What to do next:
- AI angle:

- End with "Local radar" (3–7 bullets).
- Do NOT invent facts.

Return STRICT JSON only:
{{
  "title": "...",
  "description": "...",
  "body_markdown": "..."
}}

TRANSCRIPT:
{transcript}
""".strip()

    raw = openai_chat(system, user)
    data = safe_json_loads(extract_json(raw))
    return (
        str(data.get("title", "")).strip(),
        str(data.get("description", "")).strip(),
        str(data.get("body_markdown", "")).strip(),
    )


def changed_transcripts() -> List[str]:
    before = ""
    sha = os.environ.get("GITHUB_SHA", "")

    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if event_path and os.path.exists(event_path):
        try:
            with open(event_path, "r", encoding="utf-8") as f:
                evt = json.load(f)
            before = evt.get("before", "") or ""
        except Exception:
            before = ""

    files: List[str] = []
    if before and sha and before != "0000000000000000000000000000000000000000":
        try:
            diff = sh(["git", "diff", "--name-only", before, sha])
            for line in diff.splitlines():
                line = line.strip()
                if DATE_RE.match(line):
                    files.append(line)
        except Exception:
            pass

    if files:
        return sorted(set(files))

    candidates = []
    if os.path.isdir(TRANSCRIPTS_DIR):
        for fn in os.listdir(TRANSCRIPTS_DIR):
            if re.match(r"\d{4}-\d{2}-\d{2}-raw\.txt$", fn):
                full = os.path.join(TRANSCRIPTS_DIR, fn)
                candidates.append((os.path.getmtime(full), full))
    candidates.sort(reverse=True)
    return [candidates[0][1]] if candidates else []


def make_transcript_page(date_str: str, transcript: str) -> str:
    title = f"{date_str} Raw Transcript"
    desc = "Raw transcript (source text)."
    body = f"""
## Raw transcript

```text
{wrap_text(transcript, 110)}

“””.strip()
return mdx_frontmatter(title, desc) + “\n” + body + “\n”

def date_from_path(path: str) -> str:
m = DATE_RE.match(path)
if not m:
return “”
return m.group(1)

def write_outputs(date_str: str, transcript: str) -> None:
# Generate episode + signals (AI)
ep_title, ep_desc, ep_body = gen_episode(date_str, transcript)
sig_title, sig_desc, sig_body = gen_signals(date_str, transcript)

# File paths (Mintlify-safe + predictable)
episode_path = os.path.join(EPISODES_DIR, f"{date_str}.mdx")
signals_path = os.path.join(SIGNALS_DIR, f"{date_str}-signals.mdx")

# Raw transcript gets its own Mintlify page (so /transcripts/YYYY-MM-DD-raw works)
transcript_page_path = os.path.join(TRANSCRIPTS_DIR, f"{date_str}-raw.mdx")

# Write
write_text(episode_path, mdx_frontmatter(ep_title, ep_desc) + "\n" + (ep_body or "").strip() + "\n")
write_text(signals_path, mdx_frontmatter(sig_title, sig_desc) + "\n" + (sig_body or "").strip() + "\n")
write_text(transcript_page_path, make_transcript_page(date_str, transcript))

print("Generated:")
print(f"- {episode_path}")
print(f"- {signals_path}")
print(f"- {transcript_page_path}")

def main() -> None:
ensure_dirs()

files = changed_transcripts()
if not files:
    print("No transcript files found to process.")
    return

# Normalize to "transcripts/...." relative paths
norm_files: List[str] = []
for p in files:
    p = p.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    norm_files.append(p)

for path in norm_files:
    date_str = date_from_path(path)
    if not date_str:
        print(f"Skipping non-matching file: {path}")
        continue

    transcript = read_text(path)
    if not transcript.strip():
        print(f"Skipping empty transcript: {path}")
        continue

    write_outputs(date_str, transcript)

    if name == “main”:
main()
