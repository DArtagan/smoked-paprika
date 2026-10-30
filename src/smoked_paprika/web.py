from importlib.metadata import version

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "version": version("smoked-paprika")})


def create_app() -> Starlette:
    # No MCP endpoint: over HTTP it is served only behind OAuth and the email
    # allowlist (the design's Authentication section), never on its own.
    return Starlette(routes=[Route("/healthz", healthz, methods=["GET"])])
