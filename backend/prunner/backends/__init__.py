from prunner.backends.abc import BackendABC
from prunner.backends.docker import DockerBackend
from prunner.backends.k8s import K8sBackend


backends: dict[str, type[BackendABC]] = {
    'docker': DockerBackend,
    'k8s': K8sBackend,
}
