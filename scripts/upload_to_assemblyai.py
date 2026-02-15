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

ASSEMBLY_API_KEY = "7dececb4df024a7a8b61c38abc83d93a"
REPO_DIR = os.path.expanduser("~/coachella-valley-intelligence")
TRANSCRIPTS_DIR = os.path.join(REPO_DIR, "transcripts/source")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def extract_date(filename):
    """Extract YYYY-MM-DD from Audio Hijack filename like '14 20260214 1500 VoiceOnly.mp3'"""
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
    subprocess.run(["git", "-C", REPO_DIR, "add", out_path], check=True)
    subprocess.run(["git", "-C", REPO_DIR, "commit", "-m", f"transcript: {date_str}"], check=True)
    subprocess.run(["git", "-C", REPO_DIR, "push"], check=True)
    log("Pushed to GitHub — GitHub Actions will generate intelligence files.")

if __name__ == "__main__":
    mp3_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not mp3_path or not os.path.exists(mp3_path):
        print("Usage: upload_to_assemblyai.py <path_to_mp3>")
        sys.exit(1)
    date_str = extract_date(os.path.basename(mp3_path))
    log(f"Processing {mp3_path} for date {date_str}")
    upload_url = upload_mp3(mp3_path)
    transcript_id = request_transcript(upload_url)
    transcript = poll_transcript(transcript_id)
    save_and_push(date_str, transcript)
    log("Done.")
