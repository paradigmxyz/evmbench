import uvicorn

from api.core.config import settings
from api.util.logger import logger


def main() -> None:
    logger.info(f'Starting at {settings.BACKEND_WEB_HOST}:{settings.BACKEND_WEB_PORT} {settings.BACKEND_DEV = }')

    if settings.BACKEND_DEV:
        # Single worker in dev env
        uvicorn.run(
            'api.app:app',
            host=settings.BACKEND_WEB_HOST,
            port=settings.BACKEND_WEB_PORT,
        )
        return

    uvicorn.run(
        'api.app:app',
        host=settings.BACKEND_WEB_HOST,
        port=settings.BACKEND_WEB_PORT,
        workers=settings.BACKEND_WEB_WORKERS,
        server_header=False,
    )


if __name__ == '__main__':
    main()
