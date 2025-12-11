# Facebook Authentication Routes for Sucana v4
from fastapi import APIRouter, HTTPException, Query, Depends, Request, BackgroundTasks
from typing import Optional, Dict, Any, List
import logging
import json
from datetime import datetime, timedelta
import asyncio
import os

from facebook_api_service import FacebookAPIService
from facebook_database_service import FacebookDatabaseService
from facebook_ads_creation_service import FacebookAdsCreationService
from facebook_models import (
    FacebookAccount, 
    FacebookAdAccount, 
    FacebookAuthResponse,
    FacebookAccountsListResponse,
    SyncConfigRequest,
    SyncJobStatus
)
from facebook_ad_creation_models import (
    VideoAdCreateRequest,
    VideoAdCreationResponse,
    CampaignCreateRequest,
    TargetingSpec,
    CampaignTemplate,
    AudiencePreset
)
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/facebook", tags=["Facebook Marketing API"])

# Initialize services lazily
facebook_service = None
facebook_db_service = None
facebook_ads_service = None

def get_facebook_service():
    """Get or create Facebook API service instance"""
    global facebook_service
    if facebook_service is None:
        facebook_service = FacebookAPIService()
    return facebook_service

def get_facebook_db_service():
    """Get or create Facebook Database service instance"""
    global facebook_db_service
    if facebook_db_service is None:
        facebook_db_service = FacebookDatabaseService()
    return facebook_db_service

def get_facebook_ads_service():
    """Get or create Facebook Ads Creation service instance"""
    global facebook_ads_service
    if facebook_ads_service is None:
        app_id = os.getenv("FACEBOOK_APP_ID")
        app_secret = os.getenv("FACEBOOK_APP_SECRET")
        facebook_ads_service = FacebookAdsCreationService(app_id, app_secret)
    return facebook_ads_service

