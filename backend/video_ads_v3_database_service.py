"""
Video Ads V3 Database Service
Handles all database operations for V3 tables with stateless design
"""

import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncpg
import asyncio
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()


class VideoAdsV3DatabaseService:
    """Service for managing V3 video ads campaign data in Supabase"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            print("⚠️ Warning: Supabase credentials not found. Database operations will be disabled.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            print("✅ V3 Database service initialized")
    
    # ==================== Campaign Management ====================
    
    async def create_campaign(self, user_id: str, campaign_name: str = None, product_url: str = None) -> Dict[str, Any]:
        """Create a new campaign"""
        if not self.supabase:
            return None
        
        try:
            campaign_id = str(uuid.uuid4())
            
            data = {
                "user_id": user_id,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name or f"Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "product_url": product_url,
                "status": "draft",
                "current_step": 1
            }
            
            result = self.supabase.table("video_ads_v3_campaigns").insert(data).execute()
            
            if result.data:
                print(f"✅ Created V3 campaign: {campaign_id}")
                return result.data[0]
            
            return None
            
        except Exception as e:
            print(f"❌ Error creating V3 campaign: {e}")
            return None
    
    async def get_campaign(self, campaign_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get campaign by campaign_id"""
        if not self.supabase:
            return None
        
        try:
            query = self.supabase.table("video_ads_v3_campaigns").select("*").eq("campaign_id", campaign_id)
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting V3 campaign: {e}")
            return None
    
    async def get_user_campaigns(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's campaigns, ordered by most recent (optimized for list view)"""
        if not self.supabase:
            return []
        
        try:
            # Only select fields needed for the campaigns list view
            result = self.supabase.table("video_ads_v3_campaigns") \
                .select("campaign_id, campaign_name, current_step, status, created_at, updated_at") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"❌ Error getting user campaigns: {e}")
            return []
    
    async def update_campaign(self, campaign_id: str, updates: Dict[str, Any]) -> bool:
        """Update campaign details"""
        if not self.supabase:
            return False
        
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.supabase.table("video_ads_v3_campaigns").update(updates).eq("campaign_id", campaign_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error updating V3 campaign: {e}")
            return False
    
    async def list_campaigns(self, user_id: str) -> List[Dict[str, Any]]:
        """List all campaigns for a user"""
        if not self.supabase:
            return []
        
        try:
            result = self.supabase.table("video_ads_v3_campaigns").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            
            return result.data or []
            
        except Exception as e:
            print(f"❌ Error listing V3 campaigns: {e}")
            return []

    async def update_campaign_status(self, campaign_id: str, status: str, error_message: str = None) -> bool:
        """Update campaign status and optional error message"""
        if not self.supabase:
            return False

        try:
            updates = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }

            if error_message is not None:
                updates["error_message"] = error_message

            result = self.supabase.table("video_ads_v3_campaigns").update(updates).eq("campaign_id", campaign_id).execute()

            print(f"✅ Updated campaign status: {campaign_id} -> {status}")
            return bool(result.data)

        except Exception as e:
            print(f"❌ Error updating campaign status: {e}")
            return False

    # ==================== Campaign Content Management ====================
    
    async def save_product_info(self, campaign_id: str, product_data: Dict[str, Any]) -> bool:
        """Save or update product info for a campaign"""
        print(f"📊 save_product_info called: campaign_id={campaign_id}")
        if not self.supabase:
            print(f"❌ No Supabase client")
            return False
        
        try:
            # Get the campaign first
            campaign = await self.get_campaign(campaign_id)
            print(f"📊 Campaign lookup result: found={bool(campaign)}")
            if campaign:
                print(f"📊 Campaign details: id={campaign.get('id')}, campaign_id={campaign.get('campaign_id')}")
            if not campaign:
                print(f"❌ Campaign not found: {campaign_id}")
                return False
            
            # Check if content already exists
            print(f"📊 Checking for existing content with campaign_id={campaign['campaign_id']}")
            existing = self.supabase.table("video_ads_v3_campaign_content").select("id").eq("campaign_id", campaign["campaign_id"]).execute()
            print(f"📊 Existing content check result: {existing}")
            print(f"📊 Existing content found: {bool(existing.data)}")
            
            if existing.data:
                # Update existing
                print(f"📊 Updating existing content...")
                update_data = {
                    "product_data": product_data,
                    "updated_at": datetime.utcnow().isoformat()
                }
                print(f"📊 Update data: {update_data}")
                result = self.supabase.table("video_ads_v3_campaign_content").update(update_data).eq("campaign_id", campaign["campaign_id"]).execute()
                print(f"📊 Update result: {result}")
                print(f"📊 Update result data: {result.data}")
            else:
                # Create new
                print(f"📊 Creating new content with campaign_id={campaign['campaign_id']}")
                insert_data = {
                    "campaign_id": campaign["campaign_id"],
                    "product_data": product_data
                }
                print(f"📊 Insert data: {insert_data}")
                result = self.supabase.table("video_ads_v3_campaign_content").insert(insert_data).execute()
                print(f"📊 Insert result: {result}")
                print(f"📊 Insert result data: {result.data}")
                if result.data:
                    print(f"📊 Inserted record ID: {result.data[0].get('id')}")
            
            # Update campaign step
            print(f"📊 Updating campaign step to 2...")
            step_update = await self.update_campaign(campaign_id, {"current_step": 2})
            print(f"📊 Campaign step update result: {step_update}")
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error saving V3 product info: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    async def save_marketing_analysis(self, campaign_id: str, analysis_data: Dict[str, Any]) -> bool:
        """Save marketing analysis (avatars, journey, objections, angles)"""
        print(f"📊 save_marketing_analysis called: campaign_id={campaign_id}")
        if not self.supabase:
            print(f"❌ No Supabase client")
            return False
        
        try:
            campaign = await self.get_campaign(campaign_id)
            print(f"📊 Campaign lookup result: found={bool(campaign)}")
            if not campaign:
                print(f"❌ Campaign not found: {campaign_id}")
                return False
            
            # Check if content exists
            print(f"📊 Checking for existing content with campaign_id={campaign['campaign_id']}")
            existing = self.supabase.table("video_ads_v3_campaign_content").select("id").eq("campaign_id", campaign["campaign_id"]).execute()
            print(f"📊 Existing content found: {bool(existing.data)}")
            
            update_data = {
                "avatar_analysis": analysis_data.get("avatars"),
                "journey_mapping": analysis_data.get("journey"),
                "objections_analysis": analysis_data.get("objections"),
                "angles": analysis_data.get("angles"),
                "updated_at": datetime.utcnow().isoformat()
            }
            print(f"📊 Update data keys: {update_data.keys()}")
            
            if existing.data:
                print(f"📊 Updating existing content...")
                result = self.supabase.table("video_ads_v3_campaign_content").update(update_data).eq("campaign_id", campaign["campaign_id"]).execute()
                print(f"📊 Update result: {result}")
            else:
                print(f"📊 Creating new content...")
                update_data["campaign_id"] = campaign["campaign_id"]
                result = self.supabase.table("video_ads_v3_campaign_content").insert(update_data).execute()
                print(f"📊 Insert result: {result}")
            
            # Update campaign step
            print(f"📊 Updating campaign step to 3...")
            await self.update_campaign(campaign_id, {"current_step": 3})
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error saving V3 marketing analysis: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    async def save_hooks(self, campaign_id: str, hooks_data: List[Any]) -> bool:
        """Save generated hooks"""
        print(f"📊 save_hooks called: campaign_id={campaign_id}, hooks_count={len(hooks_data)}")
        if not self.supabase:
            print(f"❌ No Supabase client")
            return False
        
        try:
            campaign = await self.get_campaign(campaign_id)
            print(f"📊 Campaign lookup result: found={bool(campaign)}")
            if not campaign:
                print(f"❌ Campaign not found: {campaign_id}")
                return False
            
            update_data = {
                "hooks": hooks_data,
                "updated_at": datetime.utcnow().isoformat()
            }
            print(f"📊 Updating hooks for campaign_id={campaign['campaign_id']}")
            result = self.supabase.table("video_ads_v3_campaign_content").update(update_data).eq("campaign_id", campaign["campaign_id"]).execute()
            print(f"📊 Hooks update result: {result}")
            
            # Update campaign step
            print(f"📊 Updating campaign step to 4...")
            await self.update_campaign(campaign_id, {"current_step": 4})
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error saving V3 hooks: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    async def save_scripts(self, campaign_id: str, scripts_data: Any) -> bool:
        """Save generated scripts (supports both old List format and new Dict format with raw/restructured)"""

        # Handle both old format (List) and new format (Dict with raw/restructured)
        if isinstance(scripts_data, dict) and "raw" in scripts_data and "restructured" in scripts_data:
            # New format: save restructured to scripts column for frontend compatibility
            restructured = scripts_data["restructured"]
            raw = scripts_data["raw"]
            print(f"📊 save_scripts called: campaign_id={campaign_id}, raw_count={len(raw)}, restructured_angles={len(restructured.get('angles', []))}")
            scripts_to_save = [restructured]  # Wrap in array for backward compatibility
        else:
            # Old format: assume it's already in the correct format
            scripts_to_save = scripts_data if isinstance(scripts_data, list) else [scripts_data]
            print(f"📊 save_scripts called: campaign_id={campaign_id}, scripts_count={len(scripts_to_save)}")

        if not self.supabase:
            print(f"❌ No Supabase client")
            return False

        try:
            campaign = await self.get_campaign(campaign_id)
            print(f"📊 Campaign lookup result: found={bool(campaign)}")
            if not campaign:
                print(f"❌ Campaign not found: {campaign_id}")
                return False

            update_data = {
                "scripts": scripts_to_save,
                "updated_at": datetime.utcnow().isoformat()
            }
            print(f"📊 Updating scripts for campaign_id={campaign['campaign_id']}")
            result = self.supabase.table("video_ads_v3_campaign_content").update(update_data).eq("campaign_id", campaign["campaign_id"]).execute()
            print(f"📊 Scripts update result: {result}")

            # Update campaign step
            print(f"📊 Updating campaign step to 5...")
            await self.update_campaign(campaign_id, {"current_step": 5})

            return bool(result.data)

        except Exception as e:
            print(f"❌ Error saving V3 scripts: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    async def save_selected_angles(self, campaign_id: str, selected_angles: List[Any]) -> bool:
        """Save user's selected angles"""
        print(f"📊 save_selected_angles called: campaign_id={campaign_id}, angles_count={len(selected_angles)}")
        if not self.supabase:
            print(f"❌ No Supabase client")
            return False
        
        try:
            campaign = await self.get_campaign(campaign_id)
            print(f"📊 Campaign lookup result: found={bool(campaign)}")
            if not campaign:
                print(f"❌ Campaign not found: {campaign_id}")
                return False
            
            update_data = {
                "selected_angles": selected_angles,
                "updated_at": datetime.utcnow().isoformat()
            }
            print(f"📊 Updating selected angles for campaign_id={campaign['campaign_id']}")
            result = self.supabase.table("video_ads_v3_campaign_content").update(update_data).eq("campaign_id", campaign["campaign_id"]).execute()
            print(f"📊 Selected angles update result: {result}")
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error saving V3 selected angles: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    async def save_selected_hooks(self, campaign_id: str, selected_hooks: List[Any]) -> bool:
        """Save user's selected hooks"""
        print(f"📊 save_selected_hooks called: campaign_id={campaign_id}, hooks_count={len(selected_hooks)}")
        if not self.supabase:
            print(f"❌ No Supabase client")
            return False
        
        try:
            campaign = await self.get_campaign(campaign_id)
            print(f"📊 Campaign lookup result: found={bool(campaign)}")
            if not campaign:
                print(f"❌ Campaign not found: {campaign_id}")
                return False
            
            update_data = {
                "selected_hooks": selected_hooks,
                "updated_at": datetime.utcnow().isoformat()
            }
            print(f"📊 Updating selected hooks for campaign_id={campaign['campaign_id']}")
            result = self.supabase.table("video_ads_v3_campaign_content").update(update_data).eq("campaign_id", campaign["campaign_id"]).execute()
            print(f"📊 Selected hooks update result: {result}")
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error saving V3 selected hooks: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False
    
    # ==================== Campaign Content Retrieval ====================
    
    async def get_campaigns_product_info_batch(self, campaign_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get product info for multiple campaigns in a single query (batch optimization)"""
        if not self.supabase or not campaign_ids:
            return {}
        
        try:
            # Fetch all product data in one query
            result = self.supabase.table("video_ads_v3_campaign_content").select(
                "campaign_id, product_data"
            ).in_("campaign_id", campaign_ids).execute()
            
            # Return as a dictionary keyed by campaign_id
            product_info_map = {}
            if result.data:
                for item in result.data:
                    campaign_id = item.get("campaign_id")
                    if campaign_id:
                        product_info_map[campaign_id] = item.get("product_data")
            
            return product_info_map
            
        except Exception as e:
            print(f"❌ Error getting batch product info: {e}")
            return {}
    
    async def get_campaign_product_info(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get just the product info for a campaign (lightweight for listings)"""
        if not self.supabase:
            return None
        
        try:
            # Direct query without getting full campaign first
            result = self.supabase.table("video_ads_v3_campaign_content").select(
                "product_data"
            ).eq("campaign_id", campaign_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0].get("product_data")
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting product info: {e}")
            return None
    
    async def get_campaign_content(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get all campaign content"""
        if not self.supabase:
            return None
        
        try:
            campaign = await self.get_campaign(campaign_id)
            if not campaign:
                return None
            
            # Explicitly select all columns including the new selected_scripts, audio_data, and video_data columns
            result = self.supabase.table("video_ads_v3_campaign_content").select(
                "id, campaign_id, product_data, avatar_analysis, journey_mapping, objections_analysis, "
                "angles, selected_angles, hooks, selected_hooks, scripts, selected_scripts, audio_data, video_data, created_at, updated_at"
            ).eq("campaign_id", campaign["campaign_id"]).execute()
            
            if result.data and len(result.data) > 0:
                content = result.data[0]
                print(f"📚 Retrieved content keys: {list(content.keys())}")
                print(f"📚 Has selected_scripts: {'selected_scripts' in content}, value: {content.get('selected_scripts', 'NOT FOUND')}")
                return content
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting V3 campaign content: {e}")
            return None
    
    async def update_campaign_content(self, campaign_id: str, updates: Dict[str, Any]) -> bool:
        """Update campaign content with new data"""
        if not self.supabase:
            return False
        
        try:
            campaign = await self.get_campaign(campaign_id)
            if not campaign:
                return False
            
            # Check if content exists - use campaign_id, not id
            existing = self.supabase.table("video_ads_v3_campaign_content").select("id").eq("campaign_id", campaign["campaign_id"]).execute()
            
            update_data = {
                **updates,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if existing.data:
                print(f"📝 Updating existing content for campaign: {campaign['campaign_id']}")
                result = self.supabase.table("video_ads_v3_campaign_content").update(update_data).eq("campaign_id", campaign["campaign_id"]).execute()
                print(f"📝 Update result: {bool(result.data)}")
            else:
                update_data["campaign_id"] = campaign["campaign_id"]  # Use campaign_id, not id
                print(f"📝 Inserting new content for campaign: {campaign['campaign_id']}")
                result = self.supabase.table("video_ads_v3_campaign_content").insert(update_data).execute()
                print(f"📝 Insert result: {bool(result.data)}")
            
            print(f"📝 Campaign content saved: {campaign['campaign_id']}, data keys: {list(update_data.keys())}")
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error updating V3 campaign content: {e}")
            return False
    
    async def get_complete_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get complete campaign data including all content and videos"""
        if not self.supabase:
            return None
        
        try:
            campaign = await self.get_campaign(campaign_id)
            if not campaign:
                return None
            
            # Get campaign content
            content = await self.get_campaign_content(campaign_id)
            
            # Get all videos
            videos = await self.get_campaign_videos(campaign_id)
            
            return {
                "campaign": campaign,
                "content": content,
                "videos": videos
            }
            
        except Exception as e:
            print(f"❌ Error getting complete V3 campaign: {e}")
            return None
    
    # ==================== Video Management ====================
    
    async def create_video(self, campaign_id: str, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new video for a campaign"""
        if not self.supabase:
            return None
        
        try:
            campaign = await self.get_campaign(campaign_id)
            if not campaign:
                return None
            
            # Get next video number
            existing_videos = await self.get_campaign_videos(campaign_id)
            video_number = len(existing_videos) + 1
            
            data = {
                "campaign_id": campaign["campaign_id"],
                "video_number": video_number,
                "angle_data": video_data.get("angle_data"),
                "hook_data": video_data.get("hook_data"),
                "script_data": video_data.get("script_data"),
                "voice_data": video_data.get("voice_data"),
                "actor_data": video_data.get("actor_data"),
                "status": "draft"
            }
            
            result = self.supabase.table("video_ads_v3_videos").insert(data).execute()
            
            if result.data:
                print(f"✅ Created V3 video #{video_number} for campaign {campaign_id}")
                return result.data[0]
            
            return None
            
        except Exception as e:
            print(f"❌ Error creating V3 video: {e}")
            return None
    
    async def update_video(self, video_id: str, updates: Dict[str, Any]) -> bool:
        """Update video details"""
        if not self.supabase:
            return False
        
        try:
            result = self.supabase.table("video_ads_v3_videos").update(updates).eq("id", video_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error updating V3 video: {e}")
            return False
    
    async def get_campaign_videos(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get all videos for a campaign"""
        if not self.supabase:
            return []
        
        try:
            campaign = await self.get_campaign(campaign_id)
            if not campaign:
                return []
            
            result = self.supabase.table("video_ads_v3_videos").select("*").eq("campaign_id", campaign["campaign_id"]).order("video_number").execute()
            
            return result.data or []
            
        except Exception as e:
            print(f"❌ Error getting V3 campaign videos: {e}")
            return []
    
    async def save_video_generation(self, video_id: str, audio_url: str = None, video_url: str = None, 
                                   hedra_job_id: str = None, status: str = None) -> bool:
        """Update video with generation results"""
        if not self.supabase:
            return False
        
        try:
            updates = {}
            
            if audio_url:
                updates["audio_url"] = audio_url
            if video_url:
                updates["video_url"] = video_url
            if hedra_job_id:
                updates["hedra_job_id"] = hedra_job_id
            if status:
                updates["status"] = status
            
            if audio_url and not video_url:
                updates["status"] = "audio_generated"
            elif video_url:
                updates["status"] = "completed"
            
            result = self.supabase.table("video_ads_v3_videos").update(updates).eq("id", video_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error saving V3 video generation: {e}")
            return False
    
    async def save_campaign_content(self, campaign_id: str, content_data: Dict[str, Any]) -> bool:
        """Save or update campaign content"""
        if not self.supabase:
            return False
        
        try:
            # Check if campaign exists
            campaign = await self.get_campaign(campaign_id)
            if not campaign:
                print(f"❌ Campaign not found: {campaign_id}")
                return False
            
            # Check if content entry exists
            existing = self.supabase.table("video_ads_v3_campaign_content") \
                .select("campaign_id") \
                .eq("campaign_id", campaign["campaign_id"]) \
                .execute()
            
            content_data["updated_at"] = datetime.utcnow().isoformat()
            
            if existing.data:
                # Update existing content
                result = self.supabase.table("video_ads_v3_campaign_content") \
                    .update(content_data) \
                    .eq("campaign_id", campaign["campaign_id"]) \
                    .execute()
            else:
                # Create new content entry
                content_data["campaign_id"] = campaign["campaign_id"]
                content_data["created_at"] = datetime.utcnow().isoformat()
                result = self.supabase.table("video_ads_v3_campaign_content") \
                    .insert(content_data) \
                    .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"❌ Error saving campaign content: {e}")
            return False


    # ==================== Batch Processing Methods ====================

    async def update_batch_info(
        self,
        campaign_id: str,
        hooks_batch_id: str = None,
        scripts_batch_id: str = None,
        batch_status: str = None,
        batch_error: str = None
    ) -> bool:
        """Update batch processing information for a campaign"""
        if not self.supabase:
            return False

        try:
            update_data = {}

            if hooks_batch_id is not None:
                update_data["hooks_batch_id"] = hooks_batch_id

            if scripts_batch_id is not None:
                update_data["scripts_batch_id"] = scripts_batch_id

            if batch_status is not None:
                update_data["batch_status"] = batch_status

            if batch_error is not None:
                update_data["batch_error"] = batch_error

            # Update timestamps based on status
            if batch_status == "processing":
                update_data["batch_created_at"] = datetime.utcnow().isoformat()
            elif batch_status in ["completed", "failed"]:
                update_data["batch_completed_at"] = datetime.utcnow().isoformat()

            update_data["updated_at"] = datetime.utcnow().isoformat()

            result = self.supabase.table("video_ads_v3_campaigns") \
                .update(update_data) \
                .eq("campaign_id", campaign_id) \
                .execute()

            return bool(result.data)

        except Exception as e:
            print(f"❌ Error updating batch info: {e}")
            return False

    async def get_batch_info(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get batch processing information for a campaign"""
        if not self.supabase:
            return None

        try:
            result = self.supabase.table("video_ads_v3_campaigns") \
                .select("hooks_batch_id, scripts_batch_id, batch_status, batch_created_at, batch_completed_at, batch_error") \
                .eq("campaign_id", campaign_id) \
                .execute()

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            print(f"❌ Error getting batch info: {e}")
            return None

    async def get_campaigns_by_batch_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all campaigns with a specific batch status"""
        if not self.supabase:
            return []

        try:
            result = self.supabase.table("video_ads_v3_campaigns") \
                .select("campaign_id, campaign_name, batch_status, hooks_batch_id, scripts_batch_id, batch_created_at") \
                .eq("batch_status", status) \
                .execute()

            return result.data if result.data else []

        except Exception as e:
            print(f"❌ Error getting campaigns by batch status: {e}")
            return []


# Initialize the V3 database service
v3_db_service = VideoAdsV3DatabaseService()