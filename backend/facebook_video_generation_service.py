"""
Facebook Campaign Video Generation Service
Handles background video generation for Facebook campaigns created from marketing research
"""

import os
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import aiohttp
from dotenv import load_dotenv
from logging_service import logger
from hedra_client import HedraAPIClient
from s3_service import s3_service
from actor_image_handler import ActorImageHandler
from actor_images_config import ACTOR_IMAGES

load_dotenv()

# API Keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
HEDRA_API_KEY = os.getenv("HEDRA_API_KEY")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"


class FacebookVideoGenerationService:
    """Service for generating videos for Facebook campaigns"""

    def __init__(self):
        self.hedra_client = HedraAPIClient(HEDRA_API_KEY) if HEDRA_API_KEY else None
        self.actor_handler = ActorImageHandler()
        self.temp_dir = Path(tempfile.gettempdir()) / "campaign_videos"
        self.temp_dir.mkdir(exist_ok=True)

    async def generate_audio_elevenlabs(self, text: str, voice_id: str) -> Optional[str]:
        """
        Generate audio using ElevenLabs API
        Returns: S3 URL of generated audio file, or None if failed
        """
        if not ELEVENLABS_API_KEY:
            logger.error("video_gen.audio.no_api_key", "ElevenLabs API key not configured")
            return None

        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }

            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }

            logger.info("video_gen.audio.generating", f"Generating audio with voice {voice_id}")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        audio_data = await response.read()

                        # Upload to S3
                        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        s3_key = f"generated_audio/campaign_audio_{timestamp}.mp3"

                        # Use upload_file_from_bytes (it's synchronous, but fast enough)
                        audio_url = s3_service.upload_file_from_bytes(
                            file_content=audio_data,
                            s3_key=s3_key,
                            content_type="audio/mpeg"
                        )

                        logger.info("video_gen.audio.success", f"Audio generated and uploaded to {audio_url}")
                        return audio_url
                    else:
                        error_text = await response.text()
                        logger.error("video_gen.audio.failed", f"ElevenLabs API error: {response.status} - {error_text}")
                        return None

        except Exception as e:
            logger.error("video_gen.audio.error", f"Error generating audio: {e}", error=str(e))
            return None

    async def download_video_from_url(self, video_url: str, local_path: str) -> bool:
        """
        Download video from URL to local file
        Returns: True if successful, False otherwise
        """
        try:
            logger.info("video_gen.download.start", f"Downloading video from {video_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        video_data = await response.read()

                        # Ensure parent directory exists
                        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

                        # Save to local file
                        with open(local_path, 'wb') as f:
                            f.write(video_data)

                        logger.info("video_gen.download.success", f"Video downloaded to {local_path}")
                        return True
                    else:
                        logger.error("video_gen.download.failed", f"Download failed with status {response.status}")
                        return False
        except Exception as e:
            logger.error("video_gen.download.error", f"Error downloading video: {e}", error=str(e))
            return False

    async def generate_video_hedra(
        self,
        audio_url: str,
        actor_filename: str,
        campaign_id: str,
        script_id: str
    ) -> Optional[Tuple[str, str]]:
        """
        Generate video using Hedra API
        Returns: (s3_url, local_path) tuple, or None if failed

        Flow:
        1. Get actor image local path
        2. Generate video with Hedra (returns Hedra URL)
        3. Download video locally
        4. Upload to S3
        5. Return both S3 URL and local path (local path needed for Facebook upload)
        """
        if not self.hedra_client:
            logger.error("video_gen.video.no_client", "Hedra client not initialized")
            return None

        try:
            # Step 1: Get actor image local path
            logger.info("video_gen.video.actor", f"Getting actor image: {actor_filename}")
            try:
                actor_image_path = await self.actor_handler.get_actor_image_path(actor_filename)
            except Exception as e:
                logger.warning("video_gen.video.actor_failed", f"Actor not found, using default: {e}")
                actor_image_path = await self.actor_handler.get_actor_image_path("actor-01.jpg")

            logger.info("video_gen.video.generating", f"Generating video with audio: {audio_url}, actor: {actor_image_path}")

            # Step 2: Generate video using Hedra
            # Note: Hedra client returns video URL from their service
            hedra_video_url = await self.hedra_client.generate_video(
                audio_url=audio_url,
                image_url=actor_image_path
            )

            if not hedra_video_url:
                logger.error("video_gen.video.failed", "Hedra returned no video URL")
                return None

            logger.info("video_gen.video.hedra_complete", f"Hedra video URL: {hedra_video_url}")

            # Step 3: Download video locally
            local_filename = f"{campaign_id}_{script_id}_{datetime.utcnow().timestamp()}.mp4"
            local_path = str(self.temp_dir / local_filename)

            download_success = await self.download_video_from_url(hedra_video_url, local_path)
            if not download_success:
                logger.error("video_gen.video.download_failed", "Failed to download video from Hedra")
                return None

            # Step 4: Upload to S3
            s3_url = s3_service.upload_file(
                local_path,
                file_type="video",
                campaign_id=campaign_id
            )

            if not s3_url:
                logger.error("video_gen.video.s3_failed", "Failed to upload video to S3")
                # Return local path anyway since we have the video locally
                return (None, local_path)

            logger.info("video_gen.video.success", f"Video uploaded to S3: {s3_url}")

            # Step 5: Return both URLs
            # S3 URL for display/CDN, local path for Facebook upload
            return (s3_url, local_path)

        except Exception as e:
            logger.error("video_gen.video.error", f"Error generating video: {e}", error=str(e))
            return None

    async def generate_script_video(
        self,
        script_data: Dict[str, Any],
        voice_id: str,
        actor_filename: str,
        campaign_id: str
    ) -> Dict[str, Any]:
        """
        Generate a complete video for a single script

        Args:
            script_data: Dict containing hook_text, full_script, cta, script_id
            voice_id: ElevenLabs voice ID
            actor_filename: Actor image filename (e.g., "actor-01.jpg")
            campaign_id: Campaign ID for file organization

        Returns:
            Dict with status, audio_url, video_s3_url, video_local_path, error
        """
        result = {
            "status": "pending",
            "audio_url": None,
            "video_s3_url": None,
            "video_local_path": None,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None
        }

        try:
            # Step 1: Combine text (hook + script + CTA)
            hook_text = script_data.get('hook_text', '')
            full_script = script_data.get('full_script', '')
            cta = script_data.get('cta', '')
            script_id = script_data.get('script_id', 'unknown')

            combined_text = f"{hook_text}\n\n{full_script}\n\n{cta}"

            logger.info("video_gen.script.start", f"Generating video for script {script_id}")

            # Step 2: Generate audio
            result["status"] = "generating_audio"
            audio_url = await self.generate_audio_elevenlabs(combined_text, voice_id)

            if not audio_url:
                result["status"] = "failed"
                result["error"] = "Audio generation failed"
                result["completed_at"] = datetime.utcnow().isoformat()
                return result

            result["audio_url"] = audio_url

            # Step 3: Generate video (returns S3 URL and local path)
            result["status"] = "generating_video"
            video_result = await self.generate_video_hedra(
                audio_url=audio_url,
                actor_filename=actor_filename,
                campaign_id=campaign_id,
                script_id=script_id
            )

            if not video_result:
                result["status"] = "failed"
                result["error"] = "Video generation failed"
                result["completed_at"] = datetime.utcnow().isoformat()
                return result

            # Unpack the tuple (s3_url, local_path)
            s3_url, local_path = video_result
            result["video_s3_url"] = s3_url
            result["video_local_path"] = local_path

            result["status"] = "completed"
            result["completed_at"] = datetime.utcnow().isoformat()

            logger.info("video_gen.script.success", f"Video generated successfully for script {script_id}")

            return result

        except Exception as e:
            logger.error("video_gen.script.error", f"Error generating script video: {e}", error=str(e))
            result["status"] = "failed"
            result["error"] = str(e)
            result["completed_at"] = datetime.utcnow().isoformat()
            return result


# ===== Voice and Actor Helper Functions =====

async def get_elevenlabs_voices() -> List[Dict[str, Any]]:
    """
    Fetch ElevenLabs voices for Facebook campaigns
    Returns simplified list of voices with voice_id, name, description
    """
    if not ELEVENLABS_API_KEY:
        logger.warning("video_gen.voices.no_api_key", "ElevenLabs API key not configured")
        return []

    try:
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

        logger.info("video_gen.voices.fetching", "Fetching voices from ElevenLabs API")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ELEVENLABS_API_URL}/voices",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    logger.error("video_gen.voices.failed", f"ElevenLabs API returned {response.status}")
                    return []

                voices_data = await response.json()

        voices = []
        for voice_data in voices_data.get("voices", []):
            # Parse labels for additional info
            labels = voice_data.get("labels", {})
            gender = labels.get("gender") if isinstance(labels, dict) else None
            age = labels.get("age") if isinstance(labels, dict) else None
            accent = labels.get("accent") if isinstance(labels, dict) else None

            voices.append({
                "voice_id": voice_data["voice_id"],
                "name": voice_data["name"],
                "description": voice_data.get("description", ""),
                "category": voice_data.get("category", "general"),
                "gender": gender,
                "age": age,
                "accent": accent
            })

        logger.info("video_gen.voices.success", f"Retrieved {len(voices)} voices from ElevenLabs")
        return voices

    except Exception as e:
        logger.error("video_gen.voices.error", f"Error fetching ElevenLabs voices: {e}", error=str(e))
        return []


