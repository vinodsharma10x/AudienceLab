#!/usr/bin/env python3
"""
Minimal FastAPI server for testing Facebook OAuth callback
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.append('/Users/vinodsharma/code/sucana-v4/backend')

# Load environment variables
load_dotenv()

# Import Facebook components
from facebook_routes import router as facebook_router
from auth import get_current_user

# Initialize FastAPI app
app = FastAPI(title="Minimal Facebook OAuth Test Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Facebook routes
app.include_router(facebook_router)

@app.get("/")
async def root():
    return {"message": "Minimal Facebook OAuth Test Server"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
