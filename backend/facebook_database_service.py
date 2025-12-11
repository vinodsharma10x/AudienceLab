# Supabase Database Service for Facebook Integration
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from supabase import create_client, Client
import os
from dotenv import load_dotenv

from facebook_models import (
    FacebookAccount,
    FacebookAdAccount, 
    FacebookAdPerformance,
    SyncJobStatus
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class FacebookDatabaseService:
    """Service for Facebook-related database operations using Supabase"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not all([self.supabase_url, self.supabase_service_key]):
            raise ValueError("Supabase URL and Service Key must be set")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_service_key)
        logger.info("✅ Facebook Database Service initialized")
    
    # Facebook Accounts Management
    async def create_or_update_facebook_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a Facebook account record (upsert)"""
        try:
            # First try to get existing account
            existing = self.supabase.table("facebook_accounts").select("*").eq(
                "user_id", account_data['user_id']
            ).eq(
                "facebook_user_id", account_data['facebook_user_id']
            ).execute()
            
            if existing.data:
                # Update existing account
                logger.info(f"📝 Updating existing Facebook account for user {account_data['user_id']}")
                result = self.supabase.table("facebook_accounts").update({
                    "access_token": account_data['access_token'],
                    "token_expires_at": account_data['token_expires_at'],
                    "facebook_user_name": account_data.get('facebook_user_name'),
                    "account_name": account_data.get('account_name'),
                    "status": "active",
                    "updated_at": datetime.utcnow().isoformat()
                }).eq(
                    "id", existing.data[0]['id']
                ).execute()
                
                if result.data:
                    logger.info(f"✅ Updated Facebook account for user {account_data['user_id']}")
                    return result.data[0]
            else:
                # Create new account
                result = self.supabase.table("facebook_accounts").insert(account_data).execute()
                
                if result.data:
                    logger.info(f"✅ Created new Facebook account for user {account_data['user_id']}")
                    return result.data[0]
            
            raise Exception("No data returned from upsert operation")
                
        except Exception as e:
            logger.error(f"❌ Error upserting Facebook account: {e}")
            raise
    
    async def create_facebook_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - redirects to upsert"""
        return await self.create_or_update_facebook_account(account_data)
    
    async def get_facebook_accounts_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all Facebook accounts for a user"""
        try:
            result = self.supabase.table("facebook_accounts").select("*").eq("user_id", user_id).eq("status", "active").execute()
            
            logger.info(f"✅ Retrieved {len(result.data)} Facebook accounts for user {user_id}")
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Error getting Facebook accounts: {e}")
            raise
    
    async def get_facebook_account_by_id(self, account_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific Facebook account by ID (with user verification)"""
        try:
            result = self.supabase.table("facebook_accounts").select("*").eq("id", account_id).eq("user_id", user_id).eq("status", "active").execute()
            
            if result.data:
                logger.info(f"✅ Retrieved Facebook account {account_id}")
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting Facebook account: {e}")
            raise
    
    async def update_facebook_account_token(self, account_id: str, encrypted_token: str, expires_at: datetime) -> bool:
        """Update Facebook account access token"""
        try:
            result = self.supabase.table("facebook_accounts").update({
                "access_token": encrypted_token,  # Column is named access_token in your schema
                "token_expires_at": expires_at.isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", account_id).execute()
            
            if result.data:
                logger.info(f"✅ Updated token for Facebook account {account_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Error updating Facebook account token: {e}")
            raise
    
    async def update_facebook_account_status(self, account_id: str, status: str) -> bool:
        """Update Facebook account status"""
        try:
            result = self.supabase.table("facebook_accounts").update({
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", account_id).execute()
            
            if result.data:
                logger.info(f"✅ Updated Facebook account {account_id} status to {status}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Error updating Facebook account status: {e}")
            raise
    
    async def update_facebook_account_last_sync(self, account_id: str) -> bool:
        """Update Facebook account last sync time"""
        try:
            result = self.supabase.table("facebook_accounts").update({
                "last_sync": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", account_id).execute()
            
            if result.data:
                logger.info(f"✅ Updated last sync time for Facebook account {account_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Error updating Facebook account last sync: {e}")
            raise
    
    async def deactivate_facebook_account(self, account_id: str, user_id: str) -> bool:
        """Deactivate a Facebook account (soft delete)"""
        try:
            result = self.supabase.table("facebook_accounts").update({
                "status": "inactive",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", account_id).eq("user_id", user_id).execute()
            
            if result.data:
                logger.info(f"✅ Deactivated Facebook account {account_id}")
                
                # Also mark all associated ad accounts as not selected (soft delete)
                # This preserves the data but indicates they're no longer active
                ad_accounts_result = self.supabase.table("facebook_ad_accounts").update({
                    "is_selected": False,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("facebook_account_id", account_id).execute()
                
                if ad_accounts_result.data:
                    logger.info(f"✅ Deactivated {len(ad_accounts_result.data)} ad accounts for Facebook account {account_id}")
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Error deactivating Facebook account: {e}")
            raise
    
    # Ad Accounts Management
    async def upsert_ad_accounts(self, ad_accounts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert or update Facebook ad accounts"""
        try:
            # Process each ad account individually for better error handling
            results = []
            for ad_account in ad_accounts_data:
                try:
                    # Check if exists
                    existing = self.supabase.table("facebook_ad_accounts").select("*").eq(
                        "facebook_account_id", ad_account['facebook_account_id']
                    ).eq(
                        "ad_account_id", ad_account['ad_account_id']
                    ).execute()
                    
                    if existing.data:
                        # Update existing
                        result = self.supabase.table("facebook_ad_accounts").update({
                            "account_name": ad_account['account_name'],
                            "currency": ad_account['currency'],
                            "timezone_name": ad_account['timezone_name'],
                            "account_status": ad_account.get('account_status', 1),
                            "is_selected": ad_account.get('is_selected', True),
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", existing.data[0]['id']).execute()
                        
                        if result.data:
                            results.append(result.data[0])
                    else:
                        # Insert new
                        result = self.supabase.table("facebook_ad_accounts").insert(ad_account).execute()
                        if result.data:
                            results.append(result.data[0])
                            
                except Exception as e:
                    logger.warning(f"⚠️ Error upserting ad account {ad_account.get('ad_account_id')}: {e}")
                    # Continue with other accounts
            
            logger.info(f"✅ Upserted {len(results)} ad accounts")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error upserting ad accounts: {e}")
            raise
    
    async def get_ad_accounts_by_facebook_account(self, facebook_account_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get ad accounts for a Facebook account"""
        try:
            # Build query
            query = self.supabase.table("facebook_ad_accounts").select("*").eq("facebook_account_id", facebook_account_id)
            
            # By default, only return selected (active) ad accounts
            if not include_inactive:
                query = query.eq("is_selected", True)
            
            result = query.execute()
            
            logger.info(f"✅ Retrieved {len(result.data)} ad accounts for Facebook account {facebook_account_id}")
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Error getting ad accounts: {e}")
            raise
    
    # Performance Data Management
    async def insert_performance_data(self, performance_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert Facebook ad performance data with deduplication"""
        try:
            if not performance_data:
                logger.info("ℹ️ No performance data to insert")
                return []
            
            logger.info(f"🔄 Processing {len(performance_data)} performance records for deduplication...")
            
            # Group records by unique key (ad_account_id, campaign_id, date_start)
            unique_records = {}
            duplicate_count = 0
            
            for record in performance_data:
                # Create unique key for deduplication (include ad_id for ad-level uniqueness)
                key = f"{record.get('ad_account_id', '')}_{record.get('ad_id', '')}_{record.get('date_start', '')}_{record.get('date_stop', '')}"
                
                if key in unique_records:
                    duplicate_count += 1
                    # Keep the record with more recent data or higher spend
                    existing_spend = float(unique_records[key].get('spend', 0))
                    new_spend = float(record.get('spend', 0))
                    if new_spend > existing_spend:
                        unique_records[key] = record
                else:
                    unique_records[key] = record
            
            deduplicated_data = list(unique_records.values())
            logger.info(f"📊 Deduplication: {len(performance_data)} → {len(deduplicated_data)} records ({duplicate_count} duplicates removed)")
            
            if not deduplicated_data:
                return []
            
            # Check for existing records in database to avoid database-level duplicates
            existing_count = 0
            new_records = []
            
            for record in deduplicated_data:
                # Check if record already exists (use ad_id for uniqueness)
                ad_account_id = record.get('ad_account_id')
                ad_id = record.get('ad_id')
                date_start = record.get('date_start')
                date_stop = record.get('date_stop')
                
                if ad_account_id and ad_id and date_start:
                    existing = self.supabase.table("facebook_ad_performance").select("id").eq(
                        "ad_account_id", ad_account_id
                    ).eq(
                        "ad_id", ad_id
                    ).eq(
                        "date_start", date_start
                    ).eq(
                        "date_stop", date_stop
                    ).execute()
                    
                    if existing.data:
                        existing_count += 1
                        # Update existing record with newer data
                        self.supabase.table("facebook_ad_performance").update(record).eq(
                            "id", existing.data[0]['id']
                        ).execute()
                    else:
                        new_records.append(record)
                else:
                    new_records.append(record)
            
            logger.info(f"📊 Database check: {existing_count} existing records updated, {len(new_records)} new records to insert")
            
            # Insert new records in batches
            all_results = []
            if new_records:
                batch_size = 1000
                
                for i in range(0, len(new_records), batch_size):
                    batch = new_records[i:i + batch_size]
                    try:
                        result = self.supabase.table("facebook_ad_performance").insert(batch).execute()
                        if result.data:
                            all_results.extend(result.data)
                    except Exception as batch_error:
                        logger.warning(f"⚠️ Error inserting batch {i//batch_size + 1}: {batch_error}")
                        # Try inserting records individually to identify problematic records
                        for record in batch:
                            try:
                                result = self.supabase.table("facebook_ad_performance").insert(record).execute()
                                if result.data:
                                    all_results.extend(result.data)
                            except Exception as record_error:
                                logger.warning(f"⚠️ Skipped problematic record: {record_error}")
            
            total_processed = len(all_results) + existing_count
            logger.info(f"✅ Processed {total_processed} performance records ({len(all_results)} inserted, {existing_count} updated)")
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Error inserting performance data: {e}")
            raise
    
    async def get_performance_data(
        self,
        user_id: str,
        ad_account_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        campaign_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get performance data with filtering and pagination"""
        try:
            # Build query
            query = self.supabase.table("facebook_ad_performance_view").select("*")
            
            # Add filters
            query = query.eq("user_id", user_id)
            
            if ad_account_id:
                query = query.eq("ad_account_id", ad_account_id)
            
            if date_from:
                query = query.gte("date_start", date_from)
            
            if date_to:
                query = query.lte("date_stop", date_to)
            
            if campaign_name:
                query = query.ilike("campaign_name", f"%{campaign_name}%")
            
            # Get total count (without pagination)
            count_result = query.execute()
            total_count = len(count_result.data)
            
            # Apply pagination
            query = query.range(offset, offset + limit - 1).order("date_start", desc=True)
            result = query.execute()
            
            logger.info(f"✅ Retrieved {len(result.data)} performance records (total: {total_count})")
            
            return {
                "data": result.data,
                "total_count": total_count,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_next_page": offset + limit < total_count,
                    "has_previous_page": offset > 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting performance data: {e}")
            raise
    
    # Sync Jobs Management
    async def create_sync_job(self, sync_job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sync job record"""
        try:
            # Skip sync job tracking if table doesn't exist or has wrong schema
            logger.info(f"📝 Sync job {sync_job_data.get('sync_job_id')} started (job tracking disabled)")
            return sync_job_data
                
        except Exception as e:
            logger.error(f"❌ Error creating sync job: {e}")
            return sync_job_data  # Return the data anyway to continue
    
    async def update_sync_job_status(
        self,
        sync_job_id: str,
        status: str,
        progress_percentage: Optional[int] = None,
        records_processed: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update sync job status and progress"""
        try:
            # Skip sync job tracking if table doesn't exist or has wrong schema
            if status == "completed":
                logger.info(f"✅ Sync job {sync_job_id} completed with {records_processed or 0} records")
            elif status == "failed":
                logger.error(f"❌ Sync job {sync_job_id} failed: {error_message}")
            else:
                logger.info(f"📊 Sync job {sync_job_id} status: {status} ({progress_percentage or 0}%)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating sync job status: {e}")
            return False  # Don't raise, just return False
    
    async def get_sync_job_status(self, sync_job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get sync job status"""
        try:
            # Return a mock status since table doesn't exist
            logger.info(f"📊 Returning mock status for sync job {sync_job_id}")
            return {
                "sync_job_id": sync_job_id,
                "user_id": user_id,
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "progress_percentage": 50,
                "records_processed": 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting sync job status: {e}")
            return None
    
    async def get_recent_sync_jobs(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync jobs for a user"""
        try:
            # Return empty list since table doesn't exist
            logger.info(f"📊 Returning empty sync jobs list for user {user_id} (sync tracking disabled)")
            return []
            
        except Exception as e:
            logger.error(f"❌ Error getting recent sync jobs: {e}")
            return []
    
    # Data Cleanup and Maintenance
    async def cleanup_old_performance_data(self, retention_days: int = 365) -> int:
        """Clean up old performance data beyond retention period"""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()
            
            result = self.supabase.table("facebook_ad_performance").delete().lt("date_start", cutoff_date).execute()
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"✅ Cleaned up {deleted_count} old performance records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old data: {e}")
            raise
    
    async def get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's Facebook data"""
        try:
            # Get counts from different tables
            facebook_accounts = await self.get_facebook_accounts_by_user(user_id)
            
            # Get ad accounts count
            ad_accounts_count = 0
            for fb_account in facebook_accounts:
                ad_accounts = await self.get_ad_accounts_by_facebook_account(fb_account['id'])
                ad_accounts_count += len(ad_accounts)
            
            # Get performance data count (last 30 days)
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
            recent_performance = await self.get_performance_data(
                user_id=user_id,
                date_from=thirty_days_ago,
                limit=1
            )
            
            # Get recent sync jobs
            recent_syncs = await self.get_recent_sync_jobs(user_id, limit=5)
            
            summary = {
                "facebook_accounts_count": len(facebook_accounts),
                "ad_accounts_count": ad_accounts_count,
                "performance_records_last_30_days": recent_performance["total_count"],
                "last_sync_job": recent_syncs[0] if recent_syncs else None,
                "total_sync_jobs": len(recent_syncs)
            }
            
            logger.info(f"✅ Generated data summary for user {user_id}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating user data summary: {e}")
            raise

    async def store_ad_mapping(
        self,
        user_id: str,
        video_ad_id: str,
        facebook_campaign_id: str,
        facebook_adset_id: str,
        facebook_ad_id: str,
        facebook_creative_id: str,
        facebook_video_id: str = None
    ) -> Dict[str, Any]:
        """Store mapping between video ads and Facebook ads"""
        try:
            data = {
                "user_id": user_id,
                "video_ad_id": video_ad_id,
                "facebook_campaign_id": facebook_campaign_id,
                "facebook_adset_id": facebook_adset_id,
                "facebook_ad_id": facebook_ad_id,
                "facebook_creative_id": facebook_creative_id,
                "video_facebook_id": facebook_video_id,  # Maps to video_facebook_id column in table
                "created_at": datetime.utcnow().isoformat()
            }

            result = self.supabase.table("facebook_ad_mappings").insert(data).execute()

            if result.data:
                logger.info(f"✅ Stored ad mapping for video {video_ad_id} -> Facebook ad {facebook_ad_id}")
                return result.data[0]
            else:
                raise Exception("Failed to insert ad mapping")

        except Exception as e:
            logger.error(f"❌ Error storing ad mapping: {e}")
            raise
