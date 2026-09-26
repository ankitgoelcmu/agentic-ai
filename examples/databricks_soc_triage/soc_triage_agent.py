# Databricks notebook source
# MAGIC %md
# MAGIC # Multi-Model SOC Triage Agent on Databricks
# MAGIC
# MAGIC Rebuild of my SOC alert triage agent on Databricks. The goal was to see how the same agent behaves on
# MAGIC different model providers when the data, tools, and evaluation all stay in one place.
# MAGIC
# MAGIC Setup:
# MAGIC - alerts, threat intel, and past incidents are Unity Catalog tables
# MAGIC - the agent's tools are Unity Catalog SQL functions (so access is controlled with GRANT like any other asset)
# MAGIC - models come from Foundation Model APIs, and switching provider is just a different endpoint name
# MAGIC - every run is traced in MLflow and scored against labeled alerts
# MAGIC
# MAGIC For each alert the agent returns TRUE_POSITIVE, FALSE_POSITIVE, or NEEDS_ESCALATION.
# MAGIC
# MAGIC Took about 10 min for me on Free Edition serverless compute.

# COMMAND ----------

# MAGIC %pip install -U -qqq databricks-langchain langgraph mlflow databricks-sdk

# COMMAND ----------

# restart so the newly installed packages are picked up
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Config

# COMMAND ----------

