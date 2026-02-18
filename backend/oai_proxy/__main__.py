import uvicorn

from api.util.logger import logger
from oai_proxy.core.config import settings


def main() -> None:
    logger.info(
        'Starting OpenAI proxy at {}:{}',
        settings.OAI_PROXY_HOST,
        settings.OAI_PROXY_PORT,
    )
    uvicorn.run(
        'oai_proxy:app',
        host=settings.OAI_PROXY_HOST,
        port=settings.OAI_PROXY_PORT,
        workers=settings.OAI_PROXY_WORKERS,
        server_header=False,
    )


if __name__ == '__main__':
    main()
