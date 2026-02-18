from pathlib import Path

from pydantic import AliasChoices, Field, Secret
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.util.fs import ROOT_DIR


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    SECRETSVC_HOST: str = '127.0.0.1'
    SECRETSVC_PORT: int = 8081
    SECRETSVC_WORKERS: int = 1

    SECRETSVC_SECRETS_DIR: Path = ROOT_DIR / '.data' / 'secrets'
    SECRETSVC_BUNDLE_MAX_READS: int = 1

    SECRETSVC_SECRETS_TOKEN_WO: Secret[str] = Field(
        validation_alias=AliasChoices('SECRETSVC_SECRETS_TOKEN_WO', 'SECRETS_TOKEN_WO'),
    )
    SECRETSVC_SECRETS_TOKEN_RO: Secret[str] = Field(
        validation_alias=AliasChoices('SECRETSVC_SECRETS_TOKEN_RO', 'SECRETS_TOKEN_RO'),
    )


settings = Settings()  # type: ignore[missing-argument]
