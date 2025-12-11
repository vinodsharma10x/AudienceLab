#!/usr/bin/env python3
"""
Start script for Sucana v4 backend server
"""
import uvicorn
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting Sucana v4 backend server...")
    
    # For development with reload, use single worker
    # For production, use multiple workers for concurrency
    import os
    
    workers = int(os.getenv("WORKERS", "1"))
    if workers > 1:
        print(f"🔄 Starting with {workers} worker processes for better concurrency")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            workers=workers,
            log_level="info",
            timeout_keep_alive=600,  # 10 minutes for long Claude API calls
            timeout_graceful_shutdown=600
        )
    else:
        print("🔄 Starting in development mode with reload enabled")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            timeout_keep_alive=600,  # 10 minutes for long Claude API calls
            timeout_graceful_shutdown=600
        )
