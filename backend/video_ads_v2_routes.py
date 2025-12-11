# Video Ads V2 Routes for Claude-powered workflow
import os
import json
import time
import openai
import aiohttp
import uuid
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Body, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from auth import verify_token, supabase
from actor_image_handler import actor_image_handler
from video_ads_v2_models import (
    MarketingAnalysisV2Request, MarketingAnalysisV2Response, 
    MarketingAnglesV2Response, VideoAdsProductInfoV2, URLParseV2Response,
    HooksV2Request, HooksV2Response,
    # V2 Voice Actor, Audio, Video models
    VoiceActorV2Request, VoiceActorV2Response,
    AudioGenerationV2Request, AudioGenerationV2Response,
    VideoGenerationV2Request, VideoGenerationV2Response,
    ElevenLabsVoice, ActorImage, GeneratedAudioV2, ScriptWithAudioV2, GeneratedVideoV2
)
from workflow_v2_manager import VideoAdsV2WorkflowManager
from logging_service import logger

# Import shared functions from V1 routes for reuse
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import voice and video generation utilities from V1
try:
    from video_ads_routes import (
        fetch_elevenlabs_voices, get_actor_images, 
        generate_audio_with_elevenlabs, hedra_generator
    )
except ImportError as e:
    logger.warning("import.video_ads_routes.failed", f"Could not import from video_ads_routes: {e}")
    # We'll handle this gracefully in the endpoints

# Load environment variables
load_dotenv()

# Import S3 service
from s3_service import s3_service

# Import models from V1 for URL parsing compatibility
from video_ads_models import URLParseRequest

# OpenAI client for URL parsing
client = None

def init_openai_client():
    """Initialize OpenAI client"""
    global client
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = openai.OpenAI(api_key=api_key)
        return True
    return False

# Initialize OpenAI client
init_openai_client()

# Create router
router = APIRouter(prefix="/video-ads-v2", tags=["video-ads-v2"])

# Import database service
from video_ads_v2_database_service import VideoAdsV2DatabaseService

# Initialize workflow manager
workflow_manager = VideoAdsV2WorkflowManager()

# Initialize database service
db_service = VideoAdsV2DatabaseService(supabase) if supabase else None

@router.get("/health")
async def video_ads_v2_health():
    """Health check for video ads v2 service"""
    return {
        "status": "healthy",
        "service": "video-ads-v2",
        "claude_available": workflow_manager.client.client is not None,
        "prompts_loaded": len(workflow_manager.client.prompts_cache),
        "endpoints": [
            "/video-ads-v2/parse-url",
            "/video-ads-v2/create-marketing-analysis",
            "/video-ads-v2/create-marketing-angles",
            "/video-ads-v2/create-hooks",
            "/video-ads-v2/create-scripts",
            "/video-ads-v2/voice-actor",
            "/video-ads-v2/audio",
            "/video-ads-v2/video"
        ]
    }

