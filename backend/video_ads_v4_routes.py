"""
Video Ads V4 Routes - Fresh implementation for new workflow
"""

import os
import json
import uuid
import aiohttp
import openai
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any
from dotenv import load_dotenv

# Import auth and database
from auth import verify_token
from video_ads_v3_database_service import v3_db_service
from claude_service import ClaudeService
from logging_service import logger
# Facebook targeting mapper removed - stub function for compatibility
def map_avatar_to_facebook_targeting(avatar_data: dict) -> dict:
    """Stub function - Facebook integration removed"""
    return {
        "locations": avatar_data.get("locations", ["United States"]),
        "age_min": avatar_data.get("age_min", 25),
        "age_max": avatar_data.get("age_max", 55),
        "gender": avatar_data.get("gender", "all"),
        "interests": avatar_data.get("interests", []),
        "job_titles": avatar_data.get("job_titles", []),
    }

# Import models (we can create V4 specific models later if needed)
from video_ads_v2_models import VideoAdsProductInfoV2, URLParseV2Response

# Import for loading YAML prompts
import yaml
from pathlib import Path

load_dotenv()

# Initialize services
claude_service = ClaudeService()

# Initialize OpenAI client for URL parsing
openai_client = None
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    openai_client = openai.OpenAI(api_key=api_key)

# Create router with V4 prefix
router = APIRouter(prefix="/video-ads-v4", tags=["video-ads-v4"])


# ==================== URL Parsing (V4) ====================

@router.post("/parse-url", response_model=URLParseV2Response)
async def parse_url_v4(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Parse URL and extract product information (V4)"""

    url = request.get("url")
    campaign_id = request.get("campaign_id")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        user_id = current_user["user_id"]

        # Create campaign if not provided
        if not campaign_id:
            campaign = await v3_db_service.create_campaign(
                user_id=user_id,
                campaign_name=f"V4 Campaign - {url[:50]}",
                product_url=url
            )
            campaign_id = campaign["campaign_id"] if campaign else str(uuid.uuid4())
            logger.debug("v4.parse_url.campaign.created", f"Created campaign: {campaign_id}")

        # Fetch and parse URL content
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                html_content = await response.text()

        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract text content
        for script in soup(["script", "style"]):
            script.decompose()
        text_content = soup.get_text(separator='\n', strip=True)

        # Limit content length
        max_chars = 8000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "..."

        # Use OpenAI to extract product info
        product_info = {}

        if openai_client:
            prompt = f"""Extract product information from this webpage content.
            Return a JSON object with the following fields:
            - product_name: the name of the product
            - product_information: detailed description of what the product does
            - target_audience: who the product is for
            - price: the price if mentioned (or "Not specified")
            - problem_solved: what problem or pain point it solves
            - differentiation: what makes it unique compared to competitors
            - additional_information: any other relevant details

            Content: {text_content[:5000]}"""

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000
            )

            raw_info = json.loads(response.choices[0].message.content)
            logger.debug("v4.parse_url.openai.response", f"OpenAI parsed info: {raw_info}")

            # Handle additional_information which might be a dict or string
            additional_info = raw_info.get("additional_information", "")
            if isinstance(additional_info, dict):
                additional_info = json.dumps(additional_info, indent=2)

            # Map to our expected structure
            product_info = {
                "product_name": raw_info.get("product_name", ""),
                "product_information": raw_info.get("product_information", ""),
                "target_audience": raw_info.get("target_audience", ""),
                "price": raw_info.get("price", "Not specified"),
                "problem_solved": raw_info.get("problem_solved", ""),
                "differentiation": raw_info.get("differentiation", ""),
                "additional_information": additional_info,
                "product_url": url
            }
        else:
            # Fallback if OpenAI is not available
            title = soup.find('title')
            product_info = {
                "product_name": title.string if title else "Product",
                "product_information": text_content[:500],
                "target_audience": "",
                "price": "Not specified",
                "problem_solved": "",
                "differentiation": "",
                "additional_information": "",
                "product_url": url
            }

        # Save to database
        success = await v3_db_service.save_product_info(campaign_id, product_info)
        logger.debug("v4.parse_url.saved", f"Saved product info: {success}")

        # Return with fields at root level as expected by URLParseV2Response
        return URLParseV2Response(
            product_name=product_info["product_name"],
            product_information=product_info["product_information"],
            target_audience=product_info["target_audience"],
            price=product_info["price"],
            problem_solved=product_info["problem_solved"],
            differentiation=product_info["differentiation"],
            additional_information=product_info["additional_information"],
            campaign_id=campaign_id,
            conversation_id=campaign_id,  # Legacy support
            original_url=url
        )

    except aiohttp.ClientError as e:
        logger.error("v4.parse_url.fetch.error", f"Error fetching URL: {e}")
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {str(e)}")
    except Exception as e:
        logger.error("v4.parse_url.error", f"Error parsing URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Product Info (V4) ====================

@router.post("/product-info")
async def save_product_info_v4(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Save product information (V4)"""

    campaign_id = request.get("campaign_id")
    product_data = request.get("product_data") or request.get("product_info")

    if not campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id is required")

    if not product_data:
        raise HTTPException(status_code=400, detail="product_data is required")

    try:
        user_id = current_user["user_id"]

        # Verify campaign ownership
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Save product info
        success = await v3_db_service.save_product_info(campaign_id, product_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save product info")

        logger.debug("v4.product_info.saved", f"Saved product info for campaign: {campaign_id}")

        return {
            "campaign_id": campaign_id,
            "status": "saved",
            "message": "Product information saved successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("v4.product_info.error", f"Error saving product info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== V4 Marketing Research Endpoint ====================

def load_prompt_template(prompt_name: str) -> Dict[str, Any]:
    """Load a YAML prompt template"""
    prompts_dir = Path(__file__).parent / "prompts_v2"
    yaml_file = prompts_dir / f"{prompt_name}.yaml"

    if not yaml_file.exists():
        logger.error("v4.prompt.not_found", f"Prompt template not found: {prompt_name}")
        return {}

    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error("v4.prompt.load_error", f"Error loading prompt {prompt_name}: {e}")
        return {}


async def process_marketing_research_background(campaign_id: str, product_info: Dict[str, Any]):
    """Background task to process marketing research and generate hooks/scripts using regular API calls"""

    # Import mock data flags at function level for easy toggling
    from load_mock_data import USE_MOCK_DATA, SKIP_TO_SCRIPTS

    try:
        # Update status to processing
        await v3_db_service.update_campaign_status(campaign_id, "processing")
        logger.info("v4.background.start", f"Starting background processing for campaign: {campaign_id}")

        # Convert product_info dict to model
        product_model = VideoAdsProductInfoV2(**product_info)

        # Check if we're using mock data or generating real data
        if USE_MOCK_DATA:
            # Skip 4-phase generation and use mock data
            from load_mock_data import load_mock_angles, load_mock_avatars, load_mock_journey, load_mock_objections
            logger.info("v4.mock_data.enabled", "Using mock data for 4 phases - skipping generation")

            avatars = load_mock_avatars()
            journey = load_mock_journey()
            objections = load_mock_objections()
            angles_list = load_mock_angles()

            # Create a mock angles object for compatibility
            class MockAngles:
                def __init__(self, angles_list):
                    self.positive_angles = [a for a in angles_list if a.type == 'positive']
                    self.negative_angles = [a for a in angles_list if a.type == 'negative']
                def model_dump(self):
                    return {
                        'positive_angles': [a.model_dump() if hasattr(a, 'model_dump') else a for a in self.positive_angles],
                        'negative_angles': [a.model_dump() if hasattr(a, 'model_dump') else a for a in self.negative_angles]
                    }

            angles = MockAngles(angles_list)

        else:
            # Normal flow - generate all 4 phases
            # Phase 1: Avatar Analysis
            await v3_db_service.update_campaign_status(campaign_id, "analyzing_avatar")
            avatars = await claude_service.generate_avatar_analysis(product_model)
            logger.debug("v4.background.avatars.generated", f"Generated avatars for campaign: {campaign_id}")

            # Phase 2: Journey Mapping
            await v3_db_service.update_campaign_status(campaign_id, "analyzing_journey")
            journey = await claude_service.generate_journey_mapping(product_model, avatars)
            logger.debug("v4.background.journey.generated", f"Generated journey for campaign: {campaign_id}")

            # Phase 3: Objections Analysis
            await v3_db_service.update_campaign_status(campaign_id, "analyzing_objections")
            objections = await claude_service.generate_objections_analysis(product_model, avatars, journey)
            logger.debug("v4.background.objections.generated", f"Generated objections for campaign: {campaign_id}")

            # Phase 4: Angles Generation
            await v3_db_service.update_campaign_status(campaign_id, "generating_angles")
            angles = await claude_service.generate_angles(product_model, avatars, journey, objections)
            logger.debug("v4.background.angles.generated", f"Generated angles for campaign: {campaign_id}")

            # Convert angles to list
            from video_ads_v2_models import MarketingAngleV2
            angles_list = []
            if hasattr(angles, 'positive_angles'):
                angles_list.extend(angles.positive_angles)
            if hasattr(angles, 'negative_angles'):
                angles_list.extend(angles.negative_angles)

        # Save to database
        analysis_data = {
            "avatars": avatars.model_dump() if hasattr(avatars, 'model_dump') else avatars,
            "journey": journey.model_dump() if hasattr(journey, 'model_dump') else journey,
            "objections": objections.model_dump() if hasattr(objections, 'model_dump') else objections,
            "angles": angles.model_dump() if hasattr(angles, 'model_dump') else angles
        }

        success = await v3_db_service.save_marketing_analysis(campaign_id, analysis_data)
        logger.debug("v4.background.analysis.saved", f"Saved analysis for campaign: {campaign_id}, success: {success}")

        # ===== Generate Hooks using Regular API =====
        # Skip if we're jumping directly to scripts
        if not SKIP_TO_SCRIPTS:
            logger.info("v4.background.hooks.start", f"Starting hooks generation - campaign: {campaign_id}")
            await v3_db_service.update_campaign_status(campaign_id, "generating_hooks")

            # Generate all hooks in one API call
            hooks_by_angle = await claude_service.generate_hooks(
                product_info=product_model,
                selected_angles=angles_list,
                avatar_analysis=avatars,
                journey_mapping=journey,
                objections_analysis=objections
            )

            # Convert hooks to dict format for storage
            hooks_data = []
            for hook_angle in hooks_by_angle:
                if hasattr(hook_angle, 'model_dump'):
                    hooks_data.append(hook_angle.model_dump())
                else:
                    hooks_data.append(hook_angle)

            # Save hooks to database
            await v3_db_service.save_hooks(campaign_id, hooks_data)
            logger.info("v4.background.hooks.complete",
                       f"Generated {len(hooks_data)} angle-hook sets for campaign: {campaign_id}")
        else:
            # Skip hooks generation and load mock hooks data
            logger.info("v4.mock_data.skip_hooks", "Skipping hooks generation - will use mock hooks data")
            hooks_data = None  # Will be loaded later when needed for scripts

        # ===== Generate Scripts using Regular API =====
        logger.info("v4.background.scripts.start", f"Starting scripts generation - campaign: {campaign_id}")
        await v3_db_service.update_campaign_status(campaign_id, "generating_scripts")

        # OPTIONAL: Skip directly to scripts with mock hooks data
        # SKIP_TO_SCRIPTS is imported at the top of the function
        if SKIP_TO_SCRIPTS and hooks_data is None:
            from load_mock_data import load_mock_hooks_data
            logger.info("v4.mock_data.skip_to_scripts", "Skipping to scripts generation with mock hooks data")
            hooks_data = load_mock_hooks_data()

        # Generate all scripts in one API call
        scripts_result = await claude_service.generate_scripts(
            product_info=product_model,
            hooks_by_angle=hooks_data,
            avatar_analysis=avatars,
            journey_mapping=journey,
            objections_analysis=objections
        )

        # Save scripts to database
        await v3_db_service.save_scripts(campaign_id, scripts_result)
        logger.info("v4.background.scripts.complete",
                   f"Generated scripts for campaign: {campaign_id}")

        # Update campaign status to completed
        await v3_db_service.update_campaign_status(campaign_id, "completed")
        logger.info("v4.background.complete",
                   f"Campaign {campaign_id} processing complete. Hooks and scripts generated successfully.")

    except Exception as e:
        # Update status to failed with error message
        error_msg = str(e)
        await v3_db_service.update_campaign_status(campaign_id, "failed", error_msg)
        logger.error("v4.background.error", f"Error processing campaign {campaign_id}: {e}", error=error_msg)



async def process_marketing_research_background_backup(campaign_id: str, product_info: Dict[str, Any]):
    """Background task to process marketing research and generate hooks/scripts using regular API calls"""
    try:
        # Update status to processing
        await v3_db_service.update_campaign_status(campaign_id, "processing")
        logger.info("v4.background.start", f"Starting background processing for campaign: {campaign_id}")

        # Convert product_info dict to model
        product_model = VideoAdsProductInfoV2(**product_info)

        # Phase 1: Avatar Analysis
        avatars = await claude_service.generate_avatar_analysis(product_model)
        logger.debug("v4.background.avatars.generated", f"Generated avatars for campaign: {campaign_id}")

        # Phase 2: Journey Mapping
        journey = await claude_service.generate_journey_mapping(product_model, avatars)
        logger.debug("v4.background.journey.generated", f"Generated journey for campaign: {campaign_id}")

        # Phase 3: Objections Analysis
        objections = await claude_service.generate_objections_analysis(product_model, avatars, journey)
        logger.debug("v4.background.objections.generated", f"Generated objections for campaign: {campaign_id}")

        # Phase 4: Angles Generation
        angles = await claude_service.generate_angles(product_model, avatars, journey, objections)
        logger.debug("v4.background.angles.generated", f"Generated angles for campaign: {campaign_id}")

        # Save to database
        analysis_data = {
            "avatars": avatars.model_dump(),
            "journey": journey.model_dump(),
            "objections": objections.model_dump(),
            "angles": angles.model_dump()
        }

        success = await v3_db_service.save_marketing_analysis(campaign_id, analysis_data)
        logger.debug("v4.background.analysis.saved", f"Saved analysis for campaign: {campaign_id}, success: {success}")

        # ===== Generate Hooks using Regular API =====
        logger.info("v4.background.hooks.start", f"Starting hooks generation - campaign: {campaign_id}")
        await v3_db_service.update_campaign_status(campaign_id, "generating_hooks")

        # Convert angles to list of MarketingAngleV2 models
        from video_ads_v2_models import MarketingAngleV2
        angles_list = []
        if hasattr(angles, 'positive_angles'):
            angles_list.extend(angles.positive_angles)
        if hasattr(angles, 'negative_angles'):
            angles_list.extend(angles.negative_angles)

        # Generate all hooks in one API call
        hooks_by_angle = await claude_service.generate_hooks(
            product_info=product_model,
            selected_angles=angles_list,
            avatar_analysis=avatars,
            journey_mapping=journey,
            objections_analysis=objections
        )

        # Convert hooks to dict format for storage
        hooks_data = []
        for hook_angle in hooks_by_angle:
            if hasattr(hook_angle, 'model_dump'):
                hooks_data.append(hook_angle.model_dump())
            else:
                hooks_data.append(hook_angle)

        # Save hooks to database
        await v3_db_service.save_hooks(campaign_id, hooks_data)
        logger.info("v4.background.hooks.complete",
                   f"Generated {len(hooks_data)} angle-hook sets for campaign: {campaign_id}")

        # ===== Generate Scripts using Regular API =====
        logger.info("v4.background.scripts.start", f"Starting scripts generation - campaign: {campaign_id}")
        await v3_db_service.update_campaign_status(campaign_id, "generating_scripts")

        # OPTIONAL: Skip directly to scripts with mock hooks data
        # SKIP_TO_SCRIPTS is imported at the top of the function
        if SKIP_TO_SCRIPTS and hooks_data is None:
            from load_mock_data import load_mock_hooks_data
            logger.info("v4.mock_data.skip_to_scripts", "Skipping to scripts generation with mock hooks data")
            hooks_data = load_mock_hooks_data()

        # Generate all scripts in one API call
        scripts_result = await claude_service.generate_scripts(
            product_info=product_model,
            hooks_by_angle=hooks_data,
            avatar_analysis=avatars,
            journey_mapping=journey,
            objections_analysis=objections
        )

        # Save scripts to database
        await v3_db_service.save_scripts(campaign_id, scripts_result)
        logger.info("v4.background.scripts.complete",
                   f"Generated scripts for campaign: {campaign_id}")

        # Update campaign status to completed
        await v3_db_service.update_campaign_status(campaign_id, "completed")
        logger.info("v4.background.complete",
                   f"Campaign {campaign_id} processing complete. Hooks and scripts generated successfully.")

    except Exception as e:
        # Update status to failed with error message
        error_msg = str(e)
        await v3_db_service.update_campaign_status(campaign_id, "failed", error_msg)
        logger.error("v4.background.error", f"Error processing campaign {campaign_id}: {e}", error=error_msg)


@router.post("/create-marketing-research", status_code=202)
async def create_marketing_research_v4(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(verify_token)
):
    """
    V4 Marketing Research - Async background processing
    Returns immediately with 202 Accepted, processes in background
    """

    try:
        user_id = current_user["user_id"]
        campaign_id = request.get("campaign_id")

        if not campaign_id:
            raise HTTPException(status_code=400, detail="campaign_id is required")

        # Verify campaign ownership
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Get product info from database
        content = await v3_db_service.get_campaign_content(campaign_id)
        if not content or not content.get("product_data"):
            raise HTTPException(status_code=400, detail="Product information not found for campaign")

        product_info = content["product_data"]

        # Set status to pending
        await v3_db_service.update_campaign_status(campaign_id, "pending")
        logger.info("v4.marketing.research.queued", f"Campaign {campaign_id} queued for processing")

        # Add background task
        background_tasks.add_task(process_marketing_research_background, campaign_id, product_info)

        # Return immediately with 202 Accepted
        return {
            "campaign_id": campaign_id,
            "status": "pending",
            "message": "Campaign is being processed. Check status in Campaign List."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("v4.marketing.research.error", f"Error queuing campaign: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== V4 Generation Status Endpoints ====================


# ==================== V4 Campaign Management ====================

@router.get("/campaigns")
async def get_campaigns_v4(
    status: str = None,
    current_user: dict = Depends(verify_token)
):
    """Get all V4 campaigns for the user, optionally filtered by status"""
    try:
        user_id = current_user["user_id"]
        campaigns = await v3_db_service.get_user_campaigns(user_id)

        # Apply status filter if provided
        if status:
            campaigns = [c for c in campaigns if c.get("status") == status]

        # Add counts for angles, hooks, scripts if available
        for campaign in campaigns:
            try:
                content = await v3_db_service.get_campaign_content(campaign["campaign_id"])

                # Count angles
                campaign["angle_count"] = len(content.get("hooks", [])) if content.get("hooks") else 0

                # Count hooks (flatten hooks_by_category)
                campaign["hook_count"] = 0
                if content.get("hooks"):
                    for angle in content.get("hooks", []):
                        if angle.get("hooks_by_category") and isinstance(angle.get("hooks_by_category"), dict):
                            for category_hooks in angle["hooks_by_category"].values():
                                if isinstance(category_hooks, list):
                                    campaign["hook_count"] += len(category_hooks)

                # Count scripts
                campaign["script_count"] = 0
                if content.get("scripts") and isinstance(content["scripts"], list) and len(content["scripts"]) > 0:
                    scripts_data = content["scripts"][0]
                    if scripts_data.get("angles"):
                        for angle in scripts_data["angles"]:
                            if angle.get("hooks"):
                                for hook in angle["hooks"]:
                                    campaign["script_count"] += len(hook.get("scripts", []))
            except Exception as e:
                logger.warning("v4.campaigns.counts.error", f"Error calculating counts for campaign {campaign.get('campaign_id')}: {e}")
                # Set default counts if calculation fails
                campaign["angle_count"] = 0
                campaign["hook_count"] = 0
                campaign["script_count"] = 0

        return campaigns
    except Exception as e:
        logger.error("v4.campaigns.list.error", f"Error listing V4 campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaign/{campaign_id}")
async def get_campaign_v4(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get V4 campaign details with content"""
    try:
        user_id = current_user.get("user_id")

        # Get campaign (with dev-token support)
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Get campaign content (angles, hooks, scripts)
        # Note: scripts are stored as restructured format with angle_id/hook_id expanded
        # from the minimal flat array returned by Claude for smaller response size
        content = await v3_db_service.get_campaign_content(campaign_id)

        # Add content to campaign response
        campaign["content"] = content or {}

        logger.debug(f"v4.campaign.get.success",
                    f"Retrieved campaign {campaign_id} with content. "
                    f"Has angles: {bool(content and content.get('angles'))}, "
                    f"Has hooks: {bool(content and content.get('hooks'))}, "
                    f"Has scripts: {bool(content and content.get('scripts'))}")

        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.error("v4.campaign.get.error", f"Error getting V4 campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Facebook Targeting ====================

@router.get("/campaign/{campaign_id}/targeting")
async def get_campaign_targeting(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get pre-filled Facebook targeting based on avatar analysis"""
    try:
        user_id = current_user.get("user_id")

        # Get campaign
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Get avatar analysis
        content = await v3_db_service.get_campaign_content(campaign_id)
        avatar_data = content.get("avatar_analysis")

        if not avatar_data:
            logger.warning("v4.targeting.no_avatar", f"No avatar data for campaign {campaign_id}")
            # Return defaults if no avatar data
            return {
                "locations": ["United States"],
                "age_min": 25,
                "age_max": 55,
                "gender": "all",
                "interests": ["Entrepreneurship", "Business"],
                "job_titles": [],
            }

        # Map avatar data to targeting
        targeting = map_avatar_to_facebook_targeting(avatar_data)

        logger.info("v4.targeting.success", f"Mapped targeting for campaign {campaign_id}")
        return targeting

    except HTTPException:
        raise
    except Exception as e:
        logger.error("v4.targeting.error", f"Error getting targeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaign/{campaign_id}/ai-targeting-recommendations")
async def get_ai_targeting_recommendations(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get AI-powered targeting recommendations from Claude"""
    try:
        user_id = current_user.get("user_id")

        # Get campaign
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)

        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Get campaign content
        content = await v3_db_service.get_campaign_content(campaign_id)
        avatar_data = content.get("avatar_analysis")
        journey_data = content.get("journey_mapping")

        if not avatar_data:
            raise HTTPException(status_code=400, detail="Campaign must have avatar analysis for AI recommendations")

        # Load prompt template
        prompt_path = Path(__file__).parent / "prompts_v2" / "targeting_recommendations.yaml"
        with open(prompt_path, 'r') as f:
            prompt_config = yaml.safe_load(f)

        # Prepare data for prompt
        avatar_text = json.dumps(avatar_data, indent=2)
        journey_text = json.dumps(journey_data, indent=2) if journey_data else "No journey data available"

        # Format prompt
        user_prompt = prompt_config['user_prompt'].format(
            product_name=campaign.get('campaign_name', 'Product'),
            product_url=campaign.get('product_url', ''),
            avatar_analysis=avatar_text,
            journey_mapping=journey_text
        )

        # Call Claude
        logger.info("v4.ai_targeting.calling_claude", f"Requesting AI targeting for campaign {campaign_id}")

        response = await claude_service._send_message(
            system_prompt=prompt_config['system_prompt'],
            user_prompt=user_prompt,
            max_tokens=8000
        )

        # Parse response
        clean_response = claude_service._clean_json_response(response)
        recommendations = json.loads(clean_response)

        logger.info("v4.ai_targeting.success", f"Generated AI targeting recommendations for campaign {campaign_id}")
        return recommendations

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error("v4.ai_targeting.json_error", f"Failed to parse Claude response: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse AI recommendations")
    except Exception as e:
        logger.error("v4.ai_targeting.error", f"Error getting AI recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


