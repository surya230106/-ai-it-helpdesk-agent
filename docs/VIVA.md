# Viva Questions — AI IT Helpdesk Agent

### 1. What is the project?
An AI-based IT helpdesk system that diagnoses common technical issues and recommends troubleshooting steps using a knowledge base.

### 2. What are the three key agent capabilities?
**Agent + RAG + Tools.** The agent coordinates the response, RAG retrieves evidence, and tools provide structured diagnosis/checklists.

### 3. Why use RAG?
RAG grounds answers in the organization's stored troubleshooting documents and reduces unsupported answers.

### 4. Why use tools?
Tools give deterministic operations such as issue classification and safe troubleshooting checklists.

### 5. What is memory?
A small persistent store of useful, non-sensitive user context that can personalize later support.

### 6. How is a document indexed?
Text is extracted, split into overlapping chunks, embedded, and stored with the source document.

### 7. How does a ticket help?
It creates a human escalation path when a problem is unresolved, high impact, or needs administrator action.

### 8. Why not allow arbitrary commands?
Arbitrary commands create security risk. This project uses allowlisted, read-only-style support tools and human escalation.

### 9. Main technologies?
React, TypeScript, FastAPI, Python, PostgreSQL, pgvector, OpenAI models, embeddings.

### 10. Future enhancements?
Live device telemetry with explicit consent, enterprise identity integration, SLA dashboards, multilingual support, richer observability, and role-based admin workflows.
