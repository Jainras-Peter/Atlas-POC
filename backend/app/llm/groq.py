from langchain_groq import ChatGroq

from app.config import settings


def get_groq_llm(temperature: float = 0) -> ChatGroq:
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Set it in backend/.env when ACTIVE_PROVIDER=groq."
        )
    return ChatGroq(
        model=settings.model_name,
        api_key=settings.groq_api_key,
        temperature=temperature,
    )
