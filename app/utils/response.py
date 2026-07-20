from typing import Any

from fastapi.responses import JSONResponse


def success_response(data: Any, code: int = 200, message: str | None = None) -> JSONResponse:
    """Same envelope shape as the Laravel app's successResponse()."""
    return JSONResponse(
        status_code=code,
        content={"status": "success", "message": message, "data": data},
    )


def error_response(message: Any = None, code: int = 422) -> JSONResponse:
    """Same envelope shape as the Laravel app's errorResponse()."""
    return JSONResponse(
        status_code=code,
        content={"status": "error", "message": message, "data": None},
    )
