from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # OCR & AI
    OCR_PROVIDER: str = "ocr_space"  # 'auto' / 'local' / 'ocr_space'
    OCR_API_KEY: str = ""          # OCR.space API key
    LOCAL_OCR_ENABLED: bool = False
    LOCAL_OCR_URL: str = "http://127.0.0.1:8001/ocr"
    LOCAL_OCR_API_KEY: str = "local-secret-key-123"
    LOCAL_OCR_TIMEOUT_SECONDS: float = 15.0
    OCR_LOCAL_FALLBACK_TO_CLOUD: bool = True
    GROQ_API_KEY: str = ""         # Groq LLM API Key (optional for Llama 3 70B AI label analysis)

    # App
    BACKEND_URL: str = "http://localhost:8000"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
