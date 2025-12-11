"""
Claude Batch API Service
Handles batch processing for hooks and scripts generation
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
import os
from dotenv import load_dotenv
from logging_service import logger

load_dotenv()


class ClaudeBatchService:
    """Service for managing Claude Batch API operations"""

    def __init__(self):
        """Initialize the Claude Batch API client"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info("claude_batch.init", "Claude Batch Service initialized")

    async def create_hooks_and_scripts_batch(
        self,
        campaign_id: str,
        angles: List[Dict[str, Any]],
        product_info: Dict[str, Any],
        avatar_analysis: Dict[str, Any],
        journey_mapping: Dict[str, Any],
        objections_analysis: Dict[str, Any],
        hooks_prompt_template: Dict[str, Any],
        scripts_prompt_template: Dict[str, Any]
    ) -> str:
        """
        Create a batch request for generating hooks and scripts

        Args:
            campaign_id: Campaign identifier
            angles: List of marketing angles
            product_info: Product information
            avatar_analysis: Avatar analysis data
            journey_mapping: Journey mapping data
            objections_analysis: Objections analysis data
            hooks_prompt_template: Template for hook generation
            scripts_prompt_template: Template for script generation

        Returns:
            batch_id: The ID of the created batch
        """
        requests = []

        # Create hook generation requests (21 hooks per angle)
        for angle_idx, angle in enumerate(angles):
            # Build hook generation prompt
            hook_prompt = self._build_hook_prompt(
                angle, product_info, avatar_analysis,
                journey_mapping, objections_analysis, hooks_prompt_template
            )

            # Create 21 hook requests for this angle
            for hook_num in range(1, 22):  # 21 hooks per angle
                custom_id = f"hook_angle{angle_idx + 1}_hook{hook_num}"

                requests.append(Request(
                    custom_id=custom_id,
                    params=MessageCreateParamsNonStreaming(
                        model="claude-haiku-4-5-20251001",  # Fast model for hooks
                        max_tokens=15000,
                        messages=[{
                            "role": "user",
                            "content": f"{hook_prompt}\n\nGenerate hook {hook_num} of 21 for this angle."
                        }]
                    )
                ))

        # Create script generation requests (2 scripts per hook)
        # Note: Since we don't have hooks yet, we'll generate them after batch completes
        # For now, we'll prepare the structure for script generation

        logger.info("claude_batch.create",
                   f"Creating batch for campaign {campaign_id} with {len(requests)} hook requests")

        # Create the batch
        try:
            message_batch = self.client.messages.batches.create(requests=requests)

            logger.info("claude_batch.created",
                       f"Batch {message_batch.id} created for campaign {campaign_id}")

            return message_batch.id

        except Exception as e:
            logger.error("claude_batch.create_error",
                        f"Error creating batch for campaign {campaign_id}: {e}")
            raise

    def _build_hook_prompt(
        self,
        angle: Dict[str, Any],
        product_info: Dict[str, Any],
        avatar_analysis: Dict[str, Any],
        journey_mapping: Dict[str, Any],
        objections_analysis: Dict[str, Any],
        hooks_prompt_template: Dict[str, Any]
    ) -> str:
        """Build the prompt for hook generation"""

        # Build comprehensive prompt from template
        prompt_parts = []

        # Add template instructions
        if 'role' in hooks_prompt_template:
            prompt_parts.append(f"ROLE:\n{hooks_prompt_template['role']}")

        if 'purpose' in hooks_prompt_template:
            prompt_parts.append(f"PURPOSE:\n{hooks_prompt_template['purpose']}")

        if 'operating_instructions' in hooks_prompt_template:
            prompt_parts.append(f"OPERATING INSTRUCTIONS:\n{hooks_prompt_template['operating_instructions']}")

        # Add product context
        prompt_parts.append(f"""
PRODUCT INFORMATION:
Product Name: {product_info.get('product_name', 'N/A')}
Product Description: {product_info.get('product_description', 'N/A')}
Price: {product_info.get('price', 'N/A')}
Target Audience: {product_info.get('target_audience', 'N/A')}
""")

        # Add angle context
        # angle is now a dictionary (converted from MarketingAngleV2 model)
        prompt_parts.append(f"""
MARKETING ANGLE:
Angle Number: {angle.get('angle', 'N/A')}
Concept: {angle.get('concept', 'N/A')}
Category: {angle.get('category', 'N/A')}
Type: {angle.get('type', 'N/A')}
""")

        # Add avatar context if available
        if avatar_analysis and 'avatars' in avatar_analysis:
            prompt_parts.append(f"""
TARGET AVATAR ANALYSIS:
{json.dumps(avatar_analysis.get('avatars', []), indent=2)}
""")

        return "\n\n".join(prompt_parts)

    async def check_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Check the status of a batch

        Args:
            batch_id: The batch ID to check

        Returns:
            Dict with batch status information
        """
        try:
            batch = self.client.messages.batches.retrieve(batch_id)

            return {
                "id": batch.id,
                "processing_status": batch.processing_status,
                "request_counts": {
                    "processing": batch.request_counts.processing,
                    "succeeded": batch.request_counts.succeeded,
                    "errored": batch.request_counts.errored,
                    "canceled": batch.request_counts.canceled,
                    "expired": batch.request_counts.expired
                },
                "created_at": batch.created_at,
                "ended_at": batch.ended_at,
                "expires_at": batch.expires_at
            }

        except Exception as e:
            logger.error("claude_batch.status_error",
                        f"Error checking batch {batch_id} status: {e}")
            raise

    async def retrieve_batch_results(self, batch_id: str) -> Dict[str, Any]:
        """
        Retrieve results from a completed batch

        Args:
            batch_id: The batch ID to retrieve results for

        Returns:
            Dict with parsed results organized by type (hooks/scripts)
        """
        try:
            # Check if batch is complete
            batch = self.client.messages.batches.retrieve(batch_id)

            if batch.processing_status != "ended":
                raise ValueError(f"Batch {batch_id} is not complete yet. Status: {batch.processing_status}")

            # Stream and parse results
            hooks = {}
            scripts = {}
            errors = []

            for result in self.client.messages.batches.results(batch_id):
                custom_id = result.custom_id

                if result.result.type == "succeeded":
                    # Extract content from the message
                    message = result.result.message
                    content = message.content[0].text if message.content else ""

                    # Categorize by custom_id prefix
                    if custom_id.startswith("hook_"):
                        hooks[custom_id] = {
                            "custom_id": custom_id,
                            "content": content,
                            "usage": {
                                "input_tokens": message.usage.input_tokens,
                                "output_tokens": message.usage.output_tokens
                            }
                        }
                    elif custom_id.startswith("script_"):
                        scripts[custom_id] = {
                            "custom_id": custom_id,
                            "content": content,
                            "usage": {
                                "input_tokens": message.usage.input_tokens,
                                "output_tokens": message.usage.output_tokens
                            }
                        }

                elif result.result.type == "errored":
                    errors.append({
                        "custom_id": custom_id,
                        "error": result.result.error
                    })
                    logger.error("claude_batch.result_error",
                               f"Error in batch result {custom_id}: {result.result.error}")

            logger.info("claude_batch.results_retrieved",
                       f"Retrieved batch {batch_id}: {len(hooks)} hooks, {len(scripts)} scripts, {len(errors)} errors")

            return {
                "batch_id": batch_id,
                "hooks": hooks,
                "scripts": scripts,
                "errors": errors,
                "summary": {
                    "total_hooks": len(hooks),
                    "total_scripts": len(scripts),
                    "total_errors": len(errors)
                }
            }

        except Exception as e:
            logger.error("claude_batch.retrieve_error",
                        f"Error retrieving batch {batch_id} results: {e}")
            raise

    async def create_scripts_batch_from_hooks(
        self,
        campaign_id: str,
        hooks: Dict[str, Any],
        product_info: Dict[str, Any],
        scripts_prompt_template: Dict[str, Any]
    ) -> str:
        """
        Create a second batch for script generation based on generated hooks

        Args:
            campaign_id: Campaign identifier
            hooks: Generated hooks from first batch
            product_info: Product information
            scripts_prompt_template: Template for script generation

        Returns:
            batch_id: The ID of the created batch
        """
        requests = []

        # Create 2 script requests per hook
        for hook_id, hook_data in hooks.items():
            hook_content = hook_data.get("content", "")

            # Parse angle and hook number from custom_id
            # Format: "hook_angle1_hook1"
            parts = hook_id.split("_")
            angle_num = parts[1].replace("angle", "")
            hook_num = parts[2].replace("hook", "")

            for version in range(1, 3):  # 2 versions per hook
                custom_id = f"script_angle{angle_num}_hook{hook_num}_v{version}"

                script_prompt = self._build_script_prompt(
                    hook_content, product_info, scripts_prompt_template, version
                )

                requests.append(Request(
                    custom_id=custom_id,
                    params=MessageCreateParamsNonStreaming(
                        model="claude-sonnet-4-5-20250929",  # Quality model for scripts
                        max_tokens=25000,
                        messages=[{
                            "role": "user",
                            "content": script_prompt
                        }]
                    )
                ))

        logger.info("claude_batch.create_scripts",
                   f"Creating scripts batch for campaign {campaign_id} with {len(requests)} requests")

        try:
            message_batch = self.client.messages.batches.create(requests=requests)

            logger.info("claude_batch.scripts_created",
                       f"Scripts batch {message_batch.id} created for campaign {campaign_id}")

            return message_batch.id

        except Exception as e:
            logger.error("claude_batch.scripts_error",
                        f"Error creating scripts batch for campaign {campaign_id}: {e}")
            raise

    def _build_script_prompt(
        self,
        hook_content: str,
        product_info: Dict[str, Any],
        scripts_prompt_template: Dict[str, Any],
        version: int
    ) -> str:
        """Build the prompt for script generation"""

        prompt_parts = []

        # Add template instructions
        if 'role' in scripts_prompt_template:
            prompt_parts.append(f"ROLE:\n{scripts_prompt_template['role']}")

        if 'purpose' in scripts_prompt_template:
            prompt_parts.append(f"PURPOSE:\n{scripts_prompt_template['purpose']}")

        # Add hook context
        prompt_parts.append(f"""
HOOK TO EXPAND INTO SCRIPT:
{hook_content}

PRODUCT INFORMATION:
Product Name: {product_info.get('product_name', 'N/A')}
Product Description: {product_info.get('product_description', 'N/A')}
Price: {product_info.get('price', 'N/A')}

SCRIPT VERSION: {version}
Please create a {"direct response" if version == 1 else "story-driven"} version of this script.
""")

        return "\n\n".join(prompt_parts)


# Create singleton instance
claude_batch_service = ClaudeBatchService()