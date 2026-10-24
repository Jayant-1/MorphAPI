"""
MorphAPI Gateway Entrypoint
Allows execution via `uvicorn morphapi.main:app --reload`
"""

from morphapi.app import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("morphapi.main:app", host="0.0.0.0", port=8000, reload=True)
