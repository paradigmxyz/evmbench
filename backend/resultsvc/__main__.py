import uvicorn

from api.util.logger import logger
from resultsvc.core.config import settings


def main() -> None:
    logger.info(
        'Starting results service at {}:{}',
        settings.RESULTSVC_HOST,
        settings.RESULTSVC_PORT,
    )
    uvicorn.run(
        'resultsvc:app',
        host=settings.RESULTSVC_HOST,
        port=settings.RESULTSVC_PORT,
        workers=settings.RESULTSVC_WORKERS,
        server_header=False,
    )


if __name__ == '__main__':
    main()
