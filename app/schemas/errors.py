from fastapi import Request
from fastapi.responses import JSONResponse

from app.clients.elexon_client import ElexonError


async def elexon_error_handler(_: Request, error: ElexonError) -> JSONResponse:
    status_code = 429 if error.status_code == 429 else 502
    if error.status_code == 504:
        status_code = 504
    return JSONResponse(
        status_code=status_code,
        content={
            "error": "upstream_elexon_error",
            "message": str(error),
            "upstream_status": error.status_code,
            "details": {"endpoint": error.endpoint},
        },
    )
