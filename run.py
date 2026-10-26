"""Arranque local:  python run.py   →  http://127.0.0.1:8000"""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=os.getenv("SIGT_HOST", "127.0.0.1"), proxy_headers=True,
                port=int(os.getenv("SIGT_PORT", "8000")))
