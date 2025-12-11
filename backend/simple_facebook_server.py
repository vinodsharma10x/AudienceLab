#!/usr/bin/env python3
"""
Super minimal FastAPI server just for Facebook OAuth
"""
import sys
sys.path.append('/Users/vinodsharma/code/sucana-v4/backend')

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Create app
app = FastAPI(title="Minimal Facebook OAuth Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Facebook OAuth Server Running"}

@app.get("/facebook/health")
async def facebook_health():
    return {
        "status": "healthy",
        "service": "Facebook OAuth",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/facebook/auth/url")
async def get_facebook_auth_url(state: str = Query(None)):
    """Get Facebook OAuth authorization URL"""
    try:
        from facebook_api_service import FacebookAPIService
        
        service = FacebookAPIService()
        
        # Generate state if not provided
        if not state:
            state = f"user_test_{datetime.utcnow().timestamp()}"
        
        auth_url = service.get_auth_url(state=state)
        
        return {
            "auth_url": auth_url,
            "state": state
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")

@app.post("/facebook/auth/callback")
async def facebook_callback(
    code: str = Query(...),
    state: str = Query(None)
):
    """Handle Facebook OAuth callback"""
    try:
        from facebook_api_service import FacebookAPIService
        
        service = FacebookAPIService()
        
        # Exchange code for token
        token_data = await service.exchange_code_for_token(code)
        short_token = token_data.get('access_token')
        
        if not short_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
            
        # Get long-lived token
        long_token_data = await service.get_long_lived_token(short_token)
        access_token = long_token_data.get('access_token')
        expires_in = long_token_data.get('expires_in', 5184000)
        
        # Get user info
        user_info = await service.get_user_info(access_token)
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            "success": True,
            "message": "Facebook account connected successfully",
            "facebook_account": {
                "facebook_user_id": user_info['id'],
                "facebook_user_name": user_info.get('name'),
                "facebook_user_email": user_info.get('email'),
                "connected_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "ad_accounts_count": 0  # Will be fetched later
            },
            "ad_accounts": [],
            "token_info": {
                "expires_at": expires_at.isoformat(),
                "expires_in_seconds": expires_in
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

@app.get("/facebook/accounts")
async def get_facebook_accounts():
    """Get Facebook accounts - placeholder for development"""
    return {
        "success": True,
        "message": "Facebook account connected successfully",
        "accounts": [
            {
                "id": "demo_account_1",
                "name": "Vinod Sharma (Connected)",
                "status": "connected",
                "account_type": "personal",
                "connected_at": "2025-08-01T19:00:00Z",
                "permissions": ["email", "public_profile"],
                "note": "OAuth successful - waiting for advanced permissions approval"
            }
        ],
        "total_accounts": 1
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
