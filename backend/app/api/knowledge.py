from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models import User, KnowledgeDocument, KnowledgeChunk
from app.services.extraction import extract_text, chunk_text

router=APIRouter(prefix="/knowledge",tags=["Knowledge Base"])

@router.get("")
def list_docs(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return [{"id":d.id,"title":d.title,"filename":d.filename,"source_type":d.source_type,"created_at":d.created_at,"chunks":len(d.chunks)} for d in db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()]

@router.post("/upload")
async def upload(file:UploadFile=File(...),admin:User=Depends(require_admin),db:Session=Depends(get_db)):
    data=await file.read()
    if len(data)>10*1024*1024: raise HTTPException(413,"File too large")
    try: text=extract_text(file.filename or "upload.txt",data)
    except ValueError as e: raise HTTPException(400,str(e))
    chunks=chunk_text(text)
    if not chunks: raise HTTPException(400,"No readable text found")
    doc=KnowledgeDocument(title=file.filename or "Untitled",filename=file.filename,source_type="upload")
    db.add(doc);db.flush()
    for i,chunk in enumerate(chunks):
        db.add(KnowledgeChunk(document_id=doc.id,chunk_text=chunk,chunk_index=i))
    db.commit()
    return {"message":"Knowledge document indexed locally","document_id":doc.id,"chunks":len(chunks),"indexing":"local_tfidf"}
