# Video Ads V2 Models for Claude-powered workflow
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# V2 URL Parse Response (matches V2 frontend expectations)
class URLParseV2Response(BaseModel):
    product_name: str
    product_information: str
    target_audience: str
    price: str
    problem_solved: str
    differentiation: str  # Combined unique selling points
    additional_information: str  # Renamed from additional_info
    # Keep V1 fields for backward compatibility
    key_benefits: List[str] = []
    unique_selling_points: List[str] = []
    # V3 fields
    campaign_id: Optional[str] = None
    conversation_id: Optional[str] = None  # Legacy support
    original_url: Optional[str] = None

# Enhanced Product Info for V2
class VideoAdsProductInfoV2(BaseModel):
    product_name: str
    product_information: str
    target_audience: str
    price: Optional[str] = None
    problem_solved: str
    differentiation: str
    additional_information: Optional[str] = None

# Avatar Analysis Models
class DemographicData(BaseModel):
    age_range: Optional[str] = None
    geographic_location: Optional[str] = None
    socioeconomic_level: Optional[str] = None
    education_level: Optional[str] = None
    employment_situation: Optional[str] = None
    family_composition: Optional[str] = None
    average_income: Optional[str] = None

class PsychographicFactors(BaseModel):
    personality_traits: Optional[str] = None
    core_values: Optional[str] = None
    lifestyle: Optional[str] = None
    interests_hobbies: Optional[str] = None
    aspirations_goals: Optional[str] = None
    fears_concerns: Optional[str] = None
    social_influences: Optional[str] = None

class PurchasingBehavior(BaseModel):
    decision_process: Optional[str] = None
    preferred_channels: Optional[str] = None
    purchase_frequency: Optional[str] = None
    influencing_factors: Optional[str] = None
    barriers_objections: Optional[str] = None
    post_purchase: Optional[str] = None
    brand_loyalty: Optional[str] = None

class RealityExpectations(BaseModel):
    current_vs_desired: Optional[str] = None
    problems_pain_points: Optional[str] = None
    unmet_needs: Optional[str] = None
    service_expectations: Optional[str] = None
    satisfaction_level: Optional[str] = None
    expectation_gaps: Optional[str] = None
    change_triggers: Optional[str] = None

class EconomicSensitivity(BaseModel):
    budget_limitations: Optional[str] = None
    price_sensitivity: Optional[str] = None
    payment_methods: Optional[str] = None
    investment_perception: Optional[str] = None
    price_comparison: Optional[str] = None
    economic_factors: Optional[str] = None
    expected_roi: Optional[str] = None

class AvatarAnalysis(BaseModel):
    demographic_data: DemographicData
    psychographic_factors: PsychographicFactors
    purchasing_behavior: PurchasingBehavior
    reality_expectations: RealityExpectations
    economic_sensitivity: EconomicSensitivity

