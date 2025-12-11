# Video Ads Workflow Models for Sucana v4
from pydantic import BaseModel
from typing import Optional, List

# URL Parsing Models
class URLParseRequest(BaseModel):
    url: str

class URLParseResponse(BaseModel):
    product_name: Optional[str] = None
    product_information: Optional[str] = None
    target_audience: Optional[str] = None
    price: Optional[str] = None
    problem_solved: Optional[str] = None
    key_benefits: List[str] = []
    unique_selling_points: List[str] = []
    additional_info: Optional[str] = None

# Product Info Models
class VideoAdsProductInfo(BaseModel):
    product_name: str
    product_information: str
    target_audience: str
    price: Optional[str] = None
    problem_solved: str
    differentiation: str
    additional_information: Optional[str] = None

# Marketing Angles Models
class MarketingAnglesRequest(BaseModel):
    product_info: VideoAdsProductInfo

class MarketingAngle(BaseModel):
    angle: int
    category: str
    concept: str
    type: str  # "positive" or "negative"

class MarketingAnglesResponse(BaseModel):
    thread_id: str
    positive_angles: List[MarketingAngle]
    negative_angles: List[MarketingAngle]
    raw_response: str

# Hooks Models
class SelectedAngle(BaseModel):
    angle_id: str
    angle: int
    category: str
    concept: str
    type: str  # "positive" or "negative"

class HooksRequest(BaseModel):
    thread_id: str
    selected_angles: List[SelectedAngle]

class HooksByCategory(BaseModel):
    direct_question: List[str] = []
    shocking_fact: List[str] = []
    demonstration: List[str] = []
    alarm_tension: List[str] = []
    surprise_curiosity: List[str] = []
    list_enumeration: List[str] = []
    personal_story: List[str] = []

class AngleWithHooks(BaseModel):
    angle_id: str
    angle_number: int
    angle_category: str
    angle_concept: str
    angle_type: str
    hooks_by_category: HooksByCategory

class HooksResponse(BaseModel):
    thread_id: str
    hooks_by_angle: List[AngleWithHooks]
    raw_response: str

# Legacy hooks models (keeping for backward compatibility)
class HookBodyRequest(BaseModel):
    thread_id: str
    selected_angles: List[dict]

class HookBodyResponse(BaseModel):
    thread_id: str
    hooks: List[dict]
    body_messages: List[dict]
    raw_response: str

# Scripts Models
class SelectedAngleForScripts(BaseModel):
    id: str
    angle: int
    category: str
    concept: str
    type: str
    hooks_by_category: dict  # Will contain categorized hooks

class ScriptsRequest(BaseModel):
    thread_id: str
    hooks_by_angle: List[SelectedAngleForScripts]

class ScriptVariant(BaseModel):
    id: str
    version: str
    content: str
    cta: str
    target_emotion: str

class ScriptHook(BaseModel):
    selected_hook: dict
    scripts: List[ScriptVariant]

class ScriptAngle(BaseModel):
    selected_angle: dict
    hooks: List[ScriptHook]

class CampaignScripts(BaseModel):
    angles: List[ScriptAngle]

class ScriptsResponse(BaseModel):
    thread_id: str
    campaign_scripts: CampaignScripts
    raw_response: str

# Voice Actor Models
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

class VoiceActorRequest(BaseModel):
    thread_id: str
    campaign_scripts: dict  # The JSON from scripts page

class VoiceActorResponse(BaseModel):
    thread_id: str
    voices: List[ElevenLabsVoice]
    actors: List[ActorImage]
    status: str

class VoiceActorSelection(BaseModel):
    thread_id: str
    selected_voice: ElevenLabsVoice
    selected_actor: ActorImage
    campaign_scripts: dict  # Pass through from scripts page

# Audio Generation Models
class AudioGenerationRequest(BaseModel):
    thread_id: str
    voice_actor_selection: dict  # Selected voice and actor from voice-actor page
    campaign_scripts: dict  # Scripts from scripts page

class GeneratedAudio(BaseModel):
    audio_id: str
    type: str  # "combined", "hook", or "script" (keeping for backwards compatibility)
    content: str
    audio_url: str
    duration: Optional[float] = None
    file_size: Optional[int] = None
    voice_settings: Optional[dict] = None

class ScriptWithAudio(BaseModel):
    script_id: str
    hook: str
    body: str
    selected: bool
    # New combined audio field
    combined_audio: Optional[GeneratedAudio] = None
    # Keep old fields for backwards compatibility during transition
    hook_audio: Optional[GeneratedAudio] = None
    script_audio: Optional[GeneratedAudio] = None

class AudioGenerationResponse(BaseModel):
    thread_id: str
    selected_angle: dict
    voice_info: dict  # Selected voice and actor info
    scripts_with_audio: List[ScriptWithAudio]
    total_audios_generated: int
    status: str

# Video Generation Models
class VideoGenerationRequest(BaseModel):
    thread_id: str
    selected_audio: dict
    video_settings: Optional[dict] = None

class VideoGenerationResponse(BaseModel):
    thread_id: str
    video_url: str
    status: str

# Enhanced Video Generation Models
class GeneratedVideo(BaseModel):
    video_id: str
    script_id: str
    video_type: str  # "combined" (default), "hook_only", "script_only" for backwards compatibility
    hook_text: str
    script_text: str
    combined_text: Optional[str] = None  # New field for combined hook + script text
    video_url: str
    local_path: Optional[str] = None
    hedra_job_id: Optional[str] = None
    duration: Optional[float] = None
    file_size: Optional[int] = None
    aspect_ratio: str = "9:16"
    quality: str = "low"
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None
    created_at: Optional[str] = None

class VideoGenerationDetailedRequest(BaseModel):
    thread_id: str
    audio_data: dict  # Complete audio generation response
    actor_image: str  # Actor image filename
    video_settings: Optional[dict] = {
        "aspect_ratio": "9:16",
        "quality": "low",
        "max_duration": 60
    }

class VideoGenerationDetailedResponse(BaseModel):
    thread_id: str
    actor_info: dict
    generated_videos: List[GeneratedVideo]
    total_videos_generated: int
    processing_time: Optional[float] = None
    status: str
