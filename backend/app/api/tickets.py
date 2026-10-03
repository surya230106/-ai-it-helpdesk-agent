from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User, Ticket
from app.schemas.helpdesk import TicketCreate, TicketOut

router=APIRouter(prefix="/tickets",tags=["Tickets"])

def as_out(t):
    return {"id":t.id,"title":t.title,"description":t.description,"category":t.category,"priority":t.priority,"status":t.status,"ai_summary":t.ai_summary,"resolution":t.resolution,"created_at":t.created_at,"updated_at":t.updated_at}

@router.get("",response_model=list[TicketOut])
def list_tickets(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return [as_out(t) for t in db.query(Ticket).filter(Ticket.user_id==user.id).order_by(Ticket.created_at.desc()).all()]

@router.post("",response_model=TicketOut)
def create_ticket(payload:TicketCreate,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    t=Ticket(user_id=user.id,title=payload.title,description=payload.description,category=payload.category,priority=payload.priority)
    db.add(t);db.commit();db.refresh(t);return as_out(t)

@router.patch("/{ticket_id}",response_model=TicketOut)
def update_ticket(ticket_id:int,status:str|None=None,resolution:str|None=None,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    t=db.query(Ticket).filter(Ticket.id==ticket_id,Ticket.user_id==user.id).first()
    if not t: raise HTTPException(404,"Ticket not found")
    if status is not None: t.status=status
    if resolution is not None: t.resolution=resolution
    db.commit();db.refresh(t);return as_out(t)