# Journey Mapping Models
class JourneyPhase(BaseModel):
    description: str  # Keep required - core field
    emotions: Optional[List[str]] = None
    customer_needs: Optional[str] = None
    customer_knowledge: Optional[str] = None
    customer_feelings: Optional[str] = None
    customer_actions: Optional[str] = None
    customer_thoughts: Optional[str] = None
    customer_problems: Optional[str] = None
    solutions_offered: Optional[str] = None
    touchpoints: Optional[str] = None
    language_terminology: Optional[str] = None

    @field_validator('language_terminology', mode='before')
    @classmethod
    def validate_language_terminology(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            # Convert list to string
            return ', '.join(v)
        return v
    key_metrics: Optional[str] = None

class JourneyMapping(BaseModel):
    discovery_phase: JourneyPhase
    consideration_phase: JourneyPhase
    decision_phase: JourneyPhase
    retention_phase: JourneyPhase

# Objections Analysis Models
class ObjectionItem(BaseModel):
    priority: Optional[int] = None
    objection_description: Optional[str] = None
    argument_to_overcome: Optional[str] = None
    additional_incentive: Optional[str] = None

class ObjectionsAnalysis(BaseModel):
    solution_objections: List[ObjectionItem]
    offer_objections: List[ObjectionItem]
    internal_objections: List[ObjectionItem]
    external_objections: List[ObjectionItem]

# Marketing Angles Models
class MarketingAngleV2(BaseModel):
    angle: int  # Keep for backward compatibility
    angle_id: Optional[str] = None  # New field: "angle_1", "angle_2", etc.
    angle_number: Optional[int] = None  # New field: same as angle, but explicit
    category: str
    concept: str
    type: str  # "positive" or "negative"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-generate angle_id and angle_number if not provided
        if self.angle_id is None:
            self.angle_id = f"angle_{self.angle}"
        if self.angle_number is None:
            self.angle_number = self.angle

class AnglesGeneration(BaseModel):
    positive_angles: List[MarketingAngleV2]
    negative_angles: List[MarketingAngleV2]

# Comprehensive Analysis Response
class MarketingAnalysisV2(BaseModel):
    avatar_analysis: AvatarAnalysis
    journey_mapping: JourneyMapping
    objections_analysis: ObjectionsAnalysis
    angles_generation: AnglesGeneration

# Request/Response Models
class MarketingAnalysisV2Request(BaseModel):
    product_info: VideoAdsProductInfoV2
    force_new_conversation: Optional[bool] = False  # For manual uploads to ensure clean state

class MarketingAnalysisV2Response(BaseModel):
    conversation_id: str
    analysis: MarketingAnalysisV2
    processing_time: float
    claude_model: str
    
class MarketingAnglesV2Response(BaseModel):
    """Simplified response for frontend - angles only"""
    conversation_id: str
    positive_angles: List[MarketingAngleV2]
    negative_angles: List[MarketingAngleV2]
    processing_time: float

# V2 Workflow State Management
class WorkflowStateV2(BaseModel):
    conversation_id: str
    user_id: str
    current_phase: str
    product_info: VideoAdsProductInfoV2
    analysis: Optional[MarketingAnalysisV2] = None
    created_at: str
    updated_at: str

# V2 Hooks Models
class SelectedAngleV2(BaseModel):
    angle_id: str
    angle: int
    category: str
    concept: str
    type: str  # "positive" or "negative"

class HooksV2Request(BaseModel):
    conversation_id: str
    selected_angles: List[SelectedAngleV2]

# Hook item with ID and text
class HookItem(BaseModel):
    hook_id: str
    hook_text: str
    hook_category: str

class HooksByCategoryV2(BaseModel):
    # Updated to store full hook objects instead of just strings
    direct_question: List[HookItem] = []
    shocking_fact: List[HookItem] = []
    demonstration: List[HookItem] = []
    alarm_tension: List[HookItem] = []
    surprise_curiosity: List[HookItem] = []
    list_enumeration: List[HookItem] = []
    personal_story: List[HookItem] = []

class AngleWithHooksV2(BaseModel):
    angle_id: str
    angle_number: int
    angle_category: str
    angle_concept: str
    angle_type: str
    hooks_by_category: HooksByCategoryV2

class HooksV2Response(BaseModel):
    conversation_id: str
    hooks_by_angle: List[AngleWithHooksV2]
    processing_time: float

# Scripts V2 Models
class ScriptsRequestV2(BaseModel):
    conversation_id: str
    hooks_by_angle: List[AngleWithHooksV2]

class ScriptVariantV2(BaseModel):
    id: str
    version: str
    content: str
    cta: str
    target_emotion: str

class SelectedHookV2(BaseModel):
    id: str
    hook_text: str
    hook_type: str

class ScriptHookV2(BaseModel):
    selected_hook: SelectedHookV2
    scripts: List[ScriptVariantV2]

class SelectedAngleV2(BaseModel):
    id: str
    angle: int
    category: str
    concept: str
    type: str

class ScriptAngleV2(BaseModel):
    selected_angle: SelectedAngleV2
    hooks: List[ScriptHookV2]

class CampaignScriptsV2(BaseModel):
    angles: List[ScriptAngleV2]

class ScriptsResponseV2(BaseModel):
    conversation_id: str
    campaign_scripts: CampaignScriptsV2
    processing_time: float

# V2 Voice Actor Models (conversation_id instead of thread_id)
class VoiceActorV2Request(BaseModel):
    campaign_id: str  # Changed from conversation_id for V3 architecture
    campaign_scripts: dict  # The JSON from scripts page

class ElevenLabsVoice(BaseModel):
    voice_id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    labels: List[str] = []
    preview_url: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    accent: Optional[str] = None
    use_case: Optional[str] = None

class ActorImage(BaseModel):
    filename: str
    name: str
    description: str
    category: str

class VoiceActorV2Response(BaseModel):
    conversation_id: str
    voices: List[ElevenLabsVoice]
    actors: List[ActorImage]
    status: str

# V2 Audio Generation Models (conversation_id instead of thread_id)
class AudioGenerationV2Request(BaseModel):
    conversation_id: str
    voice_actor_selection: dict  # Selected voice and actor from voice-actor page
    campaign_scripts: dict  # Scripts from scripts page

class GeneratedAudioV2(BaseModel):
    audio_id: str
    type: str  # "combined", "hook", or "script" 
    content: str
    audio_url: str
    duration: Optional[float] = None
    file_size: Optional[int] = None
    voice_settings: Optional[dict] = None

class ScriptWithAudioV2(BaseModel):
    script_id: str
    hook: str
    body: str
    selected: bool
    # Combined audio field
    combined_audio: Optional[GeneratedAudioV2] = None
    # Keep old fields for backwards compatibility during transition
    hook_audio: Optional[GeneratedAudioV2] = None
    script_audio: Optional[GeneratedAudioV2] = None

class AudioGenerationV2Response(BaseModel):
    conversation_id: str
    selected_angle: dict
    voice_info: dict  # Selected voice and actor info
    scripts_with_audio: List[ScriptWithAudioV2]
    total_audios_generated: int
    processing_time: Optional[float] = None
    status: str

# V2 Video Generation Models (conversation_id instead of thread_id)
class GeneratedVideoV2(BaseModel):
    video_id: str
    script_id: str
    type: str  # "combined"
    video_url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    status: str
    processing_time: Optional[float] = None

class VideoGenerationV2Request(BaseModel):
    conversation_id: str
    audio_data: dict  # Complete audio generation response
    actor_image: str  # Actor image filename
    video_settings: Optional[dict] = {
        "aspect_ratio": "9:16",
        "quality": "low",
        "max_duration": 60
    }

class VideoGenerationV2Response(BaseModel):
    conversation_id: str
    actor_info: dict
    generated_videos: List[GeneratedVideoV2]
    total_videos_generated: int
    processing_time: Optional[float] = None
    status: str

# Document Upload Models
class DocumentUpload(BaseModel):
    """Model for uploaded document metadata"""
    id: Optional[str] = None
    campaign_id: Optional[str] = None
    file_name: str
    file_type: str
    file_size: int
    mime_type: Optional[str] = None
    s3_url: Optional[str] = None
    s3_key: Optional[str] = None
    upload_status: Optional[str] = "pending"
    created_at: Optional[datetime] = None

class DocumentUploadResponse(BaseModel):
    """Response after uploading documents"""
    success: bool
    campaign_id: Optional[str] = None  # Actual campaign_id (useful when temp_id was provided)
    documents: List[DocumentUpload]
    total_uploaded: int
    message: Optional[str] = None

class MarketingAnalysisV2RequestWithDocs(BaseModel):
    """Extended request model that includes document URLs"""
    product_info: VideoAdsProductInfoV2
    force_new_conversation: bool = False
    document_urls: Optional[List[str]] = None  # S3 URLs of uploaded documents
