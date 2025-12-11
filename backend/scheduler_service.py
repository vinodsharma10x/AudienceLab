# Background Scheduler Service for Facebook Ad Data Sync
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import os
from dotenv import load_dotenv

from facebook_database_service import FacebookDatabaseService
from facebook_api_service import FacebookAPIService
from facebook_models import SyncConfigRequest

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FacebookSyncScheduler:
    """Manages scheduled sync jobs for Facebook ad data"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db_service = FacebookDatabaseService()
        self.facebook_service = FacebookAPIService()
        self.active_jobs = {}  # Track active jobs by user_id
        
        # Configure scheduler
        self.scheduler.start()
        logger.info("✅ Facebook Sync Scheduler initialized")
    
    async def initialize_scheduled_syncs(self):
        """Initialize sync jobs for all users with sync enabled"""
        try:
            # Get all Facebook accounts with sync enabled
            all_accounts = await self.db_service.get_all_sync_enabled_accounts()
            
            for account in all_accounts:
                user_id = account['user_id']
                sync_frequency = account.get('sync_frequency', 'every_4_hours')
                
                # Schedule sync job for this user
                await self.schedule_user_sync(user_id, sync_frequency)
            
            logger.info(f"✅ Initialized {len(all_accounts)} scheduled sync jobs")
            
        except Exception as e:
            logger.error(f"❌ Error initializing scheduled syncs: {e}")
    
    async def schedule_user_sync(self, user_id: str, frequency: str = 'every_4_hours'):
        """Schedule sync job for a specific user"""
        try:
            # Remove existing job if any
            if user_id in self.active_jobs:
                self.scheduler.remove_job(self.active_jobs[user_id])
            
            # Determine trigger based on frequency
            if frequency == 'hourly':
                trigger = IntervalTrigger(hours=1)
            elif frequency == 'every_4_hours':
                trigger = IntervalTrigger(hours=4)
            elif frequency == 'nightly':
                # Run at 2 AM every day
                trigger = CronTrigger(hour=2, minute=0)
            elif frequency == 'daily':
                trigger = IntervalTrigger(days=1)
            else:
                # Default to every 4 hours
                trigger = IntervalTrigger(hours=4)
            
            # Create job ID
            job_id = f"sync_user_{user_id}"
            
            # Add job to scheduler
            self.scheduler.add_job(
                func=self.execute_user_sync,
                trigger=trigger,
                args=[user_id],
                id=job_id,
                name=f"Facebook sync for user {user_id}",
                replace_existing=True
            )
            
            # Track active job
            self.active_jobs[user_id] = job_id
            
            logger.info(f"✅ Scheduled {frequency} sync for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling sync for user {user_id}: {e}")
    
    async def execute_user_sync(self, user_id: str):
        """Execute sync job for a specific user"""
        try:
            logger.info(f"🔄 Starting scheduled sync for user {user_id}")
            
            # Get user's Facebook accounts
            facebook_accounts = await self.db_service.get_facebook_accounts_by_user(user_id)
            
            if not facebook_accounts:
                logger.warning(f"⚠️ No Facebook accounts found for user {user_id}")
                return
            
            total_records = 0
            
            for fb_account in facebook_accounts:
                # Check if sync is still enabled
                if not fb_account.get('sync_enabled', True):
                    continue
                
                try:
                    # Decrypt token
                    encrypted_token = fb_account.get('access_token')
                    if not encrypted_token:
                        continue
                    
                    access_token = self.facebook_service.decrypt_token(encrypted_token)
                    
                    # Check token expiry
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
                            await self.db_service.update_facebook_account_status(fb_account['id'], 'token_expired')
                            continue
                    
                    # Get selected ad accounts
                    selected_ad_accounts = fb_account.get('selected_ad_accounts', [])
                    if not selected_ad_accounts:
                        # Get all ad accounts if none specifically selected
                        ad_accounts = await self.db_service.get_ad_accounts_by_facebook_account(fb_account['id'])
                        selected_ad_accounts = [acc['ad_account_id'] for acc in ad_accounts if acc.get('is_selected', True)]
                    
                    if not selected_ad_accounts:
                        continue
                    
                    # Fetch performance data for last 30 days
                    date_from = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
                    date_to = datetime.utcnow().strftime('%Y-%m-%d')
                    
                    for ad_account_id in selected_ad_accounts:
                        try:
                            # Fetch performance data
                            performance_data = await self.facebook_service.get_ad_performance_data(
                                access_token=access_token,
                                ad_account_id=ad_account_id,
                                date_from=date_from,
                                date_to=date_to,
                                facebook_account_id=fb_account['id']
                            )
                            
                            # facebook_account_id is already added in the API service
                            
                            # Store in database
                            if performance_data:
                                await self.db_service.insert_performance_data(performance_data)
                                total_records += len(performance_data)
                                logger.info(f"✅ Synced {len(performance_data)} records for ad account {ad_account_id}")
                            
                        except Exception as e:
                            logger.error(f"❌ Error syncing ad account {ad_account_id}: {e}")
                    
                    # Update last sync time
                    await self.db_service.update_facebook_account_last_sync(fb_account['id'])
                    
                except Exception as e:
                    logger.error(f"❌ Error processing Facebook account {fb_account['id']}: {e}")
            
            logger.info(f"✅ Completed scheduled sync for user {user_id}. Synced {total_records} records")
            
        except Exception as e:
            logger.error(f"❌ Error in scheduled sync for user {user_id}: {e}")
    
    async def update_user_sync_frequency(self, user_id: str, frequency: str):
        """Update sync frequency for a user"""
        try:
            # Update in database
            facebook_accounts = await self.db_service.get_facebook_accounts_by_user(user_id)
            
            for account in facebook_accounts:
                self.db_service.supabase.table("facebook_accounts").update({
                    "sync_frequency": frequency,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", account['id']).execute()
            
            # Reschedule sync job
            await self.schedule_user_sync(user_id, frequency)
            
            logger.info(f"✅ Updated sync frequency to {frequency} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating sync frequency for user {user_id}: {e}")
    
    async def pause_user_sync(self, user_id: str):
        """Pause sync for a user"""
        try:
            if user_id in self.active_jobs:
                self.scheduler.remove_job(self.active_jobs[user_id])
                del self.active_jobs[user_id]
                logger.info(f"⏸️ Paused sync for user {user_id}")
            
            # Update database
            facebook_accounts = await self.db_service.get_facebook_accounts_by_user(user_id)
            for account in facebook_accounts:
                self.db_service.supabase.table("facebook_accounts").update({
                    "sync_enabled": False,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", account['id']).execute()
            
        except Exception as e:
            logger.error(f"❌ Error pausing sync for user {user_id}: {e}")
    
    async def resume_user_sync(self, user_id: str):
        """Resume sync for a user"""
        try:
            # Get user's sync frequency
            facebook_accounts = await self.db_service.get_facebook_accounts_by_user(user_id)
            if facebook_accounts:
                frequency = facebook_accounts[0].get('sync_frequency', 'every_4_hours')
                
                # Update database
                for account in facebook_accounts:
                    self.db_service.supabase.table("facebook_accounts").update({
                        "sync_enabled": True,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("id", account['id']).execute()
                
                # Schedule sync
                await self.schedule_user_sync(user_id, frequency)
                logger.info(f"▶️ Resumed sync for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error resuming sync for user {user_id}: {e}")
    
    def get_scheduler_status(self) -> Dict:
        """Get current scheduler status"""
        jobs = self.scheduler.get_jobs()
        
        return {
            "scheduler_running": self.scheduler.running,
            "total_jobs": len(jobs),
            "active_users": list(self.active_jobs.keys()),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                }
                for job in jobs
            ]
        }
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("🛑 Scheduler shutdown complete")

# Add method to database service to get all sync-enabled accounts
async def get_all_sync_enabled_accounts(self) -> List[Dict]:
    """Get all Facebook accounts with sync enabled"""
    try:
        result = self.supabase.table("facebook_accounts").select("*").eq("sync_enabled", True).eq("status", "active").execute()
        return result.data
    except Exception as e:
        logger.error(f"❌ Error getting sync-enabled accounts: {e}")
        return []

# Monkey-patch the method to FacebookDatabaseService
FacebookDatabaseService.get_all_sync_enabled_accounts = get_all_sync_enabled_accounts

# Global scheduler instance
scheduler_instance = None

def get_scheduler() -> FacebookSyncScheduler:
    """Get or create scheduler instance"""
    global scheduler_instance
    if scheduler_instance is None:
        scheduler_instance = FacebookSyncScheduler()
    return scheduler_instance

# Initialize scheduler when module is imported
if __name__ != "__main__":
    scheduler = get_scheduler()
    # Run initialization in background
    asyncio.create_task(scheduler.initialize_scheduled_syncs())