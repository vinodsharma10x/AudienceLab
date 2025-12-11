# Shared authentication module for AudienceLab
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from jose import jwt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Initialize Supabase client with better error handling
supabase: Client = None

try:
    if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_JWT_SECRET]):
        print("⚠️  Warning: Supabase environment variables not found")
        print("   Please check your .env file and ensure all Supabase variables are set")
    else:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Supabase client: {e}")
    print("   Running in development mode without Supabase authentication")
    print("   Please check your Supabase credentials in the .env file")
    supabase = None

# Security
security = HTTPBearer()

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Supabase JWT token"""
    token = credentials.credentials
    
    # Check for development token first (before trying JWT decode)
    if token == "dev-token":
        return {
            "user_id": "caa5e7e0-5a1d-4c61-9cde-4bb66d664b64",  # Real user ID for dev mode
            "email": "dev@audiencelab.io",
            "created_at": "2024-01-01T00:00:00.000Z",
            "dev_mode": True  # Flag to indicate dev mode
        }
    
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not available. Use development mode or configure Supabase."
        )
    
    try:
        # Verify JWT token with Supabase secret
        payload = jwt.decode(
            token, 
            SUPABASE_JWT_SECRET, 
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user from Supabase
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Return user data in the format expected by all routes
        return {
            "id": response.user.id,  # Facebook routes expect 'id' field
            "user_id": response.user.id,  # Keep for backward compatibility
            "email": response.user.email,
            "created_at": str(response.user.created_at) if response.user.created_at else None
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        print(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

# Alias for compatibility with existing routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user - alias for verify_token for consistency"""
    return await verify_token(credentials)
