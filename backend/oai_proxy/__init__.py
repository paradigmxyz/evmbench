from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from oai_proxy.routers.catch_all import router as catch_all_router


app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    version='0.0.1',
    title='evmbench-oai-proxy',
    default_response_class=ORJSONResponse,
)
app.include_router(catch_all_router)
