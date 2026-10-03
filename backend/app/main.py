import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.config import settings
from app.db.session import init_db, SessionLocal, engine
from app.agent.llm_provider import OllamaProvider
from app.services.seed import seed_knowledge_base
from app.api import auth, agent, tickets, knowledge, dashboard

app = FastAPI(title=settings.app_name, version='1.0.0')
logger = logging.getLogger("helpdesk.api")

@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.exception("request_failed method=%s path=%s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Sorry, I could not complete that request. Please try again."})
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(auth.router, prefix='/api')
app.include_router(agent.router, prefix='/api')
app.include_router(tickets.router, prefix='/api')
app.include_router(knowledge.router, prefix='/api')
app.include_router(dashboard.router, prefix='/api')

@app.on_event('startup')
def startup():
    init_db()
    db = SessionLocal()
    try:
        seed_knowledge_base(db)
    finally:
        db.close()

@app.get('/health')
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        database = 'healthy'
    except Exception:
        database = 'unavailable'
    ollama = OllamaProvider().health() if settings.ai_mode.lower() == 'local' and settings.ai_provider.lower() == 'ollama' else {'reachable': False, 'model': None, 'model_available': False}
    return {
        'status': 'ok', 'service': settings.app_name, 'ai_mode': settings.ai_mode,
        'ai_provider': settings.ai_provider if settings.ai_mode.lower() == 'local' else settings.ai_mode,
        'offline': settings.ai_mode.lower() == 'local', 'database': database,
        'ollama': ollama,
    }
