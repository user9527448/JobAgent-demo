"""Same-origin serving for the built JAI-050 frontend."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def install_frontend(app: FastAPI, dist_path: Path) -> None:
    """Register the SPA shell after API routes without masking their prefixes."""
    resolved_dist = dist_path.resolve()
    assets_path = resolved_dist / "assets"
    if assets_path.is_dir():
        app.mount("/app/assets", StaticFiles(directory=assets_path), name="frontend-assets")

    async def frontend_index() -> FileResponse:
        index_path = resolved_dist / "index.html"
        if not index_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "frontend.build_unavailable",
                    "message": "The frontend build is unavailable for this application instance.",
                },
            )
        return FileResponse(index_path)

    app.add_api_route("/app", frontend_index, methods=["GET"], include_in_schema=False)
    app.add_api_route("/app/", frontend_index, methods=["GET"], include_in_schema=False)
    app.add_api_route(
        "/app/{client_path:path}",
        frontend_index,
        methods=["GET"],
        include_in_schema=False,
    )
