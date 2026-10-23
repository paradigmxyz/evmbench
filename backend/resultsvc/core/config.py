from pydantic import AliasChoices, Field, Secret, field_validator
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

    # Postgres in deployments; SQLite (sqlite+aiosqlite://) for local no-Docker runs.
    DATABASE_DSN: Secret[str]
    RESULTSVC_DATABASE_POOL_SIZE: int = Field(
        default=10,
        validation_alias=AliasChoices('RESULTSVC_DATABASE_POOL_SIZE', 'DATABASE_POOL_SIZE'),
    )
    RESULTSVC_DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        validation_alias=AliasChoices('RESULTSVC_DATABASE_MAX_OVERFLOW', 'DATABASE_MAX_OVERFLOW'),
    )

    @field_validator('DATABASE_DSN', mode='after')
    @classmethod
    def _validate_database_dsn(cls, value: Secret[str]) -> Secret[str]:
        dsn = value.get_secret_value()
        if not dsn.startswith(('postgresql+asyncpg://', 'sqlite+aiosqlite://')):
            msg = 'DATABASE_DSN must be a postgresql+asyncpg:// or sqlite+aiosqlite:// URL'
            raise ValueError(msg)
        return value


settings = Settings()  # type: ignore[missing-argument]
