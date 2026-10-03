from collections import Counter
from math import log, sqrt
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import KnowledgeChunk, KnowledgeDocument

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{1,}")
STOP_WORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "in", "is", "it", "my", "of", "on", "or", "that", "the", "this", "to", "with", "you", "your", "what", "why", "do", "does"}
ALIASES = {"wifi": ["wi-fi", "wireless"], "wi-fi": ["wifi", "wireless"], "internet": ["connectivity", "websites"], "dns": ["name resolution"], "slow": ["performance", "sluggish"], "printer": ["printing", "print queue"], "crash": ["crashing", "freezes", "hangs"], "sound": ["audio", "speaker"]}
DOMAINS = {
    "Network": ["wifi", "wi-fi", "internet", "network", "vpn", "ethernet", "dns", "connectivity"],
    "Printer": ["printer", "printing", "print queue", "spooler"],
    "Email": ["outlook", "email", "smtp", "imap", "mail"],
    "Browser": ["chrome", "browser", "cache", "cookies", "extension", "website"],
    "Login & Access": ["login", "sign in", "password", "account", "mfa", "portal", "locked"],
    "Hardware": ["keyboard", "mouse", "screen", "display", "sound", "audio", "battery", "bluetooth", "overheating", "overheat", "camera", "webcam", "gpu", "graphics card", "nvidia", "amd graphics", "microphone", "mic", "touchpad", "trackpad", "usb", "hdmi", "ethernet", "ram", "memory", "ssd", "hard drive", "fan", "charger", "charging", "flicker", "headphone", "speaker"],
    "Storage": ["disk full", "disk almost full", "almost full", "nearly full", "storage", "low space", "drive c", "ssd", "drive not detected", "hard drive"],
    "Security": ["phishing", "malware", "suspicious", "compromised", "virus"],
    "Software": ["software", "install", "installation", "file will not open", "file won't open", "file not opening", "missing dll", "compatibility"],
    "Windows": ["windows", "blue screen", "update", "slow", "restarts", "restart", "starting", "startup", "not starting", "unexpected shutdown", "unexpected restart", "cpu", "disk usage", "task manager", "service", "application", "app", "frozen", "freezing", "freeze", "hang", "crash", "driver", "device manager", "memory usage"],
}

def tokenize(text: str) -> list[str]:
    return [word for word in TOKEN_RE.findall(text.lower()) if word not in STOP_WORDS]

def tfidf(tokens: list[str], frequencies: Counter, count: int) -> dict[str, float]:
    terms = Counter(tokens)
    if not terms: return {}
    return {term: (value / len(tokens)) * (log((count + 1) / (frequencies[term] + 1)) + 1) for term, value in terms.items()}

def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    dot = sum(value * right.get(term, 0.0) for term, value in left.items())
    ln = sqrt(sum(value * value for value in left.values())); rn = sqrt(sum(value * value for value in right.values()))
    return dot / (ln * rn) if ln and rn else 0.0

def expand_query(query: str) -> list[str]:
    terms = tokenize(query)
    additions = []
    for term in terms:
        additions.extend(ALIASES.get(term, []))
    return [query, " ".join(terms + additions)]

def search_knowledge(db: Session, query: str, top_k: int = 5, domain: str | None = None, issue_type: str | None = None):
    rows = db.execute(select(KnowledgeChunk, KnowledgeDocument).join(KnowledgeDocument)).all()
    if not rows: return []
    texts = [f"{doc.title} {chunk.chunk_text}" for chunk, doc in rows]
    corpus_tokens = [tokenize(text) for text in texts]
    frequencies = Counter(term for words in corpus_tokens for term in set(words))
    variants = [tokenize(v) for v in expand_query(query)]
    query_tokens = list(dict.fromkeys(t for variant in variants for t in variant))
    query_vec = tfidf(query_tokens, frequencies, len(rows))
    query_lower = query.lower()
    ranked = []
    for (chunk, doc), text, words in zip(rows, texts, corpus_tokens):
        lower = text.lower(); wordset = set(words)
        tfidf_score = cosine_similarity(query_vec, tfidf(words, frequencies, len(rows)))
        overlap = len(set(query_tokens) & wordset) / max(1, len(set(query_tokens)))
        phrase = 0.12 if any(v.strip() and v.strip() in lower for v in expand_query(query)) else 0.0
        domain_match = bool(domain and any(k in lower for k in DOMAINS.get(domain, [domain.lower()])))
        issue_match = bool(issue_type and issue_type.lower() in lower)
        score = min(1.0, 0.58 * tfidf_score + 0.28 * overlap + phrase + (0.10 if domain_match else 0) + (0.08 if issue_match else 0))
        ranked.append((score, chunk, doc))
    ranked.sort(key=lambda x: x[0], reverse=True)
    # Avoid returning adjacent/near-identical chunks from the same source.
    result, seen = [], set()
    for score, chunk, doc in ranked:
        signature = (doc.id, re.sub(r"\W+", " ", chunk.chunk_text.lower())[:160])
        if signature in seen: continue
        seen.add(signature)
        result.append({"score": float(score), "chunk": chunk, "document": doc})
        if len(result) >= max(1, min(top_k, 20)): break
    return result
