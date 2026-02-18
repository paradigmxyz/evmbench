from .abc import AuthBackendABC
from .github import GithubAuthBackend


auth_backends: dict[str, type[AuthBackendABC]] = {
    'github': GithubAuthBackend,
}
