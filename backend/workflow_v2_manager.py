# Video Ads V2 Workflow Manager for Claude Integration
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from claude_v2_client import ClaudeV2Client, ClaudeV2Conversation
from video_ads_v2_models import (
    VideoAdsProductInfoV2, MarketingAnalysisV2, MarketingAnglesV2Response,
    AvatarAnalysis, JourneyMapping, ObjectionsAnalysis, AnglesGeneration,
    WorkflowStateV2, AngleWithHooksV2, HooksByCategoryV2
)
from logging_service import logger

class VideoAdsV2WorkflowManager:
    """Manages the complete V2 workflow using Claude"""
    
    def __init__(self):
        self.client = ClaudeV2Client()
        self.active_conversations = {}  # In production, use Redis/DB
        
    async def create_marketing_analysis(
        self, 
        product_info: VideoAdsProductInfoV2, 
        user_id: str,
        force_new_conversation: bool = False
    ) -> MarketingAnalysisV2:
        """Run complete 4-phase analysis workflow"""
        
        start_time = time.time()
        conversation_id = str(uuid.uuid4())
        
        # Set logging context
        logger.set_context(
            user_id=user_id,
            conversation_id=conversation_id,
            thread_id=conversation_id
        )
        
        logger.info(
            "workflow.marketing_analysis.started",
            f"Starting marketing analysis for {product_info.product_name}",
            product_name=product_info.product_name,
            target_audience=product_info.target_audience,
            price=product_info.price
        )
        
        logger.debug(
            "workflow.marketing_analysis.init",
            "Initializing Claude V2 conversation",
            product_info=product_info.dict()
        )
        
        # Initialize conversation
        logger.debug(
            "workflow.conversation.init",
            "Initializing Claude V2 conversation"
        )
        conversation = ClaudeV2Conversation(self.client)
        logger.debug(
            "workflow.conversation.initialized",
            "Claude V2 conversation initialized successfully"
        )
        
        try:
            # Phase 1: Avatar Analysis
            logger.info(
                "workflow.phase1.started",
                "Starting Phase 1 - Avatar Analysis",
                elapsed_time=f"{time.time() - start_time:.2f}s"
            )
            avatar_result = await self._run_avatar_analysis(conversation, product_info)
            logger.info(
                "workflow.phase1.completed",
                "Phase 1: Avatar Analysis complete",
                result_type=str(type(avatar_result)),
                elapsed_time=f"{time.time() - start_time:.2f}s"
            )
            
            # Phase 2: Journey Mapping  
            logger.info(
                "workflow.phase2.started",
                "Starting Phase 2 - Journey Mapping",
                elapsed_time=f"{time.time() - start_time:.2f}s"
            )
            journey_result = await self._run_journey_mapping(conversation, avatar_result)
            logger.info(
                "workflow.phase2.completed",
                "Phase 2: Journey Mapping complete",
                result_type=str(type(journey_result)),
                elapsed_time=f"{time.time() - start_time:.2f}s"
            )
            
            # Phase 3: Objections Analysis
            logger.info(
                "workflow.phase3.started",
                "Starting Phase 3 - Objections Analysis",
                elapsed_time=f"{time.time() - start_time:.2f}s"
            )
            objections_result = await self._run_objections_analysis(conversation, avatar_result, journey_result)
            logger.info(
                "workflow.phase3.completed",
                "Phase 3: Objections Analysis complete",
                result_type=str(type(objections_result)),
                elapsed_time=f"{time.time() - start_time:.2f}s"
            )
            
            # Phase 4: Angles Generation
            logger.info(
                "workflow.phase4.started",
                "Starting Phase 4 - Angles Generation",
                elapsed_time=f"{time.time() - start_time:.2f}s"
            )
            angles_result = await self._run_angles_generation(conversation, avatar_result, journey_result, objections_result)
            logger.info(
                "workflow.phase4.completed",
                "Phase 4: Marketing Angles complete",
                result_type=str(type(angles_result)),
                elapsed_time=f"{time.time() - start_time:.2f}s"
            )
            
            # Combine results
            logger.debug(
                "workflow.analysis.combining",
                "Combining all analysis results into MarketingAnalysisV2"
            )
            analysis = MarketingAnalysisV2(
                avatar_analysis=avatar_result,
                journey_mapping=journey_result,
                objections_analysis=objections_result,
                angles_generation=angles_result
            )
            logger.debug(
                "workflow.analysis.combined",
                "Combined analysis created successfully",
                analysis_type=str(type(analysis))
            )
            
            # Store workflow state
            logger.debug(
                "workflow.state.creating",
                "Creating workflow state"
            )
            workflow_state = WorkflowStateV2(
                conversation_id=conversation_id,
                user_id=user_id,
                current_phase="completed",
                product_info=product_info,
                analysis=analysis,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            logger.debug(
                "workflow.state.created",
                "Workflow state created successfully"
            )
            
            logger.debug(
                "workflow.conversation.storing",
                "Storing conversation data in active_conversations"
            )
            self.active_conversations[conversation_id] = {
                "conversation": conversation,
                "state": workflow_state,
                "analysis": analysis
            }
            logger.debug(
                "workflow.conversation.stored",
                f"Conversation stored with ID: {conversation_id}",
                total_active=len(self.active_conversations)
            )
            
            processing_time = time.time() - start_time
            logger.info(
                "workflow.marketing_analysis.completed",
                f"Complete analysis finished in {processing_time:.2f} seconds",
                positive_angles=len(angles_result.positive_angles),
                negative_angles=len(angles_result.negative_angles),
                duration_ms=int(processing_time * 1000)
            )
            
            return analysis
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "workflow.marketing_analysis.failed",
                f"Error in create_marketing_analysis after {processing_time:.2f} seconds",
                exception=e,
                duration_ms=int(processing_time * 1000)
            )
            raise
    
    async def _run_avatar_analysis(
        self, 
        conversation: ClaudeV2Conversation, 
        product_info: VideoAdsProductInfoV2
    ) -> AvatarAnalysis:
        """Phase 1: Avatar Analysis"""
        
        # Load prompts
        system_prompt_template = self.client.get_prompt("system_prompt")
        avatar_prompt_template = self.client.get_prompt("avatar_analysis")
        
        # Format system prompt
        system_prompt = self.client.format_system_prompt(system_prompt_template)
        
        # Format user prompt with product info
        product_context = f"""
PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Price: {product_info.price or 'Not specified'}
Problem Solved: {product_info.problem_solved}
Differentiation: {product_info.differentiation}
Additional Information: {product_info.additional_information or 'None provided'}

TASK: Generate comprehensive avatar analysis with 5 detailed blocks as specified.
"""
        
        user_prompt = self.client.format_user_prompt(avatar_prompt_template) + "\n\n" + product_context
        
        # Send to Claude
        response = await conversation.send_message(system_prompt, user_prompt)
        
        # Parse response
        try:
            # Clean response to handle markdown code blocks
            clean_response = response.strip()
            
            # Look for JSON content between ```json and ``` or ``` and ```
            import re
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            json_match = re.search(json_pattern, clean_response, re.DOTALL)
            
            if json_match:
                clean_response = json_match.group(1)
            else:
                # Try to find JSON-like content (starts with { and ends with })
                json_start = clean_response.find('{')
                json_end = clean_response.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    clean_response = clean_response[json_start:json_end+1]
            
            response_data = json.loads(clean_response)
            avatar_data = response_data.get("avatar_analysis", {})
            
            # Convert to Pydantic model
            avatar_analysis = AvatarAnalysis(**avatar_data)
            conversation.store_phase_result("avatar_analysis", avatar_data)
            
            return avatar_analysis
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(
                "workflow.phase1.parse_error",
                "Error parsing avatar analysis",
                exception=e,
                response_preview=response[:500] if response else "None"
            )
            raise
    
    async def _run_journey_mapping(
        self, 
        conversation: ClaudeV2Conversation, 
        avatar_analysis: AvatarAnalysis
    ) -> JourneyMapping:
        """Phase 2: Journey Mapping"""
        
        journey_prompt_template = self.client.get_prompt("journey_mapping")
        
        # Include avatar context
        avatar_context = f"""
AVATAR CONTEXT FROM PREVIOUS ANALYSIS:
{json.dumps(avatar_analysis.dict(), indent=2)}

TASK: Generate detailed customer journey mapping with 4 phases based on this avatar profile.
"""
        
        user_prompt = self.client.format_user_prompt(journey_prompt_template) + "\n\n" + avatar_context
        
        # Send to Claude (no system prompt needed, already in conversation)
        response = await conversation.send_message("", user_prompt)
        
        try:
            # Clean response to handle markdown code blocks
            clean_response = response.strip()
            
            # Look for JSON content between ```json and ``` or ``` and ```
            import re
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            json_match = re.search(json_pattern, clean_response, re.DOTALL)
            
            if json_match:
                clean_response = json_match.group(1)
            else:
                # Try to find JSON-like content (starts with { and ends with })
                json_start = clean_response.find('{')
                json_end = clean_response.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    clean_response = clean_response[json_start:json_end+1]
            
            response_data = json.loads(clean_response)
            journey_data = response_data.get("journey_mapping", {})
            
            journey_mapping = JourneyMapping(**journey_data)
            conversation.store_phase_result("journey_mapping", journey_data)
            
            return journey_mapping
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(
                "workflow.phase2.parse_error",
                "Error parsing journey mapping",
                exception=e,
                response_preview=response[:500] if response else "None"
            )
            raise
    
    async def _run_objections_analysis(
        self, 
        conversation: ClaudeV2Conversation, 
        avatar_analysis: AvatarAnalysis,
        journey_mapping: JourneyMapping
    ) -> ObjectionsAnalysis:
        """Phase 3: Objections Analysis"""
        
        objections_prompt_template = self.client.get_prompt("objections_analysis")
        
        # Include previous context
        context = f"""
ACCUMULATED CONTEXT:
{conversation.get_accumulated_context()}

TASK: Identify and address customer objections based on avatar profile and journey analysis.
"""
        
        user_prompt = self.client.format_user_prompt(objections_prompt_template) + "\n\n" + context
        
        response = await conversation.send_message("", user_prompt)
        
        try:
            # Clean response to handle markdown code blocks
            clean_response = response.strip()
            
            # Look for JSON content between ```json and ``` or ``` and ```
            import re
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            json_match = re.search(json_pattern, clean_response, re.DOTALL)
            
            if json_match:
                clean_response = json_match.group(1)
            else:
                # Try to find JSON-like content (starts with { and ends with })
                json_start = clean_response.find('{')
                json_end = clean_response.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    clean_response = clean_response[json_start:json_end+1]
            
            response_data = json.loads(clean_response)
            objections_data = response_data.get("objections_analysis", {})
            
            objections_analysis = ObjectionsAnalysis(**objections_data)
            conversation.store_phase_result("objections_analysis", objections_data)
            
            return objections_analysis
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(
                "workflow.phase3.parse_error",
                "Error parsing objections analysis",
                exception=e,
                response_preview=response[:500] if response else "None"
            )
            raise
    
    async def _run_angles_generation(
        self, 
        conversation: ClaudeV2Conversation, 
        avatar_analysis: AvatarAnalysis,
        journey_mapping: JourneyMapping,
        objections_analysis: ObjectionsAnalysis
    ) -> AnglesGeneration:
        """Phase 4: Marketing Angles Generation"""
        
        angles_prompt_template = self.client.get_prompt("angles_generation")
        
        # Include all accumulated context
        context = f"""
COMPLETE ANALYSIS CONTEXT:
{conversation.get_accumulated_context()}

TASK: Generate 14 strategic marketing angles (7 positive, 7 negative) based on comprehensive analysis.
"""
        
        user_prompt = self.client.format_user_prompt(angles_prompt_template) + "\n\n" + context
        
        response = await conversation.send_message("", user_prompt)
        
        try:
            # Clean response to handle markdown code blocks
            clean_response = response.strip()
            
            # Look for JSON content between ```json and ``` or ``` and ```
            import re
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            json_match = re.search(json_pattern, clean_response, re.DOTALL)
            
            if json_match:
                clean_response = json_match.group(1)
            else:
                # Try to find JSON-like content (starts with { and ends with })
                json_start = clean_response.find('{')
                json_end = clean_response.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    clean_response = clean_response[json_start:json_end+1]
            
            response_data = json.loads(clean_response)
            
            # Handle both possible response formats
            if "angles_generation" in response_data:
                angles_data = response_data["angles_generation"]
            else:
                angles_data = response_data
            
            angles_generation = AnglesGeneration(**angles_data)
            conversation.store_phase_result("angles_generation", angles_data)
            
            return angles_generation
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(
                "workflow.phase4.parse_error",
                "Error parsing marketing angles",
                exception=e,
                response_preview=response[:500] if response else "None"
            )
            raise
    
    def get_conversation_state(self, conversation_id: str) -> Optional[WorkflowStateV2]:
        """Get stored conversation state"""
        conversation_data = self.active_conversations.get(conversation_id)
        if conversation_data:
            return conversation_data["state"]
        return None
    
    def get_conversation_analysis(self, conversation_id: str) -> Optional[MarketingAnalysisV2]:
        """Get stored analysis"""
        conversation_data = self.active_conversations.get(conversation_id)
        if conversation_data:
            return conversation_data["analysis"]
        return None
    
    async def create_hooks_analysis(
        self,
        product_info: VideoAdsProductInfoV2,
        complete_analysis: MarketingAnalysisV2,
        selected_angles: list,
        user_id: str
    ) -> list:
        """Generate hooks for selected angles using Claude with full context"""
        
        start_time = time.time()
        
        # Set logging context
        logger.set_context(
            user_id=user_id,
            thread_id=str(uuid.uuid4())  # New thread for hooks generation
        )
        
        logger.info(
            "workflow.hooks_generation.started",
            f"Starting Claude hooks generation for {len(selected_angles)} selected angles",
            angles_count=len(selected_angles)
        )
        
        # Initialize conversation for hooks generation
        conversation = ClaudeV2Conversation(self.client)
        
        try:
            # Load hooks generation prompt
            hooks_prompt_template = self.client.get_prompt("hooks_generation")
            
            # Log the loaded prompt template
            logger.debug(
                "workflow.hooks_generation.prompt_loaded",
                "Loaded hooks prompt template",
                template_type=str(type(hooks_prompt_template))
            )
            
            # Convert the YAML dict to a proper system prompt text
            system_prompt = f"""
{hooks_prompt_template['role']}

PURPOSE:
{hooks_prompt_template['purpose']}

OPERATING INSTRUCTIONS:
{hooks_prompt_template['operating_instructions']}

VIRAL HOOKS MANUAL PRINCIPLES:
{hooks_prompt_template['viral_hooks_manual_principles']}

JSON OUTPUT FORMAT:
{hooks_prompt_template['json_output_format']}

GENERATION RULES:
{hooks_prompt_template['generation_rules']}

CRITICAL RULES:
{hooks_prompt_template['critical_rules']}

CONTEXT INTEGRATION:
{hooks_prompt_template['context_integration']}
"""
            
            # Build comprehensive context for Claude (this becomes the user prompt)
            context = self._build_hooks_context(
                product_info, 
                complete_analysis, 
                selected_angles
            )
            
            # The user prompt is just the context - no additional formatting needed
            user_prompt = context
            
            # Log what we're sending to Claude
            logger.debug(
                "workflow.hooks_generation.prompts",
                "Sending prompts to Claude",
                system_prompt_length=len(system_prompt),
                user_prompt_length=len(user_prompt)
            )
            
            # Send to Claude with proper system prompt
            response = await conversation.send_message(system_prompt, user_prompt)
            
            # Log raw response from Claude
            logger.debug(
                "workflow.hooks_generation.response_received",
                "Received response from Claude",
                response_type=str(type(response)),
                response_length=len(response)
            )
            
            # Parse hooks response
            try:
                logger.debug(
                    "workflow.hooks_generation.parsing",
                    "Attempting to parse JSON response"
                )
                
                # Clean response to handle markdown code blocks
                clean_response = response.strip()
                
                # Look for JSON content between ```json and ``` or ``` and ```
                import re
                json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                json_match = re.search(json_pattern, clean_response, re.DOTALL)
                
                if json_match:
                    clean_response = json_match.group(1)
                else:
                    # Try to find JSON-like content (starts with { and ends with })
                    json_start = clean_response.find('{')
                    json_end = clean_response.rfind('}')
                    if json_start != -1 and json_end != -1 and json_end > json_start:
                        clean_response = clean_response[json_start:json_end+1]
                
                logger.debug(
                    "workflow.hooks_generation.json_cleaned",
                    "JSON response cleaned",
                    cleaned_length=len(clean_response)
                )
                
                response_data = json.loads(clean_response)
                logger.debug(
                    "workflow.hooks_generation.json_parsed",
                    "JSON parsing successful",
                    response_keys=list(response_data.keys())
                )
                
                hooks_by_angle = response_data.get("hooks_by_angle", [])
                logger.debug(
                    "workflow.hooks_generation.angles_found",
                    f"Found {len(hooks_by_angle)} angles in response",
                    angles_count=len(hooks_by_angle)
                )
                
                # Convert to Pydantic models for validation
                validated_hooks = []
                for hook_data in hooks_by_angle:
                    from video_ads_v2_models import AngleWithHooksV2, HooksByCategoryV2
                    
                    # Handle field name inconsistency (angle_concept vs concept)
                    angle_concept = hook_data.get("angle_concept") or hook_data.get("concept")
                    if not angle_concept:
                        raise ValueError(f"Missing angle_concept or concept field in hook_data: {hook_data.keys()}")
                    
                    hooks_by_category = HooksByCategoryV2(**hook_data["hooks_by_category"])
                    angle_with_hooks = AngleWithHooksV2(
                        angle_id=hook_data["angle_id"],
                        angle_number=hook_data["angle_number"],
                        angle_category=hook_data["angle_category"],
                        angle_concept=angle_concept,
                        angle_type=hook_data["angle_type"],
                        hooks_by_category=hooks_by_category
                    )
                    validated_hooks.append(angle_with_hooks)
                
                processing_time = time.time() - start_time
                logger.info(
                    "workflow.hooks_generation.completed",
                    f"Hooks generation completed in {processing_time:.2f} seconds",
                    duration_ms=int(processing_time * 1000),
                    hooks_count=len(validated_hooks)
                )
                
                return validated_hooks
                
            except (json.JSONDecodeError, Exception) as e:
                logger.error(
                    "workflow.hooks_generation.parse_error",
                    "Error parsing hooks response",
                    exception=e,
                    response_length=len(response) if response else 0
                )
                raise
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "workflow.hooks_generation.failed",
                f"Error in hooks generation after {processing_time:.2f} seconds",
                exception=e,
                duration_ms=int(processing_time * 1000)
            )
            raise
    
    def _build_hooks_context(
        self,
        product_info: VideoAdsProductInfoV2,
        complete_analysis: MarketingAnalysisV2,
        selected_angles: list
    ) -> str:
        """Build comprehensive context for hooks generation"""
        
        # Format selected angles
        angles_data = []
        for angle in selected_angles:
            angles_data.append({
                "angle_id": angle.angle_id,
                "angle": angle.angle,
                "category": angle.category,
                "concept": angle.concept,
                "type": angle.type
            })
        
        context = f"""
COMPLETE CONTEXT FOR HOOKS GENERATION:

PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Price: {product_info.price or 'Not specified'}
Problem Solved: {product_info.problem_solved}
Differentiation: {product_info.differentiation}
Additional Information: {product_info.additional_information or 'None provided'}

AVATAR ANALYSIS INSIGHTS:
Demographics: Age {complete_analysis.avatar_analysis.demographic_data.age_range}, {complete_analysis.avatar_analysis.demographic_data.geographic_location}, {complete_analysis.avatar_analysis.demographic_data.socioeconomic_level}
Pain Points: {complete_analysis.avatar_analysis.reality_expectations.problems_pain_points}
Core Values: {complete_analysis.avatar_analysis.psychographic_factors.core_values}
Fears/Concerns: {complete_analysis.avatar_analysis.psychographic_factors.fears_concerns}

CUSTOMER JOURNEY INSIGHTS:
Discovery Phase Emotions: {', '.join(complete_analysis.journey_mapping.discovery_phase.emotions)}
Consideration Phase Problems: {complete_analysis.journey_mapping.consideration_phase.customer_problems}
Decision Phase Needs: {complete_analysis.journey_mapping.decision_phase.customer_needs}

KEY OBJECTIONS TO ADDRESS:
Solution Objections: {', '.join([obj.objection_description for obj in complete_analysis.objections_analysis.solution_objections[:3]])}
Internal Objections: {', '.join([obj.objection_description for obj in complete_analysis.objections_analysis.internal_objections[:3]])}

SELECTED MARKETING ANGLES:
{json.dumps(angles_data, indent=2)}

"""
        
        return context
    
    async def create_scripts_analysis(
        self,
        conversation_id: str,
        hooks_by_angle: List,
        user_id: str
    ) -> dict:
        """Generate AIDA scripts using Claude with complete accumulated context"""
        
        start_time = time.time()
        
        # Set logging context
        logger.set_context(
            user_id=user_id,
            conversation_id=conversation_id,
            thread_id=conversation_id
        )
        
        logger.info(
            "workflow.scripts_generation.started",
            f"Starting Claude scripts generation for {len(hooks_by_angle)} angles",
            angles_count=len(hooks_by_angle)
        )
        
        # Log hooks details
        for i, angle_data in enumerate(hooks_by_angle):
            hooks_count = 0
            if 'hooks_by_category' in angle_data:
                for category, hooks in angle_data['hooks_by_category'].items():
                    hooks_count += len(hooks)
            logger.debug(
                f"workflow.scripts_generation.angle_{i+1}",
                f"Angle {i+1} details",
                angle_id=angle_data.get('angle_id', 'N/A'),
                hooks_count=hooks_count
            )
        
        # Retrieve stored analysis from conversation
        logger.debug(
            "workflow.scripts_generation.retrieving",
            "Retrieving stored conversation analysis",
            active_count=len(self.active_conversations),
            active_ids=list(self.active_conversations.keys())
        )
        stored_analysis = self.get_conversation_analysis(conversation_id)
        stored_state = self.get_conversation_state(conversation_id)
        logger.debug(
            "workflow.scripts_generation.retrieved",
            "Retrieved analysis and state",
            has_analysis=stored_analysis is not None,
            has_state=stored_state is not None
        )
        
        # If not in memory, try to load from database
        if not stored_analysis or not stored_state:
            logger.warning(
                "workflow.scripts_generation.memory_miss",
                f"Analysis not in memory for conversation {conversation_id}, trying to load from DB"
            )
            
            # Import database service if needed
            from video_ads_v2_database_service import VideoAdsV2DatabaseService
            from auth import supabase
            
            if supabase:
                db_service = VideoAdsV2DatabaseService(supabase)
                
                # Get campaign by conversation ID
                import asyncio
                campaign = await db_service.get_campaign_by_conversation(conversation_id, user_id)
                
                if campaign:
                    logger.debug(
                        "workflow.scripts_generation.campaign_found",
                        f"Found campaign {campaign['id']} for conversation {conversation_id}",
                        campaign_id=campaign['id']
                    )
                    
                    # Load marketing analysis from DB
                    marketing_data = await db_service.get_marketing_analysis(campaign['id'])
                    
                    if marketing_data:
                        logger.debug(
                            "workflow.scripts_generation.marketing_loaded",
                            "Loaded marketing analysis from database",
                            data_keys=list(marketing_data.keys())
                        )
                        
                        # Reconstruct the analysis object
                        from video_ads_v2_models import (
                            MarketingAnalysisV2, AvatarAnalysis, JourneyMapping,
                            ObjectionsAnalysis, AnglesGeneration
                        )
                        
                        try:
                            # Safely reconstruct each component with error handling
                            avatar_data = marketing_data.get('avatar_analysis')
                            journey_data = marketing_data.get('journey_mapping')
                            objections_data = marketing_data.get('objections_analysis')
                            angles_data = marketing_data.get('angles_generation')
                            
                            logger.debug(
                                "workflow.scripts_generation.data_check",
                                "Checking analysis data components",
                                has_avatar=avatar_data is not None,
                                has_journey=journey_data is not None,
                                has_objections=objections_data is not None,
                                has_angles=angles_data is not None
                            )
                            
                            if not all([avatar_data, journey_data, objections_data, angles_data]):
                                logger.error(
                                    "workflow.scripts_generation.missing_data",
                                    "Missing required analysis data",
                                    has_avatar=bool(avatar_data),
                                    has_journey=bool(journey_data),
                                    has_objections=bool(objections_data),
                                    has_angles=bool(angles_data)
                                )
                                stored_analysis = None
                            else:
                                stored_analysis = MarketingAnalysisV2(
                                    avatar_analysis=AvatarAnalysis(**avatar_data),
                                    journey_mapping=JourneyMapping(**journey_data),
                                    objections_analysis=ObjectionsAnalysis(**objections_data),
                                    angles_generation=AnglesGeneration(**angles_data)
                                )
                                logger.debug(
                                    "workflow.scripts_generation.analysis_reconstructed",
                                    "Successfully reconstructed MarketingAnalysisV2"
                                )
                        except Exception as e:
                            logger.error(
                                "workflow.scripts_generation.reconstruct_error",
                                "Error reconstructing MarketingAnalysisV2",
                                exception=e
                            )
                            stored_analysis = None
                        
                        # Load product info
                        product_data = await db_service.get_product_info(campaign['id'])
                        
                        if product_data and stored_analysis:
                            logger.debug(
                                "workflow.scripts_generation.product_loaded",
                                "Loaded product info from database",
                                data_keys=list(product_data.keys())
                            )
                            
                            try:
                                from video_ads_v2_models import VideoAdsProductInfoV2, WorkflowStateV2
                                
                                product_info = VideoAdsProductInfoV2(**product_data)
                                logger.debug(
                                    "workflow.scripts_generation.product_reconstructed",
                                    "Successfully reconstructed VideoAdsProductInfoV2"
                                )
                                
                                # Create a minimal state for scripts generation
                                stored_state = WorkflowStateV2(
                                    conversation_id=conversation_id,
                                    user_id=user_id,
                                    current_phase="scripts_generation",  # Add the required field
                                    product_info=product_info,
                                    analysis=stored_analysis,
                                    created_at=campaign.get('created_at', ''),
                                    updated_at=campaign.get('updated_at', '')
                                )
                                
                                logger.debug(
                                    "workflow.scripts_generation.state_reconstructed",
                                    "Successfully reconstructed state from database"
                                )
                                
                                # Store the reconstructed state in memory for future use
                                self.active_conversations[conversation_id] = {
                                    "conversation": None,  # We'll create a new conversation
                                    "state": stored_state,
                                    "analysis": stored_analysis
                                }
                                logger.debug(
                                    "workflow.scripts_generation.state_cached",
                                    "Stored reconstructed state in active_conversations"
                                )
                                
                            except Exception as e:
                                logger.error(
                                    "workflow.scripts_generation.product_error",
                                    "Error reconstructing product info or state",
                                    exception=e
                                )
                                stored_state = None
                        else:
                            if not product_data:
                                logger.error(
                                    "workflow.scripts_generation.no_product",
                                    f"No product info found in database for campaign {campaign['id']}"
                                )
                            if not stored_analysis:
                                logger.error(
                                    "workflow.scripts_generation.no_analysis",
                                    "No analysis available (failed to reconstruct from DB)"
                                )
                    else:
                        logger.error(
                            "workflow.scripts_generation.no_marketing",
                            f"No marketing analysis found in database for campaign {campaign['id']}"
                        )
                else:
                    logger.error(
                        "workflow.scripts_generation.no_campaign",
                        f"No campaign found in database for conversation {conversation_id}"
                    )
            else:
                logger.error(
                    "workflow.scripts_generation.no_db",
                    "Database service not available"
                )
        
        if not stored_analysis:
            logger.error(
                "workflow.scripts_generation.no_stored_analysis",
                f"No stored analysis found for conversation {conversation_id}"
            )
            raise Exception(f"No stored analysis found for conversation {conversation_id}")
        
        if not stored_state:
            logger.error(
                "workflow.scripts_generation.no_stored_state",
                f"No stored state found for conversation {conversation_id}"
            )
            raise Exception(f"No stored state found for conversation {conversation_id}")
        
        logger.debug(
            "workflow.scripts_generation.state_ready",
            "Retrieved stored analysis and state successfully",
            product_name=stored_state.product_info.product_name
        )
        
        # Initialize conversation for scripts generation
        conversation = ClaudeV2Conversation(self.client)
        
        try:
            # Load scripts generation prompt
            logger.debug(
                "workflow.scripts_generation.loading_prompt",
                "Loading scripts generation prompt template"
            )
            scripts_prompt_template = self.client.get_prompt("scripts_generation")
            
            logger.debug(
                "workflow.scripts_generation.prompt_loaded",
                "Loaded scripts prompt template",
                template_type=str(type(scripts_prompt_template)),
                template_keys=list(scripts_prompt_template.keys()) if isinstance(scripts_prompt_template, dict) else None
            )
            
            # Convert the YAML dict to a proper system prompt text
            system_prompt = f"""
{scripts_prompt_template['role']}

PURPOSE:
{scripts_prompt_template['purpose']}

USAGE FLOW:
{scripts_prompt_template['usage_flow']}

WRITING GUIDELINES:
{scripts_prompt_template['writing_guidelines']}

JSON OUTPUT FORMAT:
{scripts_prompt_template['json_output_format']}

SCRIPT VARIATION GUIDELINES:
{scripts_prompt_template['script_variation_guidelines']}

RULES:
{scripts_prompt_template['rules']}

ID CONVENTION:
{scripts_prompt_template['id_convention']}

CRITICAL INSTRUCTIONS:
{scripts_prompt_template['critical_instructions']}

CONTEXT INTEGRATION:
{scripts_prompt_template['context_integration']}
"""
            
            # Build comprehensive context for Claude (this becomes the user prompt)
            logger.debug(
                "workflow.scripts_generation.building_context",
                "Building comprehensive context for scripts generation"
            )
            context = self._build_scripts_context(
                stored_state.product_info, 
                stored_analysis, 
                hooks_by_angle
            )
            
            # Log prompts being sent to Claude
            logger.debug(
                "workflow.scripts_generation.prompts_ready",
                "Prompts ready to send to Claude",
                system_prompt_length=len(system_prompt),
                user_prompt_length=len(context)
            )
            
            # Send to Claude with proper system prompt and reduced max_tokens for scripts
            logger.debug(
                "workflow.scripts_generation.sending_request",
                "Sending request to Claude",
                max_tokens=6000
            )
            response = await conversation.send_message(system_prompt, context, max_tokens=6000)
            
            # Log raw response from Claude
            logger.debug(
                "workflow.scripts_generation.response_received",
                "Received response from Claude",
                response_type=str(type(response)),
                response_length=len(response)
            )
            
            # Parse scripts response
            try:
                logger.debug(
                    "workflow.scripts_generation.parsing",
                    "Attempting to parse JSON response"
                )
                
                # Clean response to handle markdown code blocks and malformed JSON
                clean_response = response.strip()
                
                # Enhanced JSON cleaning for Claude 4
                logger.debug(
                    "workflow.scripts_generation.cleaning_json",
                    "Starting enhanced JSON cleaning for scripts"
                )
                
                # Remove markdown code blocks
                import re
                json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                json_match = re.search(json_pattern, clean_response, re.DOTALL)
                
                if json_match:
                    clean_response = json_match.group(1)
                    logger.debug(
                        "workflow.scripts_generation.json_markdown",
                        "Found JSON in markdown blocks, extracted"
                    )
                else:
                    # Try to find JSON-like content (starts with { and ends with })
                    json_start = clean_response.find('{')
                    json_end = clean_response.rfind('}')
                    if json_start != -1 and json_end != -1 and json_end > json_start:
                        clean_response = clean_response[json_start:json_end+1]
                        logger.debug(
                            "workflow.scripts_generation.json_boundaries",
                            "Found JSON boundaries, extracted"
                        )
                
                # Additional cleaning for Claude 4 common issues
                # Fix trailing commas which cause JSON parse errors
                clean_response = re.sub(r',(\s*[}\]])', r'\1', clean_response)
                
                # Fix missing commas between objects/arrays
                clean_response = re.sub(r'}\s*{', '},{', clean_response)
                clean_response = re.sub(r']\s*\[', '],[', clean_response)
                
                # Remove any remaining text after final }
                final_brace = clean_response.rfind('}')
                if final_brace != -1:
                    clean_response = clean_response[:final_brace+1]
                
                logger.debug(
                    "workflow.scripts_generation.json_cleaned",
                    "JSON cleaned",
                    cleaned_length=len(clean_response),
                    preview_start=clean_response[:200] if len(clean_response) > 200 else clean_response,
                    preview_end=clean_response[-200:] if len(clean_response) > 200 else ""
                )
                
                try:
                    response_data = json.loads(clean_response)
                    logger.debug(
                        "workflow.scripts_generation.json_parsed",
                        "JSON parsing successful"
                    )
                except json.JSONDecodeError as parse_error:
                    logger.warning(
                        "workflow.scripts_generation.json_parse_failed",
                        "JSON parsing still failed",
                        error_line=parse_error.lineno,
                        error_column=parse_error.colno,
                        error_msg=parse_error.msg
                    )
                    
                    # Try to fix common Claude 4 JSON issues
                    logger.debug(
                        "workflow.scripts_generation.json_repair",
                        "Attempting additional JSON repairs"
                    )
                    
                    # Fix unescaped quotes in strings
                    clean_response = re.sub(r'(?<!\\)"(?=[^,}\]]*[,}\]])', '\\"', clean_response)
                    
                    # Fix single quotes (not valid JSON)
                    clean_response = clean_response.replace("'", '"')
                    
                    # Try parsing again
                    try:
                        response_data = json.loads(clean_response)
                        logger.debug(
                            "workflow.scripts_generation.json_repaired",
                            "JSON parsing successful after repairs"
                        )
                    except json.JSONDecodeError as final_error:
                        logger.error(
                            "workflow.scripts_generation.json_final_error",
                            "Final JSON parsing failed",
                            exception=final_error
                        )
                        # Save the problematic JSON for debugging
                        debug_file = f"debug_json_scripts_{int(time.time())}.txt"
                        with open(debug_file, "w") as f:
                            f.write(clean_response)
                        logger.error(
                            "workflow.scripts_generation.debug_saved",
                            f"Saved problematic JSON to {debug_file}"
                        )
                        raise
                
                logger.debug(
                    "workflow.scripts_generation.response_parsed",
                    "Response parsed successfully",
                    response_keys=list(response_data.keys())
                )
                
                campaign_scripts = response_data.get("campaign_scripts", {})
                logger.debug(
                    "workflow.scripts_generation.scripts_found",
                    f"Found campaign_scripts with {len(campaign_scripts.get('angles', []))} angles",
                    angles_count=len(campaign_scripts.get('angles', []))
                )
                
                processing_time = time.time() - start_time
                logger.info(
                    "workflow.scripts_generation.completed",
                    f"Scripts generation completed in {processing_time:.2f} seconds",
                    duration_ms=int(processing_time * 1000),
                    scripts_count=len(campaign_scripts.get('angles', []))
                )
                
                return campaign_scripts
                
            except (json.JSONDecodeError, Exception) as e:
                logger.error(
                    "workflow.scripts_generation.parse_error",
                    "Error parsing scripts response",
                    exception=e,
                    response_length=len(response) if response else 0
                )
                raise
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "workflow.scripts_generation.failed",
                f"Error in scripts generation after {processing_time:.2f} seconds",
                exception=e,
                duration_ms=int(processing_time * 1000)
            )
            raise
    
    def _build_scripts_context(
        self,
        product_info: VideoAdsProductInfoV2,
        complete_analysis: MarketingAnalysisV2,
        hooks_by_angle: List
    ) -> str:
        """Build comprehensive context for scripts generation including full accumulated analysis"""
        
        logger.debug(
            "workflow.scripts_context.building",
            "Building scripts context with complete accumulated analysis",
            hooks_count=len(hooks_by_angle)
        )
        
        context = f"""
COMPLETE BUSINESS CONTEXT FOR SCRIPT GENERATION:

PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Price: {product_info.price or 'Not specified'}
Problem Solved: {product_info.problem_solved}
Differentiation: {product_info.differentiation}
Additional Information: {product_info.additional_information or 'None provided'}

AVATAR ANALYSIS (ICP):
Demographics: Age {complete_analysis.avatar_analysis.demographic_data.age_range}, {complete_analysis.avatar_analysis.demographic_data.geographic_location}, Income {complete_analysis.avatar_analysis.demographic_data.average_income}
Education: {complete_analysis.avatar_analysis.demographic_data.education_level}
Employment: {complete_analysis.avatar_analysis.demographic_data.employment_situation}

Psychographics:
- Personality Traits: {complete_analysis.avatar_analysis.psychographic_factors.personality_traits}
- Core Values: {complete_analysis.avatar_analysis.psychographic_factors.core_values}
- Lifestyle: {complete_analysis.avatar_analysis.psychographic_factors.lifestyle}
- Aspirations: {complete_analysis.avatar_analysis.psychographic_factors.aspirations_goals}
- Fears/Concerns: {complete_analysis.avatar_analysis.psychographic_factors.fears_concerns}

Pain Points & Problems: {complete_analysis.avatar_analysis.reality_expectations.problems_pain_points}
Expectations: {complete_analysis.avatar_analysis.reality_expectations.current_vs_desired}

CUSTOMER JOURNEY MAPPING:
Discovery Phase:
- Emotions: {', '.join(complete_analysis.journey_mapping.discovery_phase.emotions)}
- Actions: {complete_analysis.journey_mapping.discovery_phase.customer_actions}
- Touchpoints: {complete_analysis.journey_mapping.discovery_phase.touchpoints}

Consideration Phase:
- Customer Problems: {complete_analysis.journey_mapping.consideration_phase.customer_problems}
- Customer Knowledge: {complete_analysis.journey_mapping.consideration_phase.customer_knowledge}
- Customer Thoughts: {complete_analysis.journey_mapping.consideration_phase.customer_thoughts}

Decision Phase:
- Customer Needs: {complete_analysis.journey_mapping.decision_phase.customer_needs}
- Customer Feelings: {complete_analysis.journey_mapping.decision_phase.customer_feelings}
- Customer Thoughts: {complete_analysis.journey_mapping.decision_phase.customer_thoughts}

KEY OBJECTIONS TO ADDRESS:
Solution Objections:
{chr(10).join([f"- {obj.objection_description}: {obj.argument_to_overcome}" for obj in complete_analysis.objections_analysis.solution_objections[:3]])}

Internal Objections:
{chr(10).join([f"- {obj.objection_description}: {obj.argument_to_overcome}" for obj in complete_analysis.objections_analysis.internal_objections[:3]])}

SELECTED HOOKS FOR SCRIPT GENERATION:
{json.dumps(hooks_by_angle, indent=2)}

INSTRUCTIONS:
Generate 2-3 compelling script variations for each selected hook that:
1. Flow naturally from the hook premise
2. Address the avatar's specific pain points and aspirations
3. Incorporate insights from the customer journey
4. Preemptively handle key objections
5. Include strong, specific calls to action
6. Stay within 130-170 words per script
7. Feel authentic and conversational (UGC-style)
"""
        
        logger.debug(
            "workflow.scripts_context.built",
            f"Built context with {len(context)} characters",
            context_length=len(context)
        )
        
        return context
