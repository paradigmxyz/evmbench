import httpx

from .abc import SecretStorageABC


class HttpSecretStorage(SecretStorageABC):
    def _get_base_url(self) -> str:
        base_url = (self._args.get('url') or '').rstrip('/')
        if not base_url:
            msg = 'missing secrets service url'
            raise ValueError(msg)
        return base_url

    def _get_headers(self) -> dict[str, str]:
        token = self._args.get('token', '')
        if not token:
            return {}
        return {'X-Secrets-Token': token}

    async def save_secret(self, secret_id: str, secret_data: bytes) -> None:
        url = f'{self._get_base_url()}/v1/bundles/{secret_id}'
        headers = self._get_headers()
        files = {'bundle': ('bundle.tar', secret_data, 'application/x-tar')}

        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, files=files)
            response.raise_for_status()

    async def get_and_delete_secret(self, secret_id: str) -> bytes:
        url = f'{self._get_base_url()}/v1/bundles/{secret_id}'
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.content

    async def delete_secret(self, secret_id: str) -> None:
        url = f'{self._get_base_url()}/v1/bundles/{secret_id}'
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
