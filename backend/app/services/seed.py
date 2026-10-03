from pathlib import Path
from sqlalchemy.orm import Session
from app.models import KnowledgeDocument, KnowledgeChunk
from app.services.extraction import extract_text, chunk_text


def seed_knowledge_base(db: Session):
    data_dir = Path('/app/data/kb')
    if not data_dir.exists():
        return
    for path in data_dir.glob('*'):
        if not path.is_file() or path.suffix.lower() not in {'.txt', '.md'}:
            continue
        title = path.name
        if db.query(KnowledgeDocument).filter(KnowledgeDocument.title == title).first():
            continue
        text = extract_text(title, path.read_bytes())
        chunks = chunk_text(text)
        if not chunks:
            continue
        doc = KnowledgeDocument(title=title, filename=title, source_type='seed')
        db.add(doc)
        db.flush()
        for i, chunk in enumerate(chunks):
            db.add(KnowledgeChunk(document_id=doc.id, chunk_text=chunk, chunk_index=i))
        db.commit()
