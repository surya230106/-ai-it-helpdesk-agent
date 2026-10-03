from sqlalchemy.orm import Session
from app.services.rag import search_knowledge, DOMAINS
from app.models import Ticket

def check_supported_platform(platform: str | None):
    known = {"windows", "macos", "mac os", "linux", "ios", "android", "chromeos"}
    normalized = (platform or "").strip().lower()
    return {"platform": platform, "supported": True if normalized in known else None, "note": "The operating system was not provided." if not normalized else ("General steps are available; vendor-specific instructions depend on the exact version." if normalized in known else "Platform is not confirmed. Ask which operating system is in use before giving platform-specific steps.")}

def suggest_escalation(state: dict):
    reasons = []
    if state.get("escalation_needed"): reasons.append("A safe check suggests a possible hardware fault or unresolved service issue.")
    if any("security" in str(x).lower() for x in state.get("likely_causes", [])): reasons.append("Possible security event needs trained review.")
    return {"recommended": bool(reasons), "reasons": reasons, "what_to_include": ["problem", "checks already tried", "what happened", "affected device or users"]}

def classify_issue(text: str):
    lower = text.lower()
    if any(x in lower for x in ["not starting", "won't start", "will not start", "no power", "startup problem"]): return "Windows"
    if any(x in lower for x in ["ssd", "hard drive", "disk"]) and any(x in lower for x in ["full", "space", "storage", "free", "slow"]): return "Storage"
    if "disk" in lower and "100" in lower and "usage" in lower: return "Windows"
    if any(x in lower for x in ["blue screen", "windows update", "driver problem", "driver issue", "windows restarting", "windows restart"]): return "Windows"
    for category, terms in DOMAINS.items():
        if any(term in lower for term in terms): return category
    return "General"

def detect_intent(text: str):
    t = text.lower().strip()
    if "difference between" in t or " vs " in t or " versus " in t: return "comparison"
    if any(x in t for x in ["what is", "what are", "explain", "meaning of"]): return "explanation"
    if t.startswith(("how do i", "how to", "steps to", "show me how")): return "instruction"
    if t.startswith(("why ", "why is", "why does", "what causes")): return "diagnosis"
    if any(x in t for x in ["create a ticket", "create ticket", "open a ticket", "open ticket", "please escalate", "escalate this", "raise a ticket"]): return "escalation"
    if any(x in t for x in ["not working", "not opening", "not responding", "not connecting", "can't", "cannot", "won't", "doesn't", "isn't", "freezes", "crash", "error", "slow", "overheating", "overheats", "no ", "became very", "restarts unexpectedly", "restart unexpectedly", "is online but", "screen is black", "black screen", "almost full", "nearly full", "works on one device", "not signing in", "isn't signing"]): return "troubleshoot"
    return "question"

def estimate_priority(text: str):
    t=text.lower()
    if any(x in t for x in ["all users", "server down", "security incident", "data loss", "cannot work", "business stopped"]): return "high"
    if any(x in t for x in ["slow", "intermittent", "one application", "overheating", "restarts unexpectedly"]): return "medium"
    return "low"

def generate_troubleshooting_steps(issue_category: str, text: str = ""):
    t=text.lower()
    if issue_category == "Network":
        if "dns" in t: return ["Check whether other websites load.", "On Windows, open Command Prompt and run `ipconfig /flushdns`.", "Try the site again; if it still fails, check whether other devices have the same issue."]
        if "vpn" in t: return ["Confirm your normal internet connection works first.", "Check that your organization account is active and the VPN address is correct.", "Disconnect and reconnect once; note the exact error if it fails."]
        return ["Check whether another device can access the same Wi-Fi.", "Try a second website and browser to see whether the issue is limited to one site or app.", "Reconnect to Wi-Fi; if only this device is affected, restart it and test again.", "If multiple devices fail, report a possible router or provider outage."]
    if issue_category == "Printer": return ["Confirm the printer is ready and the correct printer is selected.", "Open its queue and cancel only jobs that are stuck.", "Print a test page. If it still fails, note any printer error and whether other users are affected."]
    if issue_category == "Email": return ["Check whether Outlook is frozen for all actions or only sending.", "Verify the message appears in Outbox and note any error code.", "Try Outlook on the web to tell whether the issue is app-specific.", "If web mail also fails, contact your mail administrator with the error and time."]
    if issue_category == "Browser": return ["Try the page in a private window or another browser.", "If that works, disable extensions one at a time and clear the affected site's cached data.", "If no browser can open sites, check the network connection instead."]
    if issue_category == "Login & Access": return ["Check the exact sign-in error and confirm the account name.", "For a company portal, connect to the required network or VPN.", "Do not share your password or MFA code. Ask an administrator to check lockout or access permissions."]
    if issue_category == "Hardware":
        if any(x in t for x in ["overheat", "hot"]): return ["Place the laptop on a hard, clear surface and make sure vents are not blocked.", "Close demanding apps and check whether the fan is running normally.", "If it remains very hot, shuts down, or smells unusual, power it off and arrange hardware support."]
        if "sound" in t or "audio" in t: return ["Check mute and volume, then confirm the intended speaker or headset is selected.", "Unplug and reconnect the audio device, then test sound in another app.", "If no output device appears, note the computer model and contact support about its audio driver."]
        return ["Check whether the problem affects another port or connected device, if available.", "Disconnect and reconnect the device, then restart the computer if safe.", "Note any indicator lights or error message for support."]
    if issue_category == "Storage": return ["Check the drive's available space in Settings > System > Storage.", "Use Windows Storage settings to review temporary files before removing anything.", "Do not delete system folders; ask IT if the drive remains nearly full."]
    if issue_category == "Windows":
        if "slow" in t: return ["Restart once if you have saved your work.", "Open Task Manager and check whether CPU, Memory, or Disk stays near 100%.", "Review recently installed updates and startup apps; avoid removing drivers without IT help.", "Share the highest resource use and update date if it remains slow."]
        if "black screen" in t or "screen is black" in t: return ["Check power and brightness, then disconnect external displays or docks.", "Press `Windows + Ctrl + Shift + B` once to reset the graphics driver.", "If the screen stays black after restart, note whether the device shows a sign-in screen or startup logo and contact support."]
        if "keyboard" in t or "mouse" in t: return ["Reconnect the device or try another USB port; check batteries for wireless devices.", "Test it on another computer if available.", "If built-in input devices fail too, report the model and whether this began after an update."]
        if "crash" in t or "freeze" in t: return ["Record the app name and exact error, and check whether it happens with one file or every time.", "Save work, restart the app, and check for an approved app update.", "If it continues, send IT the error text and time of the crash."]
        return ["Write down the exact message and when the problem started.", "Check whether it affects one app or the whole computer.", "Restart only after saving work, then report whether the issue returns."]
    return ["Please share the exact error and what you were doing when it appeared.", "Say whether it affects one device or other users too."]

def kb_search(db: Session, query: str, top_k: int=5, domain: str | None = None, issue_type: str | None = None):
    results=search_knowledge(db, query, top_k, domain, issue_type)
    return [{"title":r["document"].title,"document_id":r["document"].id,"chunk_index":r["chunk"].chunk_index,"snippet":r["chunk"].chunk_text[:700],"score":round(r["score"],3)} for r in results]

def create_ticket(db: Session, user_id: int, title: str, description: str, category: str, priority: str):
    ticket = Ticket(user_id=user_id, title=title[:255], description=description, category=category, priority=priority)
    db.add(ticket); db.commit(); db.refresh(ticket)
    return {"ticket_id": ticket.id, "status": ticket.status}

get_checklist = generate_troubleshooting_steps
