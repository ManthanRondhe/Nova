"""
Vercel Python Serverless Function Entrypoint for AutoMech-AI (Nova AI).
Exposes the complete FastAPI application (`app`) from `backend/main.py`
so both the frontend static portals and `/api/*` backend routes run natively on Vercel.
"""
import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.main import app
