from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    app_name: str = "RiskIntern PhishSim"
    app_env: str = "development"
    app_secret_key: str = "change-me"
    database_url: str = "sqlite:///./riskintern.db"
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = "gpt-5.6-luna"
    openai_base_url: str = "https://api.openai.com/v1"
    campaign_provider: str = "mock"
    gophish_url: str = ""
    gophish_api_key: str = ""
    gophish_verify_tls: bool = True
    email_provider: str = "mock"
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "simulation@demo.example.com"
    authorized_email_domains: str = "demo.example.com,example.com"
    seed_on_start: bool = True
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def cors_list(self): return [x.strip() for x in self.cors_origins.split(',') if x.strip()]
    @property
    def allowed_domains(self): return {x.strip().lower() for x in self.authorized_email_domains.split(',') if x.strip()}

@lru_cache
def get_settings(): return Settings()
settings = get_settings()
