#!/usr/bin/env python3
"""
SunshineFM — AssemblyAI Upload Script
Hazel triggers this when a new VoiceOnly MP3 appears in recordings/.
Job: Upload to AssemblyAI → wait for transcript → save to transcripts/source/YYYY-MM-DD.txt → git push
"""

import os
import sys
import re
import time
import json
import subprocess
import urllib.request
from datetime import datetime

# Read API key from .env file
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            if _line.startswith("ASSEMBLYAI_API_KEY="):
                os.environ["ASSEMBLYAI_API_KEY"] = _line.strip().split("=", 1)[1]
ASSEMBLY_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")
REPO_DIR = os.path.expanduser("~/coachella-valley-intelligence")
TRANSCRIPTS_DIR = os.path.join(REPO_DIR, "transcripts/source")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def extract_date_time(filename):
    """Extract YYYY-MM-DD-HHMM from Audio Hijack filename like '14 20260214 1500 VoiceOnly.mp3'"""
    # Pattern: DD YYYYMMDD HHMM VoiceOnly.mp3
    m = re.search(r'(\d{4})(\d{2})(\d{2})\s+(\d{4})', filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}"
    # Fallback: try date only
    m = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return datetime.now().strftime("%Y-%m-%d")

def upload_mp3(mp3_path):
    log(f"Uploading {os.path.basename(mp3_path)} to AssemblyAI...")
    with open(mp3_path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(
        "https://api.assemblyai.com/v2/upload",
        data=data,
        headers={"authorization": ASSEMBLY_API_KEY},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["upload_url"]

def request_transcript(upload_url):
    log("Requesting transcription...")
    payload = json.dumps({"audio_url": upload_url}).encode()
    req = urllib.request.Request(
        "https://api.assemblyai.com/v2/transcript",
        data=payload,
        headers={
            "authorization": ASSEMBLY_API_KEY,
            "content-type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["id"]

def poll_transcript(transcript_id):
    log("Waiting for transcript...")
    url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    while True:
        req = urllib.request.Request(url, headers={"authorization": ASSEMBLY_API_KEY})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        status = data["status"]
        if status == "completed":
            log("Transcription complete.")
            return data["text"]
        elif status == "error":
            raise RuntimeError(f"AssemblyAI error: {data.get('error')}")
        log(f"Status: {status} — waiting 15s...")
        time.sleep(15)

def save_and_push(date_str, transcript):
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    out_path = os.path.join(TRANSCRIPTS_DIR, f"{date_str}.txt")
    with open(out_path, "w") as f:
        f.write(transcript)
    log(f"Saved transcript to {out_path}")
    # Append timestamp to ensure file always has a change to commit
    with open(out_path, "a") as f:
        f.write(f"\n# processed: {datetime.utcnow().isoformat()}")
    subprocess.run(["git", "-C", REPO_DIR, "add", out_path], check=True)
    subprocess.run(["git", "-C", REPO_DIR, "commit", "-m", f"transcript: {date_str}"], check=True)
    subprocess.run(["git", "-C", REPO_DIR, "push"], check=True)
    log("Pushed to GitHub — GitHub Actions will generate intelligence files.")

if __name__ == "__main__":
    mp3_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not mp3_path or not os.path.exists(mp3_path):
        print("Usage: upload_to_assemblyai.py <path_to_mp3>")
        sys.exit(1)
    date_str = extract_date_time(os.path.basename(mp3_path))
    log(f"Processing {mp3_path} for datetime {date_str}")
    upload_url = upload_mp3(mp3_path)
    transcript_id = request_transcript(upload_url)
    transcript = poll_transcript(transcript_id)
    save_and_push(date_str, transcript)
    log("Done.")
