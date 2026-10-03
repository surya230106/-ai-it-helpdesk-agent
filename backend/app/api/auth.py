from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import User
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut
from app.utils.security import hash_password, verify_password, create_token
from app.api.deps import get_current_user

router = APIRouter(prefix='/auth', tags=['Auth'])

@router.post('/register', response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, 'Email already registered')
    role = 'admin' if db.query(User).count() == 0 else 'user'
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {'access_token': create_token(user.id), 'user': user}

@router.post('/login', response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, 'Invalid email or password')
    return {'access_token': create_token(user.id), 'user': user}

@router.get('/me', response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