def get_actor_images() -> List[Dict[str, Any]]:
    """
    Get actor images configuration for Facebook campaigns
    Returns list of actors with filename, name, description, category
    """
    actors = []
    for filename, info in ACTOR_IMAGES.items():
        actors.append({
            "filename": filename,
            "name": info["name"],
            "description": info["description"],
            "category": info["category"]
        })

    logger.info("video_gen.actors.loaded", f"Loaded {len(actors)} actor images")
    return actors


async def post_campaign_to_facebook(
    campaign_id: str,
    video_generation_status: Dict[str, Any],
    selected_scripts: List[Dict[str, Any]],
    service_role_client: Any
) -> None:
    """
    Post campaign to Facebook after all videos have been generated

    Creates:
    - 1 Facebook Campaign
    - 1 Ad Set
    - Multiple Ads (one per video)
    """
    try:
        from facebook_ads_creation_service import FacebookAdsCreationService
        from facebook_database_service import FacebookDatabaseService
        from facebook_ad_creation_models import (
            VideoAdCreateRequest,
            VideoAdSelection,
            CampaignCreateRequest,
            CampaignObjective,
            AdStatus,
            TargetingSpec,
            GeoLocation
        )

        logger.info("campaign.facebook_post.fetch_data",
                   f"Fetching campaign data for {campaign_id}",
                   campaign_id=campaign_id)

        # 1. Get campaign data from database
        campaign_result = service_role_client.table("facebook_campaign_scripts").select("*").eq("id", campaign_id).execute()
        if not campaign_result.data:
            raise Exception(f"Campaign {campaign_id} not found")

        campaign_data = campaign_result.data[0]
        user_id = campaign_data["user_id"]
        ad_account_id = campaign_data["ad_account_id"]
        start_option = campaign_data["start_option"]

        logger.info("campaign.facebook_post.get_fb_account",
                   f"Getting Facebook account for user {user_id}",
                   campaign_id=campaign_id, user_id=user_id)

        # 2. Get user's Facebook access token and page_id
        fb_db_service = FacebookDatabaseService()
        fb_accounts = await fb_db_service.get_facebook_accounts_by_user(user_id)

        if not fb_accounts:
            raise Exception(f"No Facebook account found for user {user_id}")

        fb_account = fb_accounts[0]  # Use first active account
        access_token = fb_account["access_token"]
        page_id = fb_account.get("page_id")

        if not page_id:
            raise Exception(f"No Facebook page_id found for user {user_id}")

        logger.info("campaign.facebook_post.build_selections",
                   f"Building video selections for {len(selected_scripts)} scripts",
                   campaign_id=campaign_id)

        # 3. Build VideoAdSelection objects from video_generation_status and selected_scripts
        video_ad_selections = []
        for script in selected_scripts:
            script_id = script["script_id"]
            video_data = video_generation_status.get(script_id)

            if not video_data or video_data.get("status") != "completed":
                logger.warning("campaign.facebook_post.skip_video",
                             f"Skipping script {script_id} - not completed",
                             campaign_id=campaign_id, script_id=script_id)
                continue

            # Use local path instead of S3 URL for upload
            video_url = video_data.get("video_local_path") or video_data.get("video_s3_url")

            if not video_url:
                logger.warning("campaign.facebook_post.no_video_url",
                             f"No video URL for script {script_id}",
                             campaign_id=campaign_id, script_id=script_id)
                continue

            video_ad_selections.append(VideoAdSelection(
                video_ad_id=script_id,
                campaign_id=campaign_data["research_campaign_id"],
                hook=script["hook_text"],
                script=script.get("full_script", script.get("script_preview", "")),
                angle_type=script["angle_type"],
                video_url=video_url,
                thumbnail_url=None,  # Will use placeholder
                duration_seconds=30,  # Default duration
                landing_url=campaign_data["creative_settings"]["landing_page_url"],
                cta_text=campaign_data["creative_settings"]["cta_button"]
            ))

        if not video_ad_selections:
            raise Exception("No completed videos available for Facebook posting")

        logger.info("campaign.facebook_post.build_campaign_settings",
                   f"Building campaign settings",
                   campaign_id=campaign_id)

        # 4. Build CampaignCreateRequest
        # Map start_option to Facebook status
        fb_campaign_status = AdStatus.PAUSED
        if start_option == "immediately":
            fb_campaign_status = AdStatus.ACTIVE
        elif start_option == "draft":
            fb_campaign_status = AdStatus.PAUSED
        elif start_option == "schedule":
            fb_campaign_status = AdStatus.ACTIVE  # Will set start_time on adset

        new_campaign_settings = CampaignCreateRequest(
            name=campaign_data["campaign_name"],
            objective=CampaignObjective.OUTCOME_SALES,  # Using OUTCOME_SALES for conversions
            status=fb_campaign_status,
            special_ad_categories=["NONE"]
        )

        logger.info("campaign.facebook_post.build_targeting",
                   f"Building targeting spec",
                   campaign_id=campaign_id)

        # 5. Build TargetingSpec from campaign's targeting_spec
        targeting_data = campaign_data["targeting_spec"]

        # Map our targeting format to Facebook's format
        targeting = TargetingSpec(
            geo_locations=GeoLocation(
                countries=targeting_data.get("locations", ["US"])
            ),
            age_min=targeting_data.get("age_min", 18),
            age_max=targeting_data.get("age_max", 65),
            genders=None,  # Will be set based on gender field
            publisher_platforms=["facebook", "instagram"]
        )

        # Map gender
        gender = targeting_data.get("gender", "all").lower()
        if gender == "male":
            targeting.genders = [1]
        elif gender == "female":
            targeting.genders = [2]
        # If "all", leave genders as None

        # Convert daily budget from dollars to cents
        daily_budget_cents = int(campaign_data["daily_budget_per_adset"] * 100)

        logger.info("campaign.facebook_post.create_request",
                   f"Creating VideoAdCreateRequest with {len(video_ad_selections)} videos",
                   campaign_id=campaign_id)

        # 6. Build VideoAdCreateRequest
        video_ad_request = VideoAdCreateRequest(
            video_ad_selections=video_ad_selections,
            campaign_strategy="new",
            new_campaign_settings=new_campaign_settings,
            adset_strategy="new",
            targeting=targeting,
            daily_budget=daily_budget_cents,
            test_structure="single",  # Changed from TestStructure.SINGLE to string
            auto_generate_names=True,
            start_ads_paused=(fb_campaign_status == AdStatus.PAUSED),
            create_instagram_ads=True
        )

        logger.info("campaign.facebook_post.init_service",
                   f"Initializing Facebook Ads Creation Service",
                   campaign_id=campaign_id)

        # 7. Initialize FacebookAdsCreationService
        fb_app_id = os.getenv("FACEBOOK_APP_ID")
        fb_app_secret = os.getenv("FACEBOOK_APP_SECRET")

        if not fb_app_id or not fb_app_secret:
            raise Exception("Facebook App ID and Secret not configured")

        fb_service = FacebookAdsCreationService(fb_app_id, fb_app_secret)

        logger.info("campaign.facebook_post.create_ads",
                   f"Creating ads on Facebook",
                   campaign_id=campaign_id)

        # 8. Call create_ads_from_videos
        result = await fb_service.create_ads_from_videos(
            request=video_ad_request,
            ad_account_id=ad_account_id,
            page_id=page_id,
            access_token=access_token
        )

        if not result.success:
            error_msg = "; ".join(result.errors) if result.errors else "Unknown error"
            raise Exception(f"Facebook ad creation failed: {error_msg}")

        logger.info("campaign.facebook_post.success",
                   f"Successfully created {len(result.ads_created)} ads on Facebook",
                   campaign_id=campaign_id,
                   fb_campaign_id=result.campaign_id,
                   fb_adset_id=result.adset_id)

        # 9. Update database with Facebook IDs
        facebook_ad_ids = [ad["facebook_ad_id"] for ad in result.ads_created]

        service_role_client.table("facebook_campaign_scripts").update({
            "status": "completed",
            "facebook_campaign_id": result.campaign_id,
            "facebook_adset_id": result.adset_id,
            "facebook_ad_ids": facebook_ad_ids,
            "completed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", campaign_id).execute()

        logger.info("campaign.facebook_post.complete",
                   f"Campaign {campaign_id} successfully posted to Facebook",
                   campaign_id=campaign_id,
                   fb_campaign_id=result.campaign_id,
                   ads_count=len(result.ads_created))

    except Exception as e:
        logger.error("campaign.facebook_post.error",
                   f"Error posting campaign to Facebook: {e}",
                   campaign_id=campaign_id, error=str(e))
        raise


# Global service instance
video_gen_service = FacebookVideoGenerationService()


async def process_campaign_video_generation(
    campaign_id: str,
    selected_scripts: List[Dict[str, Any]],
    voice_actor: str,
    video_avatar: str,
    service_role_client
):
    """
    Background task to generate videos for all scripts in a campaign

    Args:
        campaign_id: Campaign UUID
        selected_scripts: List of script dicts with hook_text, full_script, cta, script_id
        voice_actor: ElevenLabs voice ID
        video_avatar: Actor image filename (e.g., "actor-01.jpg")
        service_role_client: Supabase client with service role (to bypass RLS)
    """
    try:
        logger.info("campaign.video_gen.start", f"Starting video generation for campaign {campaign_id}",
                   campaign_id=campaign_id, script_count=len(selected_scripts))

        # Update campaign status to generating_videos
        service_role_client.table("facebook_campaign_scripts").update({
            "status": "generating_videos",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", campaign_id).execute()

        # Initialize video_generation_status
        video_generation_status = {}
        total_scripts = len(selected_scripts)
        completed_count = 0

        # Process each script
        for idx, script in enumerate(selected_scripts):
            script_id = script.get('script_id')

            logger.info("campaign.video_gen.script",
                       f"Generating video {idx + 1}/{total_scripts} for script {script_id}",
                       campaign_id=campaign_id, script_id=script_id)

            # Generate video for this script
            result = await video_gen_service.generate_script_video(
                script_data=script,
                voice_id=voice_actor,
                actor_filename=video_avatar,
                campaign_id=campaign_id
            )

            # Update status for this script
            video_generation_status[script_id] = result

            if result["status"] == "completed":
                completed_count += 1

            # Update database with current progress
            service_role_client.table("facebook_campaign_scripts").update({
                "video_generation_status": video_generation_status,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", campaign_id).execute()

            logger.info("campaign.video_gen.progress",
                       f"Progress: {completed_count}/{total_scripts} videos completed",
                       campaign_id=campaign_id)

        # Determine final status
        if completed_count == total_scripts:
            final_status = "draft"  # All videos generated successfully, ready to publish
            logger.info("campaign.video_gen.complete",
                       f"All videos generated successfully for campaign {campaign_id}",
                       campaign_id=campaign_id)
        elif completed_count > 0:
            final_status = "partially_completed"  # Some videos failed
            logger.warning("campaign.video_gen.partial",
                          f"Only {completed_count}/{total_scripts} videos generated",
                          campaign_id=campaign_id)
        else:
            final_status = "failed"  # All videos failed
            logger.error("campaign.video_gen.failed",
                        f"All video generation failed for campaign {campaign_id}",
                        campaign_id=campaign_id)

        # Update campaign with final status
        update_data = {
            "status": final_status,
            "video_generation_status": video_generation_status,
            "updated_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat() if final_status == "draft" else None
        }

        service_role_client.table("facebook_campaign_scripts").update(update_data).eq("id", campaign_id).execute()

        logger.info("campaign.video_gen.done",
                   f"Video generation process completed for campaign {campaign_id}",
                   campaign_id=campaign_id, final_status=final_status)

        # Post to Facebook if all videos completed successfully
        if final_status == "draft" and completed_count == total_scripts:
            logger.info("campaign.facebook_post.start",
                       f"Starting Facebook posting for campaign {campaign_id}",
                       campaign_id=campaign_id)

            # Update status to posting_to_facebook
            service_role_client.table("facebook_campaign_scripts").update({
                "status": "posting_to_facebook",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", campaign_id).execute()

            try:
                # Post to Facebook (this will use the local video files)
                await post_campaign_to_facebook(
                    campaign_id=campaign_id,
                    video_generation_status=video_generation_status,
                    selected_scripts=selected_scripts,
                    service_role_client=service_role_client
                )
            except Exception as fb_error:
                logger.error("campaign.facebook_post.failed",
                           f"Facebook posting failed for campaign {campaign_id}: {fb_error}",
                           campaign_id=campaign_id, error=str(fb_error))

                # Update status to posting_failed
                service_role_client.table("facebook_campaign_scripts").update({
                    "status": "posting_failed",
                    "facebook_post_error": str(fb_error),
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", campaign_id).execute()

            finally:
                # Clean up local video files
                logger.info("campaign.video_gen.cleanup",
                           f"Cleaning up local video files for campaign {campaign_id}",
                           campaign_id=campaign_id)
                for script_id, video_data in video_generation_status.items():
                    if video_data.get("video_local_path"):
                        try:
                            import os
                            if os.path.exists(video_data["video_local_path"]):
                                os.remove(video_data["video_local_path"])
                                logger.info("campaign.video_gen.file_removed",
                                          f"Removed local file: {video_data['video_local_path']}")
                        except Exception as cleanup_error:
                            logger.warning("campaign.video_gen.cleanup_failed",
                                         f"Failed to remove file {video_data['video_local_path']}: {cleanup_error}")

    except Exception as e:
        logger.error("campaign.video_gen.error",
                    f"Error in campaign video generation: {e}",
                    campaign_id=campaign_id, error=str(e))

        # Update campaign status to failed
        try:
            service_role_client.table("facebook_campaign_scripts").update({
                "status": "failed",
                "error_message": str(e),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", campaign_id).execute()
        except Exception as db_error:
            logger.error("campaign.video_gen.db_update_failed",
                        f"Failed to update campaign status: {db_error}",
                        campaign_id=campaign_id)
