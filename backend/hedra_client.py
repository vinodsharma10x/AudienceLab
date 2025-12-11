"""
Hedra API Client for Video Generation
Handles character uploads, audio uploads, and video generation
"""

import os
import requests
import time
import aiohttp
import asyncio
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path
from logging_service import logger
from s3_service import s3_service

class HedraAPIClient:
    """Client for interacting with Hedra's video generation API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hedra.com/web-app/public"  # From n8n workflow
        self.headers = {
            "x-api-key": api_key,  # Lowercase as per n8n workflow
            "User-Agent": "Sucana-v4/1.0"
        }
    
    async def create_asset(self, name: str, asset_type: str) -> str:
        """
        Create an asset (step 1 for both image and audio) - matches n8n workflow
        Returns: asset_id
        """
        url = f"{self.base_url}/assets"
        
        # Use JSON data as per n8n workflow (bodyParameters become JSON)
        payload = {
            "name": name,
            "type": asset_type  # "image" or "audio"
        }
        
        # Add Content-Type for JSON
        headers = {**self.headers, "Content-Type": "application/json"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        asset_id = result.get('id')
                        logger.info("hedra.asset.created", f"Asset created: {asset_id} ({asset_type})", asset_id=asset_id, asset_type=asset_type)
                        return asset_id
                    else:
                        error_text = await response.text()
                        raise Exception(f"Asset creation failed: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error("hedra.asset.creation_error", f"Asset creation error: {e}", error=str(e))
            raise

    async def upload_file_to_asset(self, asset_id: str, file_path: str, file_type: str) -> str:
        """
        Upload file to existing asset (step 2) - matches n8n workflow exactly
        Returns: asset_id
        """
        url = f"{self.base_url}/assets/{asset_id}/upload"
        
        try:
            # Read file and create form data as per n8n workflow
            with open(file_path, 'rb') as file:
                data = aiohttp.FormData()
                # Use 'file' as field name and the actual file content
                data.add_field('file', file, filename=Path(file_path).name)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=self.headers, data=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info("hedra.file.uploaded", f"File uploaded to asset: {asset_id}", asset_id=asset_id)
                            return asset_id
                        else:
                            error_text = await response.text()
                            raise Exception(f"File upload failed: {response.status} - {error_text}")
                            
        except Exception as e:
            logger.error("hedra.file.upload_error", f"File upload error: {e}", error=str(e))
            raise
    
    async def upload_audio(self, audio_file_path: str) -> str:
        """
        Upload audio file and return audio_id (convenience method)
        This combines create_asset + upload_file_to_asset for audio
        Returns: audio_id
        """
        try:
            # Step 1: Create audio asset
            audio_name = Path(audio_file_path).name
            logger.info("hedra.audio.uploading", f"Uploading audio file: {audio_name}", filename=audio_name)
            audio_id = await self.create_asset(audio_name, "audio")
            
            # Step 2: Upload file to asset
            await self.upload_file_to_asset(audio_id, audio_file_path, "audio")
            
            logger.info("hedra.audio.uploaded", f"Audio uploaded successfully: {audio_id}", audio_id=audio_id)
            return audio_id
            
        except Exception as e:
            logger.error("hedra.audio.upload_failed", f"Audio upload failed: {e}", error=str(e))
            raise
    
    async def get_models(self) -> dict:
        """
        Get available AI models - specifically get Hedra Character 3 for audio-driven videos
        Returns: Hedra Character 3 model data
        """
        url = f"{self.base_url}/models"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        # API returns a list of models
                        if isinstance(result, list) and len(result) > 0:
                            # Look for Hedra Character 3 model specifically
                            hedra_character_3_id = "d1dd37a3-e39a-4854-a298-6510289f9cf2"
                            
                            for model in result:
                                if model.get('id') == hedra_character_3_id:
                                    logger.info("hedra.model.selected", 
                                               f"Selected Hedra Character 3 model for audio-driven video generation",
                                               model_id=model.get('id'), 
                                               model_name=model.get('name'))
                                    return model
                            
                            # Fallback: Look for any model that supports audio input
                            for model in result:
                                if model.get('requires_audio_input') == True:
                                    logger.info("hedra.model.fallback", 
                                               f"Using fallback audio-supporting model: {model.get('name')}",
                                               model_id=model.get('id'), 
                                               model_name=model.get('name'))
                                    return model
                            
                            # Last resort: return first model
                            model = result[0]
                            logger.warning("hedra.model.default", 
                                         f"No audio-supporting model found, using default: {model.get('name')}",
                                         model_id=model.get('id'), 
                                         model_name=model.get('name'))
                            return model
                        else:
                            raise Exception("No models available")
                    else:
                        error_text = await response.text()
                        raise Exception(f"Models retrieval failed: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error("hedra.models.retrieval_error", f"Models retrieval error: {e}", error=str(e))
            raise

    async def create_generation(self, character_id: str, audio_id: str, 
                              aspect_ratio: str = "9:16", quality: str = "720p", 
                              audio_duration: Optional[float] = None, 
                              text_prompt: Optional[str] = None) -> str:
        """
        Create video generation job (updated to match N8N workflow)
        Returns: generation_id
        """
        url = f"{self.base_url}/generations"
        
        # Get model data first
        model_data = await self.get_models()
        
        # Find the correct aspect ratio from model data
        aspect_ratios = model_data.get('aspect_ratios', ['16:9', '1:1', '9:16'])
        selected_aspect_ratio = aspect_ratio if aspect_ratio in aspect_ratios else aspect_ratios[2] if len(aspect_ratios) > 2 else aspect_ratios[0]
        
        # Use provided text_prompt or default
        actual_text_prompt = text_prompt or "the person is talking confidently to the camera"
        
        # Build generated_video_inputs
        generated_video_inputs = {
            "text_prompt": actual_text_prompt,
            "resolution": quality,
            "aspect_ratio": selected_aspect_ratio
        }
        
        # Build the base payload
        payload = {
            "type": "video",
            "ai_model_id": model_data.get('id'),
            "start_keyframe_id": character_id,  # Use character_id as start_keyframe_id
            "audio_id": audio_id,
            "generated_video_inputs": generated_video_inputs
        }
        
        # Add duration in milliseconds as per Hedra's official API
        if audio_duration is not None:
            # Convert to milliseconds (Hedra expects duration_ms)
            duration_ms = int(audio_duration * 1000)
            generated_video_inputs["duration_ms"] = duration_ms
            
            logger.info("hedra.generation.duration", 
                       f"Setting video duration: {duration_ms}ms ({audio_duration:.2f}s)", 
                       duration_ms=duration_ms, 
                       duration_seconds=audio_duration)
        
        # Log the complete payload for debugging
        import json
        
        # Save to database log for detailed tracking
        log_data = {
            "action": "hedra_api_call",
            "endpoint": url,
            "method": "POST",
            "headers": {k: v[:20] + "..." if k.lower() == "x-api-key" and len(v) > 20 else v for k, v in self.headers.items()},
            "payload": payload,
            "character_id": character_id,
            "audio_id": audio_id,
            "model_id": model_data.get('id'),
            "aspect_ratio": selected_aspect_ratio,
            "quality": quality,
            "duration_seconds": audio_duration,
            "duration_ms": generated_video_inputs.get("duration_ms")
        }
        
        logger.info(
            "hedra.api.request",
            f"🚀 HEDRA API REQUEST\n" +
            f"=====================================\n" +
            f"Endpoint: {url}\n" +
            f"Method: POST\n" +
            f"Headers: {json.dumps(log_data['headers'], indent=2)}\n" +
            f"Payload: {json.dumps(payload, indent=2)}\n" +
            f"=====================================",
            **log_data
        )
        
        # Add Content-Type for JSON
        headers = {**self.headers, "Content-Type": "application/json"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    response_text = await response.text()
                    
                    # Log the raw response
                    logger.info(
                        "hedra.api.response",
                        f"📥 HEDRA API RESPONSE\n" +
                        f"=====================================\n" +
                        f"Status: {response.status}\n" +
                        f"Headers: {dict(response.headers)}\n" +
                        f"Body: {response_text[:1000]}{'...' if len(response_text) > 1000 else ''}\n" +
                        f"=====================================",
                        status_code=response.status,
                        response_headers=dict(response.headers),
                        response_body=response_text
                    )
                    
                    if response.status == 200:
                        result = json.loads(response_text)
                        # The new API might return the generation ID in different fields
                        generation_id = result.get('id') or result.get('generation_id') or result.get('job_id')
                        
                        logger.info(
                            "hedra.generation.success",
                            f"✅ Generation job created successfully!\n" +
                            f"Generation ID: {generation_id}\n" +
                            f"Full Response: {json.dumps(result, indent=2)}",
                            generation_id=generation_id,
                            response=result
                        )
                        
                        return generation_id
                    else:
                        logger.error(
                            "hedra.api.error",
                            f"❌ HEDRA API ERROR\n" +
                            f"Status: {response.status}\n" +
                            f"Error: {response_text}\n" +
                            f"Request Payload: {json.dumps(payload, indent=2)}",
                            status_code=response.status,
                            error_text=response_text,
                            payload=payload
                        )
                        raise Exception(f"Generation creation failed: {response.status} - {response_text}")
                        
        except Exception as e:
            logger.error("hedra.generation.creation_error", f"Generation creation error: {e}", error=str(e))
            raise
    
    async def check_generation_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check generation job status - updated for new API
        Returns: status info with progress and url when complete
        """
        # Use the correct endpoint from the new API documentation
        url = f"{self.base_url}/generations/{job_id}/status"
        
        logger.debug("hedra.status.checking_url", f"Checking status URL: {url}", url=url)
        try:
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout for status checks
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        # New API uses 'status' field instead of 'progress'
                        status = result.get('status', 'unknown')
                        progress = result.get('progress', 0)
                        logger.info("hedra.status.success", f"Status check successful - Status: {status}, Progress: {progress}", 
                                   status=status, progress=progress)
                        logger.debug("hedra.generation.status_response", f"Full status response: {result}", response=result)
                        return result
                    else:
                        error_text = await response.text()
                        logger.error("hedra.status.error", f"Status check error: {response.status} - {error_text}", 
                                    status_code=response.status, error=error_text)
                        raise Exception(f"Status check failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error("hedra.status.exception", f"Exception checking status: {e}", error=str(e))
            raise
    
    async def wait_for_completion(self, job_id: str, max_wait_minutes: int = 15) -> Dict[str, Any]:
        """
        Wait for generation to complete - matches n8n workflow logic
        Returns: final status with video_url
        """
        max_wait_seconds = max_wait_minutes * 60
        check_interval = 15  # Wait 15 seconds between checks like n8n workflow
        elapsed = 0
        check_count = 0
        
        logger.info("hedra.generation.waiting", f"Waiting for generation {job_id} to complete (max {max_wait_minutes} minutes)...", 
                   job_id=job_id, max_wait_minutes=max_wait_minutes)
        
        while elapsed < max_wait_seconds:
            check_count += 1
            logger.info("hedra.status.checking", f"Checking status (attempt {check_count}, elapsed: {elapsed}s)...", 
                       attempt=check_count, elapsed=elapsed)
            
            try:
                status = await self.check_generation_status(job_id)
                
                # Log the full status for debugging
                logger.debug("hedra.status.response", f"Status response: {status}", status=status)
                
                progress = status.get('progress', 0)
                state = status.get('state', status.get('status', 'unknown'))
                
                logger.info("hedra.job.status", 
                           f"Job {job_id} - Progress: {progress}, State: {state}, Elapsed: {elapsed}s", 
                           job_id=job_id, progress=progress, state=state, elapsed=elapsed)
                
                # Check different completion conditions based on new API
                # New API uses 'complete' status instead of progress values
                if state == 'complete' or state == 'completed':
                    logger.info("hedra.generation.completed", f"Generation {job_id} completed!", job_id=job_id)
                    # The video URL might be in different fields
                    video_url = status.get('url') or status.get('video_url') or status.get('output_url') or status.get('video', {}).get('url')
                    if video_url:
                        logger.info("hedra.video.ready", f"Video ready at: {video_url}", video_url=video_url)
                    return status
                elif progress == 1 or progress == 100:  # Fallback for progress-based completion
                    logger.info("hedra.generation.completed", f"Generation {job_id} completed (progress: {progress})!", 
                               job_id=job_id, progress=progress)
                    return status
                elif state in ['failed', 'error', 'cancelled']:
                    error_msg = status.get('error', status.get('message', f'Job failed with state: {state}'))
                    raise Exception(f"Generation {job_id} failed: {error_msg}")
                elif state == 'processing' or state == 'pending' or state == 'in_progress':
                    # Still processing, continue waiting
                    logger.debug("hedra.generation.processing", f"Generation still processing: {state}", state=state)
                
            except Exception as e:
                logger.error("hedra.status.check.failed", f"Status check failed: {e}", error=str(e))
                # Don't raise immediately, continue trying
                if elapsed >= max_wait_seconds - check_interval:
                    raise  # Only raise on last attempt
            
            # Wait before next check
            logger.debug("hedra.status.waiting", f"Waiting {check_interval}s before next check...", interval=check_interval)
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        logger.error("hedra.generation.timeout", f"Generation {job_id} timed out after {max_wait_minutes} minutes", 
                    job_id=job_id, max_wait_minutes=max_wait_minutes)
        raise Exception(f"Generation {job_id} timed out after {max_wait_minutes} minutes")
    
    async def download_video(self, video_url: str, save_path: str) -> str:
        """
        Download generated video
        Returns: local file path
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        # Ensure directory exists
                        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(save_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        logger.info("hedra.video.downloaded", f"Video downloaded: {save_path}", save_path=save_path)
                        return save_path
                    else:
                        raise Exception(f"Video download failed: {response.status}")
                        
        except Exception as e:
            logger.error("hedra.video.download_error", f"Video download error: {e}", error=str(e))
            raise
    
    async def upload_character(self, image_path: str) -> str:
        """
        Upload a character image and return the character ID
        This combines create_asset + upload_file_to_asset for images
        """
        try:
            # Step 1: Create image asset
            asset_id = await self.create_asset(f"character_{int(time.time())}", "image")
            
            # Step 2: Upload the image file to the asset
            character_id = await self.upload_file_to_asset(asset_id, image_path, "image")
            
            logger.info("hedra.character.uploaded", f"Character uploaded successfully: {character_id}", character_id=character_id)
            return character_id
            
        except Exception as e:
            logger.error("hedra.character.upload_failed", f"Character upload failed: {e}", error=str(e))
            raise


class HedraVideoGenerator:
    """High-level video generation orchestrator"""
    
    def __init__(self, api_key: str):
        self.client = HedraAPIClient(api_key)
        self.video_cache_dir = Path(__file__).parent / "generated_videos"
        self.video_cache_dir.mkdir(exist_ok=True)
    
    async def generate_videos_for_thread(self, thread_id: str, audio_data: Dict, 
                                       actor_image_path: str) -> List[Dict]:
        """
        Generate separate videos for hooks and scripts
        Returns: list of video info
        """
        logger.info("hedra.video_generation.started", f"Starting video generation for thread {thread_id}", thread_id=thread_id)
        
        # Create thread-specific directory
        thread_dir = self.video_cache_dir / thread_id
        thread_dir.mkdir(exist_ok=True)
        
        # Upload character once (reuse for all videos)
        logger.info("hedra.character.uploading", f"Uploading character image: {actor_image_path}", path=actor_image_path)
        character_id = await self.client.upload_character(actor_image_path)
        logger.info("hedra.character.uploaded_with_id", f"Character uploaded with ID: {character_id}", character_id=character_id)
        
        generated_videos = []
        
        # Process each script with audio
        for script_data in audio_data.get('scripts_with_audio', []):
            # Check for combined audio first (new approach)
            combined_audio_url = script_data.get('combined_audio', {}).get('audio_url')
            
            if combined_audio_url:
                # Generate single combined video
                combined_video = await self._generate_single_video(
                    thread_id, character_id, script_data, combined_audio_url, 'combined'
                )
                if combined_video:
                    generated_videos.append(combined_video)
            else:
                # Fallback to separate hook/script processing (backwards compatibility)
                hook_audio_url = script_data.get('hook_audio', {}).get('audio_url')
                script_audio_url = script_data.get('script_audio', {}).get('audio_url')
                
                if not hook_audio_url and not script_audio_url:
                    logger.warning("hedra.script.skipped_no_audio", f"Skipping script {script_data.get('script_id')} - no audio available", script_id=script_data.get('script_id'))
                    continue
                
                # Generate separate videos for hook and script
                if hook_audio_url:
                    hook_video = await self._generate_single_video(
                        thread_id, character_id, script_data, hook_audio_url, 'hook'
                    )
                    if hook_video:
                        generated_videos.append(hook_video)
                
                if script_audio_url:
                    script_video = await self._generate_single_video(
                        thread_id, character_id, script_data, script_audio_url, 'script'
                    )
                    if script_video:
                        generated_videos.append(script_video)
        
        logger.info("hedra.videos.generated", f"Generated {len(generated_videos)} videos for thread {thread_id}", count=len(generated_videos), thread_id=thread_id)
        return generated_videos
    
    async def _generate_single_video(self, thread_id: str, character_id: str, 
                                   script_data: Dict, audio_url: str, video_type: str) -> Optional[Dict]:
        """Generate a single video for either hook or script"""
        
        script_id = script_data.get('script_id')
        logger.info("hedra.video.generating", f"Generating {video_type} video for script {script_id}", video_type=video_type, script_id=script_id)
        
        try:
            # Convert URL to local path
            audio_local_path = self._url_to_local_path(audio_url)
            
            # Verify file exists
            if not Path(audio_local_path).exists():
                raise FileNotFoundError(f"Audio file not found: {audio_local_path}")
            
            # Get audio duration from the script data
            audio_duration = None
            if video_type == 'combined':
                audio_data = script_data.get('combined_audio', {})
                audio_duration = audio_data.get('duration')
            elif video_type == 'hook':
                audio_data = script_data.get('hook_audio', {})
                audio_duration = audio_data.get('duration')
            elif video_type == 'script':
                audio_data = script_data.get('script_audio', {})
                audio_duration = audio_data.get('duration')
            
            logger.debug("hedra.audio.duration_from_data", f"Duration from script data: {audio_duration}", 
                        video_type=video_type, duration=audio_duration)
            
            # If duration not in data, try to calculate it
            if audio_duration is None:
                try:
                    result = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_local_path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        audio_duration = float(result.stdout.strip())
                        logger.info("hedra.audio.duration_calculated", f"Calculated audio duration: {audio_duration} seconds", duration=audio_duration)
                except Exception as e:
                    logger.warning("hedra.audio.duration_calculation_failed", f"Could not calculate audio duration: {e}", error=str(e))
                    # Fallback to a default duration
                    audio_duration = 10.0
            
            # Upload audio
            logger.debug("hedra.audio.uploading_from", f"Uploading audio from: {audio_local_path}", path=audio_local_path)
            audio_id = await self.client.upload_audio(audio_local_path)
            logger.info("hedra.audio.uploaded_with_id", f"Audio uploaded with ID: {audio_id}", audio_id=audio_id)
            
            # Prepare the actual text content for the video
            hook_text = script_data.get('hook', '')
            script_text = script_data.get('body', '')
            
            # Create appropriate text prompt based on video type
            if video_type == 'combined':
                text_prompt = f"{hook_text} {script_text}".strip()
            elif video_type == 'hook':
                text_prompt = hook_text
            elif video_type == 'script':
                text_prompt = script_text
            else:
                text_prompt = f"{hook_text} {script_text}".strip()
            
            # Truncate if too long (Hedra might have limits)
            if len(text_prompt) > 1000:
                text_prompt = text_prompt[:997] + "..."
            
            logger.info("hedra.video.text_prompt", f"Using text prompt: {text_prompt[:100]}...", 
                       video_type=video_type, prompt_length=len(text_prompt))
            
            # Create generation job with duration and actual text
            job_id = await self.client.create_generation(
                character_id=character_id,
                audio_id=audio_id,
                aspect_ratio="9:16",  # TikTok format
                quality="720p",       # Better quality: 540p or 720p
                audio_duration=audio_duration,
                text_prompt=text_prompt  # Pass the actual script content
            )
            
            # Wait for completion
            result = await self.client.wait_for_completion(job_id, max_wait_minutes=15)
            
            # Download video - check multiple possible fields for video URL
            video_url = result.get('url') or result.get('video_url') or result.get('output_url') or result.get('video', {}).get('url')
            if video_url:
                local_video_path = self.video_cache_dir / thread_id / f"{script_id}_{video_type}.mp4"
                downloaded_path = await self.client.download_video(video_url, str(local_video_path))
                
                # Upload to S3 if available
                final_video_url = f"/generated_videos/{thread_id}/{script_id}_{video_type}.mp4"  # Default local URL
                
                if s3_service.enabled:
                    s3_url = s3_service.upload_file(
                        str(local_video_path),
                        file_type="video",
                        campaign_id=thread_id  # Use thread_id as campaign_id for organization
                    )
                    if s3_url:
                        final_video_url = s3_url
                        logger.info("hedra.video.s3_uploaded", f"Uploaded video to S3: {s3_url}", url=s3_url)
                        
                        # Optionally delete local file after successful S3 upload to save space
                        # os.remove(str(local_video_path))
                    else:
                        logger.warning("hedra.video.s3_upload_failed", "Failed to upload video to S3, using local storage")
                else:
                    logger.info("hedra.video.local_storage", "Using local storage (S3 not configured)")
                
                # Prepare text content based on video type
                hook_text = script_data.get('hook', '')
                script_text = script_data.get('body', '')
                combined_text = ""
                
                if video_type == 'combined':
                    combined_text = f"{hook_text}. {script_text}" if hook_text and script_text else (hook_text or script_text)
                elif video_type == 'hook':
                    hook_text = hook_text
                    script_text = ""
                elif video_type == 'script':
                    hook_text = ""
                    script_text = script_text
                
                return {
                    "script_id": script_id,
                    "video_type": video_type,
                    "hook_text": hook_text,
                    "script_text": script_text,
                    "combined_text": combined_text,
                    "video_url": final_video_url,
                    "local_path": downloaded_path,
                    "hedra_job_id": job_id,
                    "duration": result.get('duration'),
                    "status": "completed"
                }
        
        except Exception as e:
            logger.error("hedra.video.generation_failed", f"Failed to generate {video_type} video for script {script_id}: {e}", video_type=video_type, script_id=script_id, error=str(e))
            
            # Prepare text content for error case
            hook_text = script_data.get('hook', '')
            script_text = script_data.get('body', '')
            combined_text = ""
            
            if video_type == 'combined':
                combined_text = f"{hook_text}. {script_text}" if hook_text and script_text else (hook_text or script_text)
            elif video_type == 'hook':
                script_text = ""
            elif video_type == 'script':
                hook_text = ""
            
            return {
                "script_id": script_id,
                "video_type": video_type,
                "hook_text": hook_text,
                "script_text": script_text,
                "combined_text": combined_text,
                "error": str(e),
                "status": "failed"
            }
    
    def _url_to_local_path(self, url: str) -> str:
        """Convert URL path to local file system path or download from S3"""
        # Handle S3 URLs
        if url.startswith('https://') and 's3' in url:
            # This is an S3 URL, we need to download it temporarily
            import requests
            import tempfile
            import os
            
            logger.info("hedra.audio.s3_download", f"Downloading audio from S3: {url}")
            
            try:
                # Download the file
                response = requests.get(url)
                response.raise_for_status()
                
                # Create a temporary file
                temp_dir = Path(__file__).parent / "temp_audio"
                temp_dir.mkdir(exist_ok=True)
                
                # Extract filename from URL
                filename = url.split('/')[-1]
                temp_path = temp_dir / filename
                
                # Write to temporary file
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info("hedra.audio.s3_downloaded", f"Downloaded S3 audio to: {temp_path}")
                return str(temp_path)
                
            except Exception as e:
                logger.error("hedra.audio.s3_download_error", f"Failed to download S3 audio: {e}")
                raise FileNotFoundError(f"Could not download audio from S3: {url}")
        
        # Handle local URLs
        elif url.startswith('/generated_audio/'):
            # Remove leading slash and convert to absolute path
            relative_path = url[1:]  # Remove leading /
            return str(Path(__file__).parent / relative_path)
        return url
    

# Initialize Hedra client
HEDRA_API_KEY = os.getenv("HEDRA_API_KEY")
if HEDRA_API_KEY:
    hedra_generator = HedraVideoGenerator(HEDRA_API_KEY)
    logger.info("hedra.generator.initialized", "Hedra video generator initialized")
else:
    hedra_generator = None
    logger.warning("hedra.api_key.missing", "HEDRA_API_KEY not found - video generation disabled")
