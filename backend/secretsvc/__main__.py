import uvicorn

from api.util.logger import logger
from secretsvc.core.config import settings


def main() -> None:
    logger.info(
        'Starting secrets service at {}:{}',
        settings.SECRETSVC_HOST,
        settings.SECRETSVC_PORT,
    )
    uvicorn.run(
        'secretsvc:app',
        host=settings.SECRETSVC_HOST,
        port=settings.SECRETSVC_PORT,
        workers=settings.SECRETSVC_WORKERS,
        server_header=False,
    )


if __name__ == '__main__':
    main()
