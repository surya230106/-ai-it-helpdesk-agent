from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.helpdesk import ChatIn, ChatOut, MemoryOut
from app.agent.agent import run_agent
from app.services.memory import get_memories

router=APIRouter(prefix="/agent",tags=["Agent"])

@router.post("/chat",response_model=ChatOut)
def chat(payload: ChatIn, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    return run_agent(db,user.id,payload.message,payload.history)

@router.get("/memory",response_model=list[MemoryOut])
def memory(user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    return get_memories(db,user.id)
