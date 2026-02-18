from pydantic import AliasChoices, Field, PostgresDsn, Secret
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.util.fs import ROOT_DIR


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    DATABASE_DSN: Secret[PostgresDsn]
    PRUNNER_DATABASE_POOL_SIZE: int = Field(
        default=5,
        validation_alias=AliasChoices('PRUNNER_DATABASE_POOL_SIZE', 'DATABASE_POOL_SIZE'),
    )
    PRUNNER_DATABASE_MAX_OVERFLOW: int = Field(
        default=5,
        validation_alias=AliasChoices('PRUNNER_DATABASE_MAX_OVERFLOW', 'DATABASE_MAX_OVERFLOW'),
    )

    PRUNNER_BACKEND: str = 'docker'
    PRUNNER_BACKEND_ARGUMENTS: dict[str, str] = Field(default_factory=dict)
    PRUNNER_POLL_SECONDS: float = 10.0
    PRUNNER_MAX_CONTAINER_AGE_SECONDS: int = 3600
    PRUNNER_MANAGER_NAME: str = Field(
        default='evmbench-instancer',
        validation_alias=AliasChoices('PRUNNER_MANAGER_NAME', 'MANAGER_NAME', 'INSTANCER_MANAGER_NAME'),
    )


settings = Settings()  # type: ignore[missing-argument]