# use whatever catalog the workspace defaults to
# (Free Edition uses "workspace", trial workspaces usually use "main")
CATALOG = spark.sql("SELECT current_catalog()").first()[0]
SCHEMA = "soc_agent_lab"
FQ = f"{CATALOG}.{SCHEMA}"  # fully qualified prefix used for tables and functions

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FQ}")
print(f"Using schema: {FQ}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Sample security data
# MAGIC
# MAGIC Three tables the agent can query through tools, plus `alert_labels` with the expected verdicts.
# MAGIC There's no tool for `alert_labels`, so the agent can't see the answers it gets scored on.
# MAGIC
# MAGIC IPs are from the RFC 5737 documentation ranges and domains use .example, so nothing here points at real infrastructure.

# COMMAND ----------

# (alert_id, alert_type, severity, host, user, indicator, description)
alerts = [
    ("A-1001", "Outbound C2 connection", "high", "web-prod-03", "svc-web", "198.51.100.23",
     "web-prod-03 opened repeated outbound connections to 198.51.100.23 on port 443 every 60 seconds (beaconing pattern)."),
    ("A-1002", "Impossible travel", "medium", "vpn-gw-01", "jchen", "203.0.113.10",
     "User jchen logged in from Chicago, then from 203.0.113.10 twelve minutes later, geolocated to Frankfurt."),
    ("A-1003", "SSH brute force", "high", "bastion-01", "root", "192.0.2.77",
     "350 failed SSH logins to bastion-01 from 192.0.2.77 within 10 minutes, followed by one successful login as root."),
    ("A-1004", "Malware hash detected", "medium", "laptop-ops-17", "mpatel", "9f86d081884c7d65",
     "Endpoint agent flagged file deploy-helper.exe with hash 9f86d081884c7d65 on laptop-ops-17."),
    ("A-1005", "Data exfiltration", "high", "finance-db-02", "etl-finance", "files-share-x.example",
     "12 GB uploaded from finance-db-02 to files-share-x.example at 02:14, outside the normal ETL window."),
    ("A-1006", "Suspicious DNS", "medium", "laptop-hr-04", "lgarcia", "login-okta-verify.example",
     "laptop-hr-04 resolved login-okta-verify.example, a domain registered 3 days ago, then made an HTTPS request to it."),
]

# expected verdicts, only used for scoring in section 7
# A-1003 is the tricky one: past brute force cases went both ways, the successful login is what matters
# A-1005 has no intel and mixed history, so the right call is to escalate
alert_labels = [
    ("A-1001", "TRUE_POSITIVE"),
    ("A-1002", "FALSE_POSITIVE"),
    ("A-1003", "TRUE_POSITIVE"),
    ("A-1004", "FALSE_POSITIVE"),
    ("A-1005", "NEEDS_ESCALATION"),
    ("A-1006", "TRUE_POSITIVE"),
]

# (indicator, reputation, category, source)
# files-share-x.example is left out on purpose, so A-1005 has no intel
threat_intel = [
    ("198.51.100.23", "malicious", "command-and-control", "Commercial TI feed"),
    ("192.0.2.77", "malicious", "brute-force scanner", "Honeypot network"),
    ("203.0.113.10", "benign", "corporate VPN egress (Frankfurt PoP)", "Internal allowlist"),
    ("9f86d081884c7d65", "benign", "internal tool deploy-helper, signed by IT", "Internal allowlist"),
    ("login-okta-verify.example", "malicious", "credential phishing", "Commercial TI feed"),
]

# (incident_id, alert_type, host, verdict, resolution)
past_incidents = [
    ("INC-2201", "Outbound C2 connection", "api-prod-01", "TRUE_POSITIVE", "Beaconing to known C2 confirmed. Host isolated and reimaged."),
    ("INC-2214", "Impossible travel", "vpn-gw-01", "FALSE_POSITIVE", "Login came through the Frankfurt VPN egress. No action needed."),
    ("INC-2230", "Impossible travel", "vpn-gw-01", "FALSE_POSITIVE", "Same VPN egress pattern. Added to tuning backlog."),
    ("INC-2245", "SSH brute force", "bastion-02", "FALSE_POSITIVE", "Failed attempts only, all blocked. Source IP added to blocklist."),
    ("INC-2263", "SSH brute force", "bastion-01", "TRUE_POSITIVE", "Failed attempts followed by a successful login. Credentials rotated, host investigated."),
    ("INC-2270", "Malware hash detected", "laptop-ops-09", "FALSE_POSITIVE", "deploy-helper.exe is an approved internal tool. Hash allowlisted."),
    ("INC-2288", "Data exfiltration", "finance-db-01", "FALSE_POSITIVE", "Large upload was an approved quarterly backup to a sanctioned vendor."),
    ("INC-2291", "Data exfiltration", "hr-db-01", "TRUE_POSITIVE", "Upload to an unsanctioned file-sharing site by a compromised service account."),
    ("INC-2302", "Suspicious DNS", "laptop-fin-11", "TRUE_POSITIVE", "Newly registered lookalike domain used for credential phishing. User reset password."),
]

# table name -> (rows, schema)
tables = {
    "alerts": (alerts, "alert_id STRING, alert_type STRING, severity STRING, host STRING, user_name STRING, indicator STRING, description STRING"),
    "alert_labels": (alert_labels, "alert_id STRING, expected_verdict STRING"),
    "threat_intel": (threat_intel, "indicator STRING, reputation STRING, category STRING, source STRING"),
    "past_incidents": (past_incidents, "incident_id STRING, alert_type STRING, host STRING, verdict STRING, resolution STRING"),
}

# overwrite so the notebook can be re-run cleanly
for name, (rows, schema) in tables.items():
    spark.createDataFrame(rows, schema).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.{name}")
    print(f"Created {FQ}.{name} ({len(rows)} rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Tools as Unity Catalog functions
# MAGIC
# MAGIC Each tool is a SQL function in Unity Catalog. Reasons for doing it this way:
# MAGIC - access is controlled with GRANT EXECUTE, same as tables
# MAGIC - the functions only read data, so the agent can't modify anything
# MAGIC - the same functions can be used from LangGraph, the OpenAI SDK, etc.
# MAGIC
# MAGIC The COMMENT on each function is what the model sees as the tool description, so it's written for the model.

# COMMAND ----------

# tool 1: fetch an alert by ID
# returns JSON so the model gets structured fields, and "Alert not found" instead of NULL for bad IDs
# MAX() is only there because Databricks requires correlated scalar subqueries to be aggregated;
# alert_id is unique, so it always picks the single matching row
spark.sql(f"""
CREATE OR REPLACE FUNCTION {FQ}.get_alert(id STRING COMMENT 'Alert ID, for example A-1001')
RETURNS STRING
COMMENT 'Returns the details of a security alert as JSON: alert type, severity, host, user, the indicator (IP, domain, or file hash), and a description. Always call this first.'
RETURN COALESCE(
  (SELECT MAX(to_json(named_struct(
      'alert_id', a.alert_id, 'alert_type', a.alert_type, 'severity', a.severity,
      'host', a.host, 'user', a.user_name, 'indicator', a.indicator, 'description', a.description)))
   FROM {FQ}.alerts a WHERE a.alert_id = id),
  'Alert not found')
""")

# tool 2: threat intel lookup
# returns [] when there's no match; the comment tells the model that means "unknown", not "safe"
spark.sql(f"""
CREATE OR REPLACE FUNCTION {FQ}.lookup_threat_intel(ioc STRING COMMENT 'An indicator of compromise: IP address, domain, or file hash')
RETURNS STRING
COMMENT 'Looks up an indicator in threat intelligence. Returns a JSON list with reputation (malicious or benign), category, and source. Returns [] if there is no intel for this indicator, which means unknown, not safe.'
RETURN (
  SELECT to_json(collect_list(named_struct(
      'indicator', t.indicator, 'reputation', t.reputation, 'category', t.category, 'source', t.source)))
  FROM {FQ}.threat_intel t WHERE t.indicator = ioc)
""")

# tool 3: past incidents with the same alert type, so the agent can see how analysts resolved them before
spark.sql(f"""
CREATE OR REPLACE FUNCTION {FQ}.find_past_incidents(alert_kind STRING COMMENT 'Alert type exactly as returned by get_alert, for example SSH brute force')
RETURNS STRING
COMMENT 'Returns past incidents with the same alert type as a JSON list, including how each was resolved and whether it was a true or false positive. Use this to learn from previous analyst decisions.'
RETURN (
  SELECT to_json(collect_list(named_struct(
      'incident_id', p.incident_id, 'host', p.host, 'verdict', p.verdict, 'resolution', p.resolution)))
  FROM {FQ}.past_incidents p WHERE p.alert_type = alert_kind)
""")

print("Tools registered in Unity Catalog")

# COMMAND ----------

# quick check that the functions work from plain SQL before wiring them into the agent
display(spark.sql(f"""
SELECT
  {FQ}.get_alert('A-1003')                      AS alert,
  {FQ}.lookup_threat_intel('192.0.2.77')        AS intel,
  {FQ}.find_past_incidents('SSH brute force')   AS history
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC Optional: in a real setup, only the agent's service principal or group would get EXECUTE on these functions.
# MAGIC ```sql
# MAGIC GRANT EXECUTE ON FUNCTION <catalog>.soc_agent_lab.lookup_threat_intel TO `soc-agents`;
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Find usable model endpoints
# MAGIC
# MAGIC Endpoint names change when new model versions come out, so this lists the workspace endpoints, picks one per
# MAGIC provider, and sends a test call to make sure it actually works.
# MAGIC
# MAGIC Free Edition blocks some pay-per-token models. If Claude/Gemini get skipped, run this on a trial workspace.
# MAGIC The open-weight models (Llama, Gemma, gpt-oss) are included so there's still something to compare on Free Edition.

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks

w = WorkspaceClient()
available = sorted(e.name for e in w.serving_endpoints.list())

# provider -> (keyword to match, preferred endpoint names in order)
PROVIDERS = {
    "Anthropic Claude": ("claude", ["databricks-claude-sonnet-4-5", "databricks-claude-sonnet-4", "databricks-claude-3-7-sonnet"]),
    "Google Gemini":    ("gemini", ["databricks-gemini-2-5-flash", "databricks-gemini-3-flash", "databricks-gemini-2-5-pro"]),
    "OpenAI GPT":       ("gpt",    ["databricks-gpt-5-mini", "databricks-gpt-5"]),
    # open-weight models, usually available even on Free Edition
    "Meta Llama":       ("llama",  ["databricks-meta-llama-3-3-70b-instruct", "databricks-llama-4-maverick"]),
    "Google Gemma":     ("gemma",  ["databricks-gemma-3-12b"]),
}

def model_kwargs(endpoint: str) -> dict:
    # GPT-5 models only accept the default temperature, so don't pass one
    # everything else gets temperature 0 to keep runs comparable
    return {} if "gpt-5" in endpoint else {"temperature": 0}

def pick_endpoint(keyword, preferred):
    # try the preferred names first, then fall back to any endpoint with the keyword
    # (skip embedding endpoints since they can't chat)
    for name in preferred:
        if name in available:
            return name
    matches = [n for n in available if keyword in n and "embed" not in n]
    return matches[0] if matches else None

MODELS = {}  # provider -> endpoint that passed the test call
for provider, (keyword, preferred) in PROVIDERS.items():
    endpoint = pick_endpoint(keyword, preferred)
    if not endpoint:
        print(f"[skip] {provider}: no endpoint found")
        continue
    try:
        # an endpoint can show up in the list but still be blocked for this workspace, so test it
        ChatDatabricks(endpoint=endpoint, **model_kwargs(endpoint)).invoke("Reply with OK.")
        MODELS[provider] = endpoint
        print(f"[ok]   {provider}: {endpoint}")
    except Exception as e:
        print(f"[skip] {provider}: {endpoint} not usable here ({str(e)[:120]})")

assert MODELS, "No usable model endpoints in this workspace. Try a trial workspace."

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Agent (LangGraph)
# MAGIC
# MAGIC Basic tool-calling loop: model picks a tool, tool runs, result goes back to the model, repeat until it answers.
# MAGIC Same graph for every provider, only the endpoint changes.

# COMMAND ----------

import mlflow
from typing import Annotated, TypedDict
from databricks_langchain import UCFunctionToolkit
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# log every agent run as an MLflow trace (model calls + tool calls)
mlflow.langchain.autolog()

# wrap the UC functions as LangChain tools
tools = UCFunctionToolkit(function_names=[
    f"{FQ}.get_alert",
    f"{FQ}.lookup_threat_intel",
    f"{FQ}.find_past_incidents",
]).tools

# fixed output format so the verdict can be parsed and scored in section 7
SYSTEM_PROMPT = """You are a SOC analyst triaging security alerts.

Process:
1. Call get_alert to read the alert.
2. Call lookup_threat_intel for the alert's indicator.
3. Call find_past_incidents with the alert type to see how similar alerts were resolved.
4. Decide based only on the evidence from the tools.

Rules:
- An empty threat intel result means the indicator is unknown, not that it is safe.
- If the evidence is missing or conflicting, choose NEEDS_ESCALATION. Never guess.

End your answer with exactly this format:
VERDICT: <TRUE_POSITIVE | FALSE_POSITIVE | NEEDS_ESCALATION>
CONFIDENCE: <high | medium | low>
REASONING: <two or three sentences citing the evidence>
RECOMMENDED_ACTION: <one sentence>"""

class AgentState(TypedDict):
    # add_messages appends new messages instead of replacing the list
    messages: Annotated[list, add_messages]

# tool name -> tool, used by run_tools to execute whatever the model asked for
TOOLS_BY_NAME = {t.name: t for t in tools}

def run_tools(state: AgentState):
    # run every tool call from the last model message and return the results as ToolMessages
    # (written by hand instead of langgraph.prebuilt.ToolNode to avoid version conflicts on Databricks)
    results = []
    for call in state["messages"][-1].tool_calls:
        try:
            output = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
        except Exception as e:
            # send the error back to the model so it can retry or explain, instead of crashing the run
            output = f"Tool error: {e}"
        results.append(ToolMessage(content=str(output), name=call["name"], tool_call_id=call["id"]))
    return {"messages": results}

def route(state: AgentState):
    # keep looping while the model is asking for tools, stop once it gives a plain answer
    return "tools" if getattr(state["messages"][-1], "tool_calls", None) else END

def build_agent(endpoint: str):
    # bind_tools gives the model the tool schemas so it can request tool calls
    llm = ChatDatabricks(endpoint=endpoint, **model_kwargs(endpoint)).bind_tools(tools)

    def call_model(state: AgentState):
        # system prompt is added on every call rather than stored in state
        response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"])
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", run_tools)
    graph.add_edge(START, "agent")
    # if the model asked for a tool, go to "tools", otherwise stop
    graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()

def final_text(message) -> str:
    # some providers return content as a list of blocks instead of a plain string
    content = message.content
    if isinstance(content, list):
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return content

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Single run
# MAGIC Run one alert and check the Traces tab under the cell output to see each model call and tool call.

# COMMAND ----------

# use the first provider that passed the test call
first_provider, first_endpoint = next(iter(MODELS.items()))
agent = build_agent(first_endpoint)

# recursion_limit caps the number of steps in case a model keeps calling tools
result = agent.invoke(
    {"messages": [HumanMessage(content="Triage alert A-1003.")]},
    config={"recursion_limit": 15},
)

print(f"Model: {first_provider} ({first_endpoint})\n")
# print the tool results first, then the final answer
for m in result["messages"]:
    if isinstance(m, ToolMessage):
        print(f"[tool:{m.name}] {m.content[:200]}")
print("\n" + final_text(result["messages"][-1]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Compare providers
# MAGIC
# MAGIC Each model triages all six alerts. Accuracy is checked against `alert_labels`, and latency, tool calls,
# MAGIC and tokens are recorded. One MLflow run per provider so they can be compared in the Experiments UI.
# MAGIC
# MAGIC Tokens are logged but I don't compare them across models. Each model has its own tokenizer and prompt
# MAGIC template, so the same prompt counts differently.

# COMMAND ----------

import re
import time
import pandas as pd

labels = {r.alert_id: r.expected_verdict for r in spark.table(f"{FQ}.alert_labels").collect()}

# \** handles models that bold the verdict in markdown
VERDICT_RE = re.compile(r"VERDICT:\s*\**\s*(TRUE_POSITIVE|FALSE_POSITIVE|NEEDS_ESCALATION)")

rows = []
for provider, endpoint in MODELS.items():
    agent = build_agent(endpoint)
    with mlflow.start_run(run_name=f"soc-triage-{provider}"):
        mlflow.log_params({"provider": provider, "endpoint": endpoint})
        for alert_id, expected in labels.items():
            start = time.time()
            try:
                out = agent.invoke(
                    {"messages": [HumanMessage(content=f"Triage alert {alert_id}.")]},
                    config={"recursion_limit": 15},
                )
                text = final_text(out["messages"][-1])
                match = VERDICT_RE.search(text)
                verdict = match.group(1) if match else "UNPARSED"  # model didn't follow the output format
                tool_calls = sum(isinstance(m, ToolMessage) for m in out["messages"])
                # not every provider returns usage_metadata, so default to 0
                tokens = sum((getattr(m, "usage_metadata", None) or {}).get("total_tokens", 0) for m in out["messages"])
            except Exception as e:
                # keep going if one alert fails so the rest of the comparison still runs
                verdict, tool_calls, tokens = f"ERROR: {str(e)[:60]}", 0, 0
            rows.append({
                "provider": provider, "alert_id": alert_id, "expected": expected, "verdict": verdict,
                "correct": verdict == expected, "latency_s": round(time.time() - start, 1),
                "tool_calls": tool_calls, "tokens": tokens,
            })

        # per-provider metrics for this MLflow run
        run_df = pd.DataFrame([r for r in rows if r["provider"] == provider])
        mlflow.log_metrics({
            "accuracy": run_df["correct"].mean(),
            "avg_latency_s": run_df["latency_s"].mean(),
            "avg_tool_calls": run_df["tool_calls"].mean(),
            "total_tokens": run_df["tokens"].sum(),
        })

results = pd.DataFrame(rows)
display(results)

# COMMAND ----------

# one row per provider, this is what goes in the README results table
summary = (
    results.groupby("provider")
    .agg(accuracy=("correct", "mean"), avg_latency_s=("latency_s", "mean"),
         avg_tool_calls=("tool_calls", "mean"), total_tokens=("tokens", "sum"))
    .round(2)
    .reset_index()
)
display(summary)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Notes
# MAGIC
# MAGIC What I got on Free Edition (gpt-oss-120b, Llama 3.3 70B, Gemma 3 12B):
# MAGIC - Llama and Gemma got 6/6. gpt-oss got 5/6, missing A-1005: it called it TRUE_POSITIVE instead of escalating.
# MAGIC - The smallest model (Gemma 12B) was fully accurate and the fastest, so bigger wasn't better for this task.
# MAGIC - Every run made exactly 3 tool calls, so the tool descriptions and prompt held up across models.
# MAGIC
# MAGIC Other notes:
# MAGIC - Switching models only changed the endpoint name. Data, tools, permissions, and tracing stayed the same.
# MAGIC - Because the tools are UC functions, access is handled with GRANT and every call is auditable.
# MAGIC - A-1003 turned out easier than I meant it to be: the source IP is in threat intel, so a model can get it right
# MAGIC   from the intel alone. Removing it from threat_intel would make the incident history the only way to get it right.
# MAGIC
# MAGIC Next things to try:
# MAGIC - deploy with Mosaic AI Agent Framework and use the Review App for analyst feedback
# MAGIC - add AI Gateway rate limits and guardrails on the model endpoints
# MAGIC - swap find_past_incidents for a Vector Search retriever over free-text incident reports
# MAGIC - more alerts, plus MLflow LLM judges to score the reasoning and not just the verdict
# MAGIC - rerun on a trial workspace with Claude and Gemini

# COMMAND ----------

# cleanup, uncomment to drop everything the lab created
# spark.sql(f"DROP SCHEMA IF EXISTS {FQ} CASCADE")
