from app.services.extraction import chunk_text

def test_chunk_text():
    text="abcdefghijklmnopqrstuvwxyz"
    chunks=chunk_text(text,size=10,overlap=2)
    assert chunks
    assert "abcdefghij" in chunks[0]
