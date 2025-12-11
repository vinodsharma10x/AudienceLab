# Claude v2 API Client for Sucana Video Ads Workflow
# Updated to include scripts generation capability
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
import anthropic
from pathlib import Path
import yaml
from logging_service import logger

class ClaudeV2Client:
    """Claude API client for v2 video ads workflow"""
    
    def __init__(self):
        self.client = None
        self.prompts_cache = {}
        self.init_client()
        self.load_prompts()
        # Import workflow manager for phase execution
        self._workflow_manager = None
    
    def init_client(self):
        """Initialize Claude client with extended timeout"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("claude.init.api_key_missing", "ANTHROPIC_API_KEY not found in environment variables")
            return False
        
        try:
            # Set timeout to 9 minutes (540 seconds)
            self.client = anthropic.Anthropic(
                api_key=api_key,
                timeout=540.0  # 9 minutes timeout
            )
            logger.info("claude.init.success", "Claude client initialized successfully with 9-minute timeout")
            return True
        except Exception as e:
            logger.error("claude.init.failed", f"Failed to initialize Claude client: {e}", error=str(e))
            return False
    
    def load_prompts(self):
        """Load YAML prompt templates"""
        prompts_dir = Path(__file__).parent / "prompts_v2"
        
        if not prompts_dir.exists():
            logger.error("claude.prompts.dir_not_found", f"Prompts directory not found: {prompts_dir}", directory=str(prompts_dir))
            return
        
        try:
            for yaml_file in prompts_dir.glob("*.yaml"):
                prompt_name = yaml_file.stem
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    self.prompts_cache[prompt_name] = yaml.safe_load(f)
            
            logger.info("claude.prompts.loaded", f"Loaded {len(self.prompts_cache)} prompt templates", count=len(self.prompts_cache))
            
        except Exception as e:
            logger.error("claude.prompts.load_failed", f"Failed to load prompts: {e}", error=str(e))
    
    def get_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """Get a specific prompt template"""
        return self.prompts_cache.get(prompt_name, {})
    
    def format_system_prompt(self, base_prompt: Dict[str, Any], **kwargs) -> str:
        """Format system prompt with variables"""
        try:
            system_parts = []
            
            # Add role
            if 'role' in base_prompt:
                system_parts.append(f"ROLE:\n{base_prompt['role']}")
            
            # Add capabilities
            if 'capabilities' in base_prompt:
                caps = "\n".join([f"- {cap}" for cap in base_prompt['capabilities']])
                system_parts.append(f"CAPABILITIES:\n{caps}")
            
            # Add output requirements
            if 'output_requirements' in base_prompt:
                reqs = "\n".join([f"- {req}" for req in base_prompt['output_requirements']])
                system_parts.append(f"OUTPUT REQUIREMENTS:\n{reqs}")
            
            # Add workflow context
            if 'workflow_context' in base_prompt:
                system_parts.append(f"WORKFLOW CONTEXT:\n{base_prompt['workflow_context']}")
            
            # Format with kwargs
            system_prompt = "\n\n".join(system_parts)
            return system_prompt.format(**kwargs)
            
        except Exception as e:
            logger.error("claude.prompt.system_format_error", f"Error formatting system prompt: {e}", error=str(e))
            return ""
    
    def format_user_prompt(self, prompt_template: Dict[str, Any], **kwargs) -> str:
        """Format user prompt with variables"""
        try:
            user_parts = []
            
            # Add instructions
            if 'instructions' in prompt_template:
                user_parts.append(prompt_template['instructions'])
            
            # Add specific guidelines
            if 'guidelines' in prompt_template:
                guidelines = prompt_template['guidelines']
                if isinstance(guidelines, list):
                    guidelines = "\n".join([f"- {guideline}" for guideline in guidelines])
                else:
                    guidelines = str(guidelines)
                user_parts.append(f"GUIDELINES:\n{guidelines}")
            
            # Add examples if present
            if 'examples' in prompt_template:
                user_parts.append("EXAMPLES:")
                examples = prompt_template['examples']
                if isinstance(examples, dict):
                    for key, example in examples.items():
                        user_parts.append(f"{key}: {example}")
                elif isinstance(examples, list):
                    for example in examples:
                        user_parts.append(f"Example: {example}")
            
            # Add output format
            if 'output_format' in prompt_template:
                format_info = prompt_template['output_format']
                if isinstance(format_info, dict) and 'schema' in format_info:
                    user_parts.append(f"OUTPUT FORMAT:\n{format_info['schema']}")
                else:
                    user_parts.append(f"OUTPUT FORMAT:\n{str(format_info)}")
            
            # Format with kwargs
            user_prompt = "\n\n".join(user_parts)
            if kwargs:
                user_prompt = user_prompt.format(**kwargs)
            
            return user_prompt
            
        except Exception as e:
            logger.error("claude.prompt.user_format_error", f"Error formatting user prompt: {e}", error=str(e))
            return str(prompt_template)
    
    async def generate_avatars(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate avatar analysis for the product"""
        from workflow_v2_manager import VideoAdsV2WorkflowManager
        from video_ads_v2_models import VideoAdsProductInfoV2
        
        if not self._workflow_manager:
            self._workflow_manager = VideoAdsV2WorkflowManager()
        
        # Convert dict to model
        product_model = VideoAdsProductInfoV2(**product_info)
        
        # Create a conversation and run avatar analysis
        conversation = ClaudeV2Conversation(self)
        result = await self._workflow_manager._run_avatar_analysis(conversation, product_model)
        
        return result.model_dump() if hasattr(result, 'model_dump') else result
    
    async def generate_journey(self, product_info: Dict[str, Any], avatars: Dict[str, Any]) -> Dict[str, Any]:
        """Generate journey mapping based on avatars"""
        from workflow_v2_manager import VideoAdsV2WorkflowManager
        from video_ads_v2_models import AvatarAnalysis
        
        if not self._workflow_manager:
            self._workflow_manager = VideoAdsV2WorkflowManager()
        
        # Convert dict to model
        avatar_model = AvatarAnalysis(**avatars) if not hasattr(avatars, 'dict') else avatars
        
        # Create a conversation and run journey mapping
        conversation = ClaudeV2Conversation(self)
        conversation.context["avatar_analysis"] = avatars
        result = await self._workflow_manager._run_journey_mapping(conversation, avatar_model)
        
        return result.model_dump() if hasattr(result, 'model_dump') else result
    
    async def generate_objections(self, product_info: Dict[str, Any], avatars: Dict[str, Any], journey: Dict[str, Any]) -> Dict[str, Any]:
        """Generate objections analysis based on avatars and journey"""
        from workflow_v2_manager import VideoAdsV2WorkflowManager
        from video_ads_v2_models import AvatarAnalysis, JourneyMapping
        
        if not self._workflow_manager:
            self._workflow_manager = VideoAdsV2WorkflowManager()
        
        # Convert dicts to models
        avatar_model = AvatarAnalysis(**avatars) if not hasattr(avatars, 'dict') else avatars
        journey_model = JourneyMapping(**journey) if not hasattr(journey, 'dict') else journey
        
        # Create a conversation and run objections analysis
        conversation = ClaudeV2Conversation(self)
        conversation.context["avatar_analysis"] = avatars
        conversation.context["journey_mapping"] = journey
        result = await self._workflow_manager._run_objections_analysis(conversation, avatar_model, journey_model)
        
        return result.model_dump() if hasattr(result, 'model_dump') else result
    
    async def generate_angles(self, product_info: Dict[str, Any], avatars: Dict[str, Any], journey: Dict[str, Any], objections: Dict[str, Any]) -> Dict[str, Any]:
        """Generate marketing angles based on all previous analyses"""
        from workflow_v2_manager import VideoAdsV2WorkflowManager
        from video_ads_v2_models import AvatarAnalysis, JourneyMapping, ObjectionsAnalysis
        
        if not self._workflow_manager:
            self._workflow_manager = VideoAdsV2WorkflowManager()
        
        # Convert dicts to models
        avatar_model = AvatarAnalysis(**avatars) if not hasattr(avatars, 'dict') else avatars
        journey_model = JourneyMapping(**journey) if not hasattr(journey, 'dict') else journey
        objections_model = ObjectionsAnalysis(**objections) if not hasattr(objections, 'dict') else objections
        
        # Create a conversation and run angles generation
        conversation = ClaudeV2Conversation(self)
        conversation.context["avatar_analysis"] = avatars
        conversation.context["journey_mapping"] = journey
        conversation.context["objections_analysis"] = objections
        result = await self._workflow_manager._run_angles_generation(conversation, avatar_model, journey_model, objections_model)
        
        return result.model_dump() if hasattr(result, 'model_dump') else result

