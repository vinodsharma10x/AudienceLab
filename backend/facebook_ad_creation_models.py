# Facebook Ad Creation Models for Sucana v4
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

# ==================== Enums ====================

class CampaignObjective(str, Enum):
    """Facebook Campaign Objectives (v18.0)"""
    OUTCOME_AWARENESS = "OUTCOME_AWARENESS"  # Brand awareness, reach
    OUTCOME_TRAFFIC = "OUTCOME_TRAFFIC"  # Link clicks, landing page views
    OUTCOME_ENGAGEMENT = "OUTCOME_ENGAGEMENT"  # Post engagement, page likes
    OUTCOME_LEADS = "OUTCOME_LEADS"  # Lead generation
    OUTCOME_APP_PROMOTION = "OUTCOME_APP_PROMOTION"  # App installs
    OUTCOME_SALES = "OUTCOME_SALES"  # Conversions, catalog sales

class OptimizationGoal(str, Enum):
    """Ad Set Optimization Goals"""
    NONE = "NONE"
    IMPRESSIONS = "IMPRESSIONS"
    REACH = "REACH"
    LINK_CLICKS = "LINK_CLICKS"
    LANDING_PAGE_VIEWS = "LANDING_PAGE_VIEWS"
    LEAD_GENERATION = "LEAD_GENERATION"
    CONVERSIONS = "CONVERSIONS"
    VALUE = "VALUE"
    THRUPLAY = "THRUPLAY"  # For video ads

class BillingEvent(str, Enum):
    """Billing Events"""
    IMPRESSIONS = "IMPRESSIONS"
    LINK_CLICKS = "LINK_CLICKS"
    THRUPLAY = "THRUPLAY"  # Video views

