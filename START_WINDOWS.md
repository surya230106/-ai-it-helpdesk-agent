# Start on Windows 11 + VS Code

## 1. Install
- Docker Desktop
- VS Code
- Git (optional)

## 2. Open the project
Extract the ZIP and open the `ai-it-helpdesk-agent` folder in VS Code.

## 3. Local/offline mode (default)
Copy `.env.example` to `.env` in the project root. No API key is required:

```env
AI_MODE=local
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-luna
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
JWT_SECRET=use-a-long-random-value
```

## 4. Start
In the VS Code terminal:

```powershell
docker compose up --build
```

## 5. Open
- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## 6. First demo
Create the first account; it is treated as the demo admin. The starter knowledge documents are indexed automatically. Then ask:

`My Wi-Fi shows connected but websites do not open.`

The response should display the diagnosis, tools used, and knowledge sources.

## Stop
```powershell
docker compose down
```

To also delete database data:
```powershell
docker compose down -v
```
