from abc import ABC, abstractmethod

from api.core.tokens import Token


class AuthBackendABC(ABC):
    def __init__(self, args: dict[str, str]) -> None:
        self._args = args

    @abstractmethod
    async def get_redirect_url(self, state: str, redirect_uri: str) -> str: ...

    @abstractmethod
    async def get_token(self, code: str) -> Token | None: ...
