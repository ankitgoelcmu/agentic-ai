# tools.py
import os
import json
import random
from datetime import datetime
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_core.tools import tool

from typing import Annotated, Literal

import httpx
from langchain.tools import InjectedToolArg, tool
from markdownify import markdownify

load_dotenv()

def _tavily() -> TavilyClient:
    """Returns a Tavily client using TAVILY_API_KEY from .env"""
    return TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def search_threat_intel(ioc: str) -> str:
    """
    Search threat intelligence database for an IOC (IP, domain, hash).
    Returns threat score and known malicious activity.
    """
    # Mock - production: call real threat intel API
    return json.dumps({
        "ioc": ioc,
        "threat_score": random.randint(40, 95),
        "known_malicious": True,
        "tags": ["botnet", "c2"],
        "first_seen": "2024-01-15"
    })

@tool
def query_siem_logs(query: str, time_range: str = "1h") -> str:
    """
    Query SIEM logs for security events matching the query.
    Returns matching log entries and count.
    """
    # Mock - production: call Sumo Logic API
    return json.dumps({
        "query": query,
        "time_range": time_range,
        "count": random.randint(1, 500),
        "sample_events": [
            {"timestamp": datetime.now().isoformat(),
             "event": f"Suspicious activity matching: {query}",
             "severity": "HIGH"}
        ]
    })

@tool
def create_incident_ticket(
    title: str,
    severity: str,
    description: str
) -> str:
    """
    Create an incident ticket in the ticketing system.
    Returns ticket ID and URL.
    """
    ticket_id = f"INC-{random.randint(10000, 99999)}"
    return json.dumps({
        "ticket_id": ticket_id,
        "url": f"https://jira.company.com/browse/{ticket_id}",
        "status": "OPEN",
        "created_at": datetime.now().isoformat()
    })

@tool
def send_alert(channel: str, message: str, severity: str) -> str:
    """
    Send alert notification to specified channel (slack, email, pagerduty).
    """
    print(f"\n[ALERT -> {channel.upper()}] [{severity}] {message}\n")
    return json.dumps({"delivered": True, "channel": channel})



@tool
def competetive_analysis(ticker: str) -> str:
    """
    Search the web for competitive analysis of a stock ticker.
    Returns real competitor comparisons, market share, and strategic positioning.
    """
    results = _tavily().search(
        query=f"{ticker} stock competitive analysis market share vs competitors 2025",
        search_depth="advanced",
        max_results=5,
    )
    return json.dumps({
        "ticker": ticker,
        "query": results.get("query"),
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })


@tool
def financial_analysis(ticker: str) -> str:
    """
    Search the web for financial metrics of a stock ticker.
    Returns real revenue growth, profit margins, P/E ratio, and earnings trends.
    """
    results = _tavily().search(
        query=f"{ticker} financial results revenue earnings profit margin PE ratio 2025",
        search_depth="advanced",
        max_results=5,
    )
    return json.dumps({
        "ticker": ticker,
        "query": results.get("query"),
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })


@tool
def news_sentiment_analysis(ticker: str) -> str:
    """
    Search the web for recent news and sentiment around a stock ticker.
    Returns latest headlines, analyst opinions, and overall market sentiment.
    """
    results = _tavily().search(
        query=f"{ticker} stock news analyst sentiment outlook 2025",
        search_depth="advanced",
        max_results=5,
        # topic="news" filters to recent news articles specifically
        topic="news",
    )
    return json.dumps({
        "ticker": ticker,
        "query": results.get("query"),
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })


@tool
def bull_case_analysis(ticker: str) -> str:
    """
    Search the web for bullish arguments for a stock ticker.
    Returns growth catalysts, competitive advantages, and upside thesis.
    """
    results = _tavily().search(
        query=f"{ticker} stock bull case growth catalysts investment thesis upside 2025",
        search_depth="advanced",
        max_results=5,
    )
    return json.dumps({
        "ticker": ticker,
        "query": results.get("query"),
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })


@tool
def bear_case_analysis(ticker: str) -> str:
    """
    Search the web for bearish arguments for a stock ticker.
    Returns risks, competitive threats, valuation concerns, and downside scenarios.
    """
    results = _tavily().search(
        query=f"{ticker} stock bear case risks challenges headwinds downside 2025",
        search_depth="advanced",
        max_results=5,
    )
    return json.dumps({
        "ticker": ticker,
        "query": results.get("query"),
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })




@tool
def product_technical_support (query: str) -> str:
    """
    Search the web for technical support information related to a product issue.
    Returns troubleshooting steps, user guides, and relevant forum discussions.
    """
    results = _tavily().search(
        query=f"{query} product technical support troubleshooting user guide forum",
        search_depth="advanced",
        max_results=5,
        topic="support",
    )
    return json.dumps({
        "query": query,
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })


@tool
def product_billing_support (query: str) -> str:
    """
    Search the web for billing support information related to a product issue.
    Returns payment troubleshooting, subscription management, and relevant forum discussions.
    """
    results = _tavily().search(
        query=f"{query} product billing support payment troubleshooting subscription management forum",
        search_depth="advanced",
        max_results=5,
        topic="support",
    )
    return json.dumps({
        "query": query,
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })


@tool
def product_upgrade_support (query: str) -> str:
    """
    Search the web for upgrade support information related to a product issue.
    Returns upgrade procedures, compatibility information, and relevant forum discussions.
    """
    results = _tavily().search(
        query=f"{query} product upgrade support upgrade procedures compatibility forum",
        search_depth="advanced",
        max_results=5,
        topic="support",
    )
    return json.dumps({
        "query": query,
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })

@tool
def product_add_feature_request (query: str) -> str:
    """
    Search the web for feature request information related to a product issue.
    Returns existing feature requests, user discussions, and relevant forum threads.
    """
    results = _tavily().search(
        query=f"{query} product feature request user discussion forum",
        search_depth="advanced",
        max_results=5,
        topic="support",
    )
    return json.dumps({
        "query": query,
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })

@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query.

    Uses Tavily to discover relevant URLs, then fetches and returns full webpage content as markdown.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default: 1)
        topic: Topic filter - 'general', 'news', or 'finance' (default: 'general')

    Returns:
        Formatted search results with full webpage content
    """
    search_results = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
    )
    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]
        content = fetch_webpage_content(url)
        result_texts.append(f"## {title}\n**URL:** {url}\n\n{content}\n---")

    return f"Found {len(result_texts)} result(s) for '{query}':\n\n" + "\n".join(
        result_texts
    )







def fetch_webpage_content(url: str, timeout: float = 10.0) -> str:
    """Fetch webpage and convert HTML to markdown."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = httpx.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return markdownify(response.text)
    except Exception as e:
        return f"Error fetching {url}: {e!s}"


@tool(parse_docstring=True)
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query.

    Uses Tavily to discover relevant URLs, then fetches and returns full webpage content as markdown.

    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default: 1)
        topic: Topic filter - 'general', 'news', or 'finance' (default: 'general')

    Returns:
        Formatted search results with full webpage content
    """
    search_results =  _tavily().search(
        query,
        max_results=max_results,
        topic=topic,
    )
    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]
        content = fetch_webpage_content(url)
        result_texts.append(f"## {title}\n**URL:** {url}\n\n{content}\n---")

    return f"Found {len(result_texts)} result(s) for '{query}':\n\n" + "\n".join(
        result_texts
    )