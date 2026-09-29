from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings


def get_gemini_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Set it in backend/.env when ACTIVE_PROVIDER=gemini."
        )
    return ChatGoogleGenerativeAI(
        model=settings.model_name,
        api_key=settings.gemini_api_key,
        temperature=temperature,
    )
