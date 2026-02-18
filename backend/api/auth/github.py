from http import HTTPStatus
from urllib.parse import quote, urlencode

import orjson
from httpx import AsyncClient, Response

from api.core.tokens import Token

from .abc import AuthBackendABC


def get_json(in_response: Response) -> dict[str, str] | None:
    if in_response.status_code != HTTPStatus.OK:
        return None

    try:
        out_response = orjson.loads(in_response.text)
    except orjson.JSONDecodeError:
        return None

    if not isinstance(out_response, dict):
        return None

    return out_response


class GithubAuthBackend(AuthBackendABC):
    def __init__(self, args: dict[str, str]) -> None:
        super().__init__(args)
        self._client_id = self._args.get('client_id')
        self._client_secret = self._args.get('client_secret')

        if not self._client_id or not self._client_secret:
            msg = 'Client id or secret is not set'
            raise ValueError(msg)

    async def get_redirect_url(self, state: str, redirect_uri: str) -> str:
        qs = urlencode(
            query={
                'client_id': self._client_id,
                'redirect_uri': redirect_uri,
                'state': state,
                # no scopes are needed
            },
            quote_via=quote,
        )
        return f'https://github.com/login/oauth/authorize?{qs}'

    async def get_token(self, code: str) -> Token | None:
        async with AsyncClient() as client:
            r = get_json(
                await client.post(
                    'https://github.com/login/oauth/access_token',
                    headers={
                        'Accept': 'application/json',
                    },
                    json={
                        'client_id': self._client_id,
                        'client_secret': self._client_secret,
                        'code': code,
                    },
                )
            )
            if not r:
                return None

            r = get_json(
                await client.get(
                    'https://api.github.com/user',
                    headers={
                        'Accept': 'application/json',
                        'Authorization': f'Bearer {r.get("access_token")}',
                    },
                )
            )
            if not r:
                return None

            return Token(
                user_id=str(r['id']),
                login=r['login'],
                avatar_url=r.get('avatar_url'),
            )
