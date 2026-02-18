from instancer.backends import BackendABC, backends
from instancer.core.config import settings


workers_backend: BackendABC = backends[settings.INSTANCER_WORKERS_BACKEND](settings.INSTANCER_WORKERS_BACKEND_ARGUMENTS)
