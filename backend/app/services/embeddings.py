from openai import OpenAI
from app.core.config import settings

def openai_enabled() -> bool:
    return settings.ai_mode == "openai" and bool(settings.openai_api_key.strip())

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not openai_enabled() or not texts:
        return []
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(model=settings.openai_embedding_model, input=texts)
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
    except Exception:
        return []
