#!/usr/bin/env python3
import os
import re
import json
import subprocess
import urllib.request
from datetime import datetime

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
    "temperature": 0.6,
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

def changed_transcripts() -> list[str]:
  """
  In a push event, find which transcript files changed.
  If workflow_dispatch (no before SHA), fall back to newest transcript file.
  """
  before = os.environ.get("GITHUB_EVENT_BEFORE", "")
  sha = os.environ.get("GITHUB_SHA", "")

  # Try to read the GitHub event json to get "before"
  try:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if event_path and os.path.exists(event_path):
      with open(event_path, "r", encoding="utf-8") as f:
        evt = json.load(f)
      before = evt.get("before", before) or before
  except Exception:
    pass

  files: list[str] = []
  if before and sha and before != "0000000000000000000000000000000000000000":
    try:
      diff = sh(["git", "diff", "--name-only", before, sha])
      for line in diff.splitlines():
        if DATE_RE.search(line):
          files.append(line.strip())
    except Exception:
      pass

  if files:
    return sorted(set(files))

  # fallback: newest transcript
  candidates = []
  if os.path.isdir(TRANSCRIPTS_DIR):
    for fn in os.listdir(TRANSCRIPTS_DIR):
      if fn.endswith("-raw.txt") and re.match(r"\d{4}-\d{2}-\d{2}-raw\.txt$", fn):
        full = os.path.join(TRANSCRIPTS_DIR, fn)
        candidates.append((os.path.getmtime(full), full))
  candidates.sort(reverse=True)
  return [candidates[0][1]] if candidates else []

def read_text(path: str) -> str:
  with open(path, "r", encoding="utf-8", errors="ignore") as f:
    return f.read().strip()

def write_text(path: str, content: str):
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", encoding="utf-8") as f:
    f.write(content.rstrip() + "\n")

def mdx_frontmatter(title: str, description: str) -> str:
  # Mintlify is fine with YAML frontmatter. Keep it simple.
  title = title.replace('"', '\\"').strip()
  description = description.replace('"', '\\"').strip()
  return f"""---
title: "{title}"
description: "{description}"
---
"""

def gen_episode(date_str: str, transcript: str) -> tuple[str, str]:
  system = (
    "You are SunshineFM's lead editor. Write in Sat's voice: human, sharp, slightly witty, "
    "reflective, and locally grounded in Palm Springs Coachella. "
    "Output must be clean MDX/markdown with headings and bullet clarity. No hallucinated facts."
  )

  user = f"""
Episode date: {date_str}

TASK:
Create a flagship episode page from the transcript.

REQUIREMENTS:
- Create a strong, human title (not just the date).
- Include sections with H2 headings:
  1) What happened (fast summary)
  2) The local angle (Palm Springs Coachella)
  3) What to do next (operators / founders)
  4) AI lens (how AI applies, where it's overhyped, where it's real)
  5) Quotes (3–6 short, verbatim lines from the transcript; keep them short)
- Add a short "Key claims (copy/paste citeable)" bullet list (5–9 bullets).
- Do NOT invent names, meetings, or events not present in transcript.

Return JSON with:
{{
  "title": "...",
  "description": "...",
  "body_markdown": "..."
}}

TRANSCRIPT:
{transcript}
""".strip()

  raw = openai_chat(system, user)
  data = json.loads(extract_json(raw))
  return data["title"], data["description"], data["body_markdown"]

def gen_signals(date_str: str, transcript: str) -> tuple[str, str]:
  system = (
    "You are SunshineFM's signals desk. Tone: crisp, operational, local-first. "
    "Short sentences. Clear actions. No fluff."
  )

  user = f"""
Signal date: {date_str}

TASK:
Create a Signals page based on the transcript. Think of signals as: what changed, why it matters locally,
what to build/do next, and the AI angle.

REQUIREMENTS:
- Title format: "{date_str}: Signal Drop"
- Include 5–10 signals. Each signal must follow this exact mini-template:
  - What changed:
  - Why it matters (Palm Springs Coachella):
  - What to do next:
  - AI angle:
- End with "Local radar" (3–7 bullets of things to watch next).
- Do NOT invent facts.

Return JSON with:
{{
  "title": "...",
  "description": "...",
  "body_markdown": "..."
}}

TRANSCRIPT:
{transcript}
""".strip()

  raw = openai_chat(system, user)
  data = json.loads(extract_json(raw))
  return data["title"], data["description"], data["body_markdown"]

def extract_json(text: str) -> str:
  """
  Be forgiving if the model wraps JSON in text. Grab the first {...} block.
  """
  m = re.search(r"\{.*\}", text, flags=re.DOTALL)
  if not m:
    raise ValueError("Could not find JSON in model output.")
  return m.group(0)

def update_today(latest_date: str, episode_title: str):
  """
  Update intelligence/today.mdx so 'Latest flagship' + 'Latest signals' point at the newest date.
  Uses markers. If missing, appends a minimal block.
  """
  episode_link = f"/intelligence/episodes/{latest_date}"
  signals_link = f"/intelligence/signals/{latest_date}-signals"

  block = f"""<!--AUTO:latest-start-->
## Latest flagship
- [{latest_date}: {episode_title}]({episode_link})

## Latest signals
- [{latest_date}: Signal Drop]({signals_link})
<!--AUTO:latest-end-->
"""

  existing = ""
  if os.path.exists(TODAY_PATH):
    existing = read_text(TODAY_PATH)

  if "<!--AUTO:latest-start-->" in existing and "<!--AUTO:latest-end-->" in existing:
    new = re.sub(
      r"<!--AUTO:latest-start-->.*?<!--AUTO:latest-end-->",
      block.strip(),
      existing,
      flags=re.DOTALL,
    )
    write_text(TODAY_PATH, new)
  else:
    # If today.mdx exists, append; otherwise create a minimal page
    if existing:
      write_text(TODAY_PATH, existing + "\n\n" + block)
    else:
      minimal = f"""---
title: "Today"
description: "The latest SunshineFM intelligence for Palm Springs Coachella."
---

{block}
"""
      write_text(TODAY_PATH, minimal)

def main():
  ensure_dirs()

  files = changed_transcripts()
  if not files:
    print("No transcript files found to process.")
    return

  for path in files:
    m = DATE_RE.search(path)
    if not m:
      print(f"Skipping non-matching file: {path}")
      continue

    date_str = m.group(1)
    transcript = read_text(path)

    # Generate episode + signals
    ep_title, ep_desc, ep_body = gen_episode(date_str, transcript)
    sig_title, sig_desc, sig_body = gen_signals(date_str, transcript)

    # Write files
    episode_path = os.path.join(EPISODES_DIR, f"{date_str}.mdx")
    signals_path = os.path.join(SIGNALS_DIR, f"{date_str}-signals.mdx")

    write_text(episode_path, mdx_frontmatter(ep_title, ep_desc) + "\n" + ep_body.strip() + "\n")
    write_text(signals_path, mdx_frontmatter(sig_title, sig_desc) + "\n" + sig_body.strip() + "\n")

    # Update Today page pointer
    update_today(date_str, ep_title)

    print(f"Generated:\n- {episode_path}\n- {signals_path}\n- {TODAY_PATH}")

if __name__ == "__main__":
  main()
