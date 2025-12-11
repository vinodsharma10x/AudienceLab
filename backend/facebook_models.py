# Facebook Marketing API Models for Sucana v4
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class SyncFrequency(str, Enum):
    EVERY_4_HOURS = "every_4_hours"
    NIGHTLY = "nightly"
    HOURLY = "hourly"
    DAILY = "daily"

class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TOKEN_EXPIRED = "token_expired"
    ERROR = "error"

# Request/Response Models
class FacebookAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None

class FacebookAuthResponse(BaseModel):
    success: bool
    message: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None

class FacebookAccountResponse(BaseModel):
    id: str
    user_id: str
    facebook_user_id: str
    facebook_user_name: str
    account_name: Optional[str] = None
    status: AccountStatus
    created_at: datetime
    last_sync: Optional[datetime] = None

class AdAccountSelection(BaseModel):
    facebook_account_id: str
    ad_account_ids: List[str]  # Empty list means "all accounts"

class SyncConfigRequest(BaseModel):
    """Request model for starting a sync job"""
    ad_account_ids: Optional[List[str]] = []  # Empty means all accounts
    date_from: Optional[str] = None  # YYYY-MM-DD format
    date_to: Optional[str] = None  # YYYY-MM-DD format  
    sync_frequency: Optional[str] = "manual"  # manual, hourly, every_4_hours, daily

# Database Models (for Supabase)
class FacebookAccount(BaseModel):
    """Facebook account linked to user"""
    id: Optional[str] = None
    user_id: str
    facebook_user_id: str
    facebook_user_name: str
    access_token: str  # Encrypted in database
    token_expires_at: Optional[datetime] = None
    account_name: Optional[str] = None
    status: AccountStatus = AccountStatus.ACTIVE
    sync_frequency: Optional[str] = "every_4_hours"  # manual, hourly, every_4_hours, daily
    sync_enabled: bool = True
    selected_ad_accounts: List[str] = []  # Empty means all accounts
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FacebookAdAccount(BaseModel):
    """Facebook Ad Account metadata"""
    id: Optional[str] = None
    facebook_account_id: str
    ad_account_id: str  # Facebook's ad account ID
    account_name: str
    currency: str
    timezone_name: str
    account_status: int
    is_selected: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FacebookAdPerformance(BaseModel):
    """Ad performance data from Facebook"""
    id: Optional[str] = None
    facebook_account_id: str
    ad_account_id: str
    
    # Campaign/Ad identifiers
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    adset_id: Optional[str] = None
    adset_name: Optional[str] = None
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    
    # Date range
    date_start: str
    date_stop: str
    
    # Delivery and spend metrics
    delivery_info: Optional[Dict[str, Any]] = None
    spend: Optional[float] = None
    impressions: Optional[int] = None
    reach: Optional[int] = None
    frequency: Optional[float] = None
    
    # Cost metrics
    cpm: Optional[float] = None  # Cost per 1000 impressions
    cpc: Optional[float] = None  # Cost per click
    ctr: Optional[float] = None  # Click-through rate
    
    # Click metrics
    clicks: Optional[int] = None
    outbound_clicks_unique: Optional[int] = None
    outbound_clicks_cpc_unique: Optional[float] = None
    outbound_clicks_ctr_unique: Optional[float] = None
    
    # Video metrics
    video_3s_views: Optional[int] = None
    video_p50_watched_actions: Optional[int] = None
    video_p95_watched_actions: Optional[int] = None
    
    # Conversion metrics
    leads: Optional[int] = None
    landing_page_views: Optional[int] = None
    cost_per_landing_page_view: Optional[float] = None
    cost_per_lead: Optional[float] = None
    
    # Action metrics
    scheduled_actions: Optional[int] = None
    cost_per_scheduled_action: Optional[float] = None
    purchases: Optional[int] = None
    purchase_value: Optional[float] = None
    
    # Metadata
    raw_data: Optional[Dict[str, Any]] = None  # Store full FB response
    sync_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None

class SyncJobStatus(BaseModel):
    """Background sync job status"""
    id: Optional[str] = None
    facebook_account_id: str
    job_type: str = "ad_performance_sync"
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_processed: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

# Response Models for API endpoints
class FacebookAccountsListResponse(BaseModel):
    success: bool
    accounts: List[FacebookAccountResponse]
    total: int

class AdAccountsListResponse(BaseModel):
    success: bool
    facebook_account_id: str
    ad_accounts: List[Dict[str, Any]]
    total: int

class SyncStatusResponse(BaseModel):
    success: bool
    facebook_account_id: str
    last_sync: Optional[datetime]
    next_sync: Optional[datetime]
    sync_frequency: Optional[str]  # manual, hourly, every_4_hours, daily
    sync_enabled: bool
    records_count: int
    last_error: Optional[str] = None

class PerformanceDataResponse(BaseModel):
    success: bool
    data: List[FacebookAdPerformance]
    total: int
    page: int
    page_size: int
    date_range: Dict[str, str]
