import logging
logger = logging.getLogger(__name__)

def hook_websocket(app):
    @app.middleware("http")
    async def log_requests(request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        return await call_next(request)