@router.get("/auth/url")
async def get_facebook_auth_url(
    current_user: dict = Depends(get_current_user),
    state: Optional[str] = Query(None, description="Optional state parameter for OAuth")
):
    """
    Get Facebook OAuth authorization URL
    
    This endpoint generates the Facebook OAuth URL that users need to visit
    to authorize access to their Facebook Business Manager accounts.
    """
    try:
        # Generate state parameter if not provided (for security)
        if not state:
            state = f"user_{current_user['user_id']}_{datetime.utcnow().timestamp()}"
        
        auth_url = get_facebook_service().get_auth_url(state=state)
        
        logger.info(f"✅ Generated Facebook auth URL for user {current_user['user_id']}")
        
        return {
            "auth_url": auth_url,
            "state": state,
            "expires_in": 3600,  # URL valid for 1 hour
            "instructions": {
                "step_1": "Visit the auth_url in your browser",
                "step_2": "Login to Facebook and authorize the app",
                "step_3": "You'll be redirected back with an authorization code",
                "step_4": "Use the /facebook/auth/callback endpoint with the code"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error generating Facebook auth URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")

@router.post("/auth/callback", response_model=FacebookAuthResponse)
async def facebook_auth_callback(
    code: str = Query(..., description="Authorization code from Facebook"),
    state: Optional[str] = Query(None, description="State parameter from OAuth flow"),
    current_user: dict = Depends(get_current_user)
):
    """
    Handle Facebook OAuth callback
    
    This endpoint processes the authorization code received from Facebook
    and exchanges it for access tokens, then stores the account information.
    """
    try:
        # Step 1: Exchange authorization code for short-lived token
        logger.info(f"🔄 Exchanging code for token for user {current_user['user_id']}")
        token_data = await get_facebook_service().exchange_code_for_token(code)
        short_token = token_data.get('access_token')
        
        if not short_token:
            raise HTTPException(status_code=400, detail="Failed to get access token from Facebook")
        
        # Step 2: Exchange short-lived token for long-lived token
        logger.info("🔄 Getting long-lived token")
        long_token_data = await get_facebook_service().get_long_lived_token(short_token)
        access_token = long_token_data.get('access_token')
        expires_in = long_token_data.get('expires_in', 5184000)  # Default 60 days
        
        # Step 3: Get user information from Facebook
        logger.info("🔄 Fetching user info from Facebook")
        user_info = await get_facebook_service().get_user_info(access_token)
        
        # Step 4: Get ad accounts accessible to this user (now that app is published)
        logger.info("🔄 Fetching ad accounts")
        ad_accounts = []
        try:
            ad_accounts = await get_facebook_service().get_ad_accounts(access_token)
            logger.info(f"✅ Successfully fetched {len(ad_accounts)} ad accounts")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch ad accounts: {str(e)}")
            # Continue without ad accounts - user may not have business manager access
        
        # Step 5: Encrypt and store the access token
        encrypted_token = get_facebook_service().encrypt_token(access_token)
        
        # Calculate token expiry
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Step 6: Store in Supabase database
        facebook_account_data = {
            "user_id": current_user['user_id'],
            "facebook_user_id": user_info['id'],
            "facebook_user_name": user_info.get('name'),
            "access_token": encrypted_token,  # Using access_token column as per schema
            "token_expires_at": expires_at.isoformat(),
            "account_name": user_info.get('name'),
            "status": "active",
            "sync_enabled": True
        }
        
        # Save or update the Facebook account in database
        db_service = get_facebook_db_service()
        saved_account = await db_service.create_or_update_facebook_account(facebook_account_data)
        is_reconnect = saved_account.get('updated_at') != saved_account.get('created_at')
        
        if is_reconnect:
            logger.info(f"✅ Successfully reconnected Facebook account: {saved_account['id']}")
            message = "Facebook account reconnected successfully"
        else:
            logger.info(f"✅ Successfully connected new Facebook account: {saved_account['id']}")
            message = "Facebook account connected successfully"
        
        # Step 7: Persist ad accounts to database
        if ad_accounts and saved_account:
            try:
                # Format ad accounts for database
                ad_accounts_data = []
                for ad_account in ad_accounts:
                    ad_accounts_data.append({
                        "facebook_account_id": saved_account['id'],
                        "ad_account_id": ad_account.get('id', '').replace('act_', ''),  # Remove act_ prefix
                        "account_name": ad_account.get('name', 'Unnamed Account'),
                        "currency": ad_account.get('currency', 'USD'),
                        "timezone_name": ad_account.get('timezone_name', 'UTC'),
                        "account_status": ad_account.get('account_status', 1),
                        "is_selected": True  # Default to selected
                    })
                
                # Upsert ad accounts
                if ad_accounts_data:
                    await db_service.upsert_ad_accounts(ad_accounts_data)
                    logger.info(f"✅ Successfully stored {len(ad_accounts_data)} ad accounts")
            except Exception as e:
                logger.error(f"⚠️ Failed to store ad accounts: {e}")
                # Non-critical error - continue
        
        return FacebookAuthResponse(
            success=True,
            message=message,
            facebook_account=facebook_account_data,
            ad_accounts=ad_accounts,
            token_info={
                "expires_at": expires_at.isoformat(),
                "expires_in_seconds": expires_in,
                "scope": ["ads_read", "business_management", "pages_read_engagement", "read_insights"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Facebook OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

@router.get("/accounts", response_model=FacebookAccountsListResponse)
async def get_facebook_accounts(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all Facebook accounts connected by the current user
    
    Returns a list of Facebook Business Manager accounts that the user
    has previously connected through the OAuth flow.
    """
    try:
        logger.info(f"🔄 Fetching Facebook accounts for user {current_user.get('user_id', 'unknown')}")
        
        # Query Supabase database for user's Facebook accounts
        db_service = get_facebook_db_service()
        facebook_accounts_data = await db_service.get_facebook_accounts_by_user(current_user['user_id'])
        
        # Convert database records to response format
        facebook_accounts = []
        for account_data in facebook_accounts_data:
            facebook_accounts.append({
                "id": account_data['id'],
                "user_id": account_data['user_id'],  # Required by model
                "facebook_user_id": account_data['facebook_user_id'],
                "facebook_user_name": account_data['facebook_user_name'],
                "account_name": account_data.get('account_name') or account_data['facebook_user_name'],
                "status": account_data['status'],
                "created_at": account_data['created_at'],  # Required by model
                "last_sync": account_data.get('last_sync')
            })
        
        logger.info(f"✅ Found {len(facebook_accounts)} Facebook accounts for user")
        
        return FacebookAccountsListResponse(
            success=True,
            accounts=facebook_accounts,
            total=len(facebook_accounts)
        )
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Error fetching Facebook accounts: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch accounts: {str(e)}")

@router.get("/ad-accounts")
async def get_all_ad_accounts(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all ad accounts across all connected Facebook accounts for the current user
    
    Returns a consolidated list of all ad accounts accessible through all
    connected Facebook Business Manager accounts.
    """
    try:
        db_service = get_facebook_db_service()
        
        # Get all Facebook accounts for the user
        facebook_accounts = await db_service.get_facebook_accounts_by_user(current_user['user_id'])
        
        if not facebook_accounts:
            return {
                "ad_accounts": [],
                "total_count": 0,
                "message": "No Facebook accounts connected"
            }
        
        # Collect all ad accounts across all Facebook accounts
        all_ad_accounts = []
        for fb_account in facebook_accounts:
            try:
                ad_accounts = await db_service.get_ad_accounts_by_facebook_account(
                    fb_account['id'], 
                    include_inactive=True
                )
                
                # Add Facebook account info to each ad account for context
                for ad_account in ad_accounts:
                    formatted_account = {
                        "id": ad_account['id'],
                        "ad_account_id": ad_account['ad_account_id'],
                        "account_name": ad_account['account_name'],
                        "currency": ad_account['currency'],
                        "timezone_name": ad_account['timezone_name'],
                        "account_status": ad_account['account_status'],
                        "is_selected": ad_account.get('is_selected', True),
                        "facebook_account_id": fb_account['id'],
                        "facebook_account_name": fb_account.get('account_name') or fb_account.get('facebook_user_name'),
                        "created_at": ad_account['created_at']
                    }
                    all_ad_accounts.append(formatted_account)
                    
            except Exception as e:
                logger.warning(f"⚠️ Error fetching ad accounts for Facebook account {fb_account['id']}: {e}")
                continue
        
        logger.info(f"✅ Found {len(all_ad_accounts)} ad accounts across {len(facebook_accounts)} Facebook accounts")
        
        return {
            "ad_accounts": all_ad_accounts,
            "total_count": len(all_ad_accounts),
            "facebook_accounts_count": len(facebook_accounts),
            "message": "Success"
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching all ad accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch ad accounts: {str(e)}")

@router.get("/accounts/{facebook_account_id}/ad-accounts")
async def get_ad_accounts(
    facebook_account_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get ad accounts for a specific Facebook Business Manager account
    
    Fetches all ad accounts accessible through the specified
    Facebook Business Manager account.
    """
    try:
        db_service = get_facebook_db_service()
        
        # 1. Verify the facebook_account_id belongs to current_user
        fb_account = await db_service.get_facebook_account_by_id(facebook_account_id, current_user['user_id'])
        
        if not fb_account:
            raise HTTPException(status_code=404, detail="Facebook account not found")
        
        # 2. Get ad accounts from database (include all, even inactive ones for display)
        logger.info(f"🔄 Fetching ad accounts for Facebook account {facebook_account_id}")
        ad_accounts = await db_service.get_ad_accounts_by_facebook_account(facebook_account_id, include_inactive=True)
        
        # Format response
        formatted_ad_accounts = []
        for ad_account in ad_accounts:
            formatted_ad_accounts.append({
                "id": ad_account['id'],
                "ad_account_id": ad_account['ad_account_id'],
                "account_name": ad_account['account_name'],
                "currency": ad_account['currency'],
                "timezone_name": ad_account['timezone_name'],
                "account_status": ad_account['account_status'],
                "is_selected": ad_account.get('is_selected', True),
                "created_at": ad_account['created_at']
            })
        
        return {
            "facebook_account_id": facebook_account_id,
            "ad_accounts": formatted_ad_accounts,
            "total_count": len(formatted_ad_accounts),
            "last_synced": fb_account.get('last_sync'),
            "message": "Success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching ad accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch ad accounts: {str(e)}")

@router.post("/sync/start")
async def start_performance_sync(
    sync_request: SyncConfigRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a background sync job to fetch Facebook ad performance data
    
    This endpoint initiates a background task that will fetch performance
    data for the specified ad accounts and date range.
    """
    try:
        logger.info(f"🔄 Starting sync job for user {current_user['user_id']} with request: {sync_request}")
        
        # Validate user has connected Facebook accounts
        db_service = get_facebook_db_service()
        facebook_accounts = await db_service.get_facebook_accounts_by_user(current_user['user_id'])
        
        if not facebook_accounts:
            logger.warning(f"⚠️ User {current_user['user_id']} has no connected Facebook accounts")
            raise HTTPException(status_code=400, detail="No Facebook accounts connected. Please connect a Facebook account first.")
        
        # Generate sync job ID
        sync_job_id = f"sync_{current_user['user_id']}_{int(datetime.utcnow().timestamp())}"
        
        logger.info(f"🚀 Generated sync job ID: {sync_job_id} for {len(facebook_accounts)} Facebook accounts")
        
        # Add background task
        background_tasks.add_task(
            process_sync_job,
            sync_job_id=sync_job_id,
            user_id=current_user['user_id'],
            sync_request=sync_request
        )
        
        return {
            "sync_job_id": sync_job_id,
            "status": "started",
            "message": f"Sync job started successfully for {len(facebook_accounts)} Facebook account(s)",
            "facebook_accounts_count": len(facebook_accounts),
            "estimated_completion": "2-5 minutes",
            "instructions": "Use GET /facebook/sync/status/{sync_job_id} to check progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting sync job: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")

@router.post("/accounts/{facebook_account_id}/refresh-token")
async def refresh_facebook_token(
    facebook_account_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Refresh the access token for a Facebook account
    
    Exchanges the current token for a new long-lived token
    """
    try:
        db_service = get_facebook_db_service()
        facebook_service = get_facebook_service()
        
        # Get the Facebook account
        fb_account = await db_service.get_facebook_account_by_id(facebook_account_id, current_user['user_id'])
        
        if not fb_account:
            raise HTTPException(status_code=404, detail="Facebook account not found")
        
        # Decrypt current token
        encrypted_token = fb_account.get('access_token')
        if not encrypted_token:
            raise HTTPException(status_code=400, detail="No token found for this account")
        
        current_token = facebook_service.decrypt_token(encrypted_token)
        
        # Check if token needs refresh (less than 7 days remaining)
        token_expires_at = fb_account.get('token_expires_at')
        if token_expires_at:
            expires_dt = datetime.fromisoformat(token_expires_at.replace('Z', '+00:00'))
            days_remaining = (expires_dt - datetime.utcnow()).days
            
            if days_remaining > 7:
                logger.info(f"ℹ️ Token for account {facebook_account_id} still has {days_remaining} days remaining")
                return {
                    "success": True,
                    "message": f"Token is still valid for {days_remaining} days",
                    "expires_at": expires_dt.isoformat(),
                    "needs_refresh": False
                }
        
        # Exchange for new long-lived token
        logger.info(f"🔄 Refreshing token for Facebook account {facebook_account_id}")
        
        new_token_data = await facebook_service.get_long_lived_token(current_token)
        new_token = new_token_data.get('access_token')
        expires_in = new_token_data.get('expires_in', 5184000)  # Default 60 days
        
        # Encrypt and update token
        encrypted_new_token = facebook_service.encrypt_token(new_token)
        new_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Update in database
        success = await db_service.update_facebook_account_token(
            facebook_account_id,
            encrypted_new_token,
            new_expires_at
        )
        
        if success:
            logger.info(f"✅ Successfully refreshed token for account {facebook_account_id}")
            return {
                "success": True,
                "message": "Token refreshed successfully",
                "expires_at": new_expires_at.isoformat(),
                "expires_in_days": expires_in // 86400
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update token in database")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error refreshing token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")

@router.get("/sync/status/{sync_job_id}")
async def get_sync_status(
    sync_job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the status of a running sync job
    
    Check the progress and status of a previously started
    Facebook ad performance data sync job.
    """
    try:
        logger.info(f"🔄 Checking sync status for job {sync_job_id}")
        
        db_service = get_facebook_db_service()
        sync_job = await db_service.get_sync_job_status(sync_job_id, current_user['user_id'])
        
        if not sync_job:
            raise HTTPException(status_code=404, detail="Sync job not found")
        
        # Calculate time elapsed and estimated completion
        started_at = sync_job.get('started_at')
        completed_at = sync_job.get('completed_at')
        status = sync_job.get('status', 'unknown')
        
        response_data = {
            "sync_job_id": sync_job_id,
            "status": status,
            "progress_percentage": sync_job.get('progress_percentage', 0),
            "records_processed": sync_job.get('records_processed', 0),
            "started_at": started_at,
            "completed_at": completed_at,
            "error_message": sync_job.get('error_message'),
            "created_at": sync_job.get('created_at'),
            "updated_at": sync_job.get('updated_at')
        }
        
        # Add time calculations
        if started_at and status == 'running':
            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
            response_data['elapsed_seconds'] = int(elapsed_seconds)
            response_data['elapsed_time'] = f"{int(elapsed_seconds // 60)}:{int(elapsed_seconds % 60):02d}"
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error checking sync status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")

@router.get("/sync/history")
async def get_sync_history(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=50, description="Number of sync jobs to return")
):
    """
    Get sync job history for the current user
    
    Returns a list of recent sync jobs with their status and results.
    """
    try:
        logger.info(f"🔄 Fetching sync history for user {current_user['user_id']} (limit: {limit})")
        
        db_service = get_facebook_db_service()
        sync_jobs = await db_service.get_recent_sync_jobs(current_user['user_id'], limit)
        
        # Enhance each sync job with calculated fields
        enhanced_jobs = []
        for job in sync_jobs:
            enhanced_job = dict(job)
            
            # Calculate duration if completed
            started_at = job.get('started_at')
            completed_at = job.get('completed_at')
            
            if started_at and completed_at:
                start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                duration_seconds = (end_time - start_time).total_seconds()
                enhanced_job['duration_seconds'] = int(duration_seconds)
                enhanced_job['duration_formatted'] = f"{int(duration_seconds // 60)}:{int(duration_seconds % 60):02d}"
            
            # Add human-readable timestamps
            if started_at:
                enhanced_job['started_ago'] = format_time_ago(started_at)
            if completed_at:
                enhanced_job['completed_ago'] = format_time_ago(completed_at)
                
            enhanced_jobs.append(enhanced_job)
        
        return {
            "sync_jobs": enhanced_jobs,
            "total_count": len(enhanced_jobs),
            "user_id": current_user['user_id']
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching sync history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sync history: {str(e)}")

def format_time_ago(timestamp_str: str) -> str:
    """Format timestamp as 'X minutes ago', 'X hours ago', etc."""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.utcnow()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    except:
        return "Unknown"

@router.get("/performance")
async def get_performance_data(
    ad_account_id: Optional[str] = Query(None, description="Filter by specific ad account"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    campaign_name: Optional[str] = Query(None, description="Filter by campaign name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Facebook ad performance data with filtering and pagination
    
    Retrieve stored Facebook ad performance data with various filtering
    options and pagination support.
    """
    try:
        logger.info(f"🔄 Fetching performance data for user {current_user['user_id']} with filters: ad_account={ad_account_id}, date_from={date_from}, date_to={date_to}")
        
        db_service = get_facebook_db_service()
        
        # Get performance data with pagination and filtering
        performance_result = await db_service.get_performance_data(
            user_id=current_user['user_id'],
            ad_account_id=ad_account_id,
            date_from=date_from,
            date_to=date_to,
            campaign_name=campaign_name,
            limit=limit,
            offset=offset
        )
        
        return {
            "data": performance_result["data"],
            "total_count": performance_result["total_count"],
            "page_info": performance_result["page_info"],
            "filters": {
                "ad_account_id": ad_account_id,
                "date_from": date_from,
                "date_to": date_to,
                "campaign_name": campaign_name
            },
            "message": f"Retrieved {len(performance_result['data'])} performance records" if performance_result["data"] else "No performance data found. Run a sync job first."
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching performance data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")

@router.put("/ad-accounts/{ad_account_id}/update-selection")
async def update_ad_account_selection(
    ad_account_id: str,
    selection_update: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the selection status of an ad account
    """
    try:
        db_service = get_facebook_db_service()
        is_selected = selection_update.get('is_selected', True)
        
        # Update the ad account selection status
        result = db_service.supabase.table("facebook_ad_accounts").update({
            "is_selected": is_selected,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", ad_account_id).execute()
        
        if result.data:
            logger.info(f"✅ Updated ad account {ad_account_id} selection to {is_selected}")
            return {"success": True, "message": "Selection updated"}
        else:
            raise HTTPException(status_code=404, detail="Ad account not found")
            
    except Exception as e:
        logger.error(f"❌ Error updating ad account selection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update selection: {str(e)}")

@router.put("/accounts/{facebook_account_id}/update-ad-accounts")
async def update_facebook_account_ad_accounts(
    facebook_account_id: str,
    update_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the selected ad accounts list for a Facebook account
    """
    try:
        db_service = get_facebook_db_service()
        
        # Verify ownership
        fb_account = await db_service.get_facebook_account_by_id(facebook_account_id, current_user['user_id'])
        if not fb_account:
            raise HTTPException(status_code=404, detail="Facebook account not found")
        
        selected_ad_accounts = update_data.get('selected_ad_accounts', [])
        
        # Update the Facebook account
        result = db_service.supabase.table("facebook_accounts").update({
            "selected_ad_accounts": selected_ad_accounts,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", facebook_account_id).execute()
        
        if result.data:
            logger.info(f"✅ Updated Facebook account {facebook_account_id} with {len(selected_ad_accounts)} selected ad accounts")
            return {"success": True, "message": "Ad accounts selection updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to update Facebook account")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating Facebook account ad accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update: {str(e)}")

@router.delete("/accounts/{facebook_account_id}")
async def disconnect_facebook_account(
    facebook_account_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Disconnect a Facebook Business Manager account
    
    Remove the connection to a Facebook account and delete
    associated access tokens and data.
    """
    try:
        db_service = get_facebook_db_service()
        
        # 1. Verify account belongs to user
        fb_account = await db_service.get_facebook_account_by_id(facebook_account_id, current_user['user_id'])
        
        if not fb_account:
            raise HTTPException(status_code=404, detail="Facebook account not found")
        
        # 2. Pause any scheduled sync jobs
        try:
            from scheduler_service import get_scheduler
            scheduler = get_scheduler()
            # Remove sync job for this specific account
            job_id = f"sync_user_{current_user['user_id']}"
            if job_id in scheduler.active_jobs.values():
                scheduler.scheduler.remove_job(job_id)
                logger.info(f"⏸️ Removed scheduled sync job for user {current_user['user_id']}")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove scheduled job: {e}")
        
        # 3. Soft delete - mark as inactive (keep data for audit/recovery)
        success = await db_service.deactivate_facebook_account(facebook_account_id, current_user['user_id'])
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to disconnect account")
        
        logger.info(f"✅ Disconnected Facebook account {facebook_account_id} for user {current_user['user_id']}")
        
        return {
            "success": True,
            "message": "Facebook account disconnected successfully",
            "facebook_account_id": facebook_account_id,
            "disconnected_at": datetime.utcnow().isoformat(),
            "note": "Your data has been preserved and can be recovered by reconnecting"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error disconnecting Facebook account: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")

# Background task functions
async def process_sync_job(sync_job_id: str, user_id: str, sync_request: SyncConfigRequest):
    """
    Background task to process Facebook ad performance data sync
    
    This function runs in the background to fetch data from Facebook API
    and store it in the database.
    """
    db_service = get_facebook_db_service()
    facebook_service = get_facebook_service()
    
    try:
        logger.info(f"🚀 Starting background sync job {sync_job_id} for user {user_id}")
        logger.info(f"📋 Sync request details: ad_accounts={sync_request.ad_account_ids}, date_from={sync_request.date_from}, date_to={sync_request.date_to}")
        
        # Create sync job record
        try:
            await db_service.create_sync_job({
                "sync_job_id": sync_job_id,
                "user_id": user_id,
                "status": "running",
                "started_at": datetime.utcnow().isoformat()
            })
            logger.info(f"✅ Created sync job record for {sync_job_id}")
        except Exception as e:
            logger.error(f"⚠️ Failed to create sync job record (continuing anyway): {e}")
        
        # 1. Get user's Facebook accounts
        facebook_accounts = await db_service.get_facebook_accounts_by_user(user_id)
        logger.info(f"📊 Found {len(facebook_accounts)} Facebook accounts for user {user_id}")
        
        if not facebook_accounts:
            error_msg = "No Facebook accounts connected"
            logger.warning(f"⚠️ {error_msg} for user {user_id}")
            try:
                await db_service.update_sync_job_status(sync_job_id, "failed", error_message=error_msg)
            except:
                pass  # Don't fail if sync job table doesn't exist
            return
        
        total_records = 0
        processed_accounts = 0
        
        for fb_account in facebook_accounts:
            try:
                account_name = fb_account.get('account_name') or fb_account.get('facebook_user_name', 'Unknown')
                logger.info(f"🔍 Processing Facebook account: {account_name} (ID: {fb_account['id']})")
                
                # 2. Decrypt and validate token
                encrypted_token = fb_account.get('access_token')
                if not encrypted_token:
                    logger.warning(f"⚠️ No access token for account {fb_account['id']} ({account_name})")
                    continue
                
                # Decrypt the token
                access_token = facebook_service.decrypt_token(encrypted_token)
                
                # Check if token is expired
                token_expires_at = fb_account.get('token_expires_at')
                if token_expires_at:
                    # Parse timestamp, handle both naive and aware datetimes
                    if isinstance(token_expires_at, str):
                        expires_dt = datetime.fromisoformat(token_expires_at.replace('Z', '+00:00').replace('+00:00', ''))
                    else:
                        expires_dt = token_expires_at
                    
                    # Compare using naive datetimes (remove timezone info)
                    if hasattr(expires_dt, 'tzinfo') and expires_dt.tzinfo:
                        expires_dt = expires_dt.replace(tzinfo=None)
                    
                    if expires_dt < datetime.utcnow():
                        logger.warning(f"⚠️ Token expired for account {fb_account['id']}")
                        await db_service.update_facebook_account_status(fb_account['id'], 'token_expired')
                        continue
                
                # 3. Get ad accounts for this Facebook account
                ad_accounts = await db_service.get_ad_accounts_by_facebook_account(fb_account['id'])
                logger.info(f"📊 Found {len(ad_accounts)} ad accounts for Facebook account {fb_account['id']} ({account_name})")
                
                # Filter by requested ad accounts if specified
                if sync_request.ad_account_ids:
                    original_count = len(ad_accounts)
                    ad_accounts = [acc for acc in ad_accounts if acc['ad_account_id'] in sync_request.ad_account_ids]
                    logger.info(f"🔍 Filtered to {len(ad_accounts)} ad accounts (from {original_count}) based on request filter")
                
                # Only sync selected ad accounts
                selected_before = len(ad_accounts)
                ad_accounts = [acc for acc in ad_accounts if acc.get('is_selected', True)]
                logger.info(f"✅ Selected {len(ad_accounts)} ad accounts for sync (from {selected_before} total)")
                
                if not ad_accounts:
                    logger.info(f"ℹ️ No ad accounts to sync for Facebook account {fb_account['id']} ({account_name})")
                    continue
                
                # 4. Fetch performance data for each ad account
                for ad_account in ad_accounts:
                    try:
                        logger.info(f"📊 Fetching data for ad account {ad_account['ad_account_id']}")
                        
                        # Prepare date range - try last 7 days for more recent data
                        date_from = sync_request.date_from or (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')
                        date_to = sync_request.date_to or datetime.utcnow().strftime('%Y-%m-%d')
                        
                        logger.info(f"📅 Fetching data for date range: {date_from} to {date_to}")
                        
                        # Fetch performance data from Facebook
                        performance_data = await facebook_service.get_ad_performance_data(
                            access_token=access_token,
                            ad_account_id=ad_account['ad_account_id'],
                            date_from=date_from,
                            date_to=date_to,
                            facebook_account_id=fb_account['id']
                        )
                        
                        # facebook_account_id is already added in the API service
                        
                        # Store in database
                        if performance_data:
                            await db_service.insert_performance_data(performance_data)
                            total_records += len(performance_data)
                            logger.info(f"✅ Stored {len(performance_data)} records for ad account {ad_account['ad_account_id']}")
                        
                        # Update progress
                        processed_accounts += 1
                        progress = int((processed_accounts / len(ad_accounts)) * 100)
                        await db_service.update_sync_job_status(
                            sync_job_id, 
                            "running", 
                            progress_percentage=progress,
                            records_processed=total_records
                        )
                        
                    except Exception as e:
                        logger.error(f"❌ Error syncing ad account {ad_account['ad_account_id']}: {e}")
                        # Continue with other accounts
                
                # Update last sync time for Facebook account
                await db_service.update_facebook_account_last_sync(fb_account['id'])
                
            except Exception as e:
                logger.error(f"❌ Error processing Facebook account {fb_account['id']}: {e}")
                # Continue with other accounts
        
        # 5. Mark sync job as completed
        await db_service.update_sync_job_status(
            sync_job_id, 
            "completed",
            progress_percentage=100,
            records_processed=total_records
        )
        
        logger.info(f"✅ Completed sync job {sync_job_id}. Processed {total_records} records")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in sync job {sync_job_id}: {e}")
        await db_service.update_sync_job_status(
            sync_job_id, 
            "failed", 
            error_message=str(e)
        )

# Scheduler management endpoints
@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: dict = Depends(get_current_user)
):
    """Get the status of the background sync scheduler"""
    try:
        from scheduler_service import get_scheduler
        scheduler = get_scheduler()
        status = scheduler.get_scheduler_status()
        
        # Filter to only show user's jobs
        user_jobs = [job for job in status['jobs'] if f"user_{current_user['user_id']}" in job['id']]
        status['user_jobs'] = user_jobs
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Error getting scheduler status: {e}")
        return {"error": "Scheduler not available", "message": str(e)}

@router.post("/scheduler/pause")
async def pause_user_sync(
    current_user: dict = Depends(get_current_user)
):
    """Pause automatic sync for the current user"""
    try:
        from scheduler_service import get_scheduler
        scheduler = get_scheduler()
        await scheduler.pause_user_sync(current_user['user_id'])
        
        return {"success": True, "message": "Automatic sync paused"}
        
    except Exception as e:
        logger.error(f"❌ Error pausing sync: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause sync: {str(e)}")

@router.post("/scheduler/resume")
async def resume_user_sync(
    current_user: dict = Depends(get_current_user)
):
    """Resume automatic sync for the current user"""
    try:
        from scheduler_service import get_scheduler
        scheduler = get_scheduler()
        await scheduler.resume_user_sync(current_user['user_id'])
        
        return {"success": True, "message": "Automatic sync resumed"}
        
    except Exception as e:
        logger.error(f"❌ Error resuming sync: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume sync: {str(e)}")

@router.put("/scheduler/frequency")
async def update_sync_frequency(
    frequency_update: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update sync frequency for the current user"""
    try:
        frequency = frequency_update.get('frequency', 'every_4_hours')
        
        if frequency not in ['hourly', 'every_4_hours', 'nightly', 'daily']:
            raise HTTPException(status_code=400, detail="Invalid frequency")
        
        from scheduler_service import get_scheduler
        scheduler = get_scheduler()
        await scheduler.update_user_sync_frequency(current_user['user_id'], frequency)
        
        return {"success": True, "message": f"Sync frequency updated to {frequency}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating sync frequency: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update frequency: {str(e)}")

# Health check endpoint
@router.get("/analytics")
async def get_facebook_analytics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    ad_account_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get Facebook performance analytics data"""
    try:
        user_id = current_user.get("id")
        if not user_id:
            logger.error("❌ No user ID found in current_user")
            raise HTTPException(status_code=401, detail="User not authenticated")
            
        logger.info(f"🔄 Fetching analytics for user {user_id}")
        
        # Initialize database service
        db_service = get_facebook_db_service()
        
        # Set default date range if not provided (last 30 days)
        if not date_from:
            date_from = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.utcnow().strftime('%Y-%m-%d')
        
        # First get user's Facebook accounts
        user_accounts = await db_service.get_facebook_accounts_by_user(user_id)
        user_account_ids = [acc['id'] for acc in user_accounts]
        
        # If no Facebook accounts, return empty data
        if not user_account_ids:
            logger.info(f"ℹ️ No Facebook accounts found for user {user_id}")
            return {
                "success": True,
                "performance_data": [],
                "date_range": {
                    "from": date_from,
                    "to": date_to
                },
                "total_records": 0
            }
        
        # Fetch performance data from database
        query = db_service.supabase.table("facebook_ad_performance").select("*")
        
        # Filter by user's Facebook accounts
        query = query.in_("facebook_account_id", user_account_ids)
        
        # Apply filters
        if date_from:
            query = query.gte("date_start", date_from)
        if date_to:
            query = query.lte("date_stop", date_to)
        if ad_account_id:
            query = query.eq("ad_account_id", ad_account_id)
        if campaign_id:
            query = query.eq("campaign_id", campaign_id)
        
        # Order by date descending
        query = query.order("date_start", desc=True)
        
        result = query.execute()
        
        # Data is already filtered by user's accounts
        filtered_data = result.data
        
        logger.info(f"✅ Retrieved {len(filtered_data)} analytics records for user {user_id}")
        
        return {
            "success": True,
            "performance_data": filtered_data,
            "date_range": {
                "from": date_from,
                "to": date_to
            },
            "total_records": len(filtered_data)
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")

@router.get("/health")
async def facebook_api_health():
    """Check Facebook API service health"""
    try:
        # Basic health check - verify we can initialize the service
        service = get_facebook_service()
        
        return {
            "status": "healthy",
            "service": "Facebook Marketing API",
            "timestamp": datetime.utcnow().isoformat(),
            "app_id_configured": bool(service.app_id),
            "encryption_configured": bool(service.encryption_key)
        }
        
    except Exception as e:
        logger.error(f"❌ Facebook API health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

# ==================== Ad Creation Routes ====================

@router.post("/ads/create-from-videos", response_model=VideoAdCreationResponse)
async def create_ads_from_videos(
    request: VideoAdCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create Facebook ads from selected video ads
    
    This endpoint allows users to:
    1. Select videos from their generated video ads
    2. Choose campaign strategy (new or existing)
    3. Choose ad set strategy (new or existing)
    4. Create multiple ads with different test structures
    """
    try:
        db_service = get_facebook_db_service()
        ads_service = get_facebook_ads_service()
        api_service = get_facebook_service()
        
        # Get user's active Facebook account
        fb_accounts = await db_service.get_facebook_accounts_by_user(current_user['user_id'])
        if not fb_accounts:
            raise HTTPException(status_code=400, detail="No Facebook account connected")
        
        # Use first active account
        fb_account = fb_accounts[0]
        if fb_account['status'] != 'active':
            raise HTTPException(status_code=400, detail="Facebook account is not active")
        
        # Get selected ad accounts
        selected_ad_accounts = fb_account.get('selected_ad_accounts', [])
        if not selected_ad_accounts:
            raise HTTPException(status_code=400, detail="No ad accounts selected")
        
        # Use first ad account for now
        ad_account_id = selected_ad_accounts[0]
        
        # Get Facebook page ID (required for ads)
        # TODO: Implement page selection
        page_id = os.getenv("FACEBOOK_PAGE_ID", "")
        if not page_id:
            raise HTTPException(
                status_code=400, 
                detail="Facebook Page ID not configured. Please contact support."
            )
        
        # Decrypt access token
        access_token = api_service.decrypt_token(fb_account['access_token'])
        
        # Create ads
        result = await ads_service.create_ads_from_videos(
            request=request,
            ad_account_id=ad_account_id,
            page_id=page_id,
            access_token=access_token
        )
        
        # Store mappings in database
        if result.success and result.ads_created:
            for ad in result.ads_created:
                # Extract the actual video_id from composite ID (campaign_id_video_id)
                video_ad_id = ad['video_ad_id']
                if '_' in video_ad_id:
                    # Split and take the second part (the actual video ID)
                    video_ad_id = video_ad_id.split('_', 1)[1]

                await db_service.store_ad_mapping(
                    user_id=current_user['user_id'],
                    video_ad_id=video_ad_id,
                    facebook_campaign_id=result.campaign_id,
                    facebook_adset_id=result.adset_id,
                    facebook_ad_id=ad['facebook_ad_id'],
                    facebook_creative_id=ad['facebook_creative_id'],
                    facebook_video_id=ad['facebook_video_id']
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating ads from videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaigns/list")
async def list_campaigns(
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    current_user: dict = Depends(get_current_user)
):
    """
    List existing Facebook campaigns
    
    Returns campaigns that can be used for creating new ads
    """
    try:
        db_service = get_facebook_db_service()
        ads_service = get_facebook_ads_service()
        api_service = get_facebook_service()
        
        # Get user's Facebook account
        fb_accounts = await db_service.get_facebook_accounts_by_user(current_user['user_id'])
        if not fb_accounts:
            raise HTTPException(status_code=400, detail="No Facebook account connected")
        
        fb_account = fb_accounts[0]
        selected_ad_accounts = fb_account.get('selected_ad_accounts', [])
        if not selected_ad_accounts:
            raise HTTPException(status_code=400, detail="No ad accounts selected")
        
        ad_account_id = selected_ad_accounts[0]
        access_token = api_service.decrypt_token(fb_account['access_token'])
        
        # Get campaigns from Facebook
        campaigns = await ads_service.get_existing_campaigns(
            ad_account_id=ad_account_id,
            access_token=access_token,
            limit=limit
        )
        
        # Filter by status if provided
        if status:
            campaigns = [c for c in campaigns if c['status'] == status]
        
        return {
            "success": True,
            "campaigns": campaigns,
            "total": len(campaigns)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaigns/{campaign_id}/adsets")
async def list_campaign_adsets(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    List ad sets for a specific campaign
    
    Returns ad sets that can be used for creating new ads
    """
    try:
        db_service = get_facebook_db_service()
        ads_service = get_facebook_ads_service()
        api_service = get_facebook_service()
        
        # Get user's Facebook account
        fb_accounts = await db_service.get_facebook_accounts_by_user(current_user['user_id'])
        if not fb_accounts:
            raise HTTPException(status_code=400, detail="No Facebook account connected")
        
        fb_account = fb_accounts[0]
        access_token = api_service.decrypt_token(fb_account['access_token'])
        
        # Get ad sets from Facebook
        adsets = await ads_service.get_existing_adsets(
            campaign_id=campaign_id,
            access_token=access_token
        )
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "adsets": adsets,
            "total": len(adsets)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error listing ad sets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/targeting/suggestions")
async def get_targeting_suggestions(
    interests: List[str],
    current_user: dict = Depends(get_current_user)
):
    """
    Get targeting suggestions based on interests
    
    Returns audience size estimates and related interests
    """
    try:
        # TODO: Implement targeting suggestions using Facebook's targeting search API
        # For now, return mock data
        return {
            "success": True,
            "suggestions": {
                "interests": [
                    {"id": "6003107902433", "name": "Digital marketing", "audience_size": 1500000},
                    {"id": "6003139266461", "name": "Social media marketing", "audience_size": 2000000}
                ],
                "behaviors": [
                    {"id": "6002714895372", "name": "Small business owners", "audience_size": 500000}
                ],
                "estimated_reach": {
                    "min": 100000,
                    "max": 500000
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting targeting suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video-ads/available")
async def get_available_video_ads(
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of video ads available for Facebook ad creation
    
    Returns video ads that have been generated and are ready for publishing
    """
    try:
        # Get video ads from database
        # TODO: Connect to video_ads_v3_campaigns table
        
        # Mock response for now
        return {
            "success": True,
            "video_ads": [
                {
                    "id": "video_1",
                    "campaign_name": "Summer Sale Campaign",
                    "hook": "Are you tired of overpaying?",
                    "script_preview": "Discover our revolutionary product...",
                    "angle_type": "positive",
                    "video_url": "https://example.com/video1.mp4",
                    "thumbnail_url": "https://example.com/thumb1.jpg",
                    "duration_seconds": 30,
                    "created_at": datetime.now().isoformat()
                }
            ],
            "total": 1
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting available video ads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/campaign/save")
async def save_campaign_template(
    template: CampaignTemplate,
    current_user: dict = Depends(get_current_user)
):
    """
    Save a campaign template for reuse
    """
    try:
        db_service = get_facebook_db_service()
        
        # Save template to database
        template_id = await db_service.save_campaign_template(
            user_id=current_user['user_id'],
            template=template
        )
        
        return {
            "success": True,
            "template_id": template_id,
            "message": "Campaign template saved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error saving campaign template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/campaign/list")
async def list_campaign_templates(
    current_user: dict = Depends(get_current_user)
):
    """
    List saved campaign templates
    """
    try:
        db_service = get_facebook_db_service()
        
        templates = await db_service.get_campaign_templates(current_user['user_id'])
        
        return {
            "success": True,
            "templates": templates,
            "total": len(templates)
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing campaign templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audiences/preset/save")
async def save_audience_preset(
    preset: AudiencePreset,
    current_user: dict = Depends(get_current_user)
):
    """
    Save an audience preset for reuse
    """
    try:
        db_service = get_facebook_db_service()
        
        preset_id = await db_service.save_audience_preset(
            user_id=current_user['user_id'],
            preset=preset
        )
        
        return {
            "success": True,
            "preset_id": preset_id,
            "message": "Audience preset saved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error saving audience preset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audiences/preset/list")
async def list_audience_presets(
    current_user: dict = Depends(get_current_user)
):
    """
    List saved audience presets
    """
    try:
        db_service = get_facebook_db_service()
        
        presets = await db_service.get_audience_presets(current_user['user_id'])
        
        return {
            "success": True,
            "presets": presets,
            "total": len(presets)
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing audience presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))
