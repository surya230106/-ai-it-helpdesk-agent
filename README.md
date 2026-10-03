# AI IT Helpdesk Agent

A complete VS Code project for an **AI IT Helpdesk Agent**.

## User requirement
**Topic:** AI IT Helpdesk Agent  
**What students build:** Diagnoses common technical issues and recommends troubleshooting steps using a knowledge base  
**Key capabilities:** **Agent + RAG + Tool**

## Stack
- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Python
- Database: PostgreSQL + pgvector
- AI: local/offline TF-IDF RAG and deterministic agent tools by default; OpenAI is optional.
- Auth: JWT + bcrypt
- Documents: PDF, DOCX, TXT, MD

## Run in VS Code
1. Install Docker Desktop.
2. Open the extracted project folder in VS Code.
3. No API key is required. Local/offline mode is the default (`AI_MODE=local`).
4. Run:

```powershell
docker compose up --build
```

5. Open `http://localhost:5173`.
6. API docs: `http://localhost:8000/docs`.

## Demo flow
- Register a user. The first account becomes admin for demo purposes.
- Open **Knowledge Base** and upload a troubleshooting document.
- Ask the assistant a technical question.
- Review diagnosis, priority hint, tools used, and knowledge citations.
- Create a ticket for escalation.

## Local/offline mode
`docker compose up --build` starts without an API key. Documents are chunked into PostgreSQL and searched locally with TF-IDF/cosine similarity; the agent uses local issue classification, priority, retrieval, troubleshooting, and ticket tools. To opt into OpenAI, set `AI_MODE=openai` and supply an API key.

## Important security note
This project intentionally does **not** execute arbitrary operating-system commands. The tool layer is allowlisted and safe by design. In a real enterprise deployment, live device diagnostics should require explicit user consent, least-privilege controls, and audited execution.

## File structure

```text
ai-it-helpdesk-agent/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   └── tests/
├── frontend/
│   └── src/
├── data/kb/
├── docs/
└── docker-compose.yml
```

## Troubleshooting
If the frontend image fails to build, run `npm install` and `npm run build` inside `frontend` to verify Node dependencies. If PostgreSQL is not ready on the first start, restart the backend container after the database becomes healthy.
