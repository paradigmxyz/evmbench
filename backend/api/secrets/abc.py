from abc import ABC, abstractmethod


class SecretStorageABC(ABC):
    def __init__(self, args: dict[str, str]) -> None:
        self._args = args

    @abstractmethod
    async def save_secret(self, secret_id: str, secret_data: bytes) -> None: ...

    @abstractmethod
    async def get_and_delete_secret(self, secret_id: str) -> bytes: ...

    @abstractmethod
    async def delete_secret(self, secret_id: str) -> None: ...
