from typing import Literal

from pydantic import AliasChoices, Field, PostgresDsn, Secret, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.util.fs import ROOT_DIR


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    BACKEND_DEV: bool = False

    BACKEND_WEB_HOST: str = '127.0.0.1'
    BACKEND_WEB_PORT: int = 1337
    BACKEND_WEB_WORKERS: int = 4

    DATABASE_DSN: Secret[PostgresDsn]
    BACKEND_DATABASE_POOL_SIZE: int = Field(
        default=10,
        validation_alias=AliasChoices('BACKEND_DATABASE_POOL_SIZE', 'DATABASE_POOL_SIZE'),
    )
    BACKEND_DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        validation_alias=AliasChoices('BACKEND_DATABASE_MAX_OVERFLOW', 'DATABASE_MAX_OVERFLOW'),
    )

    BACKEND_MAX_ATTACHMENT_SIZE_BYTES: int = 20 * 1024 * 1024  # 20mb
    BACKEND_MAX_ATTACHMENT_UNCOMPRESSED_BYTES: int = 30 * 1024 * 1024  # 30mb
    BACKEND_ZIP_MAX_FILES: int = 50_000
    BACKEND_ZIP_MAX_COMPRESSION_RATIO: int = 100

    BACKEND_SECRETS_BACKEND: str = 'server'
    BACKEND_SECRETS_BACKEND_ARGUMENTS: dict[str, str] = Field(default_factory=dict)

    FRONTEND_PUBLIC_URL: str = 'http://127.0.0.1:3000'
    BACKEND_PUBLIC_URL: str = 'http://127.0.0.1:1337'
    BACKEND_JWT_SECRET: Secret[str]
    BACKEND_JWT_TTL_SECONDS: int = 60 * 60 * 24 * 30  # 30d

    # How to pass OpenAI credentials to the worker.
    # - direct: worker receives plaintext OPENAI_API_KEY (default for OSS)
    # - proxy: worker receives encrypted token; oai_proxy decrypts and forwards upstream
    BACKEND_OAI_KEY_MODE: Literal['direct', 'proxy'] = 'direct'

    BACKEND_STATIC_OAI_KEY: Secret[str] | None = None
    # When true, use the proxy's static key (sends "STATIC" marker instead of encrypted key)
    # The real OpenAI key is only known by oai_proxy, never exposed to backend or agents
    BACKEND_USE_PROXY_STATIC_KEY: bool = False
    # Required only when BACKEND_OAI_KEY_MODE="proxy"
    OAI_PROXY_AES_KEY: Secret[str] | None = None

    RABBITMQ_DSN: Secret[str]
    RABBITMQ_QUEUE: str = 'instancer.jobs'
    RABBITMQ_QUEUE_SUFFIX: str | None = None
    RABBITMQ_QUEUE_TTL_SECONDS: int = 60
    RABBITMQ_QUEUE_DLQ: str | None = None
    INSTANCER_MAX_CONCURRENT_JOBS: int | None = Field(
        default=None,
        validation_alias=AliasChoices('INSTANCER_MAX_CONCURRENT_JOBS', 'MAX_CONCURRENT_JOBS'),
    )

    BACKEND_CORS_EXTRA_ORIGINS: list[str] = Field(default_factory=list)

    AUTH_BACKEND: str | None = None
    AUTH_BACKEND_ARGUMENTS: dict[str, str] = Field(default_factory=dict)

    @field_validator('RABBITMQ_QUEUE_SUFFIX', mode='before')
    @classmethod
    def _normalize_queue_suffix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        suffix = value.strip().strip('.')
        return suffix or None

    @model_validator(mode='after')
    def _default_queue_suffix(self) -> 'Settings':
        if self.RABBITMQ_QUEUE_SUFFIX:
            return self
        limit = self.INSTANCER_MAX_CONCURRENT_JOBS
        if limit is not None and limit > 0:
            self.RABBITMQ_QUEUE_SUFFIX = 'limited'
        return self

    @property
    def rabbitmq_queue_name(self) -> str:
        if not self.RABBITMQ_QUEUE_SUFFIX:
            return self.RABBITMQ_QUEUE
        return f'{self.RABBITMQ_QUEUE}.{self.RABBITMQ_QUEUE_SUFFIX}'


settings = Settings()  # type: ignore[missing-argument]