@router.post("/parse-url", response_model=URLParseV2Response)
async def parse_url_v2(
    request: URLParseRequest,
    current_user: dict = Depends(verify_token)
):
    """Parse a URL to extract product information for V2 workflow with frontend-compatible field names"""
    user_id = current_user["user_id"]
    
    # Set logging context
    logger.set_context(user_id=user_id)
    
    logger.info(
        "api.url_parse.started",
        f"Starting V2 URL parsing for {request.url}",
        url=request.url
    )
    
    try:
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.debug(
            "api.url_parse.fetching",
            "Fetching URL",
            url=request.url
        )
        
        # Use async HTTP request to avoid blocking
        async with aiohttp.ClientSession() as session:
            async with session.get(request.url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                response.raise_for_status()
                content = await response.read()
                
        logger.debug(
            "api.url_parse.fetched",
            f"Successfully fetched URL, content length: {len(content)} bytes",
            content_length=len(content)
        )
        
        # Parse HTML and extract clean text content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text content
        text_content = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit text length for API call (keep first 8000 chars to stay within token limits)
        original_length = len(clean_text)
        clean_text = clean_text[:8000]
        
        logger.debug(
            "api.url_parse.text_cleaned",
            "Cleaned text content",
            original_length=original_length,
            truncated_length=len(clean_text)
        )
        
        # Get page title and meta description for additional context
        title = soup.find('title')
        page_title = title.text.strip() if title else ""
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        meta_description = meta_desc.get('content', '').strip() if meta_desc else ""
        
        logger.debug(
            "api.url_parse.metadata",
            "Extracted page metadata",
            page_title=page_title,
            meta_description=meta_description
        )
        
        # Use OpenAI to extract structured information
        if not client:
            logger.warning(
                "api.url_parse.openai_init",
                "OpenAI client not initialized, trying to initialize"
            )
            if not init_openai_client():
                logger.error(
                    "api.url_parse.openai_failed",
                    "Failed to initialize OpenAI client"
                )
                raise HTTPException(status_code=500, detail="OpenAI client not initialized. Please check API key.")
        
        logger.debug(
            "api.url_parse.openai_ready",
            "OpenAI client ready"
        )
        
        # Create a prompt for structured extraction (V2 enhanced)
        extraction_prompt = f"""
        Analyze the following webpage content and extract structured product information. Return a JSON object with the following fields:

        - product_name: The main product or service name (max 100 chars)
        - product_information: Comprehensive description of what the product/service does (max 800 chars)
        - target_audience: Who this product is designed for (max 200 chars)
        - price: Any pricing information found (max 50 chars, include currency and billing period if found)
        - problem_solved: What problem or pain point this product solves (max 300 chars)
        - key_benefits: Array of key benefits/features (max 5 items, each max 100 chars)
        - unique_selling_points: Array of what makes this product unique (max 3 items, each max 150 chars)
        - differentiation: Combined summary of what makes this product unique and different from competitors (max 300 chars)
        - additional_information: Any other relevant information (max 500 chars)

        If information is not available or unclear, use an empty string for strings or empty array for arrays.

        Page Title: {page_title}
        Meta Description: {meta_description}
        Page Content: {clean_text}

        Return only valid JSON, no additional text:
        """
        
        logger.debug(
            "api.url_parse.openai_request",
            "Sending extraction prompt to OpenAI",
            prompt_length=len(extraction_prompt)
        )
        
        # Call OpenAI API
        try:
            ai_response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using more cost-effective model for extraction
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured product information from web content. Always return valid JSON."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,  # Lower temperature for more consistent extraction
                max_tokens=1500
            )
            
            logger.debug(
                "api.url_parse.openai_success",
                "OpenAI API call successful"
            )
            
            # Parse AI response
            ai_content = ai_response.choices[0].message.content.strip()
            
            logger.debug(
                "api.url_parse.openai_response",
                "Received OpenAI response",
                response_length=len(ai_content)
            )
            
            # Clean up response if it has markdown code blocks
            if ai_content.startswith('```json'):
                ai_content = ai_content[7:-3]
                logger.debug(
                    "api.url_parse.json_cleaned",
                    "Removed ```json``` wrapper"
                )
            elif ai_content.startswith('```'):
                ai_content = ai_content[3:-3]
                logger.debug(
                    "api.url_parse.json_cleaned",
                    "Removed ``` wrapper"
                )
            
            try:
                extracted_info = json.loads(ai_content)
                logger.debug(
                    "api.url_parse.json_parsed",
                    "JSON parsing successful",
                    extracted_fields=list(extracted_info.keys())
                )
            except json.JSONDecodeError as e:
                logger.error(
                    "api.url_parse.json_error",
                    "JSON parsing failed",
                    exception=e
                )
                # Fallback if JSON parsing fails
                extracted_info = {
                    "product_name": page_title[:100] if page_title else "",
                    "product_information": meta_description[:800] if meta_description else "",
                    "target_audience": "",
                    "price": "",
                    "problem_solved": "",
                    "key_benefits": [],
                    "unique_selling_points": [],
                    "differentiation": "",
                    "additional_information": meta_description[:500] if meta_description else ""
                }
                logger.warning(
                    "api.url_parse.fallback",
                    "Using fallback extraction"
                )
        
        except Exception as openai_error:
            logger.error(
                "api.url_parse.openai_error",
                "OpenAI API error",
                exception=openai_error
            )
            # Fallback extraction without AI
            extracted_info = {
                "product_name": page_title[:100] if page_title else "",
                "product_information": meta_description[:800] if meta_description else "",
                "target_audience": "",
                "price": "",
                "problem_solved": "",
                "key_benefits": [],
                "unique_selling_points": [],
                "differentiation": "",
                "additional_information": meta_description[:500] if meta_description else ""
            }
            logger.warning(
                "api.url_parse.fallback_api_error",
                "Using fallback extraction due to API error"
            )
        
        # Ensure all required fields exist with proper defaults
        required_fields = {
            "product_name": "",
            "product_information": "",
            "target_audience": "",
            "price": "",
            "problem_solved": "",
            "key_benefits": [],
            "unique_selling_points": [],
            "differentiation": "",
            "additional_information": ""
        }
        
        for field, default in required_fields.items():
            if field not in extracted_info:
                extracted_info[field] = default
            elif extracted_info[field] is None:
                extracted_info[field] = default
        
        # Ensure string fields are properly truncated
        extracted_info["product_name"] = str(extracted_info["product_name"])[:100]
        extracted_info["product_information"] = str(extracted_info["product_information"])[:800]
        extracted_info["target_audience"] = str(extracted_info["target_audience"])[:200]
        extracted_info["price"] = str(extracted_info["price"])[:50]
        extracted_info["problem_solved"] = str(extracted_info["problem_solved"])[:300]
        extracted_info["additional_information"] = str(extracted_info["additional_information"])[:500]
        
        # Ensure arrays are properly formatted and truncated
        if isinstance(extracted_info["key_benefits"], list):
            extracted_info["key_benefits"] = [str(benefit)[:100] for benefit in extracted_info["key_benefits"][:5]]
        else:
            extracted_info["key_benefits"] = []
            
        if isinstance(extracted_info["unique_selling_points"], list):
            extracted_info["unique_selling_points"] = [str(usp)[:150] for usp in extracted_info["unique_selling_points"][:3]]
        else:
            extracted_info["unique_selling_points"] = []
        
        # If differentiation is empty, generate from unique_selling_points
        if not extracted_info["differentiation"] and extracted_info["unique_selling_points"]:
            extracted_info["differentiation"] = ". ".join(extracted_info["unique_selling_points"])[:300]
        
        extracted_info["differentiation"] = str(extracted_info["differentiation"])[:300]
        
        logger.info(
            "api.url_parse.completed",
            f"Successfully parsed URL: {extracted_info['product_name']}",
            product_name=extracted_info['product_name'],
            key_benefits_count=len(extracted_info['key_benefits']),
            usps_count=len(extracted_info['unique_selling_points'])
        )
        
        # Don't create campaign here - it will be created in marketing angles step
        # Just return the parsed data
        return URLParseV2Response(**extracted_info)
        
    except Exception as e:
        logger.error(
            "api.url_parse.failed",
            f"V2 URL parsing error for URL: {request.url}",
            exception=e,
            url=request.url
        )
        raise HTTPException(status_code=500, detail=f"V2 URL parsing failed: {str(e)}")

@router.post("/create-marketing-analysis", response_model=MarketingAnalysisV2Response)
async def create_marketing_analysis_v2(
    request: MarketingAnalysisV2Request,
    current_user: dict = Depends(verify_token)
):
    """
    Claude V2: Complete marketing analysis workflow
    Returns comprehensive analysis (avatar, journey, objections, angles)
    """
    
    start_time = time.time()
    user_id = current_user["user_id"]
    
    # Set logging context
    logger.set_context(user_id=user_id)
    
    logger.info(
        "api.marketing_analysis.started",
        f"V2 Marketing Analysis request for {request.product_info.product_name}",
        product_name=request.product_info.product_name,
        target_audience=request.product_info.target_audience
    )
    
    try:
        logger.debug(
            "api.marketing_analysis.workflow_starting",
            "Starting Claude V2 workflow manager analysis",
            force_new_conversation=request.force_new_conversation
        )
        
        # Run complete analysis workflow
        analysis = await workflow_manager.create_marketing_analysis(
            request.product_info, 
            user_id,
            force_new_conversation=request.force_new_conversation
        )
        
        processing_time = time.time() - start_time
        
        logger.info(
            "api.marketing_analysis.workflow_completed",
            f"Claude V2 analysis completed in {processing_time:.2f} seconds",
            duration_ms=int(processing_time * 1000)
        )
        
        # Find conversation ID from active conversations
        conversation_id = None
        if not request.force_new_conversation:
            # Only reuse existing conversation if not forcing new one
            for conv_id, conv_data in workflow_manager.active_conversations.items():
                if conv_data["state"].user_id == user_id:
                    conversation_id = conv_id
                    break
        else:
            # For manual uploads, find the most recent conversation (the new one we just created)
            for conv_id, conv_data in workflow_manager.active_conversations.items():
                if conv_data["state"].user_id == user_id:
                    conversation_id = conv_id  # Take the last one found (most recent)
        
        logger.debug(
            "api.marketing_analysis.conversation_id",
            f"Found conversation ID: {conversation_id}",
            conversation_id=conversation_id
        )
        
        # Log analysis results summary
        logger.info(
            "api.marketing_analysis.results_summary",
            "Analysis results summary",
            avatar_age_range=analysis.avatar_analysis.demographic_data.age_range,
            journey_phases=4,
            solution_objections=len(analysis.objections_analysis.solution_objections),
            internal_objections=len(analysis.objections_analysis.internal_objections),
            positive_angles=len(analysis.angles_generation.positive_angles),
            negative_angles=len(analysis.angles_generation.negative_angles)
        )
        
        response = MarketingAnalysisV2Response(
            conversation_id=conversation_id,
            analysis=analysis,
            processing_time=processing_time,
            claude_model="claude-sonnet-4-5-20250929"
        )
        
        logger.info("analysis.v2.complete", f"V2 Analysis complete in {processing_time:.2f}s", processing_time=processing_time)
        return response
        
    except Exception as e:
        logger.error(
            "analysis.v2.failed",
            f"V2 Analysis failed: {str(e)}",
            error_type=str(type(e)),
            processing_time=time.time() - start_time,
            error_details=str(e)
        )
        raise HTTPException(
            status_code=500, 
            detail=f"Marketing analysis failed: {str(e)}"
        )

