# Simplified Claude Service for V3 Architecture
# Stateless utility for Claude interactions with prompt management and response parsing

import json
import re
import time
from typing import Dict, Any, Optional, List
import asyncio
import base64
import httpx
from claude_v2_client import ClaudeV2Client
from video_ads_v2_models import (
    VideoAdsProductInfoV2, 
    AvatarAnalysis, 
    JourneyMapping, 
    ObjectionsAnalysis, 
    AnglesGeneration,
    MarketingAngleV2
)
from logging_service import logger

class ClaudeService:
    """Stateless service for Claude interactions"""
    
    def __init__(self):
        self.client = ClaudeV2Client()
    
    async def _send_message(self, system_prompt: str, user_prompt: str, max_tokens: int = 25000, documents: List[Dict] = None, model: str = "claude-haiku-4-5-20251001") -> str:
        """Send a message to Claude and get response with optional document support"""
        if not self.client.client:
            raise Exception("Claude client not initialized")

        try:
            # Build message content
            if documents:
                # Build message content with documents
                message_content = []

                # Add documents first
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

                messages = [{"role": "user", "content": message_content}]
            else:
                messages = [{"role": "user", "content": user_prompt}]

            # Prepare API call parameters
            api_params = {
                "model": model,  # Model specified by caller
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": messages
            }

            # Add beta header for PDF support if needed
            extra_headers = {}
            if documents and any(doc.get('type') == 'pdf' for doc in documents):
                extra_headers = {"anthropic-beta": "pdfs-2024-09-25"}

            # Send to Claude using the Anthropic client directly with timeout
            # Use 20-minute timeout (1200 seconds) for long-running requests
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.client.messages.create,
                    **api_params,
                    extra_headers=extra_headers if extra_headers else None,
                    timeout=1200.0  # 20 minutes
                ),
                timeout=1200.0  # Also set asyncio timeout to 20 minutes
            )

            # Log response metadata for debugging token usage and truncation
            if hasattr(response, 'usage') and hasattr(response, 'stop_reason'):
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                stop_reason = response.stop_reason

                logger.info("claude_service.response.metadata",
                           f"Tokens: {input_tokens} in, {output_tokens} out | Stop reason: {stop_reason}",
                           input_tokens=input_tokens,
                           output_tokens=output_tokens,
                           stop_reason=stop_reason)

                # Warn if response was truncated due to token limit
                if stop_reason == "max_tokens":
                    logger.warning("claude_service.response.truncated",
                                 f"Response was truncated! Hit max_tokens limit of {max_tokens}. Output may be incomplete.",
                                 max_tokens=max_tokens,
                                 output_tokens=output_tokens)

            # Extract response content
            response_content = response.content[0].text
            return response_content

        except Exception as e:
            logger.error("claude_service.send_message.error", f"Error sending message to Claude: {e}", error=str(e))
            raise
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from Claude's response"""
        clean_response = response.strip()

        # Look for JSON content between ```json and ``` or ``` and ```
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

        # Remove wrapping single quotes if present (e.g., '{"key": "value"}')
        if clean_response.startswith("'") and clean_response.endswith("'"):
            clean_response = clean_response[1:-1]
            logger.debug("claude_service.json_cleanup", "Removed wrapping single quotes from JSON response")

        # Decode escape sequences (e.g., \n to actual newlines, \" to ")
        # This handles cases where JSON is stored as a string literal with escaped characters
        try:
            # Try to decode unicode escapes and common escape sequences
            if '\\n' in clean_response or '\\"' in clean_response or "\\'" in clean_response:
                # Replace escaped quotes and newlines
                clean_response = clean_response.replace('\\n', '\n')
                clean_response = clean_response.replace('\\"', '"')
                clean_response = clean_response.replace("\\'", "'")
                logger.debug("claude_service.json_cleanup", "Decoded escape sequences in JSON response")
        except Exception as e:
            logger.warning("claude_service.json_cleanup.escape_error", f"Error decoding escape sequences: {e}")
            # Continue with original response if decoding fails

        # Fix common JSON issues
        clean_response = re.sub(r',(\s*[}\]])', r'\1', clean_response)  # Remove trailing commas
        clean_response = re.sub(r'}\s*{', '},{', clean_response)  # Add missing commas between objects
        clean_response = re.sub(r']\s*\[', '],[', clean_response)  # Add missing commas between arrays

        return clean_response

    def _parse_script_id(self, script_id: str) -> Dict[str, str]:
        """Parse script_id to extract angle_id, hook_id, and script_number

        Example: "angle_1_5_1" -> {"angle_id": "angle_1", "hook_id": "angle_1_5", "script_number": "1"}
        """
        try:
            parts = script_id.split('_')
            if len(parts) < 4:
                logger.warning("claude_service.parse_script_id", f"Invalid script_id format: {script_id}")
                return {"angle_id": None, "hook_id": None, "script_number": None}

            return {
                "angle_id": f"{parts[0]}_{parts[1]}",  # "angle_1"
                "hook_id": f"{parts[0]}_{parts[1]}_{parts[2]}",  # "angle_1_5"
                "script_number": parts[3]  # "1"
            }
        except Exception as e:
            logger.error("claude_service.parse_script_id.error", f"Error parsing script_id {script_id}: {e}")
            return {"angle_id": None, "hook_id": None, "script_number": None}

    def _restructure_scripts(self, minimal_scripts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Restructure minimal flat scripts into nested hierarchy with angle_id and hook_id

        Input: [{"script_id": "angle_1_1_1", "content": "...", "cta": "...", "target_emotion": "..."}]
        Output: {"angles": [{"angle_id": "angle_1", "hooks": [{"hook_id": "angle_1_1", "scripts": [...]}]}]}
        """
        # Group scripts by angle, then by hook
        angles_dict = {}

        for script in minimal_scripts:
            script_id = script.get("script_id")
            if not script_id:
                continue

            parsed = self._parse_script_id(script_id)
            angle_id = parsed["angle_id"]
            hook_id = parsed["hook_id"]

            if not angle_id or not hook_id:
                continue

            # Initialize angle if needed
            if angle_id not in angles_dict:
                # Extract angle number from angle_id (e.g., "angle_1" -> 1)
                try:
                    angle_number = int(angle_id.split('_')[1])
                except:
                    angle_number = 0

                angles_dict[angle_id] = {
                    "angle_id": angle_id,
                    "angle_number": angle_number,
                    "hooks": {}
                }

            # Initialize hook if needed
            if hook_id not in angles_dict[angle_id]["hooks"]:
                angles_dict[angle_id]["hooks"][hook_id] = {
                    "selected_hook": {
                        "hook_id": hook_id
                    },
                    "scripts": []
                }

            # Add script with all fields including angle_id and hook_id for easy frontend access
            restructured_script = {
                "script_id": script_id,
                "angle_id": angle_id,
                "hook_id": hook_id,
                "content": script.get("content", ""),
                "cta": script.get("cta", ""),
                "target_emotion": script.get("target_emotion", "")
            }
            angles_dict[angle_id]["hooks"][hook_id]["scripts"].append(restructured_script)

        # Convert hooks dict to list
        angles_list = []
        for angle_id in sorted(angles_dict.keys()):
            angle = angles_dict[angle_id]
            angle["hooks"] = list(angle["hooks"].values())
            angles_list.append(angle)

        return {"angles": angles_list}

    def _log_missing_avatar_fields(self, avatar: 'AvatarAnalysis') -> None:
        """Log warnings for missing optional fields in avatar analysis"""
        missing = []

        # Check demographic_data
        demo = avatar.demographic_data
        if not demo.age_range: missing.append("demographic_data.age_range")
        if not demo.geographic_location: missing.append("demographic_data.geographic_location")
        if not demo.socioeconomic_level: missing.append("demographic_data.socioeconomic_level")

        # Check psychographic_factors
        psycho = avatar.psychographic_factors
        if not psycho.personality_traits: missing.append("psychographic_factors.personality_traits")
        if not psycho.core_values: missing.append("psychographic_factors.core_values")

        # Check purchasing_behavior
        purchase = avatar.purchasing_behavior
        if not purchase.decision_process: missing.append("purchasing_behavior.decision_process")
        if not purchase.preferred_channels: missing.append("purchasing_behavior.preferred_channels")

        if missing:
            logger.warning("avatar.missing_fields", f"Avatar analysis missing {len(missing)} fields: {', '.join(missing[:5])}")

    def _log_missing_journey_fields(self, journey: 'JourneyMapping') -> None:
        """Log warnings for missing optional fields in journey mapping"""
        missing = []

        for phase_name in ["discovery_phase", "consideration_phase", "decision_phase", "retention_phase"]:
            phase = getattr(journey, phase_name)
            if not phase.customer_knowledge:
                missing.append(f"{phase_name}.customer_knowledge")
            if not phase.customer_feelings:
                missing.append(f"{phase_name}.customer_feelings")
            if not phase.customer_actions:
                missing.append(f"{phase_name}.customer_actions")

        if missing:
            logger.warning("journey.missing_fields", f"Journey mapping missing {len(missing)} fields: {', '.join(missing[:5])}")

    def _log_missing_objections_fields(self, objections: 'ObjectionsAnalysis') -> None:
        """Log warnings for missing optional fields in objections analysis"""
        missing = []

        for category in ["solution_objections", "offer_objections", "internal_objections", "external_objections"]:
            items = getattr(objections, category)
            for i, item in enumerate(items):
                if not item.priority:
                    missing.append(f"{category}[{i}].priority")
                if not item.objection_description:
                    missing.append(f"{category}[{i}].objection_description")
                if not item.argument_to_overcome:
                    missing.append(f"{category}[{i}].argument_to_overcome")

        if missing:
            logger.warning("objections.missing_fields", f"Objections analysis missing {len(missing)} fields: {', '.join(missing[:5])}")

    async def generate_avatar_analysis(
        self,
        product_info: VideoAdsProductInfoV2,
        document_urls: Optional[List[str]] = None
    ) -> AvatarAnalysis:
        """Generate avatar analysis using Claude"""

        # Process documents if provided
        documents = []
        if document_urls:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for url in document_urls:
                    try:
                        # Download document from S3
                        response = await client.get(url)
                        if response.status_code == 200:
                            # Determine media type from URL
                            media_type = "application/pdf"  # Default
                            if url.lower().endswith('.png'):
                                media_type = "image/png"
                            elif url.lower().endswith('.jpg') or url.lower().endswith('.jpeg'):
                                media_type = "image/jpeg"
                            elif url.lower().endswith('.docx'):
                                media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            elif url.lower().endswith('.pptx'):
                                media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

                            # Convert to base64
                            content_base64 = base64.b64encode(response.content).decode('utf-8')

                            documents.append({
                                "type": "document" if media_type == "application/pdf" else "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": content_base64
                                }
                            })
                            logger.info(f"Successfully processed document from {url}")
                    except Exception as e:
                        logger.error(f"Error downloading document from {url}: {e}")
                        # Continue processing other documents

        # Load only the avatar_analysis.yaml prompt
        avatar_prompt_template = self.client.get_prompt("avatar_analysis")

        # Build the complete prompt from YAML instructions
        prompt_parts = []

        # Add instructions from YAML
        if 'instructions' in avatar_prompt_template:
            prompt_parts.append(avatar_prompt_template['instructions'])

        # Add the product context
        prompt_parts.append(f"""
PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Price: {product_info.price or 'Not specified'}
Problem Solved: {product_info.problem_solved}
Differentiation: {product_info.differentiation}
Additional Information: {product_info.additional_information or 'None provided'}
""")

        # Add output format instructions from YAML
        if 'output_format' in avatar_prompt_template and 'format' in avatar_prompt_template['output_format']:
            prompt_parts.append(avatar_prompt_template['output_format']['format'])

        user_prompt = "\n".join(prompt_parts)

        # Send to Claude with documents (empty system prompt - everything is in user prompt)
        response = await self._send_message("", user_prompt, documents=documents if documents else None, model="claude-haiku-4-5-20251001")

        # Parse response
        try:
            clean_response = self._clean_json_response(response)
            response_data = json.loads(clean_response)
            avatar_data = response_data.get("avatar_analysis", response_data)

            avatar = AvatarAnalysis(**avatar_data)

            # Log warnings for missing optional fields
            self._log_missing_avatar_fields(avatar)

            return avatar
            
        except json.JSONDecodeError as e:
            logger.error("claude_service.avatar.json_error", 
                        f"Claude returned non-JSON response. Error: {e}",
                        response_preview=response[:500])
            # Log full response for debugging
            logger.debug("claude_service.avatar.full_response", f"Full response: {response}")
            raise ValueError(f"Claude did not return valid JSON. Response started with: {response[:100]}...")
        except Exception as e:
            logger.error("claude_service.avatar.parse_error", f"Error parsing avatar analysis: {e}")
            raise
    
    async def generate_journey_mapping(
        self,
        product_info: VideoAdsProductInfoV2,
        avatar_analysis: AvatarAnalysis
    ) -> JourneyMapping:
        """Generate journey mapping using Claude"""
        
        # Load only the journey_mapping.yaml prompt
        journey_prompt_template = self.client.get_prompt("journey_mapping")
        
        # Build the complete prompt from YAML instructions
        prompt_parts = []
        
        # Add instructions from YAML
        if 'instructions' in journey_prompt_template:
            prompt_parts.append(journey_prompt_template['instructions'])
        
        # Add the product and avatar context
        prompt_parts.append(f"""
PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Price: {product_info.price or 'Not specified'}
Problem Solved: {product_info.problem_solved}
Differentiation: {product_info.differentiation}
Additional Information: {product_info.additional_information or 'None provided'}

AVATAR ANALYSIS:
{json.dumps(avatar_analysis.dict(), indent=2)}
""")

        # Add output format instructions from YAML (some use 'format', others use 'schema')
        if 'output_format' in journey_prompt_template:
            output_format = journey_prompt_template['output_format']
            if 'format' in output_format:
                prompt_parts.append(output_format['format'])
            elif 'schema' in output_format:
                prompt_parts.append(output_format['schema'])

        user_prompt = "\n".join(prompt_parts)

        # Send to Claude
        response = await self._send_message("", user_prompt, model="claude-haiku-4-5-20251001")
        
        # Parse response
        try:
            clean_response = self._clean_json_response(response)
            response_data = json.loads(clean_response)
            journey_data = response_data.get("journey_mapping", response_data)

            journey = JourneyMapping(**journey_data)

            # Log warnings for missing optional fields
            self._log_missing_journey_fields(journey)

            return journey
            
        except Exception as e:
            logger.error("claude_service.journey.parse_error", f"Error parsing journey mapping: {e}")
            raise
    
    async def generate_objections_analysis(
        self,
        product_info: VideoAdsProductInfoV2,
        avatar_analysis: AvatarAnalysis,
        journey_mapping: JourneyMapping
    ) -> ObjectionsAnalysis:
        """Generate objections analysis using Claude"""
        
        # Load only the objections_analysis.yaml prompt
        objections_prompt_template = self.client.get_prompt("objections_analysis")
        
        # Build the complete prompt from YAML instructions
        prompt_parts = []
        
        # Add instructions from YAML
        if 'instructions' in objections_prompt_template:
            prompt_parts.append(objections_prompt_template['instructions'])
        
        # Add the product, avatar, and journey context
        prompt_parts.append(f"""
PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Price: {product_info.price or 'Not specified'}
Problem Solved: {product_info.problem_solved}
Differentiation: {product_info.differentiation}
Additional Information: {product_info.additional_information or 'None provided'}

AVATAR ANALYSIS:
{json.dumps(avatar_analysis.dict(), indent=2)}

JOURNEY MAPPING:
{json.dumps(journey_mapping.dict(), indent=2)}
""")

        # Add output format instructions from YAML (some use 'format', others use 'schema')
        if 'output_format' in objections_prompt_template:
            output_format = objections_prompt_template['output_format']
            if 'format' in output_format:
                prompt_parts.append(output_format['format'])
            elif 'schema' in output_format:
                prompt_parts.append(output_format['schema'])

        user_prompt = "\n".join(prompt_parts)

        # Send to Claude
        response = await self._send_message("", user_prompt, model="claude-haiku-4-5-20251001")
        
        # Parse response
        try:
            clean_response = self._clean_json_response(response)
            response_data = json.loads(clean_response)
            objections_data = response_data.get("objections_analysis", response_data)

            objections = ObjectionsAnalysis(**objections_data)

            # Log warnings for missing optional fields
            self._log_missing_objections_fields(objections)

            return objections
            
        except Exception as e:
            logger.error("claude_service.objections.parse_error", f"Error parsing objections: {e}")
            raise
    
    async def generate_angles(
        self,
        product_info: VideoAdsProductInfoV2,
        avatar_analysis: AvatarAnalysis,
        journey_mapping: JourneyMapping,
        objections_analysis: ObjectionsAnalysis
    ) -> AnglesGeneration:
        """Generate marketing angles using Claude"""
        
        # Load only the angles_generation.yaml prompt
        angles_prompt_template = self.client.get_prompt("angles_generation")
        
        # Build the complete prompt from YAML instructions
        prompt_parts = []
        
        # Add instructions from YAML
        if 'instructions' in angles_prompt_template:
            prompt_parts.append(angles_prompt_template['instructions'])
        
        # Add all context
        prompt_parts.append(f"""
PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Price: {product_info.price or 'Not specified'}
Problem Solved: {product_info.problem_solved}
Differentiation: {product_info.differentiation}
Additional Information: {product_info.additional_information or 'None provided'}

AVATAR ANALYSIS:
{json.dumps(avatar_analysis.dict(), indent=2)}

JOURNEY MAPPING:
{json.dumps(journey_mapping.dict(), indent=2)}

OBJECTIONS ANALYSIS:
{json.dumps(objections_analysis.dict(), indent=2)}
""")

        # Add output format instructions from YAML (some use 'format', others use 'schema')
        if 'output_format' in angles_prompt_template:
            output_format = angles_prompt_template['output_format']
            if 'format' in output_format:
                prompt_parts.append(output_format['format'])
            elif 'schema' in output_format:
                prompt_parts.append(output_format['schema'])

        user_prompt = "\n".join(prompt_parts)

        # Send to Claude
        response = await self._send_message("", user_prompt, model="claude-haiku-4-5-20251001")
        
        # Parse response and handle both old and new formats
        try:
            clean_response = self._clean_json_response(response)
            response_data = json.loads(clean_response)
            
            # Handle both possible response formats
            if "angles_generation" in response_data:
                angles_data = response_data["angles_generation"]
            else:
                angles_data = response_data
            
            # Parse angles using the standardized format from YAML
            positive_angles = []
            for angle in angles_data.get("positive_angles", []):
                positive_angles.append(MarketingAngleV2(
                    angle=angle["angle_number"],  # For backward compatibility
                    angle_id=angle["angle_id"],
                    angle_number=angle["angle_number"],
                    category=angle["angle_category"],
                    concept=angle["angle_concept"],
                    type=angle.get("angle_type", "positive")
                ))
            
            negative_angles = []
            for angle in angles_data.get("negative_angles", []):
                negative_angles.append(MarketingAngleV2(
                    angle=angle["angle_number"],  # For backward compatibility
                    angle_id=angle["angle_id"],
                    angle_number=angle["angle_number"],
                    category=angle["angle_category"],
                    concept=angle["angle_concept"],
                    type=angle.get("angle_type", "negative")
                ))
            
            return AnglesGeneration(
                positive_angles=positive_angles,
                negative_angles=negative_angles
            )
            
        except Exception as e:
            logger.error("claude_service.angles.parse_error", f"Error parsing angles: {e}")
            raise
    
    async def generate_hooks(
        self,
        product_info: VideoAdsProductInfoV2,
        selected_angles: List[MarketingAngleV2],
        avatar_analysis: Optional[AvatarAnalysis] = None,
        journey_mapping: Optional[JourneyMapping] = None,
        objections_analysis: Optional[ObjectionsAnalysis] = None
    ) -> List[Any]:
        """Generate hooks for selected angles"""

        hooks_prompt_template = self.client.get_prompt("hooks_generation")

        # Build the complete prompt from YAML instructions
        prompt_parts = []

        # Add comprehensive instructions from YAML
        # Build a complete system context from all YAML fields
        system_context_parts = []

        if 'role' in hooks_prompt_template:
            system_context_parts.append(f"ROLE:\n{hooks_prompt_template['role']}")

        if 'purpose' in hooks_prompt_template:
            system_context_parts.append(f"PURPOSE:\n{hooks_prompt_template['purpose']}")

        if 'operating_instructions' in hooks_prompt_template:
            system_context_parts.append(f"OPERATING INSTRUCTIONS:\n{hooks_prompt_template['operating_instructions']}")

        if 'viral_hooks_manual_principles' in hooks_prompt_template:
            system_context_parts.append(f"VIRAL HOOKS MANUAL PRINCIPLES:\n{hooks_prompt_template['viral_hooks_manual_principles']}")

        if 'hook_categories' in hooks_prompt_template:
            categories_text = "HOOK CATEGORIES:\n"
            if isinstance(hooks_prompt_template['hook_categories'], dict):
                if 'description' in hooks_prompt_template['hook_categories']:
                    categories_text += f"{hooks_prompt_template['hook_categories']['description']}\n\n"
                if 'categories' in hooks_prompt_template['hook_categories']:
                    cats = hooks_prompt_template['hook_categories']['categories']
                    if isinstance(cats, dict):
                        for cat_name, cat_info in cats.items():
                            categories_text += f"- {cat_name}: {cat_info.get('description', '')}\n"
            system_context_parts.append(categories_text)

        if 'hook_id_convention' in hooks_prompt_template:
            system_context_parts.append(f"HOOK ID CONVENTION:\n{hooks_prompt_template['hook_id_convention']}")

        if 'language_and_format_requirements' in hooks_prompt_template:
            system_context_parts.append(f"LANGUAGE AND FORMAT REQUIREMENTS:\n{hooks_prompt_template['language_and_format_requirements']}")

        if 'generation_rules' in hooks_prompt_template:
            system_context_parts.append(f"GENERATION RULES:\n{hooks_prompt_template['generation_rules']}")

        if 'critical_rules' in hooks_prompt_template:
            system_context_parts.append(f"CRITICAL RULES:\n{hooks_prompt_template['critical_rules']}")

        if 'context_integration' in hooks_prompt_template:
            system_context_parts.append(f"CONTEXT INTEGRATION:\n{hooks_prompt_template['context_integration']}")

        # Add all system context
        if system_context_parts:
            prompt_parts.append("\n\n".join(system_context_parts))
        
        # Build angles data
        angles_data = []
        for angle in selected_angles:
            angles_data.append({
                "angle_id": getattr(angle, 'angle_id', f"angle_{angle.angle}"),
                "angle_number": getattr(angle, 'angle_number', angle.angle),
                "angle_category": angle.category,
                "angle_concept": angle.concept,
                "angle_type": angle.type
            })

        # Debug logging
        logger.info(f"claude_service.hooks.angles_count", f"Building prompt for {len(angles_data)} angles")
        logger.debug(f"claude_service.hooks.angles_data", f"Angles data: {json.dumps(angles_data, indent=2)}")

        # Add product and angles context
        angles_section = f"""
PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Problem Solved: {product_info.problem_solved}

SELECTED MARKETING ANGLES:
{json.dumps(angles_data, indent=2)}
"""
        prompt_parts.append(angles_section)

        # Log a sample to verify it's being added
        logger.debug(f"claude_service.hooks.angles_section_sample", f"Angles section (first 500 chars): {angles_section[:500]}")
        
        # Add optional context if available
        if avatar_analysis:
            prompt_parts.append(f"""
AVATAR INSIGHTS:
Pain Points: {avatar_analysis.reality_expectations.problems_pain_points}
Core Values: {avatar_analysis.psychographic_factors.core_values}
""")
        
        # Add output format instructions from YAML (hooks uses 'json_output_format')
        if 'json_output_format' in hooks_prompt_template:
            prompt_parts.append(hooks_prompt_template['json_output_format'])
        elif 'output_format' in hooks_prompt_template:
            output_format = hooks_prompt_template['output_format']
            if 'format' in output_format:
                prompt_parts.append(output_format['format'])
            elif 'schema' in output_format:
                prompt_parts.append(output_format['schema'])

        user_prompt = "\n".join(prompt_parts)

        # Debug logging for final prompt
        logger.info(f"claude_service.hooks.prompt_length", f"Final prompt length: {len(user_prompt)} characters")
        logger.debug(f"claude_service.hooks.prompt_sample", f"Final prompt (last 1000 chars): {user_prompt[-1000:]}")

        # Send to Claude with increased token limit for all hooks
        # Using Claude Haiku 4.5 for fast hook generation
        max_tokens = 60000
        response = await self._send_message("", user_prompt, max_tokens=max_tokens, model="claude-haiku-4-5-20251001")

        # Log raw response info
        logger.info("claude_service.hooks.response_received",
                   f"Raw response length: {len(response)} characters",
                   response_length=len(response))

        # Parse response
        try:
            clean_response = self._clean_json_response(response)
            response_data = json.loads(clean_response)

            # Debug logging
            logger.info(f"claude_service.hooks.response_keys", f"Response keys: {list(response_data.keys())}")
            logger.debug(f"claude_service.hooks.response_sample", f"Response sample: {str(response_data)[:500]}")

            hooks_by_angle = response_data.get("hooks_by_angle", [])
            logger.info(f"claude_service.hooks.angles_returned", f"Claude returned hooks for {len(hooks_by_angle)} angles")
            
            # Validate and return
            from video_ads_v2_models import AngleWithHooksV2, HooksByCategoryV2, HookItem
            
            validated_hooks = []
            for hook_data in hooks_by_angle:
                # Handle field name variations
                angle_concept = hook_data.get("angle_concept") or hook_data.get("concept")
                
                logger.debug("claude_service.hooks.processing_angle", 
                           f"Processing angle {hook_data.get('angle_id')} with categories: {list(hook_data.get('hooks_by_category', {}).keys())}")
                
                # Process hooks keeping full object structure
                # Claude returns objects with hook_id, hook_text, hook_category
                hooks_by_cat_raw = hook_data["hooks_by_category"]
                hooks_by_cat_processed = {}
                
                for category, hooks_list in hooks_by_cat_raw.items():
                    processed_hooks = []
                    if isinstance(hooks_list, list) and hooks_list:
                        for hook in hooks_list:
                            if isinstance(hook, dict):
                                # Create HookItem from Claude's response
                                processed_hooks.append(HookItem(
                                    hook_id=hook.get("hook_id", f"angle_{hook_data.get('angle_number', 0)}_{len(processed_hooks)+1}"),
                                    hook_text=hook.get("hook_text", ""),
                                    hook_category=hook.get("hook_category", category)
                                ))
                            else:
                                # Legacy: if it's just a string, create a hook item
                                processed_hooks.append(HookItem(
                                    hook_id=f"angle_{hook_data.get('angle_number', 0)}_{len(processed_hooks)+1}",
                                    hook_text=str(hook),
                                    hook_category=category
                                ))
                    hooks_by_cat_processed[category] = processed_hooks
                
                hooks_by_category = HooksByCategoryV2(**hooks_by_cat_processed)
                angle_with_hooks = AngleWithHooksV2(
                    angle_id=hook_data["angle_id"],
                    angle_number=hook_data["angle_number"],
                    angle_category=hook_data["angle_category"],
                    angle_concept=angle_concept,
                    angle_type=hook_data["angle_type"],
                    hooks_by_category=hooks_by_category
                )
                validated_hooks.append(angle_with_hooks)
            
            return validated_hooks

        except Exception as e:
            logger.error("claude_service.hooks.parse_error", f"Error parsing hooks: {e}", error=str(e), traceback=True)
            # Return empty list instead of raising to see what happens
            return []
    
    async def generate_scripts(
        self,
        product_info: VideoAdsProductInfoV2,
        hooks_by_angle: List[Any],
        avatar_analysis: Optional[AvatarAnalysis] = None,
        journey_mapping: Optional[JourneyMapping] = None,
        objections_analysis: Optional[ObjectionsAnalysis] = None
    ) -> Dict[str, Any]:
        """Generate scripts for selected hooks"""
        
        scripts_prompt_template = self.client.get_prompt("scripts_generation")

        # Build the complete prompt from YAML sections
        prompt_parts = []

        # Add role and task from YAML
        if 'role' in scripts_prompt_template:
            prompt_parts.append(f"ROLE: {scripts_prompt_template['role']}")

        if 'task' in scripts_prompt_template:
            prompt_parts.append(f"TASK:\n{scripts_prompt_template['task']}")

        if 'script_writing_rules' in scripts_prompt_template:
            prompt_parts.append(f"SCRIPT WRITING RULES:\n{scripts_prompt_template['script_writing_rules']}")

        # Add product and hooks context
        prompt_parts.append(f"""
PRODUCT INFORMATION:
Product Name: {product_info.product_name}
Product Information: {product_info.product_information}
Target Audience: {product_info.target_audience}
Problem Solved: {product_info.problem_solved}

SELECTED HOOKS FOR SCRIPT GENERATION:
{json.dumps(hooks_by_angle, indent=2, default=lambda x: x.dict() if hasattr(x, 'dict') else str(x))}
""")

        # Add optional context if available
        if avatar_analysis:
            prompt_parts.append(f"""
AVATAR INSIGHTS:
Demographics: Age {avatar_analysis.demographic_data.age_range}
Pain Points: {avatar_analysis.reality_expectations.problems_pain_points}
""")

        if journey_mapping:
            prompt_parts.append(f"""
JOURNEY INSIGHTS:
Discovery Emotions: {', '.join(journey_mapping.discovery_phase.emotions)}
Decision Needs: {journey_mapping.decision_phase.customer_needs}
""")

        # Add output format and final instructions from YAML
        if 'output_format' in scripts_prompt_template:
            prompt_parts.append(scripts_prompt_template['output_format'])

        if 'final_instructions' in scripts_prompt_template:
            prompt_parts.append(scripts_prompt_template['final_instructions'])

        user_prompt = "\n\n".join(prompt_parts)

        # Send to Claude with increased token limit for all scripts
        # Using Claude Haiku 4.5 for fast script generation
        response = await self._send_message("", user_prompt, max_tokens=60000, model="claude-haiku-4-5-20251001")

        # Parse response
        try:
            clean_response = self._clean_json_response(response)
            response_data = json.loads(clean_response)

            # Get minimal flat scripts array
            minimal_scripts = response_data.get("scripts", [])

            logger.info("claude_service.scripts.parsed", f"Parsed {len(minimal_scripts)} scripts from Claude response")

            # Restructure into nested hierarchy with angle_id and hook_id
            restructured_scripts = self._restructure_scripts(minimal_scripts)

            logger.info("claude_service.scripts.restructured",
                       f"Restructured into {len(restructured_scripts.get('angles', []))} angles")

            # Return both versions
            return {
                "raw": minimal_scripts,  # Minimal flat array from Claude
                "restructured": restructured_scripts  # Nested with angle_id/hook_id expanded
            }

        except Exception as e:
            logger.error("claude_service.scripts.parse_error", f"Error parsing scripts: {e}")
            raise