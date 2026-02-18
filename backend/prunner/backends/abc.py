from abc import ABC, abstractmethod


class BackendABC(ABC):
    def __init__(self, args: dict[str, str]) -> None:
        self._args = args

    @abstractmethod
    async def run_once(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
