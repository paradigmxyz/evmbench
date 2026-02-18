from filelock import FileLock, Timeout


class Worker:
    def __init__(self) -> None:
        self.lock: FileLock | None = None
        self.setup()

    def setup(self) -> None:
        self.lock = FileLock('worker.lock')
        try:
            self.lock.acquire(blocking=False)
        except Timeout:
            return

    @property
    def is_first(self) -> bool:
        if self.lock is None:
            return False
        return self.lock.is_locked


worker = Worker()
