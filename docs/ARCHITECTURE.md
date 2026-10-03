# AI IT Helpdesk Agent — Architecture

## Goal
Diagnose common technical issues and recommend safe troubleshooting steps using a knowledge base.

## Core capabilities
- **Agent:** decides what structured actions are useful before answering.
- **RAG:** retrieves relevant helpdesk knowledge-base chunks and uses them as evidence.
- **Tools:** issue classification, priority hint, category checklist, knowledge-base search.
- **Ticketing:** saves an issue for human escalation.
- **Memory:** stores small user context such as recent issue category.

## Flow
User → React UI → FastAPI → Helpdesk Agent → RAG + Tools → grounded response → optional Ticket

## Data
PostgreSQL stores users, documents, chunks, 1536-dimension embeddings, memories, tickets, and agent interactions. pgvector provides cosine-distance retrieval.

## Safety
The application intentionally does not expose arbitrary shell execution. Troubleshooting tools return safe, structured guidance. Sensitive credentials must not be requested or stored.
