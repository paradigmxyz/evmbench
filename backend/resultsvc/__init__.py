from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from resultsvc.routers.v1 import router as v1_router


app = FastAPI(
    docs_url='/',
    redoc_url=None,
    version='0.0.1',
    title='svmbench-results',
    default_response_class=ORJSONResponse,
)
app.include_router(v1_router)
