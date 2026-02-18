from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StartWorkerOptions:
    job_id: str
    secret_ref: str
    model: str
    result_token: str


@dataclass(frozen=True)
class StartWorkerResult:
    error: str | None = None  # gets returned to the user
    worker_id: str | None = None


@dataclass(frozen=True)
class WorkerInfo:
    id: str


class BackendABC(ABC):
    def __init__(self, args: dict[str, str]) -> None:
        self._args = args

    @abstractmethod
    async def start_worker(self, options: StartWorkerOptions) -> StartWorkerResult: ...

    @abstractmethod
    async def running_workers(self) -> int: ...

    def default_max_concurrency(self) -> int | None:
        return None
