#!/usr/bin/env python3
import os
import re
import json
import subprocess
import urllib.request

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

TRANSCRIPTS_DIR = "transcripts"
EPISODES_DIR = os.path.join("intelligence", "episodes")
SIGNALS_DIR = os.path.join("intelligence", "signals")
TODAY_PATH = os.path.join("intelligence", "today.mdx")

DATE_RE = re.compile(r"transcripts/(\d{4}-\d{2}-\d{2})-raw\.txt$")

def sh(cmd: list[str]) -> str:
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
        "temperature": 0.4,
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

def ensure_dirs():
    os.makedirs(EPISODES_DIR, exist_ok=True)
    os.makedirs(SIGNALS_DIR, exist_ok=True)

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()

def write_text(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n")

def mdx_frontmatter(title: str, description: str) -> str:
    title = str(title).replace('"', '\\"').strip()
    description = str(description).replace('"', '\\"').strip()
    return f"""---
title: "{title}"
description: "{description}"
---
"""

def extract_json(text: str) -> str:
    """
    Extract the first JSON object from a model response.
    Works even if wrapped in prose or code fences.
    """
    # Strip code fences if present
    text = re.sub(r"^```(json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)

    # Find first '{' and last '}' (best-effort)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not find JSON object in model output.")
    return text[start : end + 1]

def safe_json_loads(raw: str) -> dict:
    """
    Parse JSON with a small retry that asks the model to repair JSON if needed.
    """
    try:
        return json.loads(raw)
    except Exception:
        fixer_system = "You repair JSON. Output ONLY valid JSON. No markdown. No commentary."
        fixer_user = f"Fix this into valid JSON:\n\n{raw}"
        fixed = openai_chat(fixer_system, fixer_user)
        fixed_obj = extract_json(fixed)
        return json.loads(fixed_obj)

def normalize_markdown(x) -> str:
    """
    Guarantee we return a markdown string.
    If the model returns a list/dict, convert it into readable markdown.
    """
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()

    # If signals accidentally came back as list-of-dicts, format them.
    if isinstance(x, list):
        lines = []
        for item in x:
            if isinstance(item, dict):
                wc = item.get("What changed") or item.get("what_changed") or item.get("whatChanged") or ""
                wm = item.get("Why it matters (Palm Springs Coachella)") or item.get("why_matters") or item.get("whyMatters") or ""
                wn = item.get("What to do next") or item.get("what_next") or item.get("whatNext") or ""
                aa = item.get("AI angle") or item.get("ai_angle") or item.get("aiAngle") or ""
                lines.append(f"- **What changed:** {str(wc).strip()}")
                lines.append(f"  - **Why it matters (Palm Springs Coachella):** {str(wm).strip()}")
                lines.append(f"  - **What to do next:** {str(wn).strip()}")
                lines.append(f"  - **AI angle:** {str(aa).strip()}")
            else:
                lines.append(f"- {str(item).strip()}")
        return "\n".join(lines).strip()

    if isinstance(x, dict):
        # If already structured, just JSON-dump into a code block so it doesn't break MDX
        return "```json\n" + json.dumps(x, indent=2) + "\n```"

    return str(x).strip()

def changed_transcripts() -> list[str]:
    """
    In push events: process changed transcript files.
    In workflow_dispatch: process newest transcript file.
    In workflow_run: often no 'before' diff; we fall back to newest transcript file.
    """
    before = ""
    sha = os.environ.get("GITHUB_SHA", "")

    # Try reading event payload
    try:
        event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        if event_path and os.path.exists(event_path):
            with open(event_path, "r", encoding="utf-8") as f:
                evt = json.load(f)
            before = (evt.get("before") or "").strip()
    except Exception:
        before = ""

    files: list[str] = []
    if before and sha and before != "0000000000000000000000000000000000000000":
        try:
            diff = sh(["git", "diff", "--name-only", before, sha])
            for line in diff.splitlines():
                line = line.strip()
                if DATE_RE.search(line):
                    files.append(line)
        except Exception:
            pass

    if files:
        return sorted(set(files))

    # fallback: newest transcript
    candidates = []
    if os.path.isdir(TRANSCRIPTS_DIR):
        for fn in os.listdir(TRANSCRIPTS_DIR):
            if re.match(r"\d{4}-\d{2}-\d{2}-raw\.txt$", fn):
                full = os.path.join(TRANSCRIPTS_DIR, fn)
                candidates.append((os.path.getmtime(full), full))
    candidates.sort(reverse=True)
    return [candidates[0][1]] if candidates else []

def gen_episode(date_str: str, transcript: str) -> tuple[str, str, str]:
    system = (
        "You are SunshineFM's lead editor. Write in Sat's voice: human, sharp, slightly witty, "
        "reflective, and locally grounded in Palm Springs Coachella. "
        "Never invent facts, names, numbers, or events. If something isn't in the transcript, omit it."
    )

    user = f"""
Episode date: {date_str}

Create a flagship episode page from the transcript.

REQUIREMENTS:
- Write a strong, human title (not just the date).
- Length target: 1,200–2,000 words unless the transcript is genuinely short.
- Use more of the transcript: pull in concrete details, not generic summaries.
- Include these H2 sections (in this order):

## What happened (fast summary)
- 8–12 bullets that reflect the real transcript content.

## The narrative (what Sat is really saying)
- 3–6 short paragraphs capturing the through-line and vibe.

## Key moments (timestamped if possible)
- 6–12 bullets. If you see timestamps in the transcript, include them like “(11:14) …”.
- If no timestamps exist, label them as “Moment 1…Moment 10”.

## The local angle (Palm Springs Coachella)
- 4–8 bullets, tied to what was actually discussed.

## The operator playbook (what to do next)
- 8–15 bullets written as actions for founders/operators.

## AI lens (what’s real vs hype)
- 6–10 bullets. Explicitly separate “Real” vs “Hype” when appropriate.

## Quotes
- 6–12 short, verbatim lines from the transcript. Keep each quote short.

## Key claims (copy/paste citeable)
- 10–15 bullets that are directly supported by the transcript.

- Do NOT invent names, meetings, companies, dates, or events that are not in the transcript.
- If the transcript is vague on a point, say so instead of guessing.

Return ONLY valid JSON:
{{
  "title": "...",
  "description": "...",
  "body_markdown": "markdown string"
}}

TRANSCRIPT:
{transcript}
""".strip()

    raw = openai_chat(system, user)
    data = safe_json_loads(extract_json(raw))

    title = str(data.get("title", f"{date_str} Episode")).strip()
    desc = str(data.get("description", "")).strip()
    body = normalize_markdown(data.get("body_markdown", ""))

    return title, desc, body

def render_signals_markdown(date_str: str, signals: list[dict], local_radar: list[str]) -> str:
    out = []
    for s in signals:
        wc = str(s.get("what_changed", "")).strip()
        wm = str(s.get("why_matters", "")).strip()
        wn = str(s.get("what_next", "")).strip()
        aa = str(s.get("ai_angle", "")).strip()

        out.append(f"- **What changed:** {wc}")
        out.append(f"  - **Why it matters (Palm Springs Coachella):** {wm}")
        out.append(f"  - **What to do next:** {wn}")
        out.append(f"  - **AI angle:** {aa}")
        out.append("")

    out.append("## Local radar")
    for item in local_radar:
        out.append(f"- {str(item).strip()}")

    return "\n".join(out).strip()

def gen_signals(date_str: str, transcript: str) -> tuple[str, str, str]:
    system = (
        "You are SunshineFM's signals desk. Tone: crisp, operational, local-first. "
        "Never invent facts. If the transcript doesn't support a signal, do not include it."
    )

    user = f"""
Signal date: {date_str}

Create a Signals page based ONLY on the transcript.

Return ONLY valid JSON with this exact schema:
{{
  "title": "{date_str}: Signal Drop",
  "description": "one sentence",
  "signals": [
    {{
      "what_changed": "...",
      "why_matters": "... (Palm Springs Coachella)",
      "what_next": "...",
      "ai_angle": "..."
    }}
  ],
  "local_radar": ["...", "..."]
}}

Rules:
- 5–10 signals
- local_radar: 3–7 bullets
- No extra keys, no markdown in JSON values beyond normal punctuation

TRANSCRIPT:
{transcript}
""".strip()

    raw = openai_chat(system, user)
    data = safe_json_loads(extract_json(raw))

    title = str(data.get("title", f"{date_str}: Signal Drop")).strip()
    desc = str(data.get("description", "")).strip()
    signals = data.get("signals", [])
    radar = data.get("local_radar", [])

    # If the model still returns something weird, normalize safely.
    if not isinstance(signals, list):
        signals = []
    signals = [s for s in signals if isinstance(s, dict)]
    if not isinstance(radar, list):
        radar = []
    radar = [str(x) for x in radar]

    body = render_signals_markdown(date_str, signals, radar)
    return title, desc, body

def update_today(latest_date: str, episode_title: str):
  """
  Update intelligence/today.mdx so 'Latest flagship' + 'Latest signals' point at the newest date.
  Uses MDX-safe markers: {/* ... */}
  """
  episode_link = f"/intelligence/episodes/{latest_date}"
  signals_link = f"/intelligence/signals/{latest_date}-signals"

  block = f"""{{/*AUTO:latest-start*/}}
## Latest flagship
- [{latest_date}: {episode_title}]({episode_link})

## Latest signals
- [{latest_date}: Signal Drop]({signals_link})
{{/*AUTO:latest-end*/}}
"""

  existing = ""
  if os.path.exists(TODAY_PATH):
    existing = read_text(TODAY_PATH)

  # Replace existing AUTO block if present
  if "{/*AUTO:latest-start*/}" in existing and "{/*AUTO:latest-end*/}" in existing:
    new = re.sub(
      r"\{\/*AUTO:latest-start\*\/\}.*?\{\/*AUTO:latest-end\*\/\}",
      block.strip(),
      existing,
      flags=re.DOTALL,
    )
    write_text(TODAY_PATH, new)
    return

  # Otherwise append (or create)
  if existing:
    write_text(TODAY_PATH, existing.rstrip() + "\n\n" + block)
  else:
    minimal = f"""---
title: "Today"
description: "The latest SunshineFM intelligence for Palm Springs Coachella: newest flagship, newest signals, and transcript-backed links."
---

{block}
"""
    write_text(TODAY_PATH, minimal)
