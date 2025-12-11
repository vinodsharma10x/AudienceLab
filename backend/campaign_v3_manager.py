"""
Campaign V3 Manager - Stateless Campaign Management
Replaces the memory-based workflow manager with database-backed operations
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from video_ads_v3_database_service import v3_db_service


class CampaignV3Manager:
    """Stateless campaign manager that uses database instead of memory"""
    
    def __init__(self):
        self.db = v3_db_service
        print("✅ V3 Campaign Manager initialized (stateless)")
    
    async def create_campaign(self, user_id: str, product_url: str = None) -> str:
        """Create a new campaign and return campaign_id"""
        campaign = await self.db.create_campaign(user_id, product_url=product_url)
        
        if campaign:
            return campaign["campaign_id"]
        
        # Fallback if DB is not available
        return str(uuid.uuid4())
    
    async def get_campaign_state(self, campaign_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get complete campaign state from database"""
        
        # Get campaign details
        campaign = await self.db.get_campaign(campaign_id, user_id)
        if not campaign:
            return None
        
        # Get campaign content
        content = await self.db.get_campaign_content(campaign_id)
        
        # Build state object similar to old workflow manager
        state = {
            "user_id": campaign["user_id"],
            "campaign_id": campaign["campaign_id"],
            "campaign_name": campaign.get("campaign_name"),
            "current_step": campaign.get("current_step", 1),
            "created_at": campaign.get("created_at")
        }
        
        if content:
            state.update({
                "product_info": content.get("product_data"),
                "avatar_analysis": content.get("avatar_analysis"),
                "journey_mapping": content.get("journey_mapping"),
                "objections_analysis": content.get("objections_analysis"),
                "angles": content.get("angles"),
                "hooks": content.get("hooks"),
                "scripts": content.get("scripts"),
                "selected_angles": content.get("selected_angles"),
                "selected_hooks": content.get("selected_hooks")
            })
        
        return state
    
    async def update_product_info(self, campaign_id: str, product_data: Dict[str, Any]) -> bool:
        """Update product information"""
        return await self.db.save_product_info(campaign_id, product_data)
    
    async def update_marketing_analysis(self, campaign_id: str, analysis_data: Dict[str, Any]) -> bool:
        """Update marketing analysis (avatars, journey, objections, angles)"""
        return await self.db.save_marketing_analysis(campaign_id, analysis_data)
    
    async def update_hooks(self, campaign_id: str, hooks_data: List[Any], selected_hooks: List[Any] = None) -> bool:
        """Update hooks and optionally selected hooks"""
        success = await self.db.save_hooks(campaign_id, hooks_data)
        
        if success and selected_hooks:
            await self.db.save_selected_hooks(campaign_id, selected_hooks)
        
        return success
    
    async def update_scripts(self, campaign_id: str, scripts_data: List[Any]) -> bool:
        """Update scripts"""
        return await self.db.save_scripts(campaign_id, scripts_data)
    
    async def get_product_info(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get product info for a campaign"""
        content = await self.db.get_campaign_content(campaign_id)
        return content.get("product_data") if content else None
    
    async def get_marketing_analysis(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get marketing analysis for a campaign"""
        content = await self.db.get_campaign_content(campaign_id)
        
        if not content:
            return None
        
        return {
            "avatars": content.get("avatar_analysis"),
            "journey": content.get("journey_mapping"),
            "objections": content.get("objections_analysis"),
            "angles": content.get("angles")
        }
    
    async def get_angles(self, campaign_id: str) -> Optional[List[Any]]:
        """Get angles for a campaign"""
        content = await self.db.get_campaign_content(campaign_id)
        return content.get("angles") if content else None
    
    async def get_hooks(self, campaign_id: str) -> Optional[List[Any]]:
        """Get hooks for a campaign"""
        content = await self.db.get_campaign_content(campaign_id)
        return content.get("hooks") if content else None
    
    async def get_scripts(self, campaign_id: str) -> Optional[List[Any]]:
        """Get scripts for a campaign"""
        content = await self.db.get_campaign_content(campaign_id)
        return content.get("scripts") if content else None
    
    async def get_selected_angles(self, campaign_id: str) -> Optional[List[Any]]:
        """Get selected angles for a campaign"""
        content = await self.db.get_campaign_content(campaign_id)
        return content.get("selected_angles") if content else None
    
    async def get_selected_hooks(self, campaign_id: str) -> Optional[List[Any]]:
        """Get selected hooks for a campaign"""
        content = await self.db.get_campaign_content(campaign_id)
        return content.get("selected_hooks") if content else None
    
    async def create_video_entry(self, campaign_id: str, video_data: Dict[str, Any]) -> Optional[str]:
        """Create a new video entry for a campaign"""
        video = await self.db.create_video(campaign_id, video_data)
        return video["id"] if video else None
    
    async def get_campaign_videos(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get all videos for a campaign"""
        return await self.db.get_campaign_videos(campaign_id)
    
    async def update_video_status(self, video_id: str, status: str, **kwargs) -> bool:
        """Update video status and other fields"""
        updates = {"status": status}
        updates.update(kwargs)
        return await self.db.update_video(video_id, updates)
    
    async def get_complete_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get complete campaign data including all content and videos"""
        return await self.db.get_complete_campaign(campaign_id)
    
    async def list_user_campaigns(self, user_id: str) -> List[Dict[str, Any]]:
        """List all campaigns for a user"""
        return await self.db.list_campaigns(user_id)
    
    # Compatibility methods for easier migration
    
    def start_conversation(self, user_id: str) -> str:
        """Compatibility method - creates a campaign synchronously"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        campaign_id = loop.run_until_complete(self.create_campaign(user_id))
        loop.close()
        return campaign_id
    
    def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Compatibility method - gets campaign state synchronously"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        state = loop.run_until_complete(self.get_campaign_state(conversation_id))
        loop.close()
        return state


# Initialize the V3 campaign manager
campaign_v3_manager = CampaignV3Manager()