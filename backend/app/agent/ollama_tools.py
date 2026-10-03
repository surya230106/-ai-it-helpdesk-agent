"""Ollama function definitions backed by the application's existing allowlisted tools."""
import json

from sqlalchemy.orm import Session

from app.agent.diagnostics import DIAGNOSTIC_TOOLS, identify_hardware, start_diagnostic
from app.agent.tools import (
    check_supported_platform, classify_issue, create_ticket, estimate_priority,
    generate_troubleshooting_steps, kb_search, suggest_escalation,
)

def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required}}}

TEXT = {"type": "string"}
TOOLS = [
    _tool("search_knowledge_base", "Find relevant helpdesk guidance. Use when documented evidence would help.", {"query": TEXT, "top_k": {"type": "integer", "minimum": 1, "maximum": 5}}, ["query"]),
    _tool("classify_issue", "Classify the user's current IT problem.", {"text": TEXT}, ["text"]),
    _tool("estimate_priority", "Estimate support priority from user impact.", {"text": TEXT}, ["text"]),
    _tool("generate_troubleshooting_steps", "Get a safe checklist for an issue. Prefer the diagnostic tool for one-step diagnosis.", {"issue_category": TEXT, "text": TEXT}, ["issue_category", "text"]),
    _tool("check_supported_platform", "Check whether platform-specific guidance is available.", {"platform": TEXT}, ["platform"]),
    _tool("suggest_escalation", "Check whether a known diagnostic state should be escalated.", {"state": {"type": "object", "properties": {"escalation_needed": {"type": "boolean"}, "likely_causes": {"type": "array", "items": TEXT}}, "required": ["escalation_needed", "likely_causes"]}}, ["state"]),
    _tool("create_ticket", "Create a ticket only when the user clearly asks for a ticket or escalation.", {"title": TEXT, "description": TEXT, "category": TEXT, "priority": TEXT}, ["title", "description", "category", "priority"]),
]
for _name in DIAGNOSTIC_TOOLS:
    TOOLS.append(_tool(_name, f"Start a structured {_name.replace('diagnose_', '').replace('_', ' ')} diagnostic check based on the issue.", {"issue": TEXT}, ["issue"]))

def execute_tool(db: Session, user_id: int, name: str, args: dict, original_message: str, state: dict | None = None):
    if name == "search_knowledge_base":
        return kb_search(db, str(args.get("query", original_message))[:1000], int(args.get("top_k", 4)), domain=(state or {}).get("issue_domain"))
    if name == "classify_issue":
        return {"category": classify_issue(str(args.get("text", original_message))[:2000])}
    if name == "estimate_priority":
        return {"priority": estimate_priority(str(args.get("text", original_message))[:2000])}
    if name == "generate_troubleshooting_steps":
        return {"steps": generate_troubleshooting_steps(str(args.get("issue_category", "General"))[:80], str(args.get("text", original_message))[:1000])}
    if name == "check_supported_platform":
        return check_supported_platform(str(args.get("platform", ""))[:80])
    if name == "suggest_escalation":
        return suggest_escalation(state or args.get("state", {}))
    if name == "create_ticket":
        if not any(term in original_message.lower() for term in ("ticket", "escalate", "support request")):
            return {"created": False, "reason": "The user has not explicitly asked to create a ticket."}
        return create_ticket(db, user_id, str(args.get("title", "IT support request")), str(args.get("description", original_message)), str(args.get("category", (state or {}).get("issue_domain", "General"))), str(args.get("priority", "medium")))
    diagnostic = DIAGNOSTIC_TOOLS.get(name)
    if diagnostic:
        issue = str(args.get("issue", original_message))[:1000]
        return diagnostic(issue) if name != "diagnose_issue" else start_diagnostic(issue, classify_issue(issue))
    return {"error": "That tool is not available."}

def encode_tool_result(result) -> str:
    try:
        return json.dumps(result, ensure_ascii=False, default=str)[:8000]
    except (TypeError, ValueError):
        return '{"error":"Tool result could not be encoded."}'
