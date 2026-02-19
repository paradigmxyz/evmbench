from pydantic import AliasChoices, Field, PostgresDsn, Secret, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from api.util.fs import ROOT_DIR


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    RABBITMQ_DSN: Secret[str]
    RABBITMQ_QUEUE: str = 'instancer.jobs'
    RABBITMQ_QUEUE_SUFFIX: str | None = None
    RABBITMQ_QUEUE_TTL_SECONDS: int | None = None
    RABBITMQ_QUEUE_DLQ: str | None = None

    DATABASE_DSN: Secret[PostgresDsn]
    INSTANCER_DATABASE_POOL_SIZE: int = Field(
        default=10,
        validation_alias=AliasChoices('INSTANCER_DATABASE_POOL_SIZE', 'DATABASE_POOL_SIZE'),
    )
    INSTANCER_DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        validation_alias=AliasChoices('INSTANCER_DATABASE_MAX_OVERFLOW', 'DATABASE_MAX_OVERFLOW'),
    )

    INSTANCER_MANAGER_NAME: str = Field(
        default='svmbench-instancer',
        validation_alias=AliasChoices('INSTANCER_MANAGER_NAME', 'MANAGER_NAME'),
    )
    INSTANCER_WORKERS_BACKEND: str = 'docker'
    INSTANCER_WORKERS_BACKEND_ARGUMENTS: dict[str, str] = Field(default_factory=dict)
    INSTANCER_WORKER_IMAGE: str = 'svmbench/worker:latest'
    INSTANCER_WORKER_RUNTIME_IMAGE: str | None = None
    INSTANCER_WORKER_RUNTIME_PORT: int = 8082
    INSTANCER_JOB_TTL_SECONDS: int = 60
    INSTANCER_JOB_DLQ: str | None = None
    INSTANCER_MAX_CONCURRENT_JOBS: int | None = Field(
        default=None,
        validation_alias=AliasChoices('INSTANCER_MAX_CONCURRENT_JOBS', 'MAX_CONCURRENT_JOBS'),
    )
    INSTANCER_CAPACITY_POLL_SECONDS: int = 15

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

    INSTANCER_SECRETSVC_HOST: str = 'secretsvc'
    INSTANCER_SECRETSVC_PORT: int = 8081
    INSTANCER_SECRETS_TOKEN_RO: Secret[str] = Field(
        validation_alias=AliasChoices('INSTANCER_SECRETS_TOKEN_RO', 'SECRETS_TOKEN_RO'),
    )

    INSTANCER_RESULTSVC_HOST: str = 'resultsvc'
    INSTANCER_RESULTSVC_PORT: int = 8083

    # Optional: only needed when the backend is configured for proxy-token mode.
    INSTANCER_OAI_PROXY_BASE_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices('INSTANCER_OAI_PROXY_BASE_URL', 'OAI_PROXY_BASE_URL'),
    )

    @field_validator('INSTANCER_OAI_PROXY_BASE_URL', mode='before')
    @classmethod
    def _normalize_proxy_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


settings = Settings()  # type: ignore[missing-argument]