class ClaudeV2Conversation:
    """Manages a Claude conversation for the full workflow"""
    
    def __init__(self, client: ClaudeV2Client):
        self.client = client
        self.conversation_id = None
        self.messages = []
        self.context = {
            "product_info": {},
            "avatar_analysis": {},
            "journey_mapping": {},
            "objections_analysis": {},
            "angles_generation": {}
        }
    
    async def send_message(self, system_prompt: str, user_prompt: str, max_tokens: int = 25000, documents: List[Dict] = None) -> str:
        """Send a message to Claude and get response with optional document support"""
        if not self.client.client:
            raise Exception("Claude client not initialized")
        
        try:
            # Build message content with documents if provided
            message_content = []

            # Add documents first if provided
            if documents:
                for doc in documents:
                    if doc.get('type') == 'pdf':
                        # PDF document format
                        message_content.append({
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": doc['data']
                            }
                        })
                    elif doc.get('type') in ['image', 'png', 'jpg', 'jpeg']:
                        # Image format
                        message_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": doc.get('media_type', 'image/jpeg'),
                                "data": doc['data']
                            }
                        })

            # Add the text prompt
            message_content.append({
                "type": "text",
                "text": user_prompt
            })

            # Add user message to conversation
            self.messages.append({
                "role": "user",
                "content": message_content if documents else user_prompt
            })

            # Prepare API call parameters
            api_params = {
                "model": "claude-haiku-4-5-20251001",  # Using Claude Haiku 4.5 (fast, cost-effective)
                "max_tokens": 25000,
                "system": system_prompt,
                "messages": self.messages
            }

            # Add beta header for PDF support if needed
            extra_headers = {}
            if documents and any(doc.get('type') == 'pdf' for doc in documents):
                extra_headers = {"anthropic-beta": "pdfs-2024-09-25"}

            # Send to Claude
            response = await asyncio.to_thread(
                self.client.client.messages.create,
                **api_params,
                extra_headers=extra_headers if extra_headers else None
            )
            
            # Extract response content
            response_content = response.content[0].text
            
            # Add assistant response to conversation
            self.messages.append({
                "role": "assistant",
                "content": response_content
            })
            
            return response_content
            
        except Exception as e:
            logger.error("claude.message.send_error", f"Error sending message to Claude: {e}", error=str(e))
            raise
    
    def store_phase_result(self, phase: str, result: Dict[str, Any]):
        """Store result from a specific phase"""
        self.context[phase] = result
    
    def get_accumulated_context(self) -> str:
        """Get formatted context from all previous phases"""
        context_parts = []
        
        for phase, data in self.context.items():
            if data:
                context_parts.append(f"{phase.upper()}:")
                context_parts.append(json.dumps(data, indent=2))
                context_parts.append("")
        
        return "\n".join(context_parts)