@router.post("/create-marketing-angles", response_model=MarketingAnglesV2Response)
async def create_marketing_angles_v2(
    request: MarketingAnalysisV2Request,
    current_user: dict = Depends(verify_token)
):
    """
    Claude V2: Marketing angles generation (simplified frontend response)
    Runs full analysis but returns only angles for current UX compatibility
    """
    
    start_time = time.time()
    user_id = current_user["user_id"]
    
    logger.info(
        "marketing_angles.v2.request",
        f"V2 Marketing Angles request from user {user_id}",
        user_id=user_id,
        product_name=request.product_info.product_name,
        force_new_conversation=request.force_new_conversation
    )
    
    try:
        # Run complete analysis workflow
        analysis = await workflow_manager.create_marketing_analysis(
            request.product_info, 
            user_id,
            force_new_conversation=request.force_new_conversation
        )
        
        processing_time = time.time() - start_time
        
        # Find conversation ID from active conversations
        conversation_id = None
        if not request.force_new_conversation:
            # Only reuse existing conversation if not forcing new one
            for conv_id, conv_data in workflow_manager.active_conversations.items():
                if conv_data["state"].user_id == user_id:
                    conversation_id = conv_id
                    break
        else:
            # For manual uploads, find the most recent conversation (the new one we just created)
            for conv_id, conv_data in workflow_manager.active_conversations.items():
                if conv_data["state"].user_id == user_id:
                    conversation_id = conv_id  # Take the last one found (most recent)
        
        # Save to database if service is available
        if db_service and conversation_id:
            try:
                # Get or create campaign
                campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
                
                if not campaign:
                    # Create new campaign if it doesn't exist
                    campaign = await db_service.create_campaign(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        campaign_name=request.product_info.product_name or "New Campaign"
                    )
                    
                    # Save product info if we're creating a new campaign
                    if campaign:
                        await db_service.save_product_info(
                            campaign_id=campaign['id'],
                            product_info=request.product_info.model_dump() if hasattr(request.product_info, 'model_dump') else request.product_info.dict()
                        )
                
                if campaign:
                    # Save marketing analysis
                    await db_service.save_marketing_analysis(
                        campaign_id=campaign['id'],
                        analysis=analysis.model_dump() if hasattr(analysis, 'model_dump') else analysis.dict(),
                        processing_time_ms=int(processing_time * 1000),
                        claude_model="claude-sonnet-4-5-20250929"
                    )
                    
                    # Update campaign step
                    await db_service.update_campaign_step(campaign['id'], 3)
                    
                    logger.debug("database.marketing_analysis.saved", f"Saved marketing analysis for campaign {campaign['id']}", campaign_id=campaign['id'])
                    
            except Exception as db_error:
                logger.warning("database.save.error", f"Database save error: {db_error}", error=str(db_error))
                # Continue without saving - don't fail the request
        
        # Return simplified response with angles only (for current frontend)
        response = MarketingAnglesV2Response(
            conversation_id=conversation_id,
            positive_angles=analysis.angles_generation.positive_angles,
            negative_angles=analysis.angles_generation.negative_angles,
            processing_time=processing_time
        )
        
        logger.info(
            "marketing_angles.v2.complete",
            f"V2 Angles complete: {len(response.positive_angles)} positive, {len(response.negative_angles)} negative",
            positive_count=len(response.positive_angles),
            negative_count=len(response.negative_angles),
            processing_time=processing_time
        )
        
        return response
        
    except Exception as e:
        logger.error("marketing_angles.v2.failed", f"V2 Angles failed: {str(e)}", error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Marketing angles generation failed: {str(e)}"
        )

