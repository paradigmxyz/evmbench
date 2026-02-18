from pydantic import AliasChoices, Field, PostgresDsn, Secret
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.util.fs import ROOT_DIR


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    RESULTSVC_HOST: str = '127.0.0.1'
    RESULTSVC_PORT: int = 8083
    RESULTSVC_WORKERS: int = 1

    DATABASE_DSN: Secret[PostgresDsn]
    RESULTSVC_DATABASE_POOL_SIZE: int = Field(
        default=10,
        validation_alias=AliasChoices('RESULTSVC_DATABASE_POOL_SIZE', 'DATABASE_POOL_SIZE'),
    )
    RESULTSVC_DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        validation_alias=AliasChoices('RESULTSVC_DATABASE_MAX_OVERFLOW', 'DATABASE_MAX_OVERFLOW'),
    )


settings = Settings()  # type: ignore[missing-argument]
