from pydantic import Secret, model_validator
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
    OAI_SHARED_KEY_ENABLED: bool = False
    # Static OpenAI key - when set, requests with "Bearer STATIC" use this key
    # The real key never leaves this service
    OAI_PROXY_STATIC_KEY: Secret[str] | None = None

    @model_validator(mode='after')
    def _disable_shared_key(self) -> 'Settings':
        if not self.OAI_SHARED_KEY_ENABLED:
            self.OAI_PROXY_STATIC_KEY = None
        return self


settings = Settings()  # type: ignore[missing-argument]
