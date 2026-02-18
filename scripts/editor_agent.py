#!/usr/bin/env python3
"""
SunshineFM Editor Agent — Fact-check and enhance raw transcripts.
Sits between upload_to_assemblyai.py and generate_mintlify_artifacts.py.
Uses Claude API with web_search tool to verify claims and add annotations.

Usage: python3 editor_agent.py <YYYY-MM-DD-HHMM>
Example: python3 editor_agent.py 2026-02-16-1459
"""

import os
import sys
import json
import time
import re
import urllib.request

# Read API key from .env file (same pattern as upload_to_assemblyai.py)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            if _line.startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = _line.strip().split("=", 1)[1]

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
TRANSCRIPTS_SOURCE_DIR = "transcripts/source"
MAX_RETRIES = 3
MAX_WEB_SEARCHES = 30  # increased to support extra verification passes

CLAIM_EXTRACTION_SYSTEM = """\
You are a fact-checking research assistant for SunshineFM, \
a radio station broadcasting from Palm Springs Coachella.

Your task is to identify every specific, verifiable factual claim in a radio transcript. \
Focus on claims that can be checked against public sources:

- Funding amounts and valuations (e.g., "$1 billion acquisition")
- Specific dates and timelines (e.g., "Valentine's Day", "Friday the 13th")
- Person names and their roles (e.g., "Peter Steinberger from Austria")
- Company names and products (e.g., "OpenClaw", "ChatGPT 5.2")
- Statistics and metrics (e.g., "200,000 GitHub stars", "72 million daily users")
- Policy or regulatory claims (e.g., "$68 billion commitment")
- Job loss or economic figures (e.g., "55,000 US layoffs")
- Patent or legal claims (e.g., "Meta patent for post-death AI")

Do NOT flag:
- Opinions, predictions, or commentary
- Rhetorical questions
- Self-references by the host
- General knowledge statements
- Promotional content about the station

Return ONLY a valid JSON array. Each element must have these exact keys:
- "claim": the factual assertion in plain language
- "speaker_context": brief context about when/why this was said
- "category": one of "funding_amount", "date", "person_name", "company_name", \
"statistic", "product_detail", "patent_legal", "economic_figure"
- "quote_fragment": the exact words from the transcript (15-40 words) containing this claim

Return valid JSON only. No markdown fencing, no commentary."""

PROPER_NOUN_EXTRACTION_SYSTEM = """\
You are a proper noun extraction assistant for SunshineFM's editorial fact-checking pipeline.

Your task: extract every person name that appears alongside a company name, title, or role \
in the provided transcript.

Return ONLY a valid JSON array. Each element must have these exact keys:
- "name": the full person name as it appears in the transcript
- "company": the company or organization mentioned alongside this person
- "title": the title or role mentioned (e.g., "VP", "CEO", "editor", "founder")
- "quote_fragment": the exact transcript excerpt (10-30 words) where this person+company+title \
appears

Include EVERY distinct name+company+title combination. If the same name appears with \
DIFFERENT companies or roles, include a separate entry for each occurrence — this is \
the most important case to capture.

Return valid JSON only. No markdown fencing, no commentary."""

