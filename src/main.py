"""
Application entrypoint for AI Farmer Assistant.

Can be run via:
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
or directly via:
    python -m src.main
"""

import uvicorn
from src.config import get_settings
from src.api import app

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False
    )
