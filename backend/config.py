from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # OCR & AI
    OCR_PROVIDER: str = "cloud"  # 'cloud' (OCR.space)
    OCR_API_KEY: str = ""          # OCR.space API key
    GROQ_API_KEY: str = ""         # Groq LLM API Key (optional for Llama 3 70B AI label analysis)

    # App
    BACKEND_URL: str = "http://localhost:8000"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
