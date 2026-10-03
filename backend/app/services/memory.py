from sqlalchemy.orm import Session
from app.models import Memory

def get_memories(db: Session, user_id: int):
    return db.query(Memory).filter(Memory.user_id==user_id).order_by(Memory.updated_at.desc()).limit(12).all()

def upsert_memory(db: Session, user_id: int, key: str, value: str):
    row=db.query(Memory).filter(Memory.user_id==user_id, Memory.key==key).first()
    if row: row.value=value
    else: row=Memory(user_id=user_id,key=key,value=value); db.add(row)
    db.commit(); return row
