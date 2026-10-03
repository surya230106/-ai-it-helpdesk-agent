from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User, Ticket, AgentInteraction

router=APIRouter(prefix="/dashboard",tags=["Dashboard"])

@router.get("")
def dashboard(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    total=db.query(func.count(Ticket.id)).filter(Ticket.user_id==user.id).scalar() or 0
    open_count=db.query(func.count(Ticket.id)).filter(Ticket.user_id==user.id,Ticket.status=="open").scalar() or 0
    resolved=db.query(func.count(Ticket.id)).filter(Ticket.user_id==user.id,Ticket.status=="resolved").scalar() or 0
    chats=db.query(func.count(AgentInteraction.id)).filter(AgentInteraction.user_id==user.id).scalar() or 0
    return {"tickets":total,"open_tickets":open_count,"resolved_tickets":resolved,"agent_interactions":chats}
