"""
Facebook Campaign Creation Routes
Handles creation of Facebook campaigns from video ads research
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from auth import verify_token
from video_ads_v3_database_service import v3_db_service
from logging_service import logger
from facebook_video_generation_service import (
    process_campaign_video_generation,
    get_elevenlabs_voices,
    get_actor_images
)

load_dotenv()

# Initialize service role client for RLS bypass
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

service_role_client: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        service_role_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("facebook_campaign.service_role_init", "Service role client initialized for RLS bypass")
    except Exception as e:
        logger.error("facebook_campaign.service_role_init_failed", f"Failed to initialize service role client: {e}")

router = APIRouter(prefix="/facebook-campaigns", tags=["Facebook Campaigns"])


# ===== Request/Response Models =====

class SelectedScript(BaseModel):
    script_id: str
    angle_id: str
    hook_id: str
    angle_name: str
    angle_type: str  # 'positive' or 'negative'
    hook_text: str
    script_preview: str
    full_script: str
    cta: str


class TargetingSpec(BaseModel):
    locations: List[str]
    age_min: int
    age_max: int
    gender: str  # 'all', 'male', 'female'
    interests: List[str]
    job_titles: List[str]
    placements: str  # 'automatic' or 'manual'


class CreativeSettings(BaseModel):
    voice_actor: str
    video_avatar: str
    landing_page_url: str
    cta_button: str


class CreateCampaignRequest(BaseModel):
    campaign_name: str
    research_campaign_id: str
    ad_account_id: str
    objective: str = "CONVERSIONS"
    daily_budget_per_adset: float = 10.0
    start_option: str = "immediately"  # 'immediately', 'draft', 'schedule'
    scheduled_start_time: Optional[str] = None
    targeting_spec: TargetingSpec
    creative_settings: CreativeSettings
    selected_scripts: List[SelectedScript]


class CampaignResponse(BaseModel):
    id: str
    campaign_name: str
    status: str
    created_at: str
    message: str


# ===== Routes =====

@router.post("/create", response_model=CampaignResponse)
async def create_facebook_campaign(
    request: CreateCampaignRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(verify_token)
):
    """
    Create a new Facebook campaign from selected scripts

    Flow:
    1. Validate inputs
    2. Save campaign to database with 'draft' or 'pending' status
    3. If start_option is 'draft', stop here
    4. If start_option is 'immediately' or 'schedule', trigger background job:
       - Generate videos for each script
       - Upload videos to Facebook
       - Create campaign structure (campaign → ad sets → ads)
       - Update status to 'completed'
    """
    try:
        user_id = current_user.get("user_id")

        # Validate inputs
        if len(request.selected_scripts) < 1 or len(request.selected_scripts) > 5:
            raise HTTPException(
                status_code=400,
                detail="Please select between 1 and 5 scripts"
            )

        if request.start_option == 'schedule' and not request.scheduled_start_time:
            raise HTTPException(
                status_code=400,
                detail="Scheduled start time is required when using 'schedule' option"
            )

        if not request.creative_settings.landing_page_url:
            raise HTTPException(
                status_code=400,
                detail="Landing page URL is required"
            )

        # Verify research campaign exists and belongs to user
        research_campaign = await v3_db_service.get_campaign(
            request.research_campaign_id,
            user_id
        )
        if not research_campaign:
            raise HTTPException(
                status_code=404,
                detail="Research campaign not found"
            )

        # Generate campaign ID
        campaign_id = str(uuid.uuid4())

        # Determine initial status based on start_option
        # For all options that need video generation, start with 'pending'
        # Only if user explicitly wants draft without generation, use 'draft'
        if request.start_option == 'draft':
            # Per original plan: draft option also generates videos
            status = 'pending'
        else:
            status = 'pending'  # Will be processed by background job

        # Prepare data for database
        campaign_data = {
            'id': campaign_id,
            'user_id': user_id,
            'campaign_name': request.campaign_name,
            'research_campaign_id': request.research_campaign_id,
            'ad_account_id': request.ad_account_id,
            'objective': request.objective,
            'daily_budget_per_adset': request.daily_budget_per_adset,
            'start_option': request.start_option,
            'scheduled_start_time': request.scheduled_start_time,
            'targeting_spec': request.targeting_spec.model_dump(),
            'creative_settings': request.creative_settings.model_dump(),
            'selected_scripts': [script.model_dump() for script in request.selected_scripts],
            'status': status,
            'video_generation_status': {},
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        }

        # Save to database
        success = await save_facebook_campaign(campaign_data)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save campaign to database"
            )

        logger.info("facebook_campaign.created",
                   f"Created Facebook campaign {campaign_id} with {len(request.selected_scripts)} scripts",
                   campaign_id=campaign_id,
                   status=status)

        # Trigger background job for video generation
        if status == 'pending':
            logger.info("facebook_campaign.background_job",
                       f"Triggering video generation for campaign {campaign_id}",
                       campaign_id=campaign_id)

            # Add background task to generate videos
            # Convert Pydantic models to dicts for background task
            selected_scripts_dicts = [script.model_dump() for script in request.selected_scripts]

            background_tasks.add_task(
                process_campaign_video_generation,
                campaign_id=campaign_id,
                selected_scripts=selected_scripts_dicts,
                voice_actor=request.creative_settings.voice_actor,
                video_avatar=request.creative_settings.video_avatar,
                service_role_client=service_role_client
            )

        # Prepare response message
        if request.start_option == 'draft':
            message = "Campaign created! Videos are being generated in the background. You can view progress in the Conversion Report."
        elif request.start_option == 'schedule':
            message = f"Campaign scheduled for {request.scheduled_start_time}. Videos are being generated now."
        else:
            message = "Campaign created! Videos are being generated in the background and campaign will go live shortly."

        return CampaignResponse(
            id=campaign_id,
            campaign_name=request.campaign_name,
            status=status,
            created_at=campaign_data['created_at'],
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("facebook_campaign.create_error",
                    f"Error creating Facebook campaign: {e}",
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_facebook_campaigns(
    current_user: dict = Depends(verify_token),
    status: Optional[str] = None
):
    """Get list of Facebook campaigns for the user"""
    try:
        user_id = current_user.get("user_id")

        campaigns = await get_user_facebook_campaigns(user_id, status)

        return campaigns

    except Exception as e:
        logger.error("facebook_campaign.list_error",
                    f"Error listing Facebook campaigns: {e}",
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice-actors")
async def get_voice_actors(
    current_user: dict = Depends(verify_token)
):
    """Get available ElevenLabs voices and actor images for Facebook campaigns"""
    try:
        logger.info("facebook_campaign.voice_actors.start", "Fetching voices and actors")

        # Fetch ElevenLabs voices
        voices = await get_elevenlabs_voices()

        # Get actor images
        actors = get_actor_images()

        logger.info("facebook_campaign.voice_actors.success",
                   f"Retrieved {len(voices)} voices and {len(actors)} actors")

        return {
            "voices": voices,
            "actors": actors,
            "status": "success"
        }

    except Exception as e:
        logger.error("facebook_campaign.voice_actors.error",
                    f"Error getting voice actors: {e}",
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}")
async def get_facebook_campaign(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get details of a specific Facebook campaign"""
    try:
        user_id = current_user.get("user_id")

        campaign = await get_facebook_campaign_by_id(campaign_id, user_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.error("facebook_campaign.get_error",
                    f"Error getting Facebook campaign: {e}",
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    new_status: str,
    current_user: dict = Depends(verify_token)
):
    """Update campaign status (e.g., activate a draft, pause a running campaign)"""
    try:
        user_id = current_user.get("user_id")

        # Verify campaign belongs to user
        campaign = await get_facebook_campaign_by_id(campaign_id, user_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Update status
        success = await update_facebook_campaign_status(campaign_id, new_status)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update campaign status")

        logger.info("facebook_campaign.status_updated",
                   f"Updated campaign {campaign_id} status to {new_status}",
                   campaign_id=campaign_id,
                   new_status=new_status)

        return {"success": True, "message": f"Campaign status updated to {new_status}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("facebook_campaign.status_update_error",
                    f"Error updating campaign status: {e}",
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ===== Database Functions =====

async def save_facebook_campaign(campaign_data: Dict[str, Any]) -> bool:
    """Save Facebook campaign to database using service role to bypass RLS"""
    if not service_role_client:
        logger.error("facebook_campaign.save_error", "Service role client not available")
        return False

    try:
        result = service_role_client.table("facebook_campaign_scripts").insert(campaign_data).execute()
        return bool(result.data)
    except Exception as e:
        logger.error("facebook_campaign.save_error",
                    f"Error saving Facebook campaign: {e}",
                    error=str(e))
        return False


async def get_user_facebook_campaigns(user_id: str, status: Optional[str] = None) -> List[Dict]:
    """Get all Facebook campaigns for a user using service role"""
    if not service_role_client:
        return []

    try:
        query = service_role_client.table("facebook_campaign_scripts").select("*").eq("user_id", user_id).order("created_at", desc=True)

        if status:
            query = query.eq("status", status)

        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error("facebook_campaign.get_user_campaigns_error",
                    f"Error getting user Facebook campaigns: {e}",
                    error=str(e))
        return []


async def get_facebook_campaign_by_id(campaign_id: str, user_id: str) -> Optional[Dict]:
    """Get a specific Facebook campaign by ID using service role"""
    if not service_role_client:
        return None

    try:
        result = service_role_client.table("facebook_campaign_scripts").select("*").eq("id", campaign_id).eq("user_id", user_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("facebook_campaign.get_by_id_error",
                    f"Error getting Facebook campaign by ID: {e}",
                    error=str(e))
        return None


async def update_facebook_campaign_status(campaign_id: str, new_status: str) -> bool:
    """Update Facebook campaign status using service role"""
    if not service_role_client:
        return False

    try:
        update_data = {
            'status': new_status,
            'updated_at': datetime.utcnow().isoformat()
        }

        if new_status == 'pending':
            update_data['started_at'] = datetime.utcnow().isoformat()
        elif new_status == 'completed':
            update_data['completed_at'] = datetime.utcnow().isoformat()

        result = service_role_client.table("facebook_campaign_scripts").update(update_data).eq("id", campaign_id).execute()
        return bool(result.data)
    except Exception as e:
        logger.error("facebook_campaign.update_status_error",
                    f"Error updating Facebook campaign status: {e}",
                    error=str(e))
        return False
