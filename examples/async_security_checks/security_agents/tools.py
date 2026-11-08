"""Slow, deterministic tools for the three checkers.

In the original pattern each check was a single LLM call that finished in a
couple of seconds, so there was nothing to wait for. Real security checks are
slower: a DLP scan, a threat-intel lookup, a sandbox detonation. These tools
stand in for that work with a fixed `asyncio.sleep`, so the async behavior is
visible and the test windows (update, cancel) are predictable.

The detection logic is plain regex on purpose: the verdict must not depend on
the model, so a test failure points at the async machinery, not at the model.
Each delay comes from an env var (see .env.example).
"""

import asyncio
import os
import re

from langchain_core.tools import tool


def _seconds(name: str, default: float) -> float:
    return float(os.getenv(name, default))


INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"reveal .*system prompt",
    r"disregard .*(rules|instructions)",
    r"you are now",
    r"confidential tools",
]

PII_PATTERNS = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "phone": r"\+?\d{1,2}[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "street_address": r"\b\d{1,5}\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road|Blvd)\b",
}

MALWARE_INDICATORS = [
    r"\.exe\b",
    r"encrypts? (user )?files",
    r"hidden payload",
    r"remote server",
    r"ransom",
]


@tool
async def injection_pattern_scan(text: str) -> str:
    """Scan text against a library of known prompt-injection phrasings.

    Args:
        text: The exact input text under review.
    """
    await asyncio.sleep(_seconds("INJECTION_SCAN_SECONDS", 20))
    hits = [p for p in INJECTION_PATTERNS if re.search(p, text, re.IGNORECASE)]
    if hits:
        return f"MATCH: {len(hits)} injection pattern(s): {hits}"
    return "NO MATCH: no known injection patterns found."


@tool
async def dlp_scan(text: str) -> str:
    """Run a data-loss-prevention scan for personally identifiable information.

    Args:
        text: The exact input text under review.
    """
    await asyncio.sleep(_seconds("DLP_SCAN_SECONDS", 30))
    found = {kind: re.findall(p, text) for kind, p in PII_PATTERNS.items()}
    found = {kind: vals for kind, vals in found.items() if vals}
    if found:
        return f"PII FOUND: {found}"
    return "NO PII: no PII detected."


@tool
async def detonate_in_sandbox(sample: str) -> str:
    """Detonate a described file or payload in an isolated sandbox and report its behavior.

    This is the slowest check. Args:
        sample: The exact input text describing the file or payload.
    """
    await asyncio.sleep(_seconds("SANDBOX_SECONDS", 90))
    hits = [p for p in MALWARE_INDICATORS if re.search(p, sample, re.IGNORECASE)]
    if len(hits) >= 2:
        return f"MALICIOUS: {len(hits)} indicators observed: {hits}. Quarantine recommended."
    if hits:
        return f"SUSPICIOUS: 1 indicator observed: {hits}."
    return "CLEAN: no malicious behavior observed."


@tool
def quarantine_sample(sample_name: str, reason: str) -> str:
    """Move a malicious sample into quarantine. Requires human approval.

    Args:
        sample_name: Short name of the sample, such as the file name.
        reason: One sentence on why it should be quarantined.
    """
    return f"QUARANTINED: {sample_name} ({reason})"