ENHANCEMENT_SYSTEM = """\
You are the Editor Agent for SunshineFM, a radio station in Palm Springs Coachella.

Your job is to ENHANCE a raw radio transcript with fact-checking annotations. \
You have access to web search to verify claims.

CRITICAL RULES:
1. PRESERVE the original transcript text EXACTLY. Do not rewrite, rephrase, paraphrase, \
or change Sat's words. His voice IS the product.
2. ADD annotations AFTER the relevant passages using bracket notation.
3. Use web search to verify every claim in the provided claims list.

ANNOTATION FORMAT — insert these IMMEDIATELY AFTER the sentence containing the claim:
- [VERIFIED: <one-line summary> — Source: <source name>] for confirmed facts
- [CORRECTION: <what the transcript says> should be <actual fact> — Source: <source name>] \
for incorrect claims
- [UNCONFIRMED: could not verify <specific claim>] for claims with no authoritative source
- [CONTEXT: WHO: / WHAT: / WHERE: / WHEN: / WHY: ] for key story claims that benefit from \
structured context (use only the fields that apply, not all five every time)

PROPER NOUN CORRECTION ANNOTATIONS — insert these for pre-flagged name issues:
- [CORRECTION NEEDED: <explanation of the conflict> — verify actual names before publishing]
- [UNCONFIRMED: <Name> as <Title> at <Company> — no public record found]

CITATION ANNOTATION — when the transcript cites a news source, search for the actual article:
- [VERIFIED SOURCE: "<Article Title>" — <Publication>, <Date> — <URL>] if article found
- [UNCONFIRMED: Source cited but article not located — verify publication details] if not found

ENHANCEMENT GUIDELINES:
- Fix obvious transcription errors in proper nouns inline with a [TRANSCRIPTION NOTE: X -> Y] \
annotation (e.g., "Amadai" -> "Amodei", "Chachi PT" -> "ChatGPT")
- For the WHO/WHAT/WHERE/WHEN/WHY annotations, add them to the FIRST mention of each major \
story, not every mention
- Group multiple related verifications into a single [CONTEXT: ...] block when they appear \
in the same paragraph
- At the END of the transcript, add a "--- CITATIONS ---" section listing all sources used
- Do NOT add annotations to opinions, commentary, rhetorical questions, or promotional segments
- If a claim is partially correct, use [VERIFIED] for the correct part and [CORRECTION] for \
the incorrect part

CITEABLE CLAIMS — EXTRA VERIFICATION REQUIRED:
- Executive names+titles: must have confirmed search results before marking [VERIFIED]
- Product names described as new/recent: must find announcement or release coverage
- Dollar figures: must find source document confirming the amount
- If verification search returns zero results: use [UNCONFIRMED] not [VERIFIED]
- If search results contradict the claim: use [CORRECTION NEEDED] with specifics

VOICE PRESERVATION:
- Sat's conversational style, rhetorical questions, direct appeals to listeners, \
parenthetical asides, and local-to-global framing are ALL preserved as-is
- Annotations are editorial markup, clearly separated from Sat's voice
- Think of yourself as a newspaper fact-checker adding margin notes, not a rewriter

PRE-FLAGGED PROPER NOUN ISSUES:
The following issues were detected in a pre-pass and MUST be addressed with search \
and annotation:
{proper_noun_flags}

PRE-FLAGGED SOURCE CITATION ISSUES:
The following named news sources require article search and citation annotation:
{source_citation_flags}

OUTPUT: Return the complete enhanced transcript with all annotations inline. \
End with a "--- CITATIONS ---" section."""


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def write_text(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n")


def claude_chat(system, user, use_web_search=False, max_tokens=8192):
    if not API_KEY:
        raise RuntimeError("Missing ANTHROPIC_API_KEY")

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    if use_web_search:
        payload["temperature"] = 0.3
        payload["tools"] = [{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": MAX_WEB_SEARCHES,
            "user_location": {
                "type": "approximate",
                "city": "Palm Springs",
                "region": "California",
                "country": "US",
                "timezone": "America/Los_Angeles",
            },
        }]
    else:
        payload["temperature"] = 0.2

    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


def claude_chat_with_continuation(system, user, use_web_search=False, max_tokens=16384):
    """Call Claude API with automatic continuation for pause_turn responses."""
    messages = [{"role": "user", "content": user}]
    all_content_blocks = []
    final_response = None

    while True:
        payload = {
            "model": MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }

        if use_web_search:
            payload["temperature"] = 0.3
            payload["tools"] = [{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": MAX_WEB_SEARCHES,
                "user_location": {
                    "type": "approximate",
                    "city": "Palm Springs",
                    "region": "California",
                    "country": "US",
                    "timezone": "America/Los_Angeles",
                },
            }]
        else:
            payload["temperature"] = 0.2

        headers = {
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=600) as resp:
            response = json.loads(resp.read().decode("utf-8"))

        content_blocks = response.get("content", [])
        all_content_blocks.extend(content_blocks)
        final_response = response

        stop_reason = response.get("stop_reason", "")
        if stop_reason == "pause_turn":
            print("    (pause_turn received, continuing...)")
            messages.append({"role": "assistant", "content": content_blocks})
            messages.append({"role": "user", "content": "Please continue."})
        else:
            break

    final_response["content"] = all_content_blocks
    return final_response


def claude_chat_with_retry(system, user, use_web_search=False, max_tokens=8192):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if use_web_search:
                response = claude_chat_with_continuation(
                    system, user, use_web_search=True, max_tokens=max_tokens
                )
            else:
                response = claude_chat(system, user, max_tokens=max_tokens)

            if response.get("type") == "error":
                error_msg = response.get("error", {}).get("message", "Unknown API error")
                raise RuntimeError(f"API error: {error_msg}")

            content = response.get("content", [])
            if not content:
                raise RuntimeError("Empty response from API")

            return response
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = attempt * 2
                if "rate" in str(e).lower() or "429" in str(e):
                    wait = attempt * 10
                print(f"  Warning: Attempt {attempt} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Error: Failed after {MAX_RETRIES} attempts: {e}")
    raise last_error


def extract_text_from_response(response):
    content_blocks = response.get("content", [])
    text_parts = []
    for block in content_blocks:
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
    return "".join(text_parts).strip()


def extract_citations_from_response(response):
    content_blocks = response.get("content", [])
    seen_urls = set()
    citations = []
    for block in content_blocks:
        if block.get("type") == "text" and "citations" in block:
            for cite in block["citations"]:
                url = cite.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    citations.append({
                        "url": url,
                        "title": cite.get("title", "Untitled"),
                        "cited_text": cite.get("cited_text", ""),
                    })
    return citations


def get_search_count(response):
    usage = response.get("usage", {})
    server_tool_use = usage.get("server_tool_use", {})
    return server_tool_use.get("web_search_requests", 0)


def extract_claims(transcript):
    print("  Calling Claude to identify verifiable claims...")
    user_message = f"Analyze this radio transcript and extract every specific, " \
        f"verifiable factual claim.\n\nTRANSCRIPT:\n{transcript}"

    response = claude_chat_with_retry(
        system=CLAIM_EXTRACTION_SYSTEM,
        user=user_message,
        max_tokens=4096,
    )

    raw_text = extract_text_from_response(response)

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        claims = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  Warning: Failed to parse claims JSON: {e}")
        print(f"  Raw response (first 500 chars): {raw_text[:500]}")
        claims = []

    print(f"  Extracted {len(claims)} verifiable claims")
    return claims


# ---------------------------------------------------------------------------
# Pass 1b: Proper noun verification
# ---------------------------------------------------------------------------

def extract_proper_noun_mentions(transcript):
    """Use Claude to extract all person+company+title mentions from the transcript."""
    print("  Extracting person/company/title mentions for proper noun check...")
    user_message = (
        "Extract all person names that appear alongside a company name, title, or role "
        "in this radio transcript. Pay special attention to cases where the same name "
        "appears with DIFFERENT companies or roles.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )
    response = claude_chat_with_retry(
        system=PROPER_NOUN_EXTRACTION_SYSTEM,
        user=user_message,
        max_tokens=2048,
    )
    raw_text = extract_text_from_response(response)
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        mentions = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"  Warning: Failed to parse proper noun JSON: {e}")
        print(f"  Raw response (first 300 chars): {raw_text[:300]}")
        mentions = []
    print(f"  Found {len(mentions)} person/company/title mentions")
    return mentions


def detect_proper_noun_flags(mentions):
    """
    Detect suspicious patterns in proper noun mentions:
    1. Same name appearing with multiple different companies/roles
    2. Structural symmetry suggesting AI generation error
    Returns a list of flag dicts describing each issue.
    """
    flags = []

    # Group mentions by normalized name
    by_name = {}
    for m in mentions:
        key = m.get("name", "").strip().lower()
        if not key:
            continue
        by_name.setdefault(key, []).append(m)

    for name_key, entries in by_name.items():
        if len(entries) < 2:
            continue

        # Check if the same name appears with different companies
        companies = [e.get("company", "").strip().lower() for e in entries]
        unique_companies = set(c for c in companies if c)
        if len(unique_companies) > 1:
            flags.append({
                "type": "duplicate_name_multiple_companies",
                "name": entries[0].get("name", name_key),
                "occurrences": entries,
                "unique_companies": list(unique_companies),
                "description": (
                    f'Same name "{entries[0].get("name", name_key)}" appears as '
                    + ", ".join(
                        f'{e.get("title","?")} at {e.get("company","?")}'
                        for e in entries
                    )
                    + " — verify that these are distinct real people"
                ),
            })

    # Detect "too perfect" structural symmetry:
    # e.g. "VP [Name] at Company A" and "VP [Name] at Company B" with same title pattern
    title_groups = {}
    for m in mentions:
        title = m.get("title", "").strip().lower()
        if title:
            title_groups.setdefault(title, []).append(m)

    for title, entries in title_groups.items():
        if len(entries) < 2:
            continue
        companies = [e.get("company", "").strip().lower() for e in entries]
        unique_companies = set(c for c in companies if c)
        names = [e.get("name", "").strip().lower() for e in entries]
        unique_names = set(n for n in names if n)
        # Flag if same title maps to same name but different companies — very suspicious
        if len(unique_names) == 1 and len(unique_companies) > 1:
            existing_flag_names = {f["name"].lower() for f in flags}
            if list(unique_names)[0] not in existing_flag_names:
                flags.append({
                    "type": "symmetry_pattern",
                    "name": entries[0].get("name", ""),
                    "occurrences": entries,
                    "unique_companies": list(unique_companies),
                    "description": (
                        f'Suspicious symmetry: same title "{title}" and same name '
                        f'"{entries[0].get("name","")}" appear at multiple companies '
                        f'({", ".join(unique_companies)}) — likely AI generation error'
                    ),
                })

    return flags


def format_proper_noun_flags_for_prompt(flags):
    """Render detected proper noun flags as a readable block for the enhancement prompt."""
    if not flags:
        return "(none detected)"
    lines = []
    for i, flag in enumerate(flags, 1):
        lines.append(f"{i}. {flag['description']}")
        for occ in flag.get("occurrences", []):
            lines.append(
                f'   - As "{occ.get("title","?")} at {occ.get("company","?")}" '
                f'— quote: "{occ.get("quote_fragment","")}"'
            )
        lines.append(
            f"   ACTION: Search for each combination, annotate with "
            f"[CORRECTION NEEDED: ...] if implausible, [UNCONFIRMED: ...] if no results found."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pass 1c: Source citation detection
# ---------------------------------------------------------------------------

# Named news outlets commonly cited in tech/AI news radio
SOURCE_PATTERNS = [
    r"\bBloomberg\b",
    r"\bThe Guardian\b",
    r"\bGuardian\b",
    r"\bYouGov\b",
    r"\bGeekWire\b",
    r"\bThe Economist\b",
    r"\bEconomist\b",
    r"\bWall Street Journal\b",
    r"\bWSJ\b",
    r"\bNew York Times\b",
    r"\bWired\b",
    r"\bTechCrunch\b",
    r"\bThe Verge\b",
    r"\bAxios\b",
    r"\bReuters\b",
    r"\bAP\b",
    r"\bAssociated Press\b",
    r"\bForbes\b",
    r"\bFortune\b",
    r"\bFT\b",
    r"\bFinancial Times\b",
]


def detect_source_citations(transcript):
    """
    Scan transcript for mentions of named news sources.
    Returns a list of dicts with the source name and surrounding context.
    """
    flags = []
    seen = set()
    sentences = re.split(r'(?<=[.!?])\s+', transcript)
    for pattern in SOURCE_PATTERNS:
        for sentence in sentences:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                source_name = match.group(0)
                key = (source_name.lower(), sentence[:60])
                if key not in seen:
                    seen.add(key)
                    flags.append({
                        "source": source_name,
                        "context": sentence.strip()[:200],
                        "description": (
                            f'Transcript cites "{source_name}" — '
                            f'search for the specific article/report and add citation URL'
                        ),
                    })
    return flags


def format_source_flags_for_prompt(flags):
    """Render detected source citation flags for the enhancement prompt."""
    if not flags:
        return "(none detected)"
    lines = []
    for i, flag in enumerate(flags, 1):
        lines.append(f"{i}. {flag['description']}")
        lines.append(f'   Context: "{flag["context"]}"')
        lines.append(
            "   ACTION: Search for the article, add [VERIFIED SOURCE: ...] or "
            "[UNCONFIRMED: Source cited but article not located — verify publication details]"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pass 2: Enhance transcript
# ---------------------------------------------------------------------------

def enhance_transcript(transcript, claims, proper_noun_flags, source_flags):
    claims_text = json.dumps(claims, indent=2) if claims else "[]"

    if claims:
        claims_instruction = f"CLAIMS TO VERIFY:\n{claims_text}\n\n"
    else:
        claims_instruction = (
            "No pre-extracted claims list available. Identify and verify all specific "
            "factual claims (funding amounts, dates, names, statistics, etc.) directly "
            "from the transcript.\n\n"
        )

    proper_noun_block = format_proper_noun_flags_for_prompt(proper_noun_flags)
    source_block = format_source_flags_for_prompt(source_flags)

    # Build system prompt with flags interpolated
    system = ENHANCEMENT_SYSTEM.format(
        proper_noun_flags=proper_noun_block,
        source_citation_flags=source_block,
    )

    user_message = (
        f"Here is a raw radio transcript from SunshineFM, followed by verifiable claims "
        f"and pre-flagged issues.\n\n"
        f"Your task:\n"
        f"1. Address every PRE-FLAGGED PROPER NOUN ISSUE first — search each flagged "
        f"name+company combination and annotate accordingly\n"
        f"2. Address every PRE-FLAGGED SOURCE CITATION — search for the named article "
        f"and add a citation annotation\n"
        f"3. Use web search to verify each claim in the claims list\n"
        f"4. Add inline annotations to the transcript (see system prompt for format)\n"
        f"5. Fix transcription errors in proper nouns\n"
        f"6. Add WHO/WHAT/WHERE/WHEN/WHY context blocks to the first mention of each "
        f"major story\n"
        f"7. Return the complete enhanced transcript\n\n"
        f"{claims_instruction}"
        f"TRANSCRIPT:\n{transcript}"
    )

    print("  Calling Claude with web search to fact-check and enhance...")
    response = claude_chat_with_retry(
        system=system,
        user=user_message,
        use_web_search=True,
        max_tokens=16384,
    )

    enhanced_text = extract_text_from_response(response)
    citations = extract_citations_from_response(response)
    search_count = get_search_count(response)

    stop_reason = response.get("stop_reason", "")
    if stop_reason == "max_tokens":
        print("  Warning: Response was truncated (max_tokens reached)")

    print(f"  Web searches performed: {search_count}")
    print(f"  Citations collected: {len(citations)}")

    return build_enhanced_output(enhanced_text, citations)


def build_enhanced_output(enhanced_text, citations):
    output_parts = [enhanced_text]

    if "--- CITATIONS ---" not in enhanced_text and citations:
        output_parts.append("\n\n--- CITATIONS ---")
        for i, cite in enumerate(citations, 1):
            title = cite.get("title", "Untitled")
            url = cite.get("url", "")
            output_parts.append(f"[{i}] {title}")
            output_parts.append(f"    {url}")

    output_parts.append(f"\n\n--- ENHANCEMENT METADATA ---")
    output_parts.append(f"Enhanced by: SunshineFM Editor Agent")
    output_parts.append(f"Model: {MODEL}")
    output_parts.append(f"Processed: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")

    return "\n".join(output_parts)


def main():
    if len(sys.argv) < 2:
        print("Usage: editor_agent.py <YYYY-MM-DD-HHMM>")
        print("Example: editor_agent.py 2026-02-16-1459")
        sys.exit(1)

    date_str = sys.argv[1]
    input_path = os.path.join(TRANSCRIPTS_SOURCE_DIR, f"{date_str}.txt")
    output_path = os.path.join(TRANSCRIPTS_SOURCE_DIR, f"{date_str}-enhanced.txt")

    if not os.path.exists(input_path):
        print(f"Error: Transcript not found: {input_path}")
        sys.exit(1)

    if not API_KEY:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    print("SunshineFM Editor Agent")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Model:  {MODEL}")
    print(f"  Timeout: 600s per web search request")
    print()

    transcript = read_text(input_path)
    if not transcript:
        print("Error: Transcript is empty")
        sys.exit(1)

    print(f"  Transcript size: {len(transcript):,} characters")
    print()

    # Pass 1a: Extract verifiable claims
    print("Pass 1a: Extracting verifiable claims...")
    try:
        claims = extract_claims(transcript)
    except Exception as e:
        print(f"  Warning: Claim extraction failed ({e}). Proceeding with single-pass mode.")
        claims = []
    print()

    # Pass 1b: Proper noun verification pre-pass
    print("Pass 1b: Proper noun verification pre-pass...")
    try:
        mentions = extract_proper_noun_mentions(transcript)
        proper_noun_flags = detect_proper_noun_flags(mentions)
        if proper_noun_flags:
            print(f"  Flagged {len(proper_noun_flags)} proper noun issue(s):")
            for flag in proper_noun_flags:
                print(f"    - {flag['description']}")
        else:
            print("  No suspicious proper noun patterns detected")
    except Exception as e:
        print(f"  Warning: Proper noun pre-pass failed ({e}). Continuing without flags.")
        proper_noun_flags = []
    print()

    # Pass 1c: Source citation detection
    print("Pass 1c: Detecting named source citations...")
    try:
        source_flags = detect_source_citations(transcript)
        if source_flags:
            print(f"  Found {len(source_flags)} named source citation(s) to verify:")
            for flag in source_flags:
                print(f"    - {flag['source']}: {flag['context'][:80]}...")
        else:
            print("  No named source citations detected")
    except Exception as e:
        print(f"  Warning: Source citation detection failed ({e}). Continuing without flags.")
        source_flags = []
    print()

    # Pass 2: Enhance with web search
    print("Pass 2: Fact-checking and enhancing transcript...")
    enhanced = enhance_transcript(transcript, claims, proper_noun_flags, source_flags)
    print()

    # Write output
    write_text(output_path, enhanced)
    print(f"  Enhanced transcript written to: {output_path}")
    print(f"  Output size: {len(enhanced):,} characters")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
