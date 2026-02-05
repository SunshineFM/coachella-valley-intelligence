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
    If workflow_dispatch (or can't diff), fall back to newest transcript file.
    """
    before = ""
    sha = os.environ.get("GITHUB_SHA", "")

    # Try to read GitHub event payload for "before"
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
                if DATE_RE.search(line.strip()):
                    files.append(line.strip())
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


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def write_text(path: str, content: str):
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


def extract_json(text: str) -> dict:
    """
    Pull the first JSON object out of model output, then parse.
    """
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("Could not find JSON in model output.")
    return json.loads(m.group(0))


def normalize_body(body) -> str:
    """
    Sometimes the model returns a list/array. Force it into a string.
    """
    if body is None:
        return ""
    if isinstance(body, str):
        return body
    if isinstance(body, list):
        return "\n".join(str(x) for x in body)
    return str(body)


def gen_episode(date_str: str, transcript: str) -> tuple[str, str, str]:
    system = (
        "You are SunshineFM's lead editor. Write in Sat's voice: human, sharp, slightly witty, "
        "reflective, and locally grounded in Palm Springs Coachella. "
        "Output must be clean Markdown/MDX with headings and bullet clarity. No hallucinated facts."
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
    data = extract_json(raw)

    title = str(data.get("title", "")).strip() or f"{date_str}: Flagship"
    desc = str(data.get("description", "")).strip() or f"SunshineFM flagship for {date_str}."
    body = normalize_body(data.get("body_markdown", "")).strip()

    return title, desc, body


def gen_signals(date_str: str, transcript: str) -> tuple[str, str, str]:
    system = (
        "You are SunshineFM's signals desk. Tone: crisp, operational, local-first. "
        "Short sentences. Clear actions. No fluff."
    )

    user = f"""
Signal date: {date_str}

TASK:
Create a Signals page based on the transcript.

REQUIREMENTS:
- Title format: "{date_str}: Signal Drop"
- Include 5–10 signals. Each signal must follow this exact mini-template:
  - **What changed:**
  - **Why it matters (Palm Springs Coachella):**
  - **What to do next:**
  - **AI angle:**
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
    data = extract_json(raw)

    title = str(data.get("title", "")).strip() or f"{date_str}: Signal Drop"
    desc = str(data.get("description", "")).strip() or f"Signals for {date_str}."
    body = normalize_body(data.get("body_markdown", "")).strip()

    return title, desc, body


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

        ep_title, ep_desc, ep_body = gen_episode(date_str, transcript)
        sig_title, sig_desc, sig_body = gen_signals(date_str, transcript)

        episode_path = os.path.join(EPISODES_DIR, f"{date_str}.mdx")
        signals_path = os.path.join(SIGNALS_DIR, f"{date_str}-signals.mdx")

        write_text(episode_path, mdx_frontmatter(ep_title, ep_desc) + "\n" + ep_body + "\n")
        write_text(signals_path, mdx_frontmatter(sig_title, sig_desc) + "\n" + sig_body + "\n")

        print(f"Generated:\n- {episode_path}\n- {signals_path}")


if __name__ == "__main__":
    main()
