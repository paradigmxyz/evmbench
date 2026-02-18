from .abc import BackendABC
from .docker import DockerBackend
from .k8s import K8sBackend


backends: dict[str, type[BackendABC]] = {
    'docker': DockerBackend,
    'k8s': K8sBackend,
}
