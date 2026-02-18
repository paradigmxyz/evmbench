from prunner.backends import BackendABC, backends
from prunner.core.config import settings


prunner_backend: BackendABC = backends[settings.PRUNNER_BACKEND](settings.PRUNNER_BACKEND_ARGUMENTS)
