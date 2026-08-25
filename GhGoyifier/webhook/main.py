# CopyLeft 2026 github.com/sepiol026-wq | telegram:@samsepi0l_ovf. Licensed under AGPLv3.
# Portions derived from vsecoder/github-notifi-bot; original MIT license is retained in LICENSE.
import uvicorn
from fastapi import FastAPI

from GhGoyifier.webhook.api import router as pat_router
from GhGoyifier.webhook.github_app import router as github_app_router


def dispatcher():
    app = FastAPI()

    app.include_router(router=pat_router, prefix="/webhook")

    app.include_router(router=github_app_router)

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    uvicorn.run(app, host="0.0.0.0", port=4454)
