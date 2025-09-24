from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse


class VerifyTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        token_header = request.headers.get('Auth-token')
        # TODO: improve token validation
        expected_token = 'igxApoxPwT66sYBzenkEUf6YMtzk8Zh7'
        if token_header != expected_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid token"}
            )
        response = await call_next(request)
        return response
