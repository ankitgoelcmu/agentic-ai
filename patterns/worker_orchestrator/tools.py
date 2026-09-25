# tools.py
import os
import json
import random
from datetime import datetime
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_core.tools import tool

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