from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, Secret, field_validator, model_validator
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

    # Postgres in deployments; SQLite (sqlite+aiosqlite://) for local no-Docker runs.
    DATABASE_DSN: Secret[str]
    DATABASE_AUTO_CREATE_TABLES: bool = False
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

    # Shared credentials require an explicit opt-in on both the API and proxy.
    OAI_SHARED_KEY_ENABLED: bool = False
    BACKEND_STATIC_OAI_KEY: Secret[str] | None = None
    # When true, use the proxy's static key (sends "STATIC" marker instead of encrypted key)
    # The real OpenAI key is only known by oai_proxy, never exposed to backend or agents
    BACKEND_USE_PROXY_STATIC_KEY: bool = False
    # Required only when BACKEND_OAI_KEY_MODE="proxy"
    OAI_PROXY_AES_KEY: Secret[str] | None = None

    RABBITMQ_DSN: Secret[str] | None = None
    RABBITMQ_QUEUE: str = 'instancer.jobs'
    RABBITMQ_QUEUE_SUFFIX: str | None = None
    RABBITMQ_QUEUE_TTL_SECONDS: int = 60
    RABBITMQ_QUEUE_DLQ: str | None = None
    INSTANCER_MAX_CONCURRENT_JOBS: int | None = Field(
        default=None,
        validation_alias=AliasChoices('INSTANCER_MAX_CONCURRENT_JOBS', 'MAX_CONCURRENT_JOBS'),
    )

    # Job dispatch backend: 'rabbitmq' publishes to the queue consumed by the
    # instancer (Docker/K8s deployments); 'local' runs the worker as a child
    # process of the API, removing the RabbitMQ/instancer/Docker dependency.
    # Local mode requires BACKEND_WEB_WORKERS=1 (dispatching happens in-process).
    BACKEND_QUEUE_BACKEND: str = 'rabbitmq'
    BACKEND_LOCAL_MAX_CONCURRENT_JOBS: int = 1
    BACKEND_LOCAL_WORKERS_ROOT: Path = ROOT_DIR / '.data' / 'local_workers'
    BACKEND_LOCAL_WORKER_SCRIPT: Path = ROOT_DIR / 'docker' / 'worker' / 'init.py'
    BACKEND_LOCAL_RUNNER_DIR: Path = ROOT_DIR / 'worker_runner'
    BACKEND_LOCAL_RUNNER_SCRIPT: str = 'run_zcode_detect.sh'
    BACKEND_LOCAL_SECRETSVC_HOST: str = '127.0.0.1'
    BACKEND_LOCAL_SECRETSVC_PORT: int = 8081
    # Read-only secrets token shared with secretsvc (env alias matches secretsvc's own).
    BACKEND_LOCAL_SECRETS_TOKEN_RO: Secret[str] | None = Field(
        default=None,
        validation_alias=AliasChoices('BACKEND_LOCAL_SECRETS_TOKEN_RO', 'SECRETS_TOKEN_RO'),
    )
    BACKEND_LOCAL_RESULTSVC_HOST: str = '127.0.0.1'
    BACKEND_LOCAL_RESULTSVC_PORT: int = 8083

    BACKEND_CORS_EXTRA_ORIGINS: list[str] = Field(default_factory=list)

    AUTH_BACKEND: str | None = None
    AUTH_BACKEND_ARGUMENTS: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def _disable_shared_key(self) -> 'Settings':
        if not self.OAI_SHARED_KEY_ENABLED:
            self.BACKEND_STATIC_OAI_KEY = None
            self.BACKEND_USE_PROXY_STATIC_KEY = False
        return self

    @field_validator('RABBITMQ_QUEUE_SUFFIX', mode='before')
    @classmethod
    def _normalize_queue_suffix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        suffix = value.strip().strip('.')
        return suffix or None

    @field_validator('DATABASE_DSN', mode='after')
    @classmethod
    def _validate_database_dsn(cls, value: Secret[str]) -> Secret[str]:
        dsn = value.get_secret_value()
        if not dsn.startswith(('postgresql+asyncpg://', 'sqlite+aiosqlite://')):
            msg = 'DATABASE_DSN must be a postgresql+asyncpg:// or sqlite+aiosqlite:// URL'
            raise ValueError(msg)
        return value

    @model_validator(mode='after')
    def _validate_queue_backend(self) -> 'Settings':
        if self.BACKEND_QUEUE_BACKEND not in {'rabbitmq', 'local'}:
            msg = 'BACKEND_QUEUE_BACKEND must be rabbitmq or local'
            raise ValueError(msg)
        if self.BACKEND_QUEUE_BACKEND == 'rabbitmq' and not self.RABBITMQ_DSN:
            msg = 'RABBITMQ_DSN is required when BACKEND_QUEUE_BACKEND=rabbitmq'
            raise ValueError(msg)
        if self.BACKEND_QUEUE_BACKEND == 'local':
            if self.BACKEND_WEB_WORKERS != 1:
                msg = 'BACKEND_WEB_WORKERS must be 1 when BACKEND_QUEUE_BACKEND=local'
                raise ValueError(msg)
            if not self.BACKEND_LOCAL_SECRETS_TOKEN_RO:
                msg = 'SECRETS_TOKEN_RO is required when BACKEND_QUEUE_BACKEND=local'
                raise ValueError(msg)
        return self

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