class AdStatus(str, Enum):
    """Ad Status"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DELETED = "DELETED"
    ARCHIVED = "ARCHIVED"

class CallToActionType(str, Enum):
    """Call to Action Types for Ads"""
    NO_BUTTON = "NO_BUTTON"
    LEARN_MORE = "LEARN_MORE"
    SHOP_NOW = "SHOP_NOW"
    SIGN_UP = "SIGN_UP"
    DOWNLOAD = "DOWNLOAD"
    GET_QUOTE = "GET_QUOTE"
    BOOK_NOW = "BOOK_NOW"
    CONTACT_US = "CONTACT_US"
    APPLY_NOW = "APPLY_NOW"
    GET_OFFER = "GET_OFFER"
    WATCH_MORE = "WATCH_MORE"

class TestStructure(str, Enum):
    """Test Structure for Ad Creation"""
    SINGLE = "single"  # Single ad
    SPLIT_TEST = "split_test"  # A/B testing
    DYNAMIC_CREATIVE = "dynamic_creative"  # Dynamic creative optimization

# ==================== Targeting Models ====================

class GeoLocation(BaseModel):
    """Geographic targeting"""
    countries: Optional[List[str]] = None
    regions: Optional[List[Dict[str, str]]] = None  # {key: "region_id"}
    cities: Optional[List[Dict[str, Any]]] = None
    zips: Optional[List[Dict[str, str]]] = None
    location_types: List[str] = ["home", "recent"]

class DetailedTargeting(BaseModel):
    """Detailed targeting for interests and behaviors"""
    interests: Optional[List[Dict[str, Any]]] = None  # {id: "interest_id", name: "Interest Name"}
    behaviors: Optional[List[Dict[str, Any]]] = None
    demographics: Optional[List[Dict[str, Any]]] = None
    life_events: Optional[List[Dict[str, Any]]] = None
    industries: Optional[List[Dict[str, Any]]] = None
    
class TargetingSpec(BaseModel):
    """Complete targeting specification"""
    geo_locations: GeoLocation
    age_min: int = Field(default=18, ge=18, le=65)
    age_max: int = Field(default=65, ge=18, le=65)
    genders: Optional[List[int]] = None  # 1=male, 2=female
    locales: Optional[List[str]] = None  # Language codes
    detailed_targeting: Optional[DetailedTargeting] = None
    custom_audiences: Optional[List[str]] = None  # Custom audience IDs
    excluded_custom_audiences: Optional[List[str]] = None
    connections: Optional[List[str]] = None  # Page connections
    excluded_connections: Optional[List[str]] = None
    device_platforms: Optional[List[str]] = None  # mobile, desktop
    publisher_platforms: Optional[List[str]] = None  # facebook, instagram, audience_network
    facebook_positions: Optional[List[str]] = None  # feed, stories, reels, etc.
    instagram_positions: Optional[List[str]] = None
    
    @validator('age_max')
    def validate_age_range(cls, v, values):
        if 'age_min' in values and v < values['age_min']:
            raise ValueError('age_max must be greater than or equal to age_min')
        return v

# ==================== Campaign Models ====================

class CampaignCreateRequest(BaseModel):
    """Request to create a new campaign"""
    name: str = Field(..., min_length=1, max_length=400)
    objective: CampaignObjective
    status: AdStatus = AdStatus.PAUSED
    special_ad_categories: List[str] = Field(default=['NONE'])  # CREDIT, HOUSING, EMPLOYMENT, NONE
    spend_cap: Optional[int] = None  # In cents
    daily_spend_cap: Optional[int] = None  # In cents
    
class CampaignResponse(BaseModel):
    """Response after creating a campaign"""
    id: str
    name: str
    objective: str
    status: str
    created_time: datetime
    
# ==================== Ad Set Models ====================

class AdSetCreateRequest(BaseModel):
    """Request to create a new ad set"""
    campaign_id: str
    name: str = Field(..., min_length=1, max_length=400)
    targeting: TargetingSpec
    daily_budget: Optional[int] = None  # In cents
    lifetime_budget: Optional[int] = None  # In cents
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    optimization_goal: OptimizationGoal
    billing_event: BillingEvent = BillingEvent.IMPRESSIONS
    bid_amount: Optional[int] = None  # In cents
    bid_strategy: Optional[str] = None  # LOWEST_COST_WITHOUT_CAP, LOWEST_COST_WITH_BID_CAP, COST_CAP
    status: AdStatus = AdStatus.PAUSED
    
    @validator('lifetime_budget')
    def validate_budget(cls, v, values):
        if v is not None and 'daily_budget' in values and values['daily_budget'] is not None:
            raise ValueError('Cannot set both daily_budget and lifetime_budget')
        if v is None and ('daily_budget' not in values or values['daily_budget'] is None):
            raise ValueError('Must set either daily_budget or lifetime_budget')
        return v

class AdSetResponse(BaseModel):
    """Response after creating an ad set"""
    id: str
    name: str
    campaign_id: str
    status: str
    created_time: datetime

# ==================== Creative Models ====================

class VideoData(BaseModel):
    """Video creative data"""
    video_id: str  # Facebook video ID
    message: str  # Primary text
    title: Optional[str] = None  # Headline
    description: Optional[str] = None
    call_to_action: Dict[str, Any]  # {type: "LEARN_MORE", value: {link: "https://..."}}
    
class ImageData(BaseModel):
    """Image creative data"""
    image_hash: str  # Facebook image hash
    message: str  # Primary text
    link: str
    caption: Optional[str] = None
    description: Optional[str] = None
    call_to_action: Dict[str, Any]

class CreativeCreateRequest(BaseModel):
    """Request to create ad creative"""
    name: str
    object_story_spec: Dict[str, Any]  # Page ID and creative data
    degrees_of_freedom_spec: Optional[Dict[str, Any]] = None  # For dynamic creative
    asset_feed_spec: Optional[Dict[str, Any]] = None  # For catalog ads
    
class CreativeResponse(BaseModel):
    """Response after creating creative"""
    id: str
    name: str
    object_type: str
    status: str

# ==================== Ad Models ====================

class AdCreateRequest(BaseModel):
    """Request to create an ad"""
    adset_id: str
    name: str = Field(..., min_length=1, max_length=400)
    creative_id: str  # ID of the creative
    status: AdStatus = AdStatus.PAUSED
    tracking_specs: Optional[List[Dict[str, Any]]] = None  # Tracking pixels
    
class AdResponse(BaseModel):
    """Response after creating an ad"""
    id: str
    name: str
    adset_id: str
    creative_id: str
    status: str
    created_time: datetime

# ==================== Video Ad Integration Models ====================

class VideoAdSelection(BaseModel):
    """Selection of video ads from Sucana system"""
    video_ad_id: str
    campaign_id: str  # Sucana campaign ID
    hook: str
    script: str
    angle_type: Literal["positive", "negative"]
    video_url: str  # S3 URL
    thumbnail_url: Optional[str] = None
    duration_seconds: int
    landing_url: Optional[str] = None
    cta_text: Optional[str] = None

class VideoAdCreateRequest(BaseModel):
    """Request to create Facebook ads from video selections"""
    video_ad_selections: List[VideoAdSelection]
    
    # Campaign strategy
    campaign_strategy: Literal["existing", "new"] = "new"
    existing_campaign_id: Optional[str] = None
    new_campaign_settings: Optional[CampaignCreateRequest] = None
    
    # Ad set strategy
    adset_strategy: Literal["existing", "new"] = "new"
    existing_adset_id: Optional[str] = None
    new_adset_settings: Optional[Dict[str, Any]] = None  # Simplified ad set settings
    
    # Targeting (for new ad sets)
    targeting: Optional[TargetingSpec] = None
    daily_budget: Optional[int] = Field(None, ge=100)  # Minimum $1.00
    
    # Test structure
    test_structure: TestStructure = TestStructure.SINGLE
    split_test_variable: Optional[str] = None  # "creative", "audience", "placement"
    
    # Options
    auto_generate_names: bool = True
    start_ads_paused: bool = True
    create_instagram_ads: bool = True
    
    @validator('new_campaign_settings', always=True)
    def validate_campaign_settings(cls, v, values):
        if values.get('campaign_strategy') == 'new' and not v:
            raise ValueError('new_campaign_settings required when campaign_strategy is "new"')
        return v
    
    @validator('existing_campaign_id')
    def validate_existing_campaign(cls, v, values):
        if values.get('campaign_strategy') == 'existing' and not v:
            raise ValueError('existing_campaign_id required when campaign_strategy is "existing"')
        return v

class BatchAdCreationRequest(BaseModel):
    """Request for batch ad creation"""
    ads_data: List[VideoAdCreateRequest]
    parallel_processing: bool = True
    stop_on_error: bool = False

# ==================== Response Models ====================

class VideoAdCreationResponse(BaseModel):
    """Response after creating ads from videos"""
    success: bool
    campaign_id: str
    adset_id: str
    ads_created: List[Dict[str, Any]]
    video_upload_status: Dict[str, str]  # video_id -> status
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    preview_urls: Optional[List[str]] = None

class BatchAdCreationResponse(BaseModel):
    """Response for batch ad creation"""
    total_requested: int
    total_created: int
    total_failed: int
    results: List[VideoAdCreationResponse]
    job_id: str
    status: str

# ==================== Template Models ====================

class CampaignTemplate(BaseModel):
    """Campaign template for reuse"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    objective: CampaignObjective
    targeting_spec: TargetingSpec
    budget_settings: Dict[str, Any]
    placement_settings: Dict[str, Any]
    bidding_settings: Dict[str, Any]
    is_default: bool = False

class AudiencePreset(BaseModel):
    """Saved audience for reuse"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    targeting_spec: TargetingSpec
    estimated_reach_min: Optional[int] = None
    estimated_reach_max: Optional[int] = None
    is_custom_audience: bool = False
    custom_audience_id: Optional[str] = None

# ==================== Analytics Models ====================

class AdPerformanceMetrics(BaseModel):
    """Performance metrics for created ads"""
    ad_id: str
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    spend: float
    conversions: Optional[int] = None
    conversion_rate: Optional[float] = None
    roas: Optional[float] = None  # Return on ad spend
    
class CampaignOptimizationSuggestion(BaseModel):
    """Suggestions for campaign optimization"""
    suggestion_type: str  # "pause_low_performer", "increase_budget", "change_targeting"
    ad_id: Optional[str] = None
    adset_id: Optional[str] = None
    reason: str
    recommended_action: str
    expected_improvement: Optional[str] = None