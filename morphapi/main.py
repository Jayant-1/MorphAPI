"""
MorphAPI Gateway Entrypoint
Allows execution via `uvicorn morphapi.main:app --reload`
"""

from morphapi.app import app

__all__ = ["app"]

if __name__ == "__main__":
    import sys
    import uvicorn
    loop_param = "asyncio:ProactorEventLoop" if sys.platform == "win32" else "auto"
    uvicorn.run("morphapi.main:app", host="0.0.0.0", port=8000, reload=True, loop=loop_param)
