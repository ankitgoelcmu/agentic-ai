# tools.py
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain_core.tools import tool
from sigma.collection import SigmaCollection
from sigma.backends.sumologic import SumoLogicCSERuleBackend
from sigma.pipelines.sumologic import sumologic_cse_pipeline

_sumologic_pipeline = sumologic_cse_pipeline()
_sumologic_backend = SumoLogicCSERuleBackend(processing_pipeline=_sumologic_pipeline)
from tavily import TavilyClient

load_dotenv()

# --- Sigma rule corpus setup ---
SIGMA_RULES_DIR = Path(os.getenv("SIGMA_RULES_DIR", "./sigma_repo/rules"))
MAX_RULES_TO_LOAD = int(os.getenv("SIGMA_MAX_RULES", "3000"))
SKIP_STATUS = {"deprecated", "unsupported"}


def _load_rules(max_rules: int) -> list[dict]:
    """Walks the local SigmaHQ clone and returns a filtered list of usable rules."""
    rules = []
    for path in SIGMA_RULES_DIR.rglob("*.yml"):
        try:
            rule = yaml.safe_load(open(path))
        except Exception:
            continue
        if not isinstance(rule, dict) or rule.get("status") in SKIP_STATUS:
            continue
        if not rule.get("title") or not rule.get("description"):
            continue
        rules.append(rule)
        if len(rules) >= max_rules:
            break
    return rules


# Loaded once at import time. No embedding model, no API calls, no external
# dependency, just a list of dicts read from the local bundled corpus.
_all_rules = _load_rules(MAX_RULES_TO_LOAD)
print(f"[tools] loaded {len(_all_rules)} rules for keyword search")


@tool
def sigma_search(query: str) -> str:
    """Search existing Sigma rules for titles/descriptions matching keywords in
    the query. Use this before drafting a new rule."""
    query_words = query.lower().split()
    matches = []
    for rule in _all_rules:
        haystack = f"{rule.get('title', '')} {rule.get('description', '')}".lower()
        if any(w in haystack for w in query_words):
            matches.append(rule)
        if len(matches) >= 3:
            break

    if not matches:
        return "No similar rules found."

    summaries = []
    for m in matches:
        summaries.append(
            f"title: {m.get('title')}\n"
            f"logsource: {m.get('logsource')}\n"
            f"condition: {m.get('detection', {}).get('condition')}\n"
            f"tags: {m.get('tags')}"
        )
    return "\n---\n".join(summaries)

@tool
def sigma_validate(rule_yaml: str) -> str:
    """Validate a draft Sigma rule. Checks both structural correctness and
    whether the rule can actually be converted into a real query (Sumo Logic
    Cloud SIEM), which catches deeper issues pure parsing misses, such as a
    condition referencing an undefined selection block, or an invented field
    modifier that isn't real Sigma syntax."""
    try:
        collection = SigmaCollection.from_yaml(rule_yaml, collect_errors=True)
    except Exception as e:
        return f"INVALID - could not parse: {e}"

    errors = getattr(collection, "errors", [])
    if errors:
        return "INVALID:\n" + "\n".join(str(e) for e in errors)

    try:
        _sumologic_backend.convert(collection)
    except Exception as e:
        return f"INVALID - rule parses but cannot be converted to a real query: {e}"

    return "VALID - parses correctly and converts to a real Sumo Logic query."


# --- Tavily web search ---
def _tavily() -> TavilyClient:
    """Returns a Tavily client using TAVILY_API_KEY from .env"""
    return TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def tavily_search(query: str) -> str:
    """Search the web for real-world technical detail about an attack technique."""
    results = _tavily().search(query, max_results=3)
    if not results.get("results"):
        return "No results found."
    return "\n\n---\n\n".join(
        f"{r['title']} ({r['url']})\n{r['content']}"
        for r in results["results"]
    )