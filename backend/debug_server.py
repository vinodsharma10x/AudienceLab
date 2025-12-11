#!/usr/bin/env python
"""
Debug wrapper for FastAPI server with proper virtual environment activation
"""
import sys
import os

# Add the virtual environment's site-packages to the path
venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'lib', 'python3.9', 'site-packages')
sys.path.insert(0, venv_path)

# Now import and run the main application
import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )