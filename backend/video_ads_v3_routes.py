"""
Video Ads V3 Routes - Stateless Implementation with V3 Database
"""

import os
import json
import time
import openai
import aiohttp
import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Body, UploadFile, File, Form
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, List, Any, Union
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Import auth and database
from auth import verify_token, supabase
from video_ads_v3_database_service import v3_db_service
from actor_image_handler import actor_image_handler
from campaign_v3_manager import campaign_v3_manager
from claude_service import ClaudeService
from logging_service import logger

# Import models (reuse V2 models for now)
from video_ads_v2_models import (
    MarketingAnalysisV2Request, MarketingAnalysisV2Response,
    MarketingAnglesV2Response, VideoAdsProductInfoV2, URLParseV2Response,
    HooksV2Request, HooksV2Response,
    VoiceActorV2Request, VoiceActorV2Response,
    AudioGenerationV2Request, AudioGenerationV2Response,
    VideoGenerationV2Request, VideoGenerationV2Response,
    ElevenLabsVoice, ActorImage, GeneratedAudioV2, ScriptWithAudioV2, GeneratedVideoV2,
    # Document models
    DocumentUpload, DocumentUploadResponse, MarketingAnalysisV2RequestWithDocs
)

# Import shared functions from V1/V2
try:
    from video_ads_routes import (
        fetch_elevenlabs_voices, get_actor_images, 
        generate_audio_with_elevenlabs, hedra_generator
    )
except ImportError as e:
    logger.warning("import.video_ads_routes.failed", f"Could not import from video_ads_routes: {e}")

load_dotenv()

# Import S3 service
from s3_service import s3_service

# Initialize OpenAI client for URL parsing
openai_client = None
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    openai_client = openai.OpenAI(api_key=api_key)

# Initialize Claude service (simplified, stateless)
claude_service = ClaudeService()

# Create router with V3 prefix (keeping same URL structure for easy migration)
router = APIRouter(prefix="/video-ads-v2", tags=["video-ads-v3"])

# ==================== Health Check ====================

@router.get("/health")
async def video_ads_v3_health():
    """Health check for video ads V3 service"""
    return {
        "status": "healthy",
        "service": "video-ads-v3",
        "version": "3.0.0",
        "features": {
            "stateless": True,
            "multi_video": True,
            "database": "v3_tables"
        },
        "claude_available": claude_service.client.client is not None,
        "openai_available": openai_client is not None,
        "database_available": v3_db_service.supabase is not None
    }

# ==================== Campaign Management ====================

@router.post("/create-campaign")
async def create_campaign(
    product_url: Optional[str] = None,
    campaign_name: Optional[str] = None,
    current_user: dict = Depends(verify_token)
):
    """Create a new campaign (V3 stateless)"""
    try:
        user_id = current_user["user_id"]
        
        # Create campaign in database
        campaign = await v3_db_service.create_campaign(
            user_id=user_id,
            campaign_name=campaign_name,
            product_url=product_url
        )
        
        if not campaign:
            # Fallback if database is unavailable
            campaign_id = str(uuid.uuid4())
            logger.debug("campaign.create.fallback", f"Using fallback campaign_id: {campaign_id}, user_id: {user_id}")
            logger.warning("campaign.create.db_unavailable", f"Created campaign without DB: {campaign_id}")
            return {"campaign_id": campaign_id, "status": "created_without_db"}
        
        logger.debug("campaign.created", f"Created campaign: {campaign}")
        logger.info("campaign.created", f"Created V3 campaign: {campaign['campaign_id']}", 
                   campaign_id=campaign["campaign_id"], user_id=user_id)
        
        return {
            "campaign_id": campaign["campaign_id"],
            "campaign_name": campaign.get("campaign_name"),
            "status": "created"
        }
        
    except Exception as e:
        logger.error("campaign.create.error", f"Error creating campaign: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== URL Parsing (Stateless) ====================

@router.post("/parse-url", response_model=URLParseV2Response)
async def parse_url_v3(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Parse URL and extract product information (V3 stateless)"""
    
    url = request.get("url")
    campaign_id = request.get("campaign_id") or request.get("conversation_id")
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        user_id = current_user["user_id"]
        
        # Create campaign if not provided
        if not campaign_id:
            campaign = await v3_db_service.create_campaign(user_id=user_id, product_url=url)
            campaign_id = campaign["campaign_id"] if campaign else str(uuid.uuid4())
            logger.debug("parse_url.campaign.created", f"Created new campaign for URL parsing: campaign_id: {campaign_id}, url: {url}")
        
        # Fetch and parse URL content (same logic as V2)
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
            logger.debug("parse_url.openai.response", f"OpenAI parsed info: {raw_info}")
            
            # Handle additional_information which might be a dict or string
            additional_info = raw_info.get("additional_information", "")
            if isinstance(additional_info, dict):
                # Convert dict to a formatted string
                additional_info = json.dumps(additional_info, indent=2)
            elif not isinstance(additional_info, str):
                additional_info = str(additional_info)
            
            # Transform to match expected format
            product_info = {
                "product_name": raw_info.get("product_name", raw_info.get("name", "Unknown Product")),
                "product_information": raw_info.get("product_information", raw_info.get("description", "")),
                "target_audience": raw_info.get("target_audience", "General audience"),
                "price": str(raw_info.get("price", "Not specified")),  # Ensure price is string
                "problem_solved": raw_info.get("problem_solved", ", ".join(raw_info.get("pain_points", [])) if raw_info.get("pain_points") else "Various challenges"),
                "differentiation": raw_info.get("differentiation", ", ".join(raw_info.get("unique_selling_points", [])) if raw_info.get("unique_selling_points") else "Quality and value"),
                "additional_information": additional_info
            }
        else:
            # Fallback extraction
            title = soup.find('title')
            product_info = {
                "product_name": title.string if title else "Unknown Product",
                "product_information": text_content[:500],
                "target_audience": "General audience",
                "price": "Not specified",
                "problem_solved": "Various challenges",
                "differentiation": "Quality, Value, Innovation",
                "additional_information": ""
            }
        
        # Save to database
        if v3_db_service.supabase:
            success = await v3_db_service.save_product_info(campaign_id, product_info)
            logger.debug("parse_url.product_info.saved", f"Saved parsed product info for campaign: {campaign_id}, product_info: {product_info}, success: {success}")
        
        # Return in the format expected by URLParseV2Response
        return URLParseV2Response(
            product_name=product_info["product_name"],
            product_information=product_info["product_information"],
            target_audience=product_info["target_audience"],
            price=product_info["price"],
            problem_solved=product_info["problem_solved"],
            differentiation=product_info["differentiation"],
            additional_information=product_info["additional_information"],
            # Legacy fields
            key_benefits=[],
            unique_selling_points=[],
            # V3 fields
            campaign_id=campaign_id,
            conversation_id=campaign_id,  # For compatibility
            original_url=url
        )
        
    except aiohttp.ClientError as e:
        logger.error("url.parse.fetch_error", f"Error fetching URL content: {e}", error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL content. Please check if the URL is valid and accessible.")
    except json.JSONDecodeError as e:
        logger.error("url.parse.json_error", f"Error parsing OpenAI response: {e}", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to parse product information from the URL.")
    except ValidationError as e:
        logger.error("url.parse.validation_error", f"Validation error: {e}", error=str(e))
        raise HTTPException(status_code=500, detail="Product information format error. Please try manual entry.")
    except Exception as e:
        logger.error("url.parse.error", f"Unexpected error parsing URL: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# ==================== Product Info (Stateless) ====================

@router.post("/product-info")
async def save_product_info_v3(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Save product information (V3 stateless)"""
    
    campaign_id = request.get("campaign_id") or request.get("conversation_id")
    product_data = request.get("product_data") or request.get("productInfo")
    
    if not campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id is required")
    
    if not product_data:
        raise HTTPException(status_code=400, detail="product_data is required")
    
    try:
        user_id = current_user["user_id"]
        
        # Verify campaign ownership
        campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        if not campaign:
            # Create campaign if it doesn't exist
            campaign = await v3_db_service.create_campaign(user_id=user_id)
            campaign_id = campaign["campaign_id"]
        
        # Save product info
        print(f"🔍 About to save product info for campaign: {campaign_id}")
        success = await v3_db_service.save_product_info(campaign_id, product_data)
        print(f"🔍 Save product info result: {success}")
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save product info")
        
        logger.debug("product.info.save", f"saved product info for campaign: {campaign_id}, product_data:{product_data}")
        
        return {
            "campaign_id": campaign_id,
            "status": "saved",
            "message": "Product information saved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("product.info.save.error", f"Error saving product info: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Document Upload ====================

@router.post("/upload-documents", response_model=DocumentUploadResponse)
async def upload_documents_v3(
    files: List[UploadFile] = File(...),
    campaign_id: str = Form(...),
    current_user: dict = Depends(verify_token)
):
    """
    Upload multiple documents (PDF, images, etc.) to S3 for product analysis enhancement.
    Supports: PDF (32MB max), PNG, JPG, JPEG, DOCX, PPTX
    """
    user_id = current_user["user_id"]
    logger.set_context(user_id=user_id, campaign_id=campaign_id)

    logger.info(
        "api.documents.upload.started",
        f"Starting document upload for campaign {campaign_id}",
        file_count=len(files)
    )

    # Check if campaign_id is temporary (starts with "temp_")
    if campaign_id.startswith("temp_"):
        # Create a new campaign for document storage in v3 table
        # Note: v3 table has both 'id' and 'campaign_id' fields
        campaign_data = {
            "user_id": str(user_id),  # Ensure user_id is string for database
            "campaign_name": f"Document Upload - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "status": "draft"
        }
        result = supabase.table("video_ads_v3_campaigns").insert(campaign_data).execute()
        if result.data:
            # Use the campaign_id field (not id) from v3 table
            campaign_id = result.data[0]['campaign_id'] if 'campaign_id' in result.data[0] else result.data[0]['id']
            logger.info(
                "api.documents.upload.campaign_created",
                f"Created new campaign for document upload in v3 table",
                new_campaign_id=campaign_id
            )
    else:
        # Verify the campaign exists and belongs to the user in v3 table
        # Check both 'id' and 'campaign_id' fields since v3 has both
        campaign_check = supabase.table("video_ads_v3_campaigns").select("id,campaign_id").or_(f"id.eq.{str(campaign_id)},campaign_id.eq.{str(campaign_id)}").eq("user_id", str(user_id)).execute()
        if not campaign_check.data:
            raise HTTPException(
                status_code=400,
                detail=f"Campaign {campaign_id} not found or does not belong to user"
            )
        # Use the campaign_id field from the result (not the id field)
        # This ensures we're using the correct UUID that the foreign key expects
        campaign_id = campaign_check.data[0]['campaign_id']

    # Validate file types and sizes
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'pptx', 'doc', 'ppt', 'txt'}
    MAX_FILE_SIZE = 32 * 1024 * 1024  # 32MB (Claude's limit)

    uploaded_documents = []

    for file in files:
        try:
            # Get file extension
            file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''

            if file_extension not in ALLOWED_EXTENSIONS:
                logger.warning(
                    "api.documents.upload.invalid_type",
                    f"Skipping file {file.filename} - unsupported type",
                    file_type=file_extension
                )
                continue

            # Read file content
            file_content = await file.read()
            file_size = len(file_content)

            if file_size > MAX_FILE_SIZE:
                logger.warning(
                    "api.documents.upload.file_too_large",
                    f"Skipping file {file.filename} - exceeds 32MB limit",
                    file_size=file_size
                )
                continue

            # Generate S3 key
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = file.filename.replace(' ', '_').replace('/', '_')
            s3_key = f"documents/{user_id}/{campaign_id}/{timestamp}_{safe_filename}"

            # Check if S3 service is enabled
            if not s3_service.enabled:
                logger.error(
                    "api.documents.upload.s3_disabled",
                    f"S3 service is disabled - missing AWS credentials",
                    filename=file.filename
                )
                continue

            # Upload to S3
            s3_url = s3_service.upload_file_from_bytes(
                file_content=file_content,
                s3_key=s3_key,
                content_type=file.content_type or f'application/{file_extension}'
            )

            if not s3_url:
                logger.error(
                    "api.documents.upload.s3_failed",
                    f"Failed to upload {file.filename} to S3 - check AWS permissions",
                    filename=file.filename,
                    s3_key=s3_key
                )
                continue

            # Store metadata in database
            document_data = {
                "campaign_id": str(campaign_id),  # Ensure string for database
                "user_id": str(user_id),  # Ensure string for database
                "file_name": file.filename,
                "file_type": file_extension,
                "file_size": file_size,
                "mime_type": file.content_type,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "upload_status": "completed",
                "file_metadata": {
                    "original_filename": file.filename,
                    "upload_timestamp": timestamp
                }
            }

            logger.info(
                "api.documents.inserting",
                f"Inserting document with campaign_id: {campaign_id}",
                campaign_id=str(campaign_id),
                user_id=str(user_id)
            )

            result = supabase.table("video_ads_v2_documents").insert(document_data).execute()

            if result.data:
                uploaded_doc = DocumentUpload(
                    id=result.data[0]['id'],
                    campaign_id=campaign_id,
                    file_name=file.filename,
                    file_type=file_extension,
                    file_size=file_size,
                    mime_type=file.content_type,
                    s3_url=s3_url,
                    s3_key=s3_key,
                    upload_status="completed",
                    created_at=result.data[0]['created_at']
                )
                uploaded_documents.append(uploaded_doc)

                logger.info(
                    "api.documents.upload.success",
                    f"Successfully uploaded {file.filename}",
                    s3_url=s3_url,
                    file_size=file_size
                )

        except Exception as e:
            logger.error(
                "api.documents.upload.file_error",
                f"Error uploading file {file.filename}",
                exception=e,
                filename=file.filename
            )
            continue

    logger.info(
        "api.documents.upload.completed",
        f"Document upload completed for campaign {campaign_id}",
        uploaded_count=len(uploaded_documents),
        total_files=len(files)
    )

    return DocumentUploadResponse(
        success=len(uploaded_documents) > 0,
        campaign_id=campaign_id,  # Return the actual campaign_id (important if temp_id was converted)
        documents=uploaded_documents,
        total_uploaded=len(uploaded_documents),
        message=f"Successfully uploaded {len(uploaded_documents)} of {len(files)} documents"
    )

@router.get("/documents/{campaign_id}")
async def get_campaign_documents_v3(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get all documents uploaded for a campaign"""
    user_id = current_user["user_id"]

    try:
        result = supabase.table("video_ads_v2_documents").select("*").eq(
            "campaign_id", campaign_id
        ).eq("user_id", user_id).execute()

        return {
            "documents": result.data,
            "total": len(result.data)
        }
    except Exception as e:
        logger.error(
            "api.documents.get.failed",
            f"Error fetching documents for campaign {campaign_id}",
            exception=e
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document_v3(
    document_id: str,
    current_user: dict = Depends(verify_token)
):
    """Delete a document from S3 and database"""
    user_id = current_user["user_id"]

    try:
        # Get document metadata first
        result = supabase.table("video_ads_v2_documents").select("*").eq(
            "id", document_id
        ).eq("user_id", user_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = result.data

        # Delete from S3
        if s3_service.delete_file(document['s3_key']):
            # Delete from database
            supabase.table("video_ads_v2_documents").delete().eq(
                "id", document_id
            ).execute()

            logger.info(
                "api.documents.delete.success",
                f"Deleted document {document['file_name']}",
                document_id=document_id
            )

            return {"success": True, "message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete from S3")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api.documents.delete.failed",
            f"Error deleting document {document_id}",
            exception=e
        )
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Marketing Analysis (Stateless) ====================

@router.post("/create-marketing-analysis", response_model=MarketingAnalysisV2Response)
async def create_marketing_analysis_v3(
    request: MarketingAnalysisV2RequestWithDocs,  # Changed to always expect the WithDocs model
    current_user: dict = Depends(verify_token)
):
    """Generate marketing analysis using Claude (V3 stateless) - supports documents"""

    # For V3, we need to handle campaign_id differently
    # Since MarketingAnalysisV2Request doesn't have campaign_id, we'll generate one
    campaign_id = None

    try:
        user_id = current_user["user_id"]
        
        # Create a new campaign for this analysis
        campaign = await v3_db_service.create_campaign(
            user_id=user_id,
            campaign_name=f"Marketing Analysis {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        campaign_id = campaign["campaign_id"] if campaign else str(uuid.uuid4())
        
        # Use the provided product info from the request
        product_info = request.product_info.dict() if request.product_info else {}
        
        # Save product info to database
        if product_info and v3_db_service.supabase:
            await v3_db_service.save_product_info(campaign_id, product_info)
        
        # Generate marketing analysis using Claude
        start_time = time.time()

        # Convert product_info dict to model
        from video_ads_v2_models import VideoAdsProductInfoV2
        product_model = VideoAdsProductInfoV2(**product_info)

        # Get document_urls from the request (it's an optional field in MarketingAnalysisV2RequestWithDocs)
        document_urls = request.document_urls
        if document_urls:
            logger.info(
                "api.marketing_analysis.documents_included",
                f"Including {len(document_urls)} documents in analysis",
                document_count=len(document_urls)
            )

        # Phase 1: Avatar Analysis (with optional documents)
        avatars = await claude_service.generate_avatar_analysis(product_model, document_urls)
        
        # Phase 2: Journey Mapping
        journey = await claude_service.generate_journey_mapping(product_model, avatars)
        
        # Phase 3: Objections Analysis
        objections = await claude_service.generate_objections_analysis(product_model, avatars, journey)
        
        # Phase 4: Angles Generation
        angles = await claude_service.generate_angles(product_model, avatars, journey, objections)
        
        processing_time = time.time() - start_time
        
        # Create MarketingAnalysisV2 object
        from video_ads_v2_models import MarketingAnalysisV2
        analysis = MarketingAnalysisV2(
            avatar_analysis=avatars,
            journey_mapping=journey,
            objections_analysis=objections,
            angles_generation=angles
        )
        
        # Save to database (convert to dict for JSON serialization)
        analysis_data = {
            "avatars": avatars.dict(),
            "journey": journey.dict(),
            "objections": objections.dict(),
            "angles": angles.dict()  # Convert AnglesGeneration to dict
        }
        
        await v3_db_service.save_marketing_analysis(campaign_id, analysis_data)
        
        return MarketingAnalysisV2Response(
            conversation_id=campaign_id,
            analysis=analysis,
            processing_time=processing_time,
            claude_model="claude-sonnet-4-5-20250929"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("marketing.analysis.error", f"Error creating marketing analysis: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Marketing Angles (simplified version) ====================

@router.post("/create-marketing-angles")
async def create_marketing_angles_v3(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Generate marketing angles using Claude (V3 stateless) - simplified endpoint"""
    
    try:
        user_id = current_user["user_id"]
        product_info = request.get("product_info", {})
        force_new = request.get("force_new_conversation", False)
        
        # Create or get campaign
        campaign_id = None
        if not force_new:
            # Try to find existing campaign for this product
            campaigns = await v3_db_service.get_user_campaigns(user_id)
            if campaigns:
                # Use the most recent campaign
                campaign_id = campaigns[0].get("campaign_id")
        
        if not campaign_id:
            # Create new campaign
            campaign = await v3_db_service.create_campaign(
                user_id=user_id,
                campaign_name=f"Campaign for {product_info.get('product_name', 'Product')}"
            )
            campaign_id = campaign["campaign_id"] if campaign else str(uuid.uuid4())
            logger.debug("marketing.angles.campaign.created", f"Created campaign for marketing angles: {campaign_id}")
        
        # Save product info
        success = await v3_db_service.save_product_info(campaign_id, product_info)
        logger.debug("marketing.angles.product_info.saved", f"Saved product info: campaign_id: {campaign_id}, product_info: {product_info}, success: {success}")
        
        # Generate marketing analysis using Claude
        logger.info("marketing.angles.start", f"Generating angles for campaign: {campaign_id}")
        
        # Convert product_info dict to model
        from video_ads_v2_models import VideoAdsProductInfoV2
        product_model = VideoAdsProductInfoV2(**product_info)
        
        # Phase 1: Avatar Analysis
        avatars = await claude_service.generate_avatar_analysis(product_model)
        logger.debug("marketing.angles.avatars.generated", f"Generated avatars for campaign: {campaign_id}, avatars: {avatars}")
        
        # Phase 2: Journey Mapping
        journey = await claude_service.generate_journey_mapping(product_model, avatars)
        logger.debug("marketing.angles.journey.generated", f"Generated journey for campaign: {campaign_id}, journey: {journey}")
        
        # Phase 3: Objections Analysis
        objections = await claude_service.generate_objections_analysis(product_model, avatars, journey)
        logger.debug("marketing.angles.objections.generated", f"Generated objections for campaign: {campaign_id}, objections: {objections}")
        
        # Phase 4: Angles Generation
        angles = await claude_service.generate_angles(product_model, avatars, journey, objections)
        logger.debug("marketing.angles.angles.generated", f"Generated angles for campaign: {campaign_id}, angles: {angles}")
        
        # Save to database (ensure all are dicts for consistency)
        analysis_data = {
            "avatars": avatars.dict(),
            "journey": journey.dict(),
            "objections": objections.dict(),
            "angles": angles.dict()  # Convert to dict like in create_marketing_analysis
        }
        
        success = await v3_db_service.save_marketing_analysis(campaign_id, analysis_data)
        logger.debug("marketing.angles.analysis.saved", f"Saved marketing analysis for campaign: {campaign_id}, analysis_data: {analysis_data}, success: {success}")
        
        # Return in the format MarketingAngles.tsx expects
        # Convert angles from Pydantic model to dict format
        return {
            "positive_angles": [angle.dict() for angle in angles.positive_angles],
            "negative_angles": [angle.dict() for angle in angles.negative_angles],
            "conversation_id": campaign_id,  # Legacy support
            "campaign_id": campaign_id
        }
        
    except Exception as e:
        logger.error("marketing.angles.error", f"Error creating marketing angles: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/create-marketing-research")
async def create_marketing_research_v3(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Generate marketing angles using Claude (V3 stateless) - simplified endpoint"""

    try:
        user_id = current_user["user_id"]
        product_info = request.get("product_info", {})
        force_new = request.get("force_new_conversation", False)

        # Create or get campaign
        campaign_id = None
        if not force_new:
            # Try to find existing campaign for this product
            campaigns = await v3_db_service.get_user_campaigns(user_id)
            if campaigns:
                # Use the most recent campaign
                campaign_id = campaigns[0].get("campaign_id")

        if not campaign_id:
            # Create new campaign
            campaign = await v3_db_service.create_campaign(
                user_id=user_id,
                campaign_name=f"Campaign for {product_info.get('product_name', 'Product')}"
            )
            campaign_id = campaign["campaign_id"] if campaign else str(uuid.uuid4())
            logger.debug("marketing.angles.campaign.created", f"Created campaign for marketing angles: {campaign_id}")

        # Save product info
        success = await v3_db_service.save_product_info(campaign_id, product_info)
        logger.debug("marketing.angles.product_info.saved", f"Saved product info: campaign_id: {campaign_id}, product_info: {product_info}, success: {success}")
        
        # Generate marketing analysis using Claude
        logger.info("marketing.angles.start", f"Generating angles for campaign: {campaign_id}")
        
        # Convert product_info dict to model
        from video_ads_v2_models import VideoAdsProductInfoV2
        product_model = VideoAdsProductInfoV2(**product_info)
        
        # Phase 1: Avatar Analysis
        avatars = await claude_service.generate_avatar_analysis(product_model)
        logger.debug("marketing.angles.avatars.generated", f"Generated avatars for campaign: {campaign_id}, avatars: {avatars}")
        
        # Phase 2: Journey Mapping
        journey = await claude_service.generate_journey_mapping(product_model, avatars)
        logger.debug("marketing.angles.journey.generated", f"Generated journey for campaign: {campaign_id}, journey: {journey}")
        
        # Phase 3: Objections Analysis
        objections = await claude_service.generate_objections_analysis(product_model, avatars, journey)
        logger.debug("marketing.angles.objections.generated", f"Generated objections for campaign: {campaign_id}, objections: {objections}")
        
        # Phase 4: Angles Generation
        angles = await claude_service.generate_angles(product_model, avatars, journey, objections)
        logger.debug("marketing.angles.angles.generated", f"Generated angles for campaign: {campaign_id}, angles: {angles}")
        
        # Save to database (ensure all are dicts for consistency)
        analysis_data = {
            "avatars": avatars.dict(),
            "journey": journey.dict(),
            "objections": objections.dict(),
            "angles": angles.dict()  # Convert to dict like in create_marketing_analysis
        }
        
        success = await v3_db_service.save_marketing_analysis(campaign_id, analysis_data)
        logger.debug("marketing.angles.analysis.saved", f"Saved marketing analysis for campaign: {campaign_id}, analysis_data: {analysis_data}, success: {success}")
        
        # Return in the format MarketingAngles.tsx expects
        # Convert angles from Pydantic model to dict format
        return {
            "positive_angles": [angle.dict() for angle in angles.positive_angles],
            "negative_angles": [angle.dict() for angle in angles.negative_angles],
            "conversation_id": campaign_id,  # Legacy support
            "campaign_id": campaign_id
        }
        
    except Exception as e:
        logger.error("marketing.angles.error", f"Error creating marketing angles: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Get Campaign Data Endpoints ====================

@router.get("/campaign/{campaign_id}/product-info")
async def get_campaign_product_info(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get product info for a campaign"""
    try:
        user_id = current_user.get("user_id")
        
        # Get campaign to verify ownership
        # For dev-token, don't enforce user_id check
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
            
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign content
        content = await v3_db_service.get_campaign_content(campaign_id)
        logger.debug("campaign.product_info.retrieved", f"Retrieved content for campaign: {campaign_id}, content: {content}")
        
        if not content or not content.get("product_data"):
            logger.debug("campaign.product_info.empty", f"No product data found for campaign: {campaign_id}")
            # Return empty product info if not found
            return {
                "product_name": "",
                "product_information": "",
                "target_audience": "",
                "price": "",
                "problem_solved": "",
                "differentiation": "",
                "additional_information": ""
            }
        
        product_data = content["product_data"]
        return {
            "product_name": product_data.get("product_name", ""),
            "product_information": product_data.get("product_information", ""),
            "target_audience": product_data.get("target_audience", ""),
            "price": product_data.get("price", ""),
            "problem_solved": product_data.get("problem_solved", ""),
            "differentiation": product_data.get("differentiation", ""),
            "additional_information": product_data.get("additional_information", "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.product_info.get.error", f"Error getting product info: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaign/{campaign_id}/marketing-analysis")
async def get_campaign_marketing_analysis(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get marketing analysis for a campaign"""
    try:
        user_id = current_user.get("user_id")
        
        # Get campaign to verify ownership
        # For dev-token, don't enforce user_id check
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
            
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign content
        content = await v3_db_service.get_campaign_content(campaign_id)
        logger.debug("campaign.marketing.retrieved", f"Retrieved marketing content for campaign: {campaign_id}, content: {content}")
        
        if not content:
            logger.debug("campaign.marketing.empty", f"No marketing content found for campaign: {campaign_id}")
            raise HTTPException(status_code=404, detail="Marketing analysis not found")
        
        # V3 stores marketing analysis in separate columns
        marketing_analysis = {
            "avatars": content.get("avatar_analysis"),
            "journey": content.get("journey_mapping"),
            "objections": content.get("objections_analysis"),
            "angles": content.get("angles"),
            "selected_angles": content.get("selected_angles")  # Include selected angles
        }
        logger.debug("campaign.marketing.analysis.built", f"Built marketing analysis for campaign: {campaign_id}, analysis: {marketing_analysis}")
        
        # Only return if we have angles data (the main data needed for the page)
        if not marketing_analysis.get("angles"):
            logger.debug("campaign.marketing.no_angles", f"No angles found for campaign: {campaign_id}")
            raise HTTPException(status_code=404, detail="Marketing angles not found")
        
        return marketing_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.marketing.get.error", f"Error getting marketing analysis: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Save Selected Angles ====================

@router.post("/campaign/{campaign_id}/selected-angles")
async def save_selected_angles(
    campaign_id: str,
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Save selected marketing angles for a campaign"""
    try:
        selected_angles = request.get("selected_angles", [])
        logger.debug("selected_angles.saving", f"Saving selected angles for campaign: {campaign_id}, selected_angles: {selected_angles}")
        
        # Update campaign content with selected angles
        success = await v3_db_service.update_campaign_content(campaign_id, {
            "selected_angles": selected_angles
        })
        logger.debug("selected_angles.saved", f"Saved selected angles for campaign: {campaign_id}, success: {success}")
        
        return {"status": "success", "message": "Selected angles saved"}
        
    except Exception as e:
        logger.error("selected_angles.save.error", f"Error saving selected angles: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Save Selected Hooks ====================

@router.post("/campaign/{campaign_id}/selected-hooks")
async def save_selected_hooks(
    campaign_id: str,
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Save selected hooks for a campaign"""
    try:
        selected_hooks = request.get("selected_hooks", [])
        logger.debug("selected_hooks.saving", f"Saving selected hooks for campaign: {campaign_id}, selected_hooks: {selected_hooks}")
        
        # Update campaign content with selected hooks
        success = await v3_db_service.update_campaign_content(campaign_id, {
            "selected_hooks": selected_hooks
        })
        logger.debug("selected_hooks.saved", f"Saved selected hooks for campaign: {campaign_id}, success: {success}")
        
        return {"status": "success", "message": "Selected hooks saved"}
        
    except Exception as e:
        logger.error("selected_hooks.save.error", f"Error saving selected hooks: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Get Saved Hooks ====================

@router.get("/campaign/{campaign_id}/hooks")
async def get_campaign_hooks(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get saved hooks for a campaign"""
    try:
        user_id = current_user.get("user_id")
        
        # Get campaign to verify ownership
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
            
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign content
        content = await v3_db_service.get_campaign_content(campaign_id)
        logger.debug("campaign.hooks.content.retrieved", f"Retrieved content for hooks: campaign_id: {campaign_id}, content: {content}")
        
        if not content:
            logger.debug("campaign.hooks.no_content", f"No content found for campaign: {campaign_id}")
            # Return empty hooks if no content
            return {
                "hooks_by_angle": [],
                "conversation_id": campaign_id,
                "campaign_id": campaign_id
            }
        
        hooks_data = content.get("hooks")
        logger.debug("campaign.hooks.raw_data", f"Raw hooks data for campaign: {campaign_id}, hooks_data: {hooks_data}")
        
        # Handle different storage formats
        if hooks_data:
            # If hooks_data is a string (JSON), parse it
            if isinstance(hooks_data, str):
                import json
                try:
                    hooks_data = json.loads(hooks_data)
                    logger.debug("campaign.hooks.parsed_json", f"Parsed JSON hooks data: {hooks_data}")
                except:
                    hooks_data = []
                    logger.debug("campaign.hooks.json_parse_failed", f"Failed to parse JSON hooks data for campaign: {campaign_id}")
            
            # hooks_data should be a list directly now
            if isinstance(hooks_data, list):
                hooks_array = hooks_data
                logger.debug("campaign.hooks.list_format", f"Hooks data is a list with {len(hooks_array)} items")
            elif isinstance(hooks_data, dict):
                # Legacy format - try to extract hooks_by_angle
                hooks_array = hooks_data.get("hooks_by_angle", [])
                logger.debug("campaign.hooks.dict_format", f"Hooks data is a dict, extracted {len(hooks_array)} items from hooks_by_angle")
            else:
                hooks_array = []
                logger.debug("campaign.hooks.unknown_format", f"Unknown hooks data format: {type(hooks_data)}")
        else:
            hooks_array = []
            logger.debug("campaign.hooks.no_data", f"No hooks data found for campaign: {campaign_id}")
        
        # Return in the format expected by frontend
        return {
            "hooks_by_angle": hooks_array,
            "conversation_id": campaign_id,
            "campaign_id": campaign_id,
            "selected_hooks": content.get("selected_hooks", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.hooks.get.error", f"Error getting hooks: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Hooks Generation ====================

@router.post("/create-hooks")
async def create_hooks_v3(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Generate hooks for selected marketing angles (V3 stateless)"""
    
    try:
        user_id = current_user.get("user_id")
        campaign_id = request.get("conversation_id") or request.get("campaign_id")
        selected_angles = request.get("selected_angles", [])
        
        if not campaign_id:
            raise HTTPException(status_code=400, detail="Campaign ID is required")
        
        if not selected_angles:
            raise HTTPException(status_code=400, detail="Selected angles are required")
        
        # Verify campaign exists
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Generate hooks using Claude
        logger.info("hooks.generation.start", f"Generating hooks for {len(selected_angles)} angles")
        
        # Get product info and marketing analysis from database
        content = await v3_db_service.get_campaign_content(campaign_id)
        logger.debug("hooks.generation.content.retrieved", f"Retrieved content for hooks generation: campaign_id: {campaign_id}, content_keys: {content.keys() if content else None}")
        
        if not content:
            raise HTTPException(status_code=404, detail="Campaign content not found")
        
        # Reconstruct product info and marketing analysis
        from video_ads_v2_models import VideoAdsProductInfoV2, MarketingAngleV2
        product_info = VideoAdsProductInfoV2(**content.get("product_data", {}))
        logger.debug("hooks.generation.product_info", f"Product info for hooks: {product_info}")
        
        # Convert selected angles to MarketingAngleV2 models
        angle_models = []
        for angle in selected_angles:
            angle_models.append(MarketingAngleV2(**angle))
        logger.debug("hooks.generation.angles.formatted", f"Formatted {len(angle_models)} angles for generation")
        
        # Load optional context (avatar, journey, objections) if available
        from video_ads_v2_models import AvatarAnalysis, JourneyMapping, ObjectionsAnalysis
        
        avatar_analysis = None
        journey_mapping = None
        objections_analysis = None
        
        # Log what's actually in content for debugging
        logger.debug("hooks.generation.content.analysis_fields", 
                    f"avatar_analysis exists: {content.get('avatar_analysis') is not None}, "
                    f"journey_mapping exists: {content.get('journey_mapping') is not None}, "
                    f"objections_analysis exists: {content.get('objections_analysis') is not None}")
        
        if content.get("avatar_analysis"):
            try:
                avatar_analysis = AvatarAnalysis(**content["avatar_analysis"])
                logger.debug("hooks.generation.avatar.parsed", "Successfully parsed avatar analysis")
            except Exception as e:
                logger.debug("hooks.generation.avatar.parse_error", f"Could not parse avatar analysis: {e}")
        else:
            logger.debug("hooks.generation.avatar.missing", "No avatar_analysis in content")
        
        if content.get("journey_mapping"):
            try:
                journey_mapping = JourneyMapping(**content["journey_mapping"])
                logger.debug("hooks.generation.journey.parsed", "Successfully parsed journey mapping")
            except Exception as e:
                logger.debug("hooks.generation.journey.parse_error", f"Could not parse journey mapping: {e}")
        else:
            logger.debug("hooks.generation.journey.missing", "No journey_mapping in content")
        
        if content.get("objections_analysis"):
            try:
                objections_analysis = ObjectionsAnalysis(**content["objections_analysis"])
                logger.debug("hooks.generation.objections.parsed", "Successfully parsed objections analysis")
            except Exception as e:
                logger.debug("hooks.generation.objections.parse_error", f"Could not parse objections: {e}")
        else:
            logger.debug("hooks.generation.objections.missing", "No objections_analysis in content")
        
        logger.debug("hooks.generation.context.loaded", f"Loaded context - avatar: {avatar_analysis is not None}, journey: {journey_mapping is not None}, objections: {objections_analysis is not None}")
        
        # Generate hooks using Claude Service
        hooks_by_angle = await claude_service.generate_hooks(
            product_info=product_info,
            selected_angles=angle_models,
            avatar_analysis=avatar_analysis,
            journey_mapping=journey_mapping,
            objections_analysis=objections_analysis
        )
        logger.debug("hooks.generation.hooks.created", f"Generated hooks: {len(hooks_by_angle)} angles with hooks")
        
        # Convert Pydantic models to dictionaries for storage and response
        hooks_by_angle_dict = []
        for hook in hooks_by_angle:
            if hasattr(hook, 'model_dump'):
                # Pydantic v2
                hooks_by_angle_dict.append(hook.model_dump())
            elif hasattr(hook, 'dict'):
                # Pydantic v1
                hooks_by_angle_dict.append(hook.dict())
            else:
                # Already a dict
                hooks_by_angle_dict.append(hook)
        
        # Format response as expected by frontend
        hooks_response = {
            "hooks_by_angle": hooks_by_angle_dict,
            "conversation_id": campaign_id
        }
        
        # Save hooks to database - save just the hooks array, not the whole response
        content_update = {
            "selected_angles": selected_angles,
            "hooks": hooks_by_angle_dict  # Save just the hooks array as dicts
        }
        
        # Update campaign content
        success = await v3_db_service.update_campaign_content(campaign_id, content_update)
        logger.debug("hooks.generation.saved", f"Saved generated hooks for campaign: {campaign_id}, content_update: {content_update}, success: {success}")
        
        logger.info("hooks.generation.complete", f"Generated hooks for campaign: {campaign_id}")
        
        return hooks_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("hooks.generation.error", f"Error generating hooks: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Scripts Generation ====================

@router.post("/create-scripts")
async def create_scripts_v3(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Generate scripts for selected hooks (V3 stateless)"""
    
    try:
        user_id = current_user.get("user_id")
        campaign_id = request.get("campaign_id") or request.get("conversation_id")  # Prefer campaign_id
        # Accept both 'hooks_by_angle' (new format) and 'selected_hooks' (legacy)
        selected_hooks = request.get("hooks_by_angle") or request.get("selected_hooks", [])
        
        logger.debug("scripts.generation.request", 
                    f"Request received - campaign_id: {campaign_id}, "
                    f"has hooks_by_angle: {'hooks_by_angle' in request}, "
                    f"has selected_hooks: {'selected_hooks' in request}, "
                    f"hooks count: {len(selected_hooks)}")
        
        if not campaign_id:
            raise HTTPException(status_code=400, detail="Campaign ID is required")
        
        if not selected_hooks:
            raise HTTPException(status_code=400, detail="Hooks are required (hooks_by_angle or selected_hooks)")
        
        logger.debug("scripts.generation.hooks_format", 
                    f"First hook format: {selected_hooks[0] if selected_hooks else 'No hooks'}")
        
        # Verify campaign exists
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Generate scripts using Claude Service directly
        logger.info("scripts.generation.start", f"Generating scripts for {len(selected_hooks)} hooks")
        
        # Get product info from database
        content = await v3_db_service.get_campaign_content(campaign_id)
        if not content or not content.get("product_data"):
            raise HTTPException(status_code=404, detail="Product information not found for campaign")
        
        # Reconstruct product info
        from video_ads_v2_models import VideoAdsProductInfoV2
        product_info = VideoAdsProductInfoV2(**content["product_data"])
        
        # Format hooks for scripts generation - they're already in the right format from frontend
        hooks_by_angle = selected_hooks
        
        # Generate scripts using Claude Service
        scripts_result = await claude_service.generate_scripts(
            product_info=product_info,
            hooks_by_angle=hooks_by_angle,
            # Optional context if available
            avatar_analysis=None,  # Could load from content if needed
            journey_mapping=None,  # Could load from content if needed
            objections_analysis=None  # Could load from content if needed
        )
        
        logger.debug("scripts.generation.result", f"Generated scripts result type: {type(scripts_result)}, has angles: {'angles' in scripts_result if isinstance(scripts_result, dict) else False}")
        
        # Log the structure for debugging
        if isinstance(scripts_result, dict):
            logger.debug("scripts.structure", f"Scripts result keys: {list(scripts_result.keys())}")
            if 'angles' in scripts_result:
                logger.debug("scripts.angles.count", f"Number of angles: {len(scripts_result['angles'])}")
                if scripts_result['angles']:
                    first_angle = scripts_result['angles'][0]
                    logger.debug("scripts.first_angle", f"First angle keys: {list(first_angle.keys()) if isinstance(first_angle, dict) else 'Not a dict'}")
        
        # The claude_service.generate_scripts returns the content of campaign_scripts (already has 'angles' key)
        # scripts_result = { "angles": [...] }
        
        # Save scripts to database
        content_update = {
            "scripts": scripts_result,  # Store as-is since it already has the correct structure
            # Don't save selected_hooks here - let Hooks page manage that
        }
        
        success = await v3_db_service.update_campaign_content(campaign_id, content_update)
        logger.debug("scripts.generation.saved", f"Saved scripts for campaign: {campaign_id}, success: {success}")
        
        logger.info("scripts.generation.complete", f"Generated scripts for campaign: {campaign_id}")
        
        # Return in the format expected by frontend
        # scripts_result already contains { "angles": [...] }, so we wrap it in campaign_scripts
        return {
            "campaign_scripts": scripts_result,  # This already has the angles structure
            "conversation_id": campaign_id,
            "campaign_id": campaign_id,
            "processing_time": 0.0  # Could track actual time if needed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("scripts.generation.error", f"Error generating scripts: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Save Selected Scripts ====================

@router.put("/campaign/{campaign_id}/scripts/selected")
async def save_selected_scripts(
    campaign_id: str,
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Save user's selected scripts for a campaign"""
    try:
        selected_scripts = request.get("selected_scripts", [])
        logger.debug("selected_scripts.saving", f"Saving selected scripts for campaign: {campaign_id}, count: {len(selected_scripts)}")
        
        # Update campaign content with selected scripts
        success = await v3_db_service.update_campaign_content(campaign_id, {
            "selected_scripts": selected_scripts
        })
        logger.debug("selected_scripts.saved", f"Saved selected scripts for campaign: {campaign_id}, success: {success}")
        
        return {"status": "success", "message": "Selected scripts saved"}
        
    except Exception as e:
        logger.error("selected_scripts.save.error", f"Error saving selected scripts: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Get Campaign Scripts ====================

@router.get("/campaign/{campaign_id}/scripts")
async def get_campaign_scripts(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get saved scripts for a campaign"""
    try:
        user_id = current_user.get("user_id")
        
        # Get campaign to verify ownership
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
            
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign content
        content = await v3_db_service.get_campaign_content(campaign_id)
        logger.debug("campaign.scripts.retrieved", f"Retrieved scripts content for campaign: {campaign_id}, has_content: {bool(content)}")
        
        if not content or not content.get("scripts"):
            logger.debug("campaign.scripts.empty", f"No scripts found for campaign: {campaign_id}")
            return {
                "scripts_data": None,
                "conversation_id": campaign_id,
                "campaign_id": campaign_id,
                "selected_scripts": []
            }
        
        scripts_data = content.get("scripts", {})
        logger.debug("campaign.scripts.data", f"Scripts data for campaign: {campaign_id}")
        
        # Return in the format expected by the frontend
        return {
            "scripts_data": scripts_data,  # This contains the campaign_scripts structure
            "conversation_id": campaign_id,
            "campaign_id": campaign_id,
            "selected_scripts": content.get("selected_scripts", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.scripts.get.error", f"Error getting scripts: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Save Selected Scripts ====================

@router.post("/campaign/{campaign_id}/selected-scripts")
async def save_selected_scripts(
    campaign_id: str,
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Save selected scripts for a campaign"""
    try:
        user_id = current_user.get("user_id")  # Use current_user
        selected_scripts = request.get("selected_scripts", [])
        logger.debug("selected_scripts.saving", f"Saving selected scripts for campaign: {campaign_id}, user: {user_id}, selected_scripts: {selected_scripts}")
        
        # Update campaign content with selected scripts
        success = await v3_db_service.update_campaign_content(campaign_id, {
            "selected_scripts": selected_scripts
        })
        logger.debug("selected_scripts.saved", f"Saved selected scripts for campaign: {campaign_id}, success: {success}")
        
        return {"status": "success", "message": "Selected scripts saved"}
        
    except Exception as e:
        logger.error("selected_scripts.save.error", f"Error saving selected scripts: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Voice Actor Selection ====================

@router.post("/voice-actor")
async def get_voice_actors(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Get available voices and actors for selection (V3 stateless)"""
    try:
        campaign_id = request.get("campaign_id")
        campaign_scripts = request.get("campaign_scripts", {})
        
        logger.info("voice_actor.start", f"Getting voice actors for campaign: {campaign_id}")
        logger.debug("voice_actor.scripts", f"Campaign scripts keys: {list(campaign_scripts.keys()) if isinstance(campaign_scripts, dict) else 'not a dict'}")
        
        # Verify campaign exists using V3 database service
        user_id = current_user.get("user_id")
        
        # Get campaign to verify ownership
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        
        if not campaign:
            logger.error("voice_actor.not_found", f"Campaign {campaign_id} not found")
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        logger.debug("voice_actor.found", f"Campaign found - Campaign ID: {campaign.get('campaign_id')}")
        
        # Import the necessary functions from v2 routes
        from video_ads_v2_routes import fetch_elevenlabs_voices, get_actor_images
        from video_ads_v2_models import ElevenLabsVoice, ActorImage
        
        # Fetch ElevenLabs voices
        logger.debug("voice_actor.voices", "Fetching ElevenLabs voices...")
        try:
            voices = await fetch_elevenlabs_voices()
            logger.debug("voice_actor.voices.count", f"Retrieved {len(voices)} voices")
        except Exception as e:
            logger.error("voice_actor.voices.error", f"Error fetching voices: {e}")
            voices = []
        
        # Get actor images
        logger.debug("voice_actor.actors", "Getting actor images...")
        try:
            actors = get_actor_images()
            logger.debug("voice_actor.actors.count", f"Retrieved {len(actors)} actors")
        except Exception as e:
            logger.error("voice_actor.actors.error", f"Error fetching actors: {e}")
            actors = []
        
        # Convert to response format
        v3_voices = []
        for voice in voices:
            v3_voices.append({
                "voice_id": voice.voice_id,
                "name": voice.name,
                "description": voice.description,
                "category": voice.category,
                "labels": voice.labels,
                "preview_url": voice.preview_url,
                "gender": voice.gender,
                "age": voice.age,
                "accent": voice.accent,
                "use_case": voice.use_case
            })
        
        v3_actors = []
        for actor in actors:
            v3_actors.append({
                "filename": actor.filename,
                "name": actor.name,
                "description": getattr(actor, 'description', f"Actor image {actor.filename}"),
                "category": getattr(actor, 'category', 'Professional')
            })
        
        response = {
            "conversation_id": campaign_id,  # Keep for backward compatibility
            "campaign_id": campaign_id,
            "voices": v3_voices,
            "actors": v3_actors,
            "status": "success"
        }
        
        logger.info("voice_actor.success", f"Response created for campaign: {campaign_id}")
        logger.debug("voice_actor.stats", f"Response contains {len(v3_voices)} voices and {len(v3_actors)} actors")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("voice_actor.error", f"Error getting voice actors: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Voice/Actor Selection ====================

@router.put("/campaign/{campaign_id}/voice-actor/selected")
async def save_selected_voice_actor_v3(
    campaign_id: str,
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Save selected voice and actor to database immediately when selected."""
    try:
        user_id = current_user["user_id"]
        logger.info("voice_actor.save", f"Saving voice/actor selection for campaign: {campaign_id}")
        
        # Extract voice_info from request
        voice_info = request.get("voice_info", {})
        
        if not voice_info:
            raise HTTPException(status_code=400, detail="voice_info is required")
        
        # Update the campaign content with voice/actor selection
        # Use supabase directly to update the campaign content table
        from auth import supabase
        
        try:
            # First check if campaign exists
            result = supabase.table('video_ads_v3_campaign_content').select('*').eq('campaign_id', campaign_id).execute()
            
            if result.data:
                # Update existing record - merge with existing audio_data
                existing_audio_data = result.data[0].get('audio_data', {}) or {}
                existing_audio_data['voice_info'] = voice_info
                
                update_result = supabase.table('video_ads_v3_campaign_content').update({
                    'audio_data': existing_audio_data,
                    'updated_at': 'now()'
                }).eq('campaign_id', campaign_id).execute()
                
                if not update_result.data:
                    raise HTTPException(status_code=500, detail="Failed to update voice/actor selection")
            else:
                # Create new record
                insert_result = supabase.table('video_ads_v3_campaign_content').insert({
                    'campaign_id': campaign_id,
                    'audio_data': {'voice_info': voice_info},
                    'created_at': 'now()',
                    'updated_at': 'now()'
                }).execute()
                
                if not insert_result.data:
                    raise HTTPException(status_code=500, detail="Failed to save voice/actor selection")
        except Exception as db_error:
            logger.error("voice_actor.save.db_error", f"Database error: {db_error}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        logger.info("voice_actor.save.success", 
                   f"Saved voice/actor selection for campaign: {campaign_id}",
                   voice_id=voice_info.get("selected_voice", {}).get("voice_id"),
                   actor_filename=voice_info.get("selected_actor", {}).get("filename"))
        
        return {
            "status": "success",
            "message": "Voice and actor selection saved",
            "campaign_id": campaign_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("voice_actor.save.error", 
                    f"Error saving voice/actor selection: {e}", 
                    error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Audio Generation ====================

@router.post("/audio")
async def generate_audio_v3(
    request: Dict[str, Any],
    current_user: dict = Depends(verify_token)
):
    """Generate audio for scripts using ElevenLabs TTS (V3 stateless)"""
    
    try:
        user_id = current_user.get("user_id")
        campaign_id = request.get("campaign_id") or request.get("conversation_id")
        voice_actor_selection = request.get("voice_actor_selection", {})
        campaign_scripts = request.get("campaign_scripts", {})
        
        logger.info("audio.generation.start", f"Starting audio generation for campaign: {campaign_id}")
        
        if not campaign_id:
            raise HTTPException(status_code=400, detail="Campaign ID is required")
        
        # Verify campaign exists
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Extract voice and actor selection
        selected_voice = voice_actor_selection.get("selected_voice", {})
        selected_actor = voice_actor_selection.get("selected_actor", {})
        
        voice_id = selected_voice.get("voice_id")
        if not voice_id:
            logger.error("audio.generation.no_voice", f"No voice_id found in request")
            raise HTTPException(status_code=400, detail="No voice selected")
        
        logger.debug("audio.generation.voice", f"Using voice: {selected_voice.get('name', 'Unknown')} ({voice_id})")
        logger.debug("audio.generation.actor", f"Using actor: {selected_actor.get('name', 'Unknown')}")
        
        # Extract scripts from campaign_scripts
        scripts = campaign_scripts.get("scripts", [])
        selected_angle = campaign_scripts.get("selected_angle", {})
        
        if not scripts:
            logger.error("audio.generation.no_scripts", "No scripts provided")
            raise HTTPException(status_code=400, detail="No scripts provided")
        
        logger.info("audio.generation.scripts", f"Processing {len(scripts)} scripts for audio generation")
        
        # Import necessary audio generation function
        try:
            from video_ads_routes import generate_audio_with_elevenlabs
            # Get API key directly from environment
            api_key = os.getenv("ELEVENLABS_API_KEY")
            logger.debug("audio.generation.api_key_check", f"ElevenLabs API key loaded: {bool(api_key)}, key preview: {api_key[:10] if api_key else 'None'}...")
        except ImportError as e:
            logger.error("audio.generation.import_error", f"Could not import from video_ads_routes: {e}")
            raise HTTPException(status_code=500, detail="Audio generation service unavailable")
        
        # Check if we can generate audio
        can_generate_audio = bool(api_key)
        if not can_generate_audio:
            logger.warning("audio.generation.no_api_key", "ElevenLabs API key not configured, skipping audio generation")
        
        # Generate audio for each script
        scripts_with_audio = []
        total_audios_generated = 0
        
        for script in scripts:
            script_id = script.get("script_id", str(uuid.uuid4()))
            hook = script.get("hook", "")
            body = script.get("body", "")
            selected = script.get("selected", False)
            
            # Combine hook and body for audio generation
            combined_text = f"{hook} {body}".strip()
            
            combined_audio = None
            if combined_text and can_generate_audio:
                try:
                    # Generate combined audio
                    audio_content = await generate_audio_with_elevenlabs(
                        text=combined_text,
                        voice_id=voice_id,
                        audio_type="combined"
                    )
                    
                    if audio_content:
                        combined_audio = {
                            "audio_id": audio_content.audio_id,
                            "type": audio_content.type,
                            "content": audio_content.content,
                            "audio_url": audio_content.audio_url,
                            "duration": getattr(audio_content, 'duration', None),
                            "file_size": audio_content.file_size,
                            "voice_settings": audio_content.voice_settings
                        }
                        total_audios_generated += 1
                        logger.debug("audio.generation.success", f"Generated audio for script {script_id}")
                        
                except Exception as audio_error:
                    logger.error("audio.generation.script_error", f"Error generating audio for script {script_id}: {audio_error}")
            elif combined_text and not can_generate_audio:
                # Create placeholder audio data without actual generation
                combined_audio = {
                    "audio_id": f"placeholder_{script_id}",
                    "type": "combined",
                    "content": combined_text,
                    "audio_url": None,
                    "duration": None,
                    "file_size": 0,
                    "voice_settings": {"voice_id": voice_id, "placeholder": True}
                }
                logger.debug("audio.generation.placeholder", f"Created placeholder audio for script {script_id}")
            
            script_with_audio = {
                "script_id": script_id,
                "hook": hook,
                "body": body,
                "selected": selected,
                "combined_audio": combined_audio
            }
            scripts_with_audio.append(script_with_audio)
        
        logger.info("audio.generation.complete", f"Generated {total_audios_generated} audio files")
        
        # Save audio data to database
        audio_data = {
            "voice_info": {
                "selected_voice": selected_voice,
                "selected_actor": selected_actor
            },
            "selected_angle": selected_angle,
            "scripts_with_audio": scripts_with_audio,
            "total_audios_generated": total_audios_generated
        }
        
        success = await v3_db_service.update_campaign_content(campaign_id, {
            "audio_data": audio_data
        })
        
        if success:
            logger.info("audio.generation.saved", f"Saved audio data for campaign: {campaign_id}")
        else:
            logger.warning("audio.generation.save_failed", f"Failed to save audio data for campaign: {campaign_id}")
        
        # Return response in V2 format for compatibility
        return {
            "conversation_id": campaign_id,
            "campaign_id": campaign_id,
            "selected_angle": selected_angle,
            "voice_info": {
                "selected_voice": selected_voice,
                "selected_actor": selected_actor
            },
            "scripts_with_audio": scripts_with_audio,
            "total_audios_generated": total_audios_generated,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("audio.generation.error", f"Error generating audio: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Get Campaign Audio ====================

@router.get("/campaign/{campaign_id}/audio")
async def get_campaign_audio(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get saved audio data for a campaign"""
    try:
        user_id = current_user.get("user_id")
        
        # Get campaign to verify ownership
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign content
        content = await v3_db_service.get_campaign_content(campaign_id)
        
        if not content or not content.get("audio_data"):
            logger.debug("campaign.audio.empty", f"No audio data found for campaign: {campaign_id}")
            return {
                "campaign_id": campaign_id,
                "conversation_id": campaign_id,
                "audio_data": None,
                "status": "not_found"
            }
        
        audio_data = content.get("audio_data", {})
        
        # Return in the format expected by frontend
        return {
            "conversation_id": campaign_id,
            "campaign_id": campaign_id,
            "selected_angle": audio_data.get("selected_angle"),
            "voice_info": audio_data.get("voice_info"),
            "scripts_with_audio": audio_data.get("scripts_with_audio", []),
            "total_audios_generated": audio_data.get("total_audios_generated", 0),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.audio.get.error", f"Error getting audio data: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Video Generation ====================

@router.post("/video")
async def generate_video_v3(request: Dict[str, Any], current_user: dict = Depends(verify_token)):
    """
    V3 Video Generation - Stateless with database persistence
    Generates videos using Hedra API and saves to database
    """
    try:
        user_id = current_user.get("user_id")
        campaign_id = request.get("campaign_id") or request.get("conversation_id")
        
        if not campaign_id:
            raise HTTPException(status_code=400, detail="Campaign ID is required")
        
        logger.info("video.generation.start", f"Starting video generation for campaign {campaign_id}")
        
        # Verify campaign exists
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign content (including audio data)
        content = await v3_db_service.get_campaign_content(campaign_id)
        if not content:
            raise HTTPException(status_code=404, detail="Campaign content not found")
        
        # Get audio data from campaign
        audio_data = content.get("audio_data", {})
        if not audio_data:
            raise HTTPException(status_code=400, detail="No audio data found. Please generate audio first.")
        
        # Get actor image from request or audio data
        actor_image = request.get("actor_image")
        if not actor_image and audio_data.get("voice_info"):
            actor_info = audio_data["voice_info"].get("actor", {})
            actor_image = actor_info.get("filename") or actor_info.get("image") or "actor-01.jpg"
        
        video_settings = request.get("video_settings", {
            "aspect_ratio": "9:16",
            "quality": "low",
            "max_duration": 60
        })
        
        logger.debug("video.generation.params", 
                    f"Actor: {actor_image}, Settings: {video_settings}, "
                    f"Scripts count: {len(audio_data.get('scripts_with_audio', []))}")
        
        # Check if Hedra is available
        if not hedra_generator:
            logger.warning("video.generation.no_hedra", "Hedra API not configured")
            # Return mock response for development
            mock_videos = []
            for idx, script in enumerate(audio_data.get("scripts_with_audio", [])):
                mock_videos.append({
                    "video_id": f"mock_video_{campaign_id}_{idx}",
                    "script_id": script.get("script_id"),
                    "video_type": "combined",
                    "hook_text": script.get("hook", ""),
                    "script_text": script.get("body", ""),
                    "combined_text": f"{script.get('hook', '')} {script.get('body', '')}",
                    "video_url": f"/mock_videos/video_{idx}.mp4",
                    "status": "mock",
                    "duration": 30.0,
                    "aspect_ratio": video_settings.get("aspect_ratio", "9:16"),
                    "quality": video_settings.get("quality", "low")
                })
            
            # Save mock video data to database
            video_data = {
                "actor_image": actor_image,
                "video_settings": video_settings,
                "generated_videos": mock_videos,
                "total_videos_generated": len(mock_videos),
                "status": "mock",
                "processing_time": 0.0
            }
            
            await v3_db_service.update_campaign_content(campaign_id, {
                "video_data": video_data
            })
            
            # Update campaign step and status to completed for mock videos too
            await v3_db_service.update_campaign(campaign_id, {
                "current_step": 8,
                "status": "completed"
            })
            
            return {
                "conversation_id": campaign_id,
                "campaign_id": campaign_id,
                **video_data
            }
        
        # Generate videos using Hedra
        start_time = time.time()
        
        # Get actor image path (handles both dev and production environments)
        try:
            actor_image_path = await actor_image_handler.get_actor_image_path(actor_image)
            logger.info("video.generation.actor_retrieved", f"Actor image retrieved: {actor_image_path}")
        except Exception as e:
            logger.warning("video.generation.actor_not_found", f"Actor image not found: {actor_image}, error: {str(e)}")
            # Try default actor image
            actor_image = "actor-01.jpg"
            try:
                actor_image_path = await actor_image_handler.get_actor_image_path(actor_image)
                logger.info("video.generation.default_actor", f"Using default actor: {actor_image}")
            except Exception as e2:
                logger.error("video.generation.no_actor", f"Could not load any actor image: {str(e2)}")
                raise HTTPException(
                    status_code=500,
                    detail="Actor image not available"
                )

        logger.info("video.generation.hedra_start", f"Starting Hedra generation with actor: {actor_image}")
        
        # Generate videos using the available Hedra method
        try:
            # Prepare audio data in the format expected by hedra_generator
            formatted_audio_data = {
                "scripts_with_audio": audio_data.get("scripts_with_audio", [])
            }
            
            # Use the existing generate_videos_for_thread method
            generated_videos = await hedra_generator.generate_videos_for_thread(
                thread_id=campaign_id,  # Use campaign_id as thread_id
                audio_data=formatted_audio_data,
                actor_image_path=str(actor_image_path)
            )
            
            logger.info("video.generation.hedra_complete", 
                       f"Generated {len(generated_videos)} videos using Hedra")
            
        except Exception as e:
            logger.error("video.generation.hedra_error", f"Hedra generation failed: {e}")
            # Fallback to mock videos on error
            generated_videos = []
            scripts_with_audio = audio_data.get("scripts_with_audio", [])
            
            for idx, script in enumerate(scripts_with_audio):
                generated_videos.append({
                    "video_id": f"mock_video_{campaign_id}_{idx}",
                    "script_id": script.get("script_id"),
                    "video_type": "combined",
                    "hook_text": script.get("hook", ""),
                    "script_text": script.get("body", ""),
                    "combined_text": f"{script.get('hook', '')} {script.get('body', '')}",
                    "video_url": f"/mock_videos/video_{idx}.mp4",
                    "status": "mock_fallback",
                    "duration": 30.0,
                    "aspect_ratio": video_settings.get("aspect_ratio", "9:16"),
                    "quality": video_settings.get("quality", "low"),
                    "error": str(e)
                })
        
        processing_time = time.time() - start_time
        
        # Prepare video data for database
        video_data = {
            "actor_image": actor_image,
            "video_settings": video_settings,
            "generated_videos": generated_videos,
            "total_videos_generated": len([v for v in generated_videos if v.get("status") != "failed"]),
            "status": "completed" if generated_videos else "no_videos",
            "processing_time": processing_time
        }
        
        # Save video data to database
        await v3_db_service.update_campaign_content(campaign_id, {
            "video_data": video_data
        })
        
        # Update campaign step and status to completed
        await v3_db_service.update_campaign(campaign_id, {
            "current_step": 8,
            "status": "completed"
        })
        
        logger.info("video.generation.complete", 
                   f"Generated {len(generated_videos)} videos in {processing_time:.2f}s")
        
        return {
            "conversation_id": campaign_id,
            "campaign_id": campaign_id,
            **video_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("video.generation.error", f"Error generating videos: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaign/{campaign_id}/video")
async def get_campaign_video(campaign_id: str, current_user: dict = Depends(verify_token)):
    """
    Get saved video data for a campaign (V3 stateless)
    """
    try:
        user_id = current_user.get("user_id")
        
        # Verify campaign exists
        if current_user.get("dev_mode"):
            campaign = await v3_db_service.get_campaign(campaign_id)
        else:
            campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get campaign content
        content = await v3_db_service.get_campaign_content(campaign_id)
        if not content:
            return {
                "campaign_id": campaign_id,
                "status": "not_found"
            }
        
        video_data = content.get("video_data", {})
        
        if not video_data:
            return {
                "campaign_id": campaign_id,
                "status": "not_found"
            }
        
        # Return video data
        return {
            "conversation_id": campaign_id,
            "campaign_id": campaign_id,
            **video_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.video.get.error", f"Error getting video data: {e}", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Campaigns List ====================

@router.get("/campaigns")
async def get_user_campaigns(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(verify_token)
):
    """Get list of user's campaigns with V3 structure"""
    try:
        user_id = current_user.get("user_id")
        
        # Get campaigns from V3 database (optimized query)
        campaigns = await v3_db_service.get_user_campaigns(user_id, limit)
        
        # Batch fetch product info for all campaigns (single DB query instead of N queries)
        campaign_ids = [c.get('campaign_id') for c in campaigns if c.get('campaign_id')]
        product_info_map = await v3_db_service.get_campaigns_product_info_batch(campaign_ids) if campaign_ids else {}

        # Fetch video data for completed campaigns
        for campaign in campaigns:
            logger.debug(f"Campaign {campaign.get('campaign_id')}: step={campaign.get('current_step')}, status={campaign.get('status')}")
            if campaign.get('current_step') == 8 and campaign.get('status') == 'completed':
                # Get videos for this campaign
                videos = await v3_db_service.get_campaign_videos(campaign['campaign_id'])
                logger.debug(f"Found {len(videos) if videos else 0} videos for campaign {campaign['campaign_id']}")
                if videos:
                    # Add the first video's URL to the campaign
                    campaign['video_url'] = videos[0].get('video_url', '')
                    campaign['video_data'] = {
                        'video_url': videos[0].get('video_url', ''),
                        'audio_url': videos[0].get('audio_url', ''),
                        'generated_videos': videos
                    }
                    logger.info(f"Added video data to campaign {campaign['campaign_id']}: {campaign['video_url'][:50]}...")

        # Ensure backward compatibility with frontend
        for campaign in campaigns:
            # Add 'id' field for frontend compatibility (uses campaign_id as id)
            campaign['id'] = campaign.get('campaign_id')
            
            # Ensure conversation_id is present for legacy support
            if 'conversation_id' not in campaign:
                campaign['conversation_id'] = campaign.get('campaign_id', '')
            
            # Add product info from batch query
            campaign_id = campaign.get('campaign_id')
            if campaign_id and campaign_id in product_info_map:
                campaign['product_data'] = product_info_map[campaign_id]

            # Fetch selected hooks and scripts for video ads selection
            if campaign.get('current_step') >= 4:  # Has hooks
                content = await v3_db_service.get_campaign_content(campaign_id)
                if content:
                    campaign['selected_hooks'] = content.get('selected_hooks', [])
                    campaign['selected_scripts'] = content.get('selected_scripts', [])
                    campaign['selected_angles'] = content.get('selected_angles', [])
        
        return {
            "campaigns": campaigns,
            "total": len(campaigns),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error("campaigns.list.error", f"Error getting user campaigns: {e}", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve campaigns")

@router.post("/campaign/fork")
async def fork_campaign(
    source_campaign_id: str = Body(..., embed=False, alias="source_campaign_id"),
    fork_from_step: int = Body(..., embed=False, alias="fork_from_step"),
    campaign_name: str = Body(..., embed=False, alias="campaign_name"),
    current_user: dict = Depends(verify_token)
):
    """Fork a campaign from a specific step"""
    try:
        user_id = current_user.get("user_id")
        
        # Get source campaign
        source_campaign = await v3_db_service.get_campaign(source_campaign_id, user_id)
        if not source_campaign:
            raise HTTPException(status_code=404, detail="Source campaign not found")
        
        # Get source campaign content
        source_content = await v3_db_service.get_campaign_content(source_campaign_id)
        if not source_content:
            raise HTTPException(status_code=404, detail="Source campaign content not found")
        
        # Create new campaign
        new_campaign_id = str(uuid.uuid4())
        new_campaign = await v3_db_service.create_campaign(
            user_id=user_id,
            campaign_id=new_campaign_id,
            campaign_name=campaign_name
        )
        
        if not new_campaign:
            raise HTTPException(status_code=500, detail="Failed to create new campaign")
        
        # Copy content up to fork_from_step
        content_to_copy = {}
        
        # Map steps to content fields
        step_content_map = {
            0: [],  # Start
            1: ['product_info'],  # Import URL
            2: ['product_info'],  # Product Info
            3: ['marketing_analysis'],  # Marketing Analysis
            4: ['hooks'],  # Hooks
            5: ['scripts'],  # Scripts
            6: ['voice_data', 'actor_data'],  # Voice & Actor
            7: ['audio_data'],  # Audio
            8: ['video_data']  # Video
        }
        
        # Copy content based on fork_from_step
        for step in range(min(fork_from_step + 1, 9)):
            for field in step_content_map.get(step, []):
                if field in source_content:
                    content_to_copy[field] = source_content[field]
        
        # Save copied content to new campaign
        if content_to_copy:
            # Create campaign content entry
            await v3_db_service.save_campaign_content(new_campaign_id, content_to_copy)
        
        # Update campaign step
        await v3_db_service.update_campaign(new_campaign_id, {
            "current_step": fork_from_step,
            "status": "in_progress"
        })
        
        return {
            "success": True,
            "new_campaign_id": new_campaign_id,
            "new_conversation_id": new_campaign_id,  # For backward compatibility
            "campaign_name": campaign_name,
            "forked_from": source_campaign_id,
            "fork_step": fork_from_step
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.fork.error", f"Error forking campaign: {e}", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fork campaign")

# ==================== Get Single Campaign ====================

@router.get("/campaign/{campaign_id}")
async def get_campaign_details(
    campaign_id: str,
    current_user: dict = Depends(verify_token)
):
    """Get details for a specific campaign including product URL"""
    if not v3_db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        
        # Get campaign from V3 database
        campaign = await v3_db_service.get_campaign(campaign_id, user_id)
        
        if not campaign:
            raise HTTPException(status_code=404, detail=f"Campaign not found: {campaign_id}")
        
        # Get campaign content which includes product info
        content = await v3_db_service.get_campaign_content(campaign_id)
        
        # Build response with all available data
        response = {
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("campaign_name", ""),
            "current_step": campaign.get("current_step", 1),
            "status": campaign.get("status", "draft"),
            "created_at": campaign.get("created_at"),
            "updated_at": campaign.get("updated_at")
        }
        
        # Add product URL if available
        if campaign.get("product_url"):
            response["product_url"] = campaign["product_url"]
        
        # Add product info if available
        if content and content.get("product_info"):
            response["product_info"] = content["product_info"]
            # Also check if URL is in product info
            if not response.get("product_url") and content["product_info"].get("original_url"):
                response["product_url"] = content["product_info"]["original_url"]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.get.error", f"Error getting campaign: {e}", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get campaign details")

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
    if not v3_db_service:
        raise HTTPException(status_code=503, detail="Database service not available")
    
    try:
        user_id = current_user["user_id"]
        
        # Update campaign name - v3_db_service uses campaign_id as primary key
        # Note: v3_db_service.supabase is synchronous, not async
        result = v3_db_service.supabase.table("video_ads_v3_campaigns").update({
            "campaign_name": request.campaign_name,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("campaign_id", campaign_id).eq("user_id", user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Campaign not found: {campaign_id}")
        
        return {
            "status": "success",
            "campaign_id": campaign_id,
            "campaign_name": request.campaign_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("campaign.rename.error", f"Error updating campaign name: {e}", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update campaign name")

# ==================== Continue with more endpoints... ====================