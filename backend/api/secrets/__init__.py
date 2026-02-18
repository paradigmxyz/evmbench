from .abc import SecretStorageABC
from .http import HttpSecretStorage


secret_storages: dict[str, type[SecretStorageABC]] = {
    'http': HttpSecretStorage,
}
