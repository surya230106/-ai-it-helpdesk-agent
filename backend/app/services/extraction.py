from pathlib import Path
from pypdf import PdfReader
from docx import Document

SUPPORTED = {'.pdf', '.txt', '.md', '.docx'}


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError('Supported files: PDF, DOCX, TXT, MD')
    if ext in {'.txt', '.md'}:
        return data.decode('utf-8', errors='ignore')
    tmp = Path('/tmp') / f'helpdesk_{abs(hash(filename))}{ext}'
    tmp.write_bytes(data)
    try:
        if ext == '.pdf':
            reader = PdfReader(str(tmp))
            return '\n'.join((page.extract_text() or '') for page in reader.pages)
        doc = Document(str(tmp))
        return '\n'.join(paragraph.text for paragraph in doc.paragraphs)
    finally:
        tmp.unlink(missing_ok=True)


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError('size must be > 0 and overlap must be >= 0 and < size')
    normalized = ' '.join(text.split())
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = end - overlap
    return chunks
