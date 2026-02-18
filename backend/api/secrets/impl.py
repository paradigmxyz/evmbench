from api.core.config import settings
from api.secrets import SecretStorageABC, secret_storages


secret_storage: SecretStorageABC = secret_storages[settings.BACKEND_SECRETS_BACKEND](
    settings.BACKEND_SECRETS_BACKEND_ARGUMENTS,
)
