from api.auth import AuthBackendABC, auth_backends
from api.core.config import settings
from api.secrets import SecretStorageABC, secret_storages


secret_storage: SecretStorageABC = secret_storages[settings.BACKEND_SECRETS_BACKEND](
    settings.BACKEND_SECRETS_BACKEND_ARGUMENTS,
)

auth_backend: AuthBackendABC | None = (
    auth_backends[settings.AUTH_BACKEND](
        settings.AUTH_BACKEND_ARGUMENTS,
    )
    if settings.AUTH_BACKEND
    else None
)
