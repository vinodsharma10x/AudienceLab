"""
Video Ads V2 Database Service
Handles all database operations for the video ads v2 workflow
"""

import uuid
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from supabase import Client
import os
from dotenv import load_dotenv

load_dotenv()

class VideoAdsV2DatabaseService:
    def __init__(self, supabase_client: Client):
        """Initialize the database service with a Supabase client"""
        self.db = supabase_client
    
    # ==================== Campaign Management ====================
    
    async def create_campaign(self, user_id: str, conversation_id: str, campaign_name: Optional[str] = None) -> Dict:
        """Create a new campaign"""
        data = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "campaign_name": campaign_name or f"Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "current_step": 1,
            "status": "draft"
        }
        
        result = self.db.table("video_ads_v2_campaigns").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_campaign_by_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict]:
        """Get campaign by conversation ID"""
        result = self.db.table("video_ads_v2_campaigns")\
            .select("*")\
            .eq("conversation_id", conversation_id)\
            .eq("user_id", user_id)\
            .execute()
        
        # Return first result if exists, otherwise None
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    async def update_campaign_step(self, campaign_id: str, step: int, status: str = "in_progress") -> Dict:
        """Update campaign's current step and status"""
        data = {
            "current_step": step,
            "status": status
        }
        
        result = self.db.table("video_ads_v2_campaigns")\
            .update(data)\
            .eq("id", campaign_id)\
            .execute()
        
        return result.data[0] if result.data else None
    
    async def get_user_campaigns(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get all campaigns for a user"""
        result = self.db.table("video_ads_v2_campaigns")\
            .select("*, video_ads_v2_product_info(product_data)")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return result.data if result.data else []
    
    # ==================== Product Info (Step 1-2) ====================
    
    async def save_product_info(self, campaign_id: str, product_info: Dict, url: Optional[str] = None) -> Dict:
        """Save or update product info for a campaign"""
        data = {
            "campaign_id": campaign_id,
            "product_data": product_info,
            "url": url,
            "source": "url_extract" if url else "manual"
        }
        
        # Upsert (insert or update based on campaign_id)
        result = self.db.table("video_ads_v2_product_info")\
            .upsert(data, on_conflict="campaign_id")\
            .execute()
        
        return result.data[0] if result.data else None
    
    async def get_product_info(self, campaign_id: str) -> Optional[Dict]:
        """Get product info for a campaign"""
        result = self.db.table("video_ads_v2_product_info")\
            .select("*")\
            .eq("campaign_id", campaign_id)\
            .single()\
            .execute()
        
        if result.data:
            return {
                "url": result.data.get("url"),
                "source": result.data.get("source"),
                **result.data.get("product_data", {})
            }
        return None
    
    # ==================== Marketing Analysis (Step 3) ====================
    
    async def save_marketing_analysis(self, campaign_id: str, analysis: Dict, 
                                     selected_angles: Optional[List] = None,
                                     processing_time_ms: Optional[int] = None,
                                     claude_model: Optional[str] = None) -> Dict:
        """Save marketing analysis with 4 phases"""
        data = {
            "campaign_id": campaign_id,
            "avatar_analysis": analysis.get("avatar_analysis"),
            "journey_mapping": analysis.get("journey_mapping"),
            "objections_analysis": analysis.get("objections_analysis"),
            "angles_generation": analysis.get("angles_generation"),
            "selected_angles": selected_angles,
            "processing_time_ms": processing_time_ms,
            "claude_model": claude_model
        }
        
        result = self.db.table("video_ads_v2_marketing_analysis")\
            .upsert(data, on_conflict="campaign_id")\
            .execute()
        
        return result.data[0] if result.data else None
    
    async def get_marketing_analysis(self, campaign_id: str) -> Optional[Dict]:
        """Get marketing analysis for a campaign"""
        result = self.db.table("video_ads_v2_marketing_analysis")\
            .select("*")\
            .eq("campaign_id", campaign_id)\
            .single()\
            .execute()
        
        return result.data if result.data else None
    
    async def update_selected_angles(self, campaign_id: str, selected_angles: List[Dict]) -> Dict:
        """Update only the selected angles"""
        data = {"selected_angles": selected_angles}
        
        result = self.db.table("video_ads_v2_marketing_analysis")\
            .update(data)\
            .eq("campaign_id", campaign_id)\
            .execute()
        
        return result.data[0] if result.data else None
    
    # ==================== Hooks (Step 4) ====================
    
    async def save_hooks(self, campaign_id: str, hooks_data: Dict, 
                        selected_hooks: Optional[List] = None,
                        processing_time_ms: Optional[int] = None) -> Dict:
        """Save generated hooks"""
        data = {
            "campaign_id": campaign_id,
            "hooks_data": hooks_data,
            "selected_hooks": selected_hooks,
            "processing_time_ms": processing_time_ms
        }
        
        result = self.db.table("video_ads_v2_hooks")\
            .upsert(data, on_conflict="campaign_id")\
            .execute()
        
        return result.data[0] if result.data else None
    
    async def get_hooks(self, campaign_id: str) -> Optional[Dict]:
        """Get hooks for a campaign"""
        result = self.db.table("video_ads_v2_hooks")\
            .select("*")\
            .eq("campaign_id", campaign_id)\
            .single()\
            .execute()
        
        return result.data if result.data else None
    
    async def update_selected_hooks(self, campaign_id: str, selected_hooks: List[Dict]) -> Dict:
        """Update only the selected hooks"""
        data = {"selected_hooks": selected_hooks}
        
        result = self.db.table("video_ads_v2_hooks")\
            .update(data)\
            .eq("campaign_id", campaign_id)\
            .execute()
        
        return result.data[0] if result.data else None
    
    # ==================== Scripts (Step 5) ====================
    
    async def save_scripts(self, campaign_id: str, scripts_data: Dict,
                          selected_scripts: Optional[List] = None,
                          processing_time_ms: Optional[int] = None) -> Dict:
        """Save generated scripts"""
        data = {
            "campaign_id": campaign_id,
            "scripts_data": scripts_data,
            "selected_scripts": selected_scripts,
            "processing_time_ms": processing_time_ms
        }
        
        result = self.db.table("video_ads_v2_scripts")\
            .upsert(data, on_conflict="campaign_id")\
            .execute()
        
        return result.data[0] if result.data else None
    
    async def get_scripts(self, campaign_id: str) -> Optional[Dict]:
        """Get scripts for a campaign"""
        result = self.db.table("video_ads_v2_scripts")\
            .select("*")\
            .eq("campaign_id", campaign_id)\
            .single()\
            .execute()
        
        return result.data if result.data else None
    
    async def update_selected_scripts(self, campaign_id: str, selected_scripts: List[Dict]) -> Dict:
        """Update only the selected scripts"""
        data = {"selected_scripts": selected_scripts}
        
        result = self.db.table("video_ads_v2_scripts")\
            .update(data)\
            .eq("campaign_id", campaign_id)\
            .execute()
        
        return result.data[0] if result.data else None
    
    # ==================== Voice/Actor Selection (Step 6) ====================
    
    async def save_selections(self, campaign_id: str, voice_data: Dict, actor_data: Dict) -> Dict:
        """Save voice and actor selections"""
        data = {
            "campaign_id": campaign_id,
            "voice_data": voice_data,
            "actor_data": actor_data
        }
        
        result = self.db.table("video_ads_v2_selections")\
            .upsert(data, on_conflict="campaign_id")\
            .execute()
        
        return result.data[0] if result.data else None
    
    async def get_selections(self, campaign_id: str) -> Optional[Dict]:
        """Get voice and actor selections for a campaign"""
        result = self.db.table("video_ads_v2_selections")\
            .select("*")\
            .eq("campaign_id", campaign_id)\
            .single()\
            .execute()
        
        return result.data if result.data else None
    
    # ==================== Media (Steps 7-8) ====================
    
    async def save_media(self, campaign_id: str, media_type: str, script_id: str,
                        file_url: str, file_metadata: Optional[Dict] = None,
                        processing_time_ms: Optional[int] = None) -> Dict:
        """Save audio or video media"""
        data = {
            "campaign_id": campaign_id,
            "media_type": media_type,
            "script_id": script_id,
            "file_url": file_url,
            "file_metadata": file_metadata or {},
            "processing_time_ms": processing_time_ms
        }
        
        result = self.db.table("video_ads_v2_media").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_media(self, campaign_id: str, media_type: Optional[str] = None) -> List[Dict]:
        """Get media files for a campaign"""
        query = self.db.table("video_ads_v2_media")\
            .select("*")\
            .eq("campaign_id", campaign_id)
        
        if media_type:
            query = query.eq("media_type", media_type)
        
        result = query.order("created_at").execute()
        return result.data if result.data else []
    
    # ==================== Campaign Forking ====================
    
    async def fork_campaign(self, source_campaign_id: str, user_id: str, 
                           up_to_step: int, new_campaign_name: Optional[str] = None) -> tuple[str, str]:
        """
        Fork a campaign up to a specific step
        Returns: (new_conversation_id, new_campaign_id)
        """
        # 1. Get source campaign
        source_campaign = self.db.table("video_ads_v2_campaigns")\
            .select("*")\
            .eq("id", source_campaign_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not source_campaign.data:
            raise ValueError("Source campaign not found")
        
        # 2. Create new campaign
        new_conversation_id = str(uuid.uuid4())
        new_campaign_data = {
            "user_id": user_id,
            "conversation_id": new_conversation_id,
            "parent_campaign_id": source_campaign_id,
            "campaign_name": new_campaign_name or f"{source_campaign.data['campaign_name']} (Copy)",
            "current_step": up_to_step,
            "status": "draft"
        }
        
        new_campaign = self.db.table("video_ads_v2_campaigns")\
            .insert(new_campaign_data)\
            .execute()
        
        if not new_campaign.data:
            raise ValueError("Failed to create new campaign")
        
        new_campaign_id = new_campaign.data[0]["id"]
        
        # 3. Copy data based on up_to_step
        
        # Copy product info (step 2)
        if up_to_step >= 2:
            product_info = self.db.table("video_ads_v2_product_info")\
                .select("*")\
                .eq("campaign_id", source_campaign_id)\
                .single()\
                .execute()
            
            if product_info.data:
                self.db.table("video_ads_v2_product_info").insert({
                    "campaign_id": new_campaign_id,
                    "url": product_info.data["url"],
                    "product_data": product_info.data["product_data"],
                    "source": product_info.data["source"]
                }).execute()
        
        # Copy marketing analysis (step 3)
        if up_to_step >= 3:
            marketing = self.db.table("video_ads_v2_marketing_analysis")\
                .select("*")\
                .eq("campaign_id", source_campaign_id)\
                .single()\
                .execute()
            
            if marketing.data:
                self.db.table("video_ads_v2_marketing_analysis").insert({
                    "campaign_id": new_campaign_id,
                    "avatar_analysis": marketing.data["avatar_analysis"],
                    "journey_mapping": marketing.data["journey_mapping"],
                    "objections_analysis": marketing.data["objections_analysis"],
                    "angles_generation": marketing.data["angles_generation"],
                    "selected_angles": marketing.data.get("selected_angles"),
                    "processing_time_ms": marketing.data.get("processing_time_ms"),
                    "claude_model": marketing.data.get("claude_model")
                }).execute()
        
        # Copy hooks (step 4)
        if up_to_step >= 4:
            hooks = self.db.table("video_ads_v2_hooks")\
                .select("*")\
                .eq("campaign_id", source_campaign_id)\
                .single()\
                .execute()
            
            if hooks.data:
                self.db.table("video_ads_v2_hooks").insert({
                    "campaign_id": new_campaign_id,
                    "hooks_data": hooks.data["hooks_data"],
                    "selected_hooks": hooks.data.get("selected_hooks"),
                    "processing_time_ms": hooks.data.get("processing_time_ms")
                }).execute()
        
        # Copy scripts (step 5)
        if up_to_step >= 5:
            scripts = self.db.table("video_ads_v2_scripts")\
                .select("*")\
                .eq("campaign_id", source_campaign_id)\
                .single()\
                .execute()
            
            if scripts.data:
                self.db.table("video_ads_v2_scripts").insert({
                    "campaign_id": new_campaign_id,
                    "scripts_data": scripts.data["scripts_data"],
                    "selected_scripts": scripts.data.get("selected_scripts"),
                    "processing_time_ms": scripts.data.get("processing_time_ms")
                }).execute()
        
        # Copy selections (step 6)
        if up_to_step >= 6:
            selections = self.db.table("video_ads_v2_selections")\
                .select("*")\
                .eq("campaign_id", source_campaign_id)\
                .single()\
                .execute()
            
            if selections.data:
                self.db.table("video_ads_v2_selections").insert({
                    "campaign_id": new_campaign_id,
                    "voice_data": selections.data.get("voice_data"),
                    "actor_data": selections.data.get("actor_data")
                }).execute()
        
        # Copy media (steps 7-8)
        if up_to_step >= 7:
            media = self.db.table("video_ads_v2_media")\
                .select("*")\
                .eq("campaign_id", source_campaign_id)\
                .execute()
            
            for media_item in (media.data or []):
                # Only copy audio for step 7, include video for step 8
                if media_item["media_type"] == "audio" or up_to_step >= 8:
                    self.db.table("video_ads_v2_media").insert({
                        "campaign_id": new_campaign_id,
                        "media_type": media_item["media_type"],
                        "script_id": media_item["script_id"],
                        "file_url": media_item["file_url"],
                        "file_metadata": media_item.get("file_metadata"),
                        "processing_time_ms": media_item.get("processing_time_ms")
                    }).execute()
        
        return new_conversation_id, new_campaign_id
    
    # ==================== Complete Campaign Data ====================
    
    async def get_complete_campaign_data(self, campaign_id: str) -> Dict:
        """Get all data for a campaign across all tables"""
        # Get campaign
        campaign = self.db.table("video_ads_v2_campaigns")\
            .select("*")\
            .eq("id", campaign_id)\
            .single()\
            .execute()
        
        if not campaign.data:
            return None
        
        result = {"campaign": campaign.data}
        
        # Get product info
        product_info = await self.get_product_info(campaign_id)
        if product_info:
            result["product_info"] = product_info
        
        # Get marketing analysis
        marketing = await self.get_marketing_analysis(campaign_id)
        if marketing:
            result["marketing_analysis"] = marketing
        
        # Get hooks
        hooks = await self.get_hooks(campaign_id)
        if hooks:
            result["hooks"] = hooks
        
        # Get scripts
        scripts = await self.get_scripts(campaign_id)
        if scripts:
            result["scripts"] = scripts
        
        # Get selections
        selections = await self.get_selections(campaign_id)
        if selections:
            result["selections"] = selections
        
        # Get media
        media = await self.get_media(campaign_id)
        if media:
            result["media"] = media
        
        return result