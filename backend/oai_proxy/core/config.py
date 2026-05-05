from pathlib import Path

from pydantic import Secret
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.util.fs import ROOT_DIR


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    OAI_PROXY_HOST: str = '127.0.0.1'
    OAI_PROXY_PORT: int = 8084
    OAI_PROXY_WORKERS: int = 1
    OAI_PROXY_AES_KEY: Secret[str]
    OAI_PROXY_UPSTREAM_BASE_URL: str = 'https://api.openai.com'
    OAI_PROXY_STRIP_WEB_SEARCH: bool = False
    OAI_PROXY_RESPONSE_CACHE_ENABLED: bool = False
    OAI_PROXY_RESPONSE_CACHE_DIR: Path = ROOT_DIR / '.data' / 'oai_proxy_cache'
    OAI_PROXY_RESPONSE_CACHE_TTL_SECONDS: int = 0
    OAI_PROXY_RESPONSE_CACHE_MAX_ENTRY_BYTES: int = 32 * 1024 * 1024
    OAI_PROXY_RESPONSE_CACHE_MAX_ENTRIES: int = 4096
    OAI_PROXY_RESPONSE_CACHE_INCLUDE_AUTH: bool = True
    # Static OpenAI key - when set, requests with "Bearer STATIC" use this key
    # The real key never leaves this service
    OAI_PROXY_STATIC_KEY: Secret[str] | None = None


settings = Settings()  # type: ignore[missing-argument]
