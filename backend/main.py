from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import time
from dotenv import load_dotenv

# Import shared authentication
from auth import verify_token, supabase

# Import logging service
from logging_service import logger

# Load environment variables
load_dotenv()

# Scheduler removed (was for Facebook sync)

# Initialize FastAPI app
app = FastAPI(
    title="AudienceLab API",
    description="Marketing Research & Content Generation API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001", 
        "http://localhost:3002",
        "https://app.sucana.io",        # Production frontend
        "http://app.sucana.io",          # Production frontend (HTTP)
        "https://app2.sucana.io:3000",  # Added for local HTTPS development
        "http://app2.sucana.io:3000",   # Added for local HTTP development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add OPTIONS handler middleware to bypass auth for preflight requests
@app.middleware("http")
async def handle_options_requests(request, call_next):
    """Handle OPTIONS requests for CORS preflight without authentication"""
    if request.method == "OPTIONS":
        # Return 200 OK for all OPTIONS requests (CORS preflight)
        from fastapi import Response
        return Response(status_code=200, headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true"
        })
    return await call_next(request)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all incoming requests and their processing time"""
    start_time = time.time()
    
    # Log request
    logger.info(
        "request.received",
        f"{request.method} {request.url.path}",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        processing_time = time.time() - start_time
        logger.info(
            "request.completed",
            f"{request.method} {request.url.path} - {response.status_code}",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            processing_time=processing_time
        )
        
        return response
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            "request.failed",
            f"{request.method} {request.url.path} - Error: {str(e)}",
            method=request.method,
            path=request.url.path,
            error=str(e),
            processing_time=processing_time
        )
        raise

# Startup event
@app.on_event("startup")
async def startup_event():
    """Log server startup"""
    logger.info(
        "server.startup",
        "FastAPI server started",
        environment=os.getenv("ENVIRONMENT", "development"),
        supabase_connected=supabase is not None
    )

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Log server shutdown"""
    logger.info("server.shutdown", "FastAPI server shutting down")

# Local storage directories - keeping for cache/temp files but not serving
os.makedirs("generated_audio", exist_ok=True)
os.makedirs("generated_videos", exist_ok=True)

# Static file mounts commented out - using S3 for file serving
# Uncomment these lines if you need to fall back to local file serving
# app.mount("/generated_audio", StaticFiles(directory="generated_audio"), name="generated_audio")
# app.mount("/generated_videos", StaticFiles(directory="generated_videos"), name="generated_videos")

# Mount actor images directory - these are already in backend/actor_images
actor_images_dir = os.path.join(os.path.dirname(__file__), "actor_images")
if os.path.exists(actor_images_dir):
    app.mount("/images/actors", StaticFiles(directory=actor_images_dir), name="actor_images")
    logger.info("actor_images.mounted", f"Actor images mounted from {actor_images_dir}")

# Pydantic models
class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str

class DashboardData(BaseModel):
    user: UserResponse
    stats: dict
    message: str

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service status"""
    return {
        "message": "AudienceLab API is running",
        "version": "1.0.0",
        "status": "healthy",
        "supabase_connected": supabase is not None,
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "supabase_connected": supabase is not None,
        "timestamp": "2025-07-06T12:00:00Z"
    }

# Development mode authentication (only when Supabase is not available)
@app.post("/auth/dev-login")
async def dev_login():
    """Development mode login - only works when Supabase is not configured"""
    if supabase is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development login not available when Supabase is configured"
        )
    
    # Return a mock user for development
    return {
        "user": {
            "id": "dev-user-id",
            "email": "dev@audiencelab.io",
            "name": "Development User"
        },
        "token": "dev-token",
        "message": "Development mode authentication successful"
    }

@app.get("/health")
def health_check():
    """Health check endpoint for frontend to verify backend availability"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "audiencelab-backend"
    }

@app.get("/auth/verify")
async def verify_auth(current_user = Depends(verify_token)):
    """Verify user authentication"""
    return {
        "authenticated": True,
        "user": {
            "id": current_user["user_id"],
            "email": current_user["email"],
            "created_at": current_user["created_at"]
        }
    }

@app.get("/dashboard", response_model=DashboardData)
async def get_dashboard(current_user = Depends(verify_token)):
    """Get dashboard data for authenticated user"""
    
    # Mock dashboard stats - replace with real data as needed
    stats = {
        "total_projects": 0,
        "active_sessions": 0,
        "last_login": current_user["created_at"],
        "account_status": "active"
    }
    
    return DashboardData(
        user=UserResponse(
            id=current_user["user_id"],
            email=current_user["email"],
            created_at=current_user["created_at"]
        ),
        stats=stats,
        message=f"Welcome back, {current_user['email']}!"
    )

# Video ads routes
from video_ads_routes import router as video_ads_router
app.include_router(video_ads_router)

# Video ads V2 routes (Claude-powered)
# Switching to V3 implementation (stateless with V3 database)
# from video_ads_v2_routes import router as video_ads_v2_router
from video_ads_v3_routes import router as video_ads_v3_router
app.include_router(video_ads_v3_router)

# V4 routes for new workflow experimentation
from video_ads_v4_routes import router as video_ads_v4_router
app.include_router(video_ads_v4_router)

# Run the server
if __name__ == "__main__":
    import uvicorn
    logger.info("server.starting", "Starting AudienceLab backend server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