@router.get("/conversation/{conversation_id}/analysis")
async def get_conversation_analysis(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get complete analysis for a conversation"""
    
    user_id = current_user["user_id"]
    
    # Get conversation state
    state = workflow_manager.get_conversation_state(conversation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify user ownership
    if state.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get analysis
    analysis = workflow_manager.get_conversation_analysis(conversation_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "conversation_id": conversation_id,
        "analysis": analysis,
        "state": state
    }

@router.get("/conversation/{conversation_id}/angles")
async def get_conversation_angles(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get angles only for a conversation (frontend compatibility)"""
    
    user_id = current_user["user_id"]
    
    # Get conversation state
    state = workflow_manager.get_conversation_state(conversation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify user ownership
    if state.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get analysis
    analysis = workflow_manager.get_conversation_analysis(conversation_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "conversation_id": conversation_id,
        "positive_angles": analysis.angles_generation.positive_angles,
        "negative_angles": analysis.angles_generation.negative_angles,
        "created_at": state.created_at
    }

@router.post("/create-hooks", response_model=HooksV2Response)
async def create_hooks_v2(
    request: HooksV2Request,
    current_user: dict = Depends(verify_token)
):
    """Generate viral hooks for selected marketing angles using Claude V2"""
    
    start_time = time.time()
    user_id = current_user["user_id"]
    conversation_id = request.conversation_id
    selected_angles = request.selected_angles
    
    logger.info(
        "hooks.v2.creation.started",
        f"Starting V2 hooks creation for user {user_id}",
        user_id=user_id,
        conversation_id=conversation_id,
        selected_angles_count=len(selected_angles)
    )
    
    try:
        # Verify conversation exists and user ownership
        conversation_state = workflow_manager.get_conversation_state(conversation_id)
        if not conversation_state:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation_state.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this conversation")
        
        # Get complete analysis for context
        complete_analysis = workflow_manager.get_conversation_analysis(conversation_id)
        if not complete_analysis:
            raise HTTPException(status_code=404, detail="Analysis not found for this conversation")
        
        # Generate hooks using Claude with full context
        hooks_analysis = await workflow_manager.create_hooks_analysis(
            conversation_state.product_info,
            complete_analysis,
            selected_angles,
            user_id
        )
        
        processing_time = time.time() - start_time
        logger.info("hooks.v2.generation.complete", f"V2 hooks generation completed in {processing_time:.2f} seconds", processing_time=processing_time)
        
        # Save to database if service is available
        if db_service:
            try:
                campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
                
                if campaign:
                    # Convert hooks_analysis to dict for storage
                    hooks_data = [hook.model_dump() if hasattr(hook, 'model_dump') else hook.dict() for hook in hooks_analysis]
                    
                    # Don't save selected_hooks here - they will be saved when scripts are created
                    await db_service.save_hooks(
                        campaign_id=campaign['id'],
                        hooks_data={"hooks_by_angle": hooks_data},
                        selected_hooks=None,  # Don't save selected hooks yet
                        processing_time_ms=int(processing_time * 1000)
                    )
                    
                    # Update selected angles in marketing analysis
                    selected_angles_data = [angle.model_dump() if hasattr(angle, 'model_dump') else angle.dict() for angle in selected_angles]
                    await db_service.update_selected_angles(campaign['id'], selected_angles_data)
                    
                    # Update campaign step
                    await db_service.update_campaign_step(campaign['id'], 4)
                    
                    logger.debug("database.hooks.saved", f"Saved hooks for campaign {campaign['id']}", campaign_id=campaign['id'])
                    
            except Exception as db_error:
                logger.warning("database.save.error", f"Database save error: {db_error}", error=str(db_error))
                # Continue without saving
        
        return HooksV2Response(
            conversation_id=conversation_id,
            hooks_by_angle=hooks_analysis,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("hooks.v2.creation.failed", f"Error in V2 hooks creation: {str(e)}", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create hooks: {str(e)}")

@router.post("/create-scripts", response_model=dict)
async def create_scripts_v2(
    request: dict,
    current_user: dict = Depends(verify_token)
):
    """Generate scripts for selected hooks using Claude V2 with full context"""
    
    start_time = time.time()
    
    logger.debug("separator", "="*80)
    print("DEBUG: Starting create_scripts_v2 endpoint")
    logger.debug("separator", "="*80)
    print(f"DEBUG: Request data keys: {list(request.keys())}")
    print(f"DEBUG: Request: {json.dumps(request, indent=2)[:500]}...")
    logger.debug("separator", "="*80)
    
    try:
        user_id = current_user["user_id"]
        conversation_id = request.get("conversation_id")
        hooks_by_angle = request.get("hooks_by_angle", [])
        
        print(f"📝 Starting V2 scripts creation for user {user_id}")
        print(f"🔗 Conversation ID: {conversation_id}")
        print(f"📐 Processing {len(hooks_by_angle)} angles for script generation")
        
        if not conversation_id:
            print("❌ DEBUG: Missing conversation_id in request")
            raise HTTPException(status_code=400, detail="conversation_id is required")
        
        if not hooks_by_angle:
            print("❌ DEBUG: Missing hooks_by_angle in request")
            raise HTTPException(status_code=400, detail="hooks_by_angle is required")
        
        # Generate scripts using Claude with complete accumulated context
        print("DEBUG: Calling workflow_manager.create_scripts_analysis...")
        campaign_scripts = await workflow_manager.create_scripts_analysis(
            conversation_id,
            hooks_by_angle,
            user_id
        )
        
        processing_time = time.time() - start_time
        print(f"✅ V2 scripts generation completed in {processing_time:.2f} seconds")
        
        logger.debug("separator", "="*80)
        print("DEBUG: create_scripts_v2 endpoint completed successfully")
        print(f"DEBUG: Generated scripts for {len(campaign_scripts.get('angles', []))} angles")
        logger.debug("separator", "="*80)
        
        # Save to database if service is available
        if db_service:
            try:
                campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
                
                if campaign:
                    await db_service.save_scripts(
                        campaign_id=campaign['id'],
                        scripts_data=campaign_scripts,
                        processing_time_ms=int(processing_time * 1000)
                    )
                    
                    # Save selected hooks (from the scripts request)
                    # All hooks sent to create-scripts are already selected
                    selected_hooks = []
                    for angle in hooks_by_angle:
                        angle_id = angle.get('id') or angle.get('angle_id')
                        hooks_by_cat = angle.get('hooks_by_category', {})
                        
                        for hook_cat, hooks in hooks_by_cat.items():
                            # hooks is a list of hook texts (strings)
                            if isinstance(hooks, list):
                                for hook_text in hooks:
                                    selected_hooks.append({
                                        'angle_id': angle_id,
                                        'hook_type': hook_cat,
                                        'hook_text': hook_text
                                    })
                    
                    if selected_hooks:
                        print(f"💾 DEBUG: Saving {len(selected_hooks)} selected hooks")
                        await db_service.update_selected_hooks(campaign['id'], selected_hooks)
                    else:
                        print("⚠️ DEBUG: No selected hooks to save")
                    
                    # Update campaign step
                    await db_service.update_campaign_step(campaign['id'], 5)
                    
                    print(f"💾 DEBUG: Saved scripts to database for campaign {campaign['id']}")
                    
            except Exception as db_error:
                logger.warning("database.save.error", f"Database save error: {db_error}", error=str(db_error))
                # Continue without saving
        
        return {
            "conversation_id": conversation_id,
            "campaign_scripts": campaign_scripts,
            "processing_time": processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.debug("separator", "="*80)
        print(f"❌ DEBUG: Error in create_scripts_v2 after {processing_time:.2f} seconds")
        print(f"DEBUG: Error type: {type(e)}")
        print(f"DEBUG: Error message: {str(e)}")
        print(f"DEBUG: User ID: {user_id}")
        print(f"DEBUG: Conversation ID: {conversation_id if 'conversation_id' in locals() else 'N/A'}")
        logger.debug("separator", "="*80)
        print(f"❌ Error in V2 scripts creation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create scripts: {str(e)}")

# Configuration for audio and video generation
AUDIO_CACHE_DIR = Path(__file__).parent / "generated_audio"
AUDIO_CACHE_DIR.mkdir(exist_ok=True)

@router.post("/voice-actor", response_model=VoiceActorV2Response)
async def voice_actor_v2(
    request: VoiceActorV2Request,
    current_user: dict = Depends(verify_token)
):
    """Get available voices and actors for selection (V3 with campaign_id)"""
    
    try:
        logger.debug("separator", "="*80)
        logger.info("voice_actor.start", f"Starting voice_actor_v2 endpoint for campaign: {request.campaign_id}")
        logger.debug("separator", "="*80)
        logger.debug("voice_actor.request", f"Request campaign_id: {request.campaign_id}")
        logger.debug("voice_actor.scripts", f"Request campaign_scripts keys: {list(request.campaign_scripts.keys()) if hasattr(request.campaign_scripts, 'keys') else type(request.campaign_scripts)}")
        logger.debug("voice_actor.user", f"User ID: {current_user.get('user_id', 'N/A')}")
        logger.debug("separator", "="*80)
        
        # Verify campaign exists using V3 database service
        logger.debug("voice_actor.verify", f"Checking if campaign {request.campaign_id} exists...")
        user_id = current_user.get("user_id")
        
        # Get campaign to verify ownership
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(request.campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(request.campaign_id, user_id)
        
        if not campaign:
            logger.error("voice_actor.not_found", f"Campaign {request.campaign_id} not found")
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.debug("voice_actor.found", f"Campaign found - Campaign ID: {campaign.get('campaign_id')}")
        logger.info("voice_actor.verified", "Campaign verification passed")
        
        # Fetch ElevenLabs voices (reuse V1 function)
        logger.debug("voice_actor.voices", "Starting to fetch ElevenLabs voices...")
        try:
            voices = await fetch_elevenlabs_voices()
            logger.debug("voice_actor.voices.count", f"Retrieved {len(voices)} voices")
            if voices:
                logger.debug("voice_actor.voices.sample", f"First voice: {voices[0].name} - {voices[0].voice_id}")
        except Exception as e:
            logger.error("voice_actor.voices.error", f"Error fetching voices: {e}")
            # Fallback to empty list if voice service is down
            voices = []
        
        # Get actor images (reuse V1 function)
        logger.debug("voice_actor.actors", "Getting actor images...")
        try:
            actors = get_actor_images()
            logger.debug("voice_actor.actors.count", f"Retrieved {len(actors)} actors")
            if actors:
                logger.debug("voice_actor.actors.sample", f"First actor: {actors[0].name} - {actors[0].filename}")
        except Exception as e:
            logger.error("voice_actor.actors.error", f"Error fetching actors: {e}")
            # Fallback to empty list if actor service is down
            actors = []
        
        logger.debug("voice_actor.response", "Creating V2 response...")
        # Convert V1 models to V2 models for response
        v2_voices = []
        for voice in voices:
            v2_voices.append(ElevenLabsVoice(
                voice_id=voice.voice_id,
                name=voice.name,
                description=voice.description,
                category=voice.category,
                labels=voice.labels,
                preview_url=voice.preview_url,
                gender=voice.gender,
                age=voice.age,
                accent=voice.accent,
                use_case=voice.use_case
            ))
        
        v2_actors = []
        for actor in actors:
            v2_actors.append(ActorImage(
                filename=actor.filename,
                name=getattr(actor, 'name', actor.filename.replace('.jpg', '').replace('.png', '').title()),
                description=getattr(actor, 'description', f"Actor image {actor.filename}"),
                category=getattr(actor, 'category', 'Professional')
            ))
        
        response = VoiceActorV2Response(
            conversation_id=request.campaign_id,  # Keep as conversation_id in response for backward compatibility
            voices=v2_voices,
            actors=v2_actors,
            status="success"
        )
        logger.info("voice_actor.success", f"Response created successfully for campaign: {request.campaign_id}")
        logger.debug("voice_actor.stats", f"Response contains {len(v2_voices)} voices and {len(v2_actors)} actors")
        logger.debug("separator", "="*80)
        
        return response
        
    except HTTPException as he:
        logger.error("voice_actor.http_error", f"HTTP Exception: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error("voice_actor.error", f"Unexpected error: {str(e)}", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get voice actors: {str(e)}")

@router.put("/campaign/{campaign_id}/voice-actor/selected")
async def save_selected_voice_actor_v2(
    campaign_id: str,
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Save selected voice and actor to database immediately when selected (V2)."""
    try:
        logger.info("voice_actor.save.v2", f"Saving voice/actor selection for campaign: {campaign_id}")
        
        # Extract voice_info from request
        voice_info = request.get("voice_info", {})
        
        if not voice_info:
            raise HTTPException(status_code=400, detail="voice_info is required")
        
        # Use supabase directly to update the V3 campaign content table
        # Store in audio_data column as voice_info
        try:
            # First check if campaign exists in v3 table
            result = supabase.table('video_ads_v3_campaign_content').select('*').eq('campaign_id', campaign_id).execute()
            
            if result.data:
                # Update existing record - merge with existing audio_data
                existing_audio_data = result.data[0].get('audio_data', {}) or {}
                existing_audio_data['voice_info'] = voice_info
                
                update_result = supabase.table('video_ads_v3_campaign_content').update({
                    'audio_data': existing_audio_data,
                    'updated_at': 'now()'
                }).eq('campaign_id', campaign_id).execute()
                
                if update_result.data:
                    logger.info("voice_actor.save.v2.success", 
                               f"Updated voice/actor selection in V3 table for campaign: {campaign_id}")
            else:
                # Create new record
                insert_result = supabase.table('video_ads_v3_campaign_content').insert({
                    'campaign_id': campaign_id,
                    'audio_data': {'voice_info': voice_info},
                    'created_at': 'now()',
                    'updated_at': 'now()'
                }).execute()
                
                if insert_result.data:
                    logger.info("voice_actor.save.v2.success", 
                               f"Created new V3 record with voice/actor selection for campaign: {campaign_id}")
        except Exception as db_error:
            logger.error("voice_actor.save.v2.db_error", 
                        f"Database error: {db_error}")
            # Fallback to V2 selections table
            try:
                result = supabase.table('video_ads_v2_selections').upsert({
                    'conversation_id': campaign_id,
                    'voice_data': voice_info.get("selected_voice"),
                    'actor_data': voice_info.get("selected_actor"),
                    'updated_at': 'now()'
                }).execute()
                
                if result.data:
                    logger.info("voice_actor.save.v2.fallback", 
                               f"Saved to V2 selections table for campaign: {campaign_id}")
            except Exception as fallback_error:
                logger.error("voice_actor.save.v2.fallback.error", 
                            f"Failed to save to V2 table: {fallback_error}")
                raise HTTPException(status_code=500, detail="Failed to save voice/actor selection")
        
        return {
            "status": "success",
            "message": "Voice and actor selection saved",
            "campaign_id": campaign_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("voice_actor.save.v2.error", 
                    f"Error saving voice/actor selection: {e}", 
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audio", response_model=AudioGenerationV2Response)
async def generate_audio_v2(
    request: AudioGenerationV2Request,
    current_user: dict = Depends(verify_token)
):
    """Generate audio for scripts and hooks using ElevenLabs TTS (V2 with conversation_id)"""
    
    try:
        print(f"🎵 V2 Audio generation request for conversation: {request.conversation_id}")
        
        # Verify conversation exists
        conversation_state = workflow_manager.get_conversation_state(request.conversation_id)
        if not conversation_state:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation_state.user_id != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied to this conversation")
        
        # Extract data from request
        voice_selection = request.voice_actor_selection
        selected_voice = voice_selection.get("selected_voice", {})
        selected_actor = voice_selection.get("selected_actor", {})
        
        # Get voice ID
        voice_id = selected_voice.get("voice_id")
        print(f"🔍 DEBUG: selected_voice = {selected_voice}")
        print(f"🔍 DEBUG: voice_id = {voice_id}")
        if not voice_id:
            print(f"❌ DEBUG: No voice_id found in selected_voice: {selected_voice}")
            raise HTTPException(status_code=400, detail="No voice selected")
        
        print(f"🎤 Using voice: {selected_voice.get('name', 'Unknown')} ({voice_id})")
        print(f"🎭 Using actor: {selected_actor.get('name', 'Unknown')}")
        
        # Get scripts from campaign_scripts
        campaign_scripts = request.campaign_scripts
        selected_angle = campaign_scripts.get("selected_angle", {})
        scripts = campaign_scripts.get("scripts", [])
        
        if not scripts:
            raise HTTPException(status_code=400, detail="No scripts provided")
        
        print(f"📝 Processing {len(scripts)} scripts for audio generation")
        
        # Generate audio for each script (reuse V1 logic)
        scripts_with_audio = []
        total_audios_generated = 0
        
        for script in scripts:
            script_id = script.get("script_id", str(uuid.uuid4()))
            hook = script.get("hook", "")
            body = script.get("body", "")
            selected = script.get("selected", False)
            
            # Combine hook and body for audio generation
            combined_text = f"{hook} {body}".strip()
            
            if combined_text:
                try:
                    # Generate combined audio using V1 function
                    # Extract campaign_id from conversation_id if available
                    campaign_id = request.conversation_id if request.conversation_id else None
                    audio_content = await generate_audio_with_elevenlabs(
                        text=combined_text,
                        voice_id=voice_id,
                        audio_type="combined",
                        campaign_id=campaign_id
                    )
                    
                    if audio_content:
                        combined_audio = GeneratedAudioV2(
                            audio_id=audio_content.audio_id,
                            type=audio_content.type,
                            content=audio_content.content,
                            audio_url=audio_content.audio_url,
                            duration=getattr(audio_content, 'duration', None),
                            file_size=audio_content.file_size,
                            voice_settings=audio_content.voice_settings
                        )
                        total_audios_generated += 1
                    else:
                        combined_audio = None
                        
                except Exception as audio_error:
                    print(f"❌ Error generating audio for script {script_id}: {audio_error}")
                    combined_audio = None
            else:
                combined_audio = None
            
            script_with_audio = ScriptWithAudioV2(
                script_id=script_id,
                hook=hook,
                body=body,
                selected=selected,
                combined_audio=combined_audio
            )
            scripts_with_audio.append(script_with_audio)
        
        print(f"✅ Generated {total_audios_generated} audio files")
        
        # Save to database if service is available
        if db_service:
            try:
                campaign = await db_service.get_campaign_by_conversation(request.conversation_id, current_user["user_id"])
                
                if campaign:
                    # Save voice and actor selections (just IDs, not full objects)
                    await db_service.save_selections(
                        campaign_id=campaign['id'],
                        voice_data={'voice_id': voice_id, 'name': selected_voice.get('name', '')},
                        actor_data={'actor_id': selected_actor.get('filename', ''), 'name': selected_actor.get('name', '')}
                    )
                    
                    # Save audio files
                    for script_audio in scripts_with_audio:
                        if script_audio.combined_audio:
                            await db_service.save_media(
                                campaign_id=campaign['id'],
                                media_type='audio',
                                script_id=script_audio.script_id,
                                file_url=script_audio.combined_audio.audio_url,
                                file_metadata={
                                    'duration': script_audio.combined_audio.duration,
                                    'file_size': script_audio.combined_audio.file_size,
                                    'voice_settings': script_audio.combined_audio.voice_settings
                                }
                            )
                    
                    # Update selected scripts in database
                    selected_scripts = []
                    for script in scripts_with_audio:
                        if script.selected:
                            selected_scripts.append({
                                'script_id': script.script_id,
                                'hook': script.hook,
                                'body': script.body
                            })
                    
                    if selected_scripts:
                        await db_service.update_selected_scripts(campaign['id'], selected_scripts)
                    
                    # Update campaign step
                    await db_service.update_campaign_step(campaign['id'], 7)
                    
                    print(f"💾 DEBUG: Saved audio generation to database for campaign {campaign['id']}")
                    
            except Exception as db_error:
                logger.warning("database.save.error", f"Database save error: {db_error}", error=str(db_error))
                # Continue without saving
        
        response = AudioGenerationV2Response(
            conversation_id=request.conversation_id,
            selected_angle=selected_angle,
            voice_info={
                "selected_voice": selected_voice,
                "selected_actor": selected_actor
            },
            scripts_with_audio=scripts_with_audio,
            total_audios_generated=total_audios_generated,
            processing_time=time.time(),
            status="success"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in V2 audio generation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate audio: {str(e)}")

@router.post("/video", response_model=VideoGenerationV2Response)
async def generate_video_v2(
    request: VideoGenerationV2Request,
    current_user: dict = Depends(verify_token)
):
    """Generate videos using Hedra API for all hook+script combinations (V2 with conversation_id)"""
    
    try:
        start_time = time.time()
        user_id = current_user["user_id"]
        conversation_id = request.conversation_id
        
        print(f"🎬 V2 Video generation request for conversation: {conversation_id}")
        print(f"👤 User: {user_id}")
        
        # Log the complete request
        print("\n" + "="*50)
        print("📥 VIDEO GENERATION REQUEST RECEIVED")
        print("="*50)
        print(f"Conversation ID: {conversation_id}")
        print(f"Actor Image: {request.actor_image}")
        print(f"Video Settings: {request.video_settings}")
        print(f"Scripts with audio count: {len(request.audio_data.get('scripts_with_audio', []))}")
        
        # Log each script's details
        for idx, script in enumerate(request.audio_data.get('scripts_with_audio', [])):
            print(f"\n📝 Script {idx + 1}:")
            print(f"  - Script ID: {script.get('script_id')}")
            print(f"  - Has combined audio: {bool(script.get('combined_audio'))}")
            if script.get('combined_audio'):
                print(f"  - Combined audio URL: {script['combined_audio'].get('audio_url')}")
                print(f"  - Combined audio duration: {script['combined_audio'].get('duration')}")
            print(f"  - Hook: {script.get('hook', '')[:50]}...")
            print(f"  - Body: {script.get('body', '')[:50]}...")
        
        print("="*50 + "\n")
        
        # Verify conversation exists
        conversation_state = workflow_manager.get_conversation_state(conversation_id)
        if not conversation_state:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        if conversation_state.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this conversation")
        
        # Check if Hedra is available
        try:
            if not hedra_generator:
                raise HTTPException(
                    status_code=500, 
                    detail="Hedra API not configured. Please check HEDRA_API_KEY."
                )
        except NameError:
            raise HTTPException(
                status_code=500, 
                detail="Video generation service not available. Hedra integration required."
            )
        
        # Extract audio data and actor info
        audio_data = request.audio_data
        actor_image_filename = request.actor_image
        video_settings = request.video_settings or {}
        
        print(f"🎭 Actor image: {actor_image_filename}")
        print(f"🎵 Scripts with audio: {len(audio_data.get('scripts_with_audio', []))}")

        # Get actor image path (handles both dev and production environments)
        try:
            actor_image_path = await actor_image_handler.get_actor_image_path(actor_image_filename)
            print(f"✅ Actor image retrieved: {actor_image_path}")
        except Exception as e:
            logger.error(f"Failed to get actor image: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Actor image not available: {actor_image_filename}"
            )

        # Generate videos using Hedra (reuse V1 function)
        generated_videos_data = await hedra_generator.generate_videos_for_thread(
            thread_id=conversation_id,  # Use conversation_id as thread_id for Hedra
            audio_data=audio_data,
            actor_image_path=str(actor_image_path)
        )
        
        # Convert to V2 response format
        generated_videos = []
        for video_data in generated_videos_data:
            video = GeneratedVideoV2(
                video_id=f"{conversation_id}_{video_data.get('script_id', 'unknown')}_{video_data.get('video_type', 'combined')}",
                script_id=video_data.get('script_id', 'unknown'),
                type=video_data.get('video_type', 'combined'),
                video_url=video_data.get('video_url', ''),
                thumbnail_url=video_data.get('thumbnail_url'),
                duration=video_data.get('duration'),
                file_size=video_data.get('file_size'),
                status=video_data.get('status', 'completed'),
                processing_time=video_data.get('processing_time')
            )
            generated_videos.append(video)
        
        processing_time = time.time() - start_time
        
        # Save to database if service is available
        if db_service:
            try:
                campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
                
                if campaign:
                    # Save video files
                    for video in generated_videos:
                        await db_service.save_media(
                            campaign_id=campaign['id'],
                            media_type='video',
                            script_id=video.script_id,
                            file_url=video.video_url,
                            file_metadata={
                                'thumbnail_url': video.thumbnail_url,
                                'duration': video.duration,
                                'file_size': video.file_size,
                                'status': video.status,
                                'processing_time': video.processing_time
                            },
                            processing_time_ms=int(video.processing_time * 1000) if video.processing_time else None
                        )
                    
                    # Update campaign step to completed
                    await db_service.update_campaign_step(campaign['id'], 8, status='completed')
                    
                    print(f"💾 DEBUG: Saved video generation to database for campaign {campaign['id']}")
                    
            except Exception as db_error:
                logger.warning("database.save.error", f"Database save error: {db_error}", error=str(db_error))
                # Continue without saving
        
        response = VideoGenerationV2Response(
            conversation_id=conversation_id,
            actor_info={
                "actor_image": actor_image_filename,
                "actor_image_path": str(actor_image_path)
            },
            generated_videos=generated_videos,
            total_videos_generated=len(generated_videos),
            processing_time=processing_time,
            status="success"
        )
        
        print(f"🎉 V2 Video generation completed: {len(generated_videos)} videos in {processing_time:.2f}s")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in V2 video generation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate videos: {str(e)}")


# ==================== GET Endpoints for Back Navigation ====================

@router.get("/campaign/{conversation_id}/product-info")
async def get_product_info(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get product info for back navigation"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        product_info = await db_service.get_product_info(campaign['id'])
        
        if not product_info:
            raise HTTPException(status_code=404, detail="Product info not found")
        
        return product_info
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting product info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve product info")


@router.get("/campaign/{conversation_id}/marketing-analysis")
async def get_marketing_analysis(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get marketing analysis for back navigation"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        analysis = await db_service.get_marketing_analysis(campaign['id'])
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Marketing analysis not found")
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting marketing analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve marketing analysis")


@router.get("/campaign/{conversation_id}/hooks")
async def get_hooks(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get hooks for back navigation"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        hooks = await db_service.get_hooks(campaign['id'])
        
        if not hooks:
            raise HTTPException(status_code=404, detail="Hooks not found")
        
        return hooks
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting hooks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hooks")


@router.put("/campaign/{conversation_id}/scripts/selected")
async def update_selected_scripts(
    conversation_id: str,
    request: dict = Body(...),
    current_user: dict = Depends(verify_token)
) -> Dict:
    """Update selected scripts for a campaign"""
    user_id = current_user["user_id"]
    
    if not db_service:
        raise HTTPException(status_code=500, detail="Database service not available")
    
    try:
        # Get campaign
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Update selected scripts
        selected_scripts = request.get("selected_scripts", [])
        result = await db_service.update_selected_scripts(campaign['id'], selected_scripts)
        
        if result:
            # Update campaign step to indicate scripts are selected
            await db_service.update_campaign_step(campaign['id'], 6)
            
        return {"status": "success", "selected_scripts": selected_scripts}
        
    except Exception as e:
        print(f"❌ Error updating selected scripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaign/{conversation_id}/scripts")
async def get_scripts(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get scripts for back navigation"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        scripts = await db_service.get_scripts(campaign['id'])
        
        if not scripts:
            raise HTTPException(status_code=404, detail="Scripts not found")
        
        return scripts
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting scripts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scripts")


@router.get("/campaign/{conversation_id}/selections")
async def get_selections(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get voice and actor selections for back navigation"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        selections = await db_service.get_selections(campaign['id'])
        
        if not selections:
            raise HTTPException(status_code=404, detail="Selections not found")
        
        return selections
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting selections: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve selections")


@router.get("/campaign/{conversation_id}/audio")
async def get_audio(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get audio files for back navigation"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        audio_files = await db_service.get_media(campaign['id'], media_type='audio')
        
        return {"audio_files": audio_files}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting audio: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audio")


@router.get("/campaign/{conversation_id}/video")
async def get_video(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get video files for back navigation"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        video_files = await db_service.get_media(campaign['id'], media_type='video')
        
        return {"video_files": video_files}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting video: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve video")


@router.get("/campaign/{conversation_id}/complete")
async def get_complete_campaign(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get complete campaign data for all steps"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        complete_data = await db_service.get_complete_campaign_data(campaign['id'])
        
        return complete_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting complete campaign: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve campaign data")


# ==================== Fork Endpoint for Campaign Duplication ====================

class ForkCampaignRequest(BaseModel):
    source_campaign_id: str
    fork_from_step: int
    campaign_name: Optional[str] = None

class ForkCampaignResponse(BaseModel):
    new_conversation_id: str
    new_campaign_id: str
    campaign_name: str
    fork_from_step: int
    status: str


@router.post("/campaign/fork", response_model=ForkCampaignResponse)
async def fork_campaign(
    request: ForkCampaignRequest,
    current_user: dict = Depends(verify_token)
):
    """Fork a campaign to create a new one with data up to a specific step"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        
        # Fork the campaign
        new_conversation_id, new_campaign_id = await db_service.fork_campaign(
            source_campaign_id=request.source_campaign_id,
            user_id=user_id,
            up_to_step=request.fork_from_step,
            new_campaign_name=request.campaign_name
        )
        
        # Get the new campaign details
        new_campaign = await db_service.get_campaign_by_conversation(new_conversation_id, user_id)
        
        if not new_campaign:
            raise HTTPException(status_code=500, detail="Failed to create forked campaign")
        
        return ForkCampaignResponse(
            new_conversation_id=new_conversation_id,
            new_campaign_id=new_campaign_id,
            campaign_name=new_campaign['campaign_name'],
            fork_from_step=request.fork_from_step,
            status="success"
        )
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        print(f"Error forking campaign: {e}")
        raise HTTPException(status_code=500, detail="Failed to fork campaign")


# ==================== Campaign List Endpoint ====================

# ==================== Update Campaign Name ====================

class UpdateCampaignNameRequest(BaseModel):
    campaign_name: str

@router.patch("/campaign/{campaign_id}/name")
async def update_campaign_name(
    campaign_id: str,
    request: UpdateCampaignNameRequest,
    current_user: dict = Depends(verify_token)
):
    """Update the name of a campaign"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        
        # The campaign_id parameter could be either:
        # 1. The actual UUID (id field)
        # 2. The conversation_id field
        
        # First, check if it exists as a UUID id
        result = await db_service.supabase.table("video_ads_v2_campaigns")\
            .select("*")\
            .eq("id", campaign_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if result.data and len(result.data) > 0:
            campaign = result.data[0]
            actual_campaign_id = campaign_id
        else:
            # If not found by id, try conversation_id
            campaign = await db_service.get_campaign_by_conversation_id(campaign_id, user_id)
            if campaign:
                actual_campaign_id = campaign['id']
            else:
                raise HTTPException(status_code=404, detail=f"Campaign not found with id/conversation_id: {campaign_id}")
        
        # Update campaign name
        update_result = await db_service.supabase.table("video_ads_v2_campaigns").update({
            "campaign_name": request.campaign_name,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", actual_campaign_id).eq("user_id", user_id).execute()
        
        if not update_result.data:
            raise HTTPException(status_code=500, detail="Failed to update campaign name")
        
        return {
            "status": "success",
            "campaign_id": actual_campaign_id,
            "campaign_name": request.campaign_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating campaign name: {e}")
        raise HTTPException(status_code=500, detail="Failed to update campaign name")

# ==================== Resume Endpoints ====================

@router.get("/campaign/{conversation_id}/resume-audio")
async def get_audio_resume_data(
    conversation_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get data needed to resume at the Audio step"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        
        # Get campaign to verify ownership
        campaign = await db_service.get_campaign_by_conversation_id(conversation_id, user_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        campaign_id = campaign['id']
        
        # Get scripts data
        scripts = await db_service.get_scripts(campaign_id)
        if not scripts:
            raise HTTPException(status_code=404, detail="Scripts data not found")
        
        # Get selections (voice and actor)
        selections = await db_service.get_selections(campaign_id)
        if not selections:
            raise HTTPException(status_code=404, detail="Voice/Actor selections not found")
        
        return {
            "conversation_id": conversation_id,
            "scripts_data": scripts.get('scripts_data', {}),
            "selected_scripts": scripts.get('selected_scripts', []),
            "voice_data": selections.get('voice_data', {}),
            "actor_data": selections.get('actor_data', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting audio resume data: {e}")
        raise HTTPException(status_code=500, detail="Failed to load resume data")


@router.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    campaign_id: Optional[str] = Form(None),
    current_user: dict = Depends(verify_token)
):
    """Upload a video file to S3 and store metadata in database"""
    
    try:
        # Validate file type
        allowed_types = ['.mp4', '.mov', '.avi', '.webm']
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Validate file size (max 500MB)
        max_size = 500 * 1024 * 1024  # 500MB in bytes
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is 500MB, your file is {file_size / (1024*1024):.1f}MB"
            )
        
        # Reset file position for upload
        await file.seek(0)
        
        # Upload to S3
        user_id = current_user["user_id"]
        
        if not s3_service.enabled:
            raise HTTPException(
                status_code=503,
                detail="File upload service is not configured. Please contact support."
            )
        
        s3_url, s3_key = s3_service.upload_file_object(
            file_content,
            file.filename,
            file_type="upload",
            campaign_id=campaign_id,
            user_id=user_id
        )
        
        if not s3_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file. Please try again."
            )
        
        # Store metadata in database if database service is available
        upload_id = str(uuid.uuid4())
        metadata = {
            "upload_id": upload_id,
            "original_filename": file.filename,
            "file_size": file_size,
            "file_type": file_extension,
            "content_type": file.content_type,
            "uploaded_at": datetime.now().isoformat()
        }
        
        # Save to database if available
        if supabase:
            try:
                result = supabase.table("uploaded_media").insert({
                    "id": upload_id,
                    "user_id": user_id,
                    "campaign_id": campaign_id,
                    "file_url": s3_url,
                    "file_type": file_extension,
                    "file_size": file_size,
                    "original_filename": file.filename,
                    "s3_key": s3_key,
                    "metadata": metadata
                }).execute()
                
                logger.info("upload.video.saved", f"Video upload saved to database: {upload_id}")
            except Exception as db_error:
                logger.error("upload.video.db_error", f"Failed to save upload to database: {db_error}")
                # Continue even if database save fails - the file is uploaded to S3
        
        return {
            "status": "success",
            "upload_id": upload_id,
            "file_url": s3_url,
            "file_size": file_size,
            "filename": file.filename,
            "campaign_id": campaign_id,
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("upload.video.error", f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/campaigns")
async def get_user_campaigns(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(verify_token)
):
    """Get list of user's campaigns with V3 compatibility"""
    if not db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        campaigns = await db_service.get_user_campaigns(user_id, limit, offset)
        
        # Ensure each campaign has campaign_id for V3 compatibility
        for campaign in campaigns:
            # Use id as campaign_id if not present
            if 'campaign_id' not in campaign:
                campaign['campaign_id'] = campaign.get('id', '')
            
            # Ensure conversation_id is present for backward compatibility
            if 'conversation_id' not in campaign:
                campaign['conversation_id'] = campaign.get('campaign_id', campaign.get('id', ''))
            
            # Extract product data if nested
            if 'video_ads_v2_product_info' in campaign:
                product_info = campaign['video_ads_v2_product_info']
                if isinstance(product_info, list) and len(product_info) > 0:
                    campaign['product_data'] = product_info[0].get('product_data', {})
                elif isinstance(product_info, dict):
                    campaign['product_data'] = product_info.get('product_data', {})
        
        return {
            "campaigns": campaigns,
            "total": len(campaigns),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"Error getting user campaigns: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve campaigns")
