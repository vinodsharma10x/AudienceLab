# Video Ads Workflow Routes for Sucana v4
import os
import requests
import json
import openai
import base64
import hashlib
import uuid
import time
import aiohttp
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import shared authentication
from auth import verify_token

# Import S3 service
from s3_service import s3_service

# Import actor image handler
from actor_image_handler import actor_image_handler

from video_ads_models import (
    URLParseRequest, URLParseResponse, VideoAdsProductInfo,
    MarketingAnglesRequest, MarketingAnglesResponse, MarketingAngle,
    HooksRequest, HooksResponse, SelectedAngle, AngleWithHooks,
    HookBodyRequest, HookBodyResponse,
    ScriptsRequest, ScriptsResponse, SelectedAngleForScripts,
    VoiceActorRequest, VoiceActorResponse, ElevenLabsVoice, ActorImage,
    AudioGenerationRequest, AudioGenerationResponse, GeneratedAudio, ScriptWithAudio,
    VideoGenerationDetailedRequest, VideoGenerationDetailedResponse, GeneratedVideo
)

# Create router
router = APIRouter(prefix="/video-ads", tags=["video-ads"])

# Import authentication from main application
# This will be imported from the main FastAPI app when the router is included
# The verify_token dependency will be imported where needed

# OpenAI client (will be initialized from environment)
client = None

def init_openai_client():
    """Initialize OpenAI client"""
    global client
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = openai.OpenAI(api_key=api_key)
        return True
    return False

# Initialize OpenAI client on import
init_openai_client()

@router.post("/parse-url", response_model=URLParseResponse)
async def parse_url(
    request: URLParseRequest,
    current_user: dict = Depends(verify_token)
):
    """Parse a URL to extract product information for video ads workflow using AI"""
    user_id = current_user["user_id"]
    
    print(f"Starting URL parsing for user {user_id}: {request.url}")
    
    try:
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Use async HTTP request to avoid blocking
        async with aiohttp.ClientSession() as session:
            async with session.get(request.url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                response.raise_for_status()
                content = await response.read()
        
        # Parse HTML and extract clean text content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text content
        text_content = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit text length for API call (keep first 8000 chars to stay within token limits)
        clean_text = clean_text[:8000]
        
        # Get page title and meta description for additional context
        title = soup.find('title')
        page_title = title.text.strip() if title else ""
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        meta_description = meta_desc.get('content', '').strip() if meta_desc else ""
        
        # Use OpenAI to extract structured information
        if not client:
            print("OpenAI client not initialized, trying to initialize...")
            if not init_openai_client():
                raise HTTPException(status_code=500, detail="OpenAI client not initialized. Please check API key.")
        
        # Create a prompt for structured extraction
        extraction_prompt = f"""
        Analyze the following webpage content and extract structured product information. Return a JSON object with the following fields:

        - product_name: The main product or service name (max 100 chars)
        - product_information: Comprehensive description of what the product/service does (max 800 chars)
        - target_audience: Who this product is designed for (max 200 chars)
        - price: Any pricing information found (max 50 chars, include currency and billing period if found)
        - problem_solved: What problem or pain point this product solves (max 300 chars)
        - key_benefits: Array of key benefits/features (max 5 items, each max 100 chars)
        - unique_selling_points: Array of what makes this product unique (max 3 items, each max 150 chars)
        - additional_info: Any other relevant information (max 500 chars)

        If information is not available or unclear, use an empty string for strings or empty array for arrays.

        Page Title: {page_title}
        Meta Description: {meta_description}
        Page Content: {clean_text}

        Return only valid JSON, no additional text:
        """
        
        # Call OpenAI API
        try:
            ai_response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using more cost-effective model for extraction
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured product information from web content. Always return valid JSON."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,  # Lower temperature for more consistent extraction
                max_tokens=1500
            )
            
            # Parse AI response
            ai_content = ai_response.choices[0].message.content.strip()
            
            # Clean up response if it has markdown code blocks
            if ai_content.startswith('```json'):
                ai_content = ai_content[7:-3]
            elif ai_content.startswith('```'):
                ai_content = ai_content[3:-3]
            
            try:
                extracted_info = json.loads(ai_content)
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed: {e}")
                print(f"AI response: {ai_content}")
                # Fallback if JSON parsing fails
                extracted_info = {
                    "product_name": page_title[:100] if page_title else "",
                    "product_information": meta_description[:800] if meta_description else "",
                    "target_audience": "",
                    "price": "",
                    "problem_solved": "",
                    "key_benefits": [],
                    "unique_selling_points": [],
                    "additional_info": meta_description[:500] if meta_description else ""
                }
        
        except Exception as openai_error:
            print(f"OpenAI API error: {openai_error}")
            # Fallback extraction without AI
            extracted_info = {
                "product_name": page_title[:100] if page_title else "",
                "product_information": meta_description[:800] if meta_description else "",
                "target_audience": "",
                "price": "",
                "problem_solved": "",
                "key_benefits": [],
                "unique_selling_points": [],
                "additional_info": meta_description[:500] if meta_description else ""
            }
        
        # Ensure all required fields exist with proper defaults
        required_fields = {
            "product_name": "",
            "product_information": "",
            "target_audience": "",
            "price": "",
            "problem_solved": "",
            "key_benefits": [],
            "unique_selling_points": [],
            "additional_info": ""
        }
        
        for field, default in required_fields.items():
            if field not in extracted_info:
                extracted_info[field] = default
            elif extracted_info[field] is None:
                extracted_info[field] = default
        
        # Ensure string fields are properly truncated
        extracted_info["product_name"] = str(extracted_info["product_name"])[:100]
        extracted_info["product_information"] = str(extracted_info["product_information"])[:800]
        extracted_info["target_audience"] = str(extracted_info["target_audience"])[:200]
        extracted_info["price"] = str(extracted_info["price"])[:50]
        extracted_info["problem_solved"] = str(extracted_info["problem_solved"])[:300]
        extracted_info["additional_info"] = str(extracted_info["additional_info"])[:500]
        
        # Ensure arrays are properly formatted and truncated
        if isinstance(extracted_info["key_benefits"], list):
            extracted_info["key_benefits"] = [str(benefit)[:100] for benefit in extracted_info["key_benefits"][:5]]
        else:
            extracted_info["key_benefits"] = []
            
        if isinstance(extracted_info["unique_selling_points"], list):
            extracted_info["unique_selling_points"] = [str(usp)[:150] for usp in extracted_info["unique_selling_points"][:3]]
        else:
            extracted_info["unique_selling_points"] = []
        
        print(f"Successfully parsed URL for user {user_id}: {extracted_info['product_name']}")
        
        return URLParseResponse(**extracted_info)
        
    except requests.Timeout:
        print(f"Timeout error for URL: {request.url}")
        raise HTTPException(status_code=400, detail="The webpage took too long to load. Please try a different URL.")
    except requests.ConnectionError:
        print(f"Connection error for URL: {request.url}")
        raise HTTPException(status_code=400, detail="Unable to connect to the website. Please check the URL and try again.")
    except requests.RequestException as e:
        print(f"Request error for URL: {request.url} - {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        print(f"General error for URL: {request.url} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"URL parsing failed: {str(e)}")

# Assistant IDs
ASSISTANT_IDS = {
    1: "asst_tP88CULXVsGX5fxwPoQDrDNJ",  # asst_1_Avatar_ICP 
    2: "asst_Mnw7kQZZfSSllOrk6PRz8vD4",  # asst_2_Customer_Journey_Mapping
    3: "asst_jyDQVx3XVivXwG55dRclq8hs",  # asst_3_Objections
    4: "asst_K8WGtHEfd4D9OJxcvsgDmguU",  # asst_4_Angles
    5: "asst_X8eLyMprG9ae38GtyMaiIbgD",  # asst_5_Hooks
    6: "asst_NGr7lbk33Svg3ly7j3D9VMVE"   # asst_6_AIDA_Script
}

# Active threads storage (in production, use Redis or database)
active_threads = {}
user_threads = {}

async def wait_for_run_completion(client, thread_id: str, run_id: str, max_wait: int = 180):
    """Wait for OpenAI assistant run to complete with timeout - ASYNC VERSION"""
    import asyncio
    
    start_time = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start_time < max_wait:
        try:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            if run.status == "completed":
                return run
            elif run.status in ["failed", "cancelled", "expired"]:
                raise Exception(f"Run {run_id} {run.status}: {run.last_error}")
            
            await asyncio.sleep(2)  # Non-blocking sleep - allows other requests to process
            
        except Exception as e:
            print(f"Error checking run status: {e}")
            await asyncio.sleep(2)  # Non-blocking sleep
            continue
    
    raise Exception(f"Run {run_id} timed out after {max_wait} seconds")

def parse_hooks_json(response_text: str) -> dict:
    """Parse the hooks JSON response from Assistant 5"""
    import json
    
    try:
        # Clean up response if it has markdown code blocks
        clean_response = response_text.strip()
        if clean_response.startswith('```json'):
            clean_response = clean_response[7:-3]
        elif clean_response.startswith('```'):
            clean_response = clean_response[3:-3]
        
        # Parse JSON
        parsed_data = json.loads(clean_response)
        
        # Validate structure
        if "hooks_by_angle" not in parsed_data:
            raise ValueError("Missing required hooks_by_angle structure")
        
        return parsed_data
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse hooks JSON: {e}")
        print(f"Raw response: {response_text[:500]}...")
        
        # Return empty structure as fallback
        return {
            "hooks_by_angle": []
        }

def parse_marketing_angles_json(response_text: str) -> dict:
    """Parse the marketing angles JSON response from Assistant 4"""
    import json
    import re
    
    try:
        # Clean up response if it has markdown code blocks
        clean_response = response_text.strip()
        
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
        
        # Parse JSON
        parsed_data = json.loads(clean_response)
        
        # Validate structure
        if "positive_angles" not in parsed_data or "negative_angles" not in parsed_data:
            raise ValueError("Missing required angle categories")
        
        return parsed_data
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse marketing angles JSON: {e}")
        print(f"Raw response: {response_text[:500]}...")
        
        # Return empty structure as fallback
        return {
            "positive_angles": [],
            "negative_angles": []
        }

# Health check for video ads service
@router.get("/health")
async def video_ads_health():
    """Health check for video ads service"""
    return {
        "status": "healthy",
        "service": "video-ads",
        "openai_available": client is not None,
        "endpoints": [
            "/video-ads/parse-url",
            "/video-ads/create-marketing-angles",
            "/video-ads/product-info", 
            "/video-ads/marketing-angles",
            "/video-ads/hooks",
            "/video-ads/scripts",
            "/video-ads/voice-actor",
            "/video-ads/audio",
            "/video-ads/video"
        ]
    }

@router.post("/create-marketing-angles", response_model=MarketingAnglesResponse)
async def create_marketing_angles(
    request: MarketingAnglesRequest,
    current_user: dict = Depends(verify_token)
):
    """Run the 4-assistant sequence and return marketing angles for user selection"""
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")
    
    try:
        user_id = current_user["user_id"]
        
        print(f"🚀 Starting marketing angles creation for user {user_id}")
        print(f"Product: {request.product_info.product_name}")
        
        # Create a new thread for this video ads workflow
        thread = client.beta.threads.create(
            extra_headers={"OpenAI-Beta": "assistants=v2"}
        )
        thread_id = thread.id
        print(f"📎 Created thread {thread_id}")
        
        # Associate thread with user
        if user_id not in user_threads:
            user_threads[user_id] = []
        user_threads[user_id].append(thread_id)
        
        # Prepare the initial message with product info
        initial_message = f"""
Product Name: {request.product_info.product_name}
Product Information: {request.product_info.product_information}
Target Audience: {request.product_info.target_audience}
Price: {request.product_info.price or 'Not specified'}
Problem Solved: {request.product_info.problem_solved}
Differentiation: {request.product_info.differentiation}
Additional Information: {request.product_info.additional_information or 'None provided'}
"""
        
        print(f"📝 Initial message prepared for thread {thread_id}")
        
        # Add initial message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=initial_message,
            extra_headers={"OpenAI-Beta": "assistants=v2"}
        )
        
        responses = {}
        
        # Run Assistant 1: Avatar_ICP
        print(f"🤖 Running Assistant 1: Avatar_ICP for thread {thread_id}")
        
        try:
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_IDS[1],
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            await wait_for_run_completion(client, thread_id, run.id, max_wait=180)
            
            messages = client.beta.threads.messages.list(
                thread_id=thread_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            responses[1] = messages.data[0].content[0].text.value
            print(f"✅ Assistant 1 completed for thread {thread_id}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Assistant 1 failed: {error_msg}")
            if "No assistant found" in error_msg:
                print(f"⚠️ Using mock response for testing - Assistant ID {ASSISTANT_IDS[1]} not found")
                # For now, we'll use a mock response until you provide the correct assistant IDs
                responses[1] = "Avatar analysis completed for testing purposes."
            else:
                raise HTTPException(status_code=500, detail=f"Assistant 1 (Avatar_ICP) failed: {error_msg}")
        
        # Run Assistant 2: Customer Journey Mapping
        print(f"🤖 Running Assistant 2: Customer Journey Mapping for thread {thread_id}")
        
        try:
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content="Please follow the instructions provided inside the assistant.",
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_IDS[2],
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            await wait_for_run_completion(client, thread_id, run.id, max_wait=180)
            
            messages = client.beta.threads.messages.list(
                thread_id=thread_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            responses[2] = messages.data[0].content[0].text.value
            print(f"✅ Assistant 2 completed for thread {thread_id}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Assistant 2 failed: {error_msg}")
            if "No assistant found" in error_msg:
                print(f"⚠️ Using mock response for testing - Assistant ID {ASSISTANT_IDS[2]} not found")
                responses[2] = "Customer journey mapping completed for testing purposes."
            else:
                raise HTTPException(status_code=500, detail=f"Assistant 2 (Customer Journey Mapping) failed: {error_msg}")
        
        # Run Assistant 3: Objections
        print(f"🤖 Running Assistant 3: Objections for thread {thread_id}")
        
        try:
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content="Please follow the instructions provided inside the assistant.",
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_IDS[3],
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            await wait_for_run_completion(client, thread_id, run.id, max_wait=180)
            
            messages = client.beta.threads.messages.list(
                thread_id=thread_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            responses[3] = messages.data[0].content[0].text.value
            print(f"✅ Assistant 3 completed for thread {thread_id}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Assistant 3 failed: {error_msg}")
            if "No assistant found" in error_msg:
                print(f"⚠️ Using mock response for testing - Assistant ID {ASSISTANT_IDS[3]} not found")
                responses[3] = "Objections analysis completed for testing purposes."
            else:
                raise HTTPException(status_code=500, detail=f"Assistant 3 (Objections) failed: {error_msg}")
        
        # Run Assistant 4: Angles
        print(f"🤖 Running Assistant 4: Angles for thread {thread_id}")
        
        try:
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content="Please follow the instructions provided inside the assistant.",
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_IDS[4],
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            await wait_for_run_completion(client, thread_id, run.id, max_wait=180)
            
            messages = client.beta.threads.messages.list(
                thread_id=thread_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            angles_response = messages.data[0].content[0].text.value
            responses[4] = angles_response
            print(f"✅ Assistant 4 completed for thread {thread_id}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Assistant 4 failed: {error_msg}")
            if "No assistant found" in error_msg:
                print(f"⚠️ Using mock response for testing - Assistant ID {ASSISTANT_IDS[4]} not found")
                # Create a mock JSON response with the expected structure
                angles_response = f'''{{
  "positive_angles": [
    {{
      "angle": 1,
      "category": "UVT (advantageous comparison with other solutions)",
      "concept": "Our {request.product_info.product_name} outperforms competitors with {request.product_info.differentiation}",
      "type": "positive"
    }},
    {{
      "angle": 2,
      "category": "Specific future aspiration",
      "concept": "Transform your business with {request.product_info.product_name} and achieve your goals faster",
      "type": "positive"
    }},
    {{
      "angle": 3,
      "category": "Social validation / prestige",
      "concept": "Join successful {request.product_info.target_audience} who trust {request.product_info.product_name}",
      "type": "positive"
    }}
  ],
  "negative_angles": [
    {{
      "angle": 4,
      "category": "UVT (criticism of alternative solutions)",
      "concept": "Stop struggling with outdated solutions - {request.product_info.problem_solved}",
      "type": "negative"
    }},
    {{
      "angle": 5,
      "category": "Frustration of the status quo",
      "concept": "Are you tired of {request.product_info.problem_solved.lower()}? There's a better way.",
      "type": "negative"
    }}
  ]
}}'''
                responses[4] = angles_response
            else:
                raise HTTPException(status_code=500, detail=f"Assistant 4 (Angles) failed: {error_msg}")
        
        # Store thread info for later use
        active_threads[thread_id] = {
            "current_step": 4,
            "user_id": user_id,
            "workflow": "video_ads",
            "product_info": request.product_info.dict(),
            "responses": responses
        }
        
        # Parse the marketing angles JSON response
        parsed_angles = parse_marketing_angles_json(angles_response)
        
        # Convert to response format
        positive_angles = []
        negative_angles = []
        
        for angle_data in parsed_angles.get("positive_angles", []):
            positive_angles.append(MarketingAngle(
                angle=angle_data.get("angle", 0),
                category=angle_data.get("category", ""),
                concept=angle_data.get("concept", ""),
                type="positive"
            ))
        
        for angle_data in parsed_angles.get("negative_angles", []):
            negative_angles.append(MarketingAngle(
                angle=angle_data.get("angle", 0),
                category=angle_data.get("category", ""),
                concept=angle_data.get("concept", ""),
                type="negative"
            ))
        
        print(f"🎯 Generated {len(positive_angles)} positive and {len(negative_angles)} negative angles for thread {thread_id}")
        
        return MarketingAnglesResponse(
            thread_id=thread_id,
            positive_angles=positive_angles,
            negative_angles=negative_angles,
            raw_response=angles_response
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error in create_marketing_angles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create marketing angles: {str(e)}")

@router.post("/create-hooks", response_model=HooksResponse)
async def create_hooks(
    request: HooksRequest,
    current_user: dict = Depends(verify_token)
):
    """Generate hooks for selected marketing angles using Assistant 5"""
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")
    
    try:
        user_id = current_user["user_id"]
        thread_id = request.thread_id
        selected_angles = [angle.dict() for angle in request.selected_angles]
        
        if not thread_id:
            raise HTTPException(status_code=400, detail="thread_id is required")
        
        if not selected_angles:
            raise HTTPException(status_code=400, detail="selected_angles is required")
        
        print(f"🎯 Starting hooks creation for user {user_id}, thread {thread_id}")
        print(f"Selected {len(selected_angles)} angles for hook generation")
        
        # Verify thread exists in our tracking
        if thread_id not in active_threads:
            print(f"❌ Thread {thread_id} not found in active_threads")
            print(f"Active threads: {list(active_threads.keys())}")
            raise HTTPException(
                status_code=400, 
                detail="Thread expired or invalid. Please restart from marketing angles step."
            )
        
        thread_info = active_threads[thread_id]
        if thread_info["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this thread")
        
        # Format selected angles as JSON for the assistant
        angles_message = json.dumps({"selected_angles": selected_angles}, indent=2)
        
        print(f"📝 Sending selected angles to Assistant 5 for thread {thread_id}")
        
        # Add message with selected angles to the thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=angles_message,
            extra_headers={"OpenAI-Beta": "assistants=v2"}
        )
        
        # Run Assistant 5: Hooks
        print(f"🤖 Running Assistant 5: Hooks for thread {thread_id}")
        
        try:
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_IDS[5],
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            await wait_for_run_completion(client, thread_id, run.id, max_wait=180)
            
            messages = client.beta.threads.messages.list(
                thread_id=thread_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            hooks_response = messages.data[0].content[0].text.value
            print(f"✅ Assistant 5 completed for thread {thread_id}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Assistant 5 failed: {error_msg}")
            if "No assistant found" in error_msg:
                print(f"⚠️ Using mock response for testing - Assistant ID {ASSISTANT_IDS[5]} not found")
                
                # Create mock hooks response based on selected angles
                mock_hooks = {
                    "hooks_by_angle": []
                }
                
                for angle in selected_angles:
                    angle_hooks = {
                        "angle_id": f"angle_{angle['angle']}",
                        "angle_number": angle['angle'],
                        "angle_category": angle['category'],
                        "angle_concept": angle['concept'],
                        "angle_type": angle['type'],
                        "hooks_by_category": {
                            "direct_question": [
                                f"¿Ready for {angle['category'].lower()}?",
                                f"¿Want to solve {angle['concept'][:50]}...?",
                                f"¿How about {angle['type']} results?"
                            ],
                            "shocking_fact": [
                                f"80% ignore this {angle['type']} approach!",
                                f"Most fail because they don't use {angle['category'][:30]}...",
                                f"Only 10% succeed with {angle['type']} strategies."
                            ],
                            "demonstration": [
                                f"See how {angle['category']} works in practice.",
                                f"Watch this {angle['type']} transformation.",
                                f"Here's proof that {angle['concept'][:40]}... works."
                            ]
                        }
                    }
                    mock_hooks["hooks_by_angle"].append(angle_hooks)
                
                hooks_response = json.dumps(mock_hooks, indent=2)
            else:
                raise HTTPException(status_code=500, detail=f"Assistant 5 (Hooks) failed: {error_msg}")
        
        # Parse the hooks response
        parsed_hooks = parse_hooks_json(hooks_response)
        
        # Update thread info with current step and selected angles
        active_threads[thread_id].update({
            "current_step": 5,
            "selected_angles": selected_angles,
            "hooks_response": hooks_response
        })
        
        print(f"🎯 Generated hooks for {len(parsed_hooks.get('hooks_by_angle', []))} angles in thread {thread_id}")
        
        return HooksResponse(
            thread_id=thread_id,
            hooks_by_angle=parsed_hooks.get("hooks_by_angle", []),
            raw_response=hooks_response
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error in create_hooks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create hooks: {str(e)}")

@router.post("/create-scripts", response_model=ScriptsResponse)
async def create_scripts(
    request: ScriptsRequest,
    current_user: dict = Depends(verify_token)
):
    """Generate scripts for selected hooks using Assistant 6 (AIDA Script)"""
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized")
    
    try:
        user_id = current_user["user_id"]
        thread_id = request.thread_id
        hooks_by_angle = [angle.dict() for angle in request.hooks_by_angle]
        
        if not thread_id:
            raise HTTPException(status_code=400, detail="thread_id is required")
        
        if not hooks_by_angle:
            raise HTTPException(status_code=400, detail="hooks_by_angle is required")
        
        print(f"📝 Starting scripts creation for user {user_id}, thread {thread_id}")
        print(f"Processing {len(hooks_by_angle)} angles for script generation")
        
        # Verify thread exists in our tracking
        if thread_id not in active_threads:
            print(f"❌ Thread {thread_id} not found in active_threads")
            print(f"Active threads: {list(active_threads.keys())}")
            raise HTTPException(
                status_code=400, 
                detail="Thread expired or invalid. Please restart from marketing angles step."
            )
        
        thread_info = active_threads[thread_id]
        if thread_info["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Access denied to this thread")
        
        # Format hooks data as JSON for the assistant
        hooks_message = json.dumps({"hooks_by_angle": hooks_by_angle}, indent=2)
        
        print(f"📝 Sending selected hooks to Assistant 6 for thread {thread_id}")
        
        # Add message with selected hooks to the thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=hooks_message,
            extra_headers={"OpenAI-Beta": "assistants=v2"}
        )
        
        # Run Assistant 6: AIDA Script
        print(f"🤖 Running Assistant 6: AIDA Script for thread {thread_id}")
        
        try:
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_IDS[6],
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            print(f"⏳ Waiting for script generation to complete...")
            completed_run = await wait_for_run_completion(client, thread_id, run.id)
            
            if completed_run.status != "completed":
                print(f"❌ Script generation failed with status: {completed_run.status}")
                raise HTTPException(status_code=500, detail="Script generation failed")
            
            # Get the assistant's response
            messages = client.beta.threads.messages.list(
                thread_id=thread_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            scripts_response = None
            for message in messages.data:
                if message.role == "assistant" and message.content:
                    scripts_response = message.content[0].text.value
                    break
            
            if not scripts_response:
                raise HTTPException(status_code=500, detail="No script response received from assistant")
            
            print(f"✅ Script generation completed successfully")
            
        except Exception as openai_error:
            print(f"❌ OpenAI API error in script generation: {str(openai_error)}")
            # Provide mock response for development/fallback
            scripts_response = json.dumps({
                "campaign_scripts": {
                    "angles": [
                        {
                            "selected_angle": {
                                "id": hooks_by_angle[0]["id"] if hooks_by_angle else "angle_1",
                                "angle": hooks_by_angle[0]["angle"] if hooks_by_angle else 1,
                                "category": hooks_by_angle[0]["category"] if hooks_by_angle else "Sample Category",
                                "concept": hooks_by_angle[0]["concept"] if hooks_by_angle else "Sample concept",
                                "type": hooks_by_angle[0]["type"] if hooks_by_angle else "positive"
                            },
                            "hooks": [
                                {
                                    "selected_hook": {
                                        "id": "hook_1_1",
                                        "hook_text": "Sample hook text for testing",
                                        "hook_type": "direct_question"
                                    },
                                    "scripts": [
                                        {
                                            "id": "script_1_1_1",
                                            "version": "A",
                                            "content": "This is a sample script generated for testing purposes. In production, this would be generated by the OpenAI assistant based on your selected hooks and marketing angles.",
                                            "cta": "Click here to take action",
                                            "target_emotion": "Curiosity and interest"
                                        },
                                        {
                                            "id": "script_1_1_2",
                                            "version": "B",
                                            "content": "This is an alternative sample script with a different approach. The assistant would generate multiple variations to give you options for your campaign.",
                                            "cta": "Start your journey today",
                                            "target_emotion": "Motivation and urgency"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            })
        
        # Parse the scripts JSON response
        try:
            # Clean up the response (remove markdown formatting if present)
            clean_response = scripts_response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            parsed_scripts = json.loads(clean_response)
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse scripts JSON: {str(e)}")
            print(f"Raw response: {scripts_response[:500]}...")
            raise HTTPException(status_code=500, detail="Failed to parse script response")
        
        # Update thread info
        active_threads[thread_id].update({
            "current_step": 6,
            "scripts_data": parsed_scripts
        })
        
        return ScriptsResponse(
            thread_id=thread_id,
            campaign_scripts=parsed_scripts.get("campaign_scripts", {"angles": []}),
            raw_response=scripts_response
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error in create_scripts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create scripts: {str(e)}")

# ElevenLabs Integration
import base64
from actor_images_config import ACTOR_IMAGES

# ElevenLabs API configuration
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize Supabase client for voice caching
supabase = None
supabase_error = None

try:
    print("🔍 Starting Supabase initialization for voice caching...")
    from supabase import create_client
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    print(f"📋 Environment variables check:")
    print(f"   SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'} ({supabase_url[:30]}...{supabase_url[-10:] if supabase_url else 'None'})")
    print(f"   SUPABASE_SERVICE_KEY: {'✅ Set' if supabase_key else '❌ Missing'} ({'***' + supabase_key[-10:] if supabase_key else 'None'})")
    
    if not supabase_url:
        supabase_error = "SUPABASE_URL environment variable not set"
        print(f"❌ {supabase_error}")
    elif not supabase_key:
        supabase_error = "SUPABASE_SERVICE_KEY environment variable not set"
        print(f"❌ {supabase_error}")
    else:
        print("🔄 Attempting to create Supabase client...")
        try:
            # Try simple client creation first
            supabase = create_client(supabase_url, supabase_key)
            print("✅ Supabase client created successfully")
            
            # Test the connection by attempting a simple query
            print("🧪 Testing connection with simple query...")
            try:
                test_result = supabase.table("elevenlabs_voices").select("voice_id").limit(1).execute()
                print(f"✅ Connection test successful - elevenlabs_voices table accessible")
                print(f"📊 Current voices in table: {len(test_result.data)} records")
            except Exception as connection_test_error:
                print(f"⚠️ Connection test failed: {connection_test_error}")
                error_str = str(connection_test_error).lower()
                
                if "relation \"elevenlabs_voices\" does not exist" in error_str:
                    supabase_error = "elevenlabs_voices table does not exist - migration needed"
                    print(f"💡 {supabase_error}")
                    print("   Run the migration SQL in Supabase Dashboard > SQL Editor")
                    print("   Migration file: backend/migrations/create_elevenlabs_voices_table.sql")
                    # Keep supabase client but note the table issue
                elif "http_client" in error_str or "unexpected keyword argument" in error_str:
                    print("💡 HTTP client compatibility issue detected")
                    supabase_error = f"Supabase client version compatibility issue: {connection_test_error}"
                    print(f"❌ {supabase_error}")
                    # Client created but queries fail - disable Supabase for now
                    supabase = None
                elif "permission" in error_str or "denied" in error_str:
                    print("💡 Permission issue - check service key")
                    supabase_error = f"Permission denied: {connection_test_error}"
                    supabase = None
                else:
                    supabase_error = f"Database connection issue: {connection_test_error}"
                    print(f"❌ {supabase_error}")
                    supabase = None
                    
        except TypeError as client_init_error:
            supabase_error = f"Supabase client initialization failed (version compatibility): {client_init_error}"
            print(f"❌ {supabase_error}")
            print("💡 This may be a supabase-py version compatibility issue")
            supabase = None
        except Exception as client_error:
            supabase_error = f"Supabase client creation failed: {client_error}"
            print(f"❌ {supabase_error}")
            supabase = None
            
except ImportError as import_error:
    supabase_error = f"Supabase not installed: {import_error}"
    print(f"❌ {supabase_error}")
    print("💡 Install with: pip install supabase")
except Exception as general_error:
    supabase_error = f"Unexpected Supabase initialization error: {general_error}"
    print(f"❌ {supabase_error}")

print(f"🏁 Supabase initialization complete. Status: {'✅ Available' if supabase else '❌ Not Available'}")
if supabase_error:
    print(f"🔍 Error details: {supabase_error}")
print(f"🔄 Fallback: Memory cache will be used for voice caching")

# In-memory cache as fallback when Supabase is not available
memory_voice_cache = {
    "voices": [],
    "last_updated": None,
    "cache_duration_hours": 24
}

async def ensure_voice_cache_table():
    """Ensure the voice cache table exists in Supabase"""
    if not supabase:
        return False
    
    try:
        # Test if table exists by attempting a simple query
        result = supabase.table("elevenlabs_voices").select("voice_id").limit(1).execute()
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "relation \"elevenlabs_voices\" does not exist" in error_str:
            print("⚠️ elevenlabs_voices table does not exist")
            return False
        else:
            print(f"⚠️ Error checking voice cache table: {e}")
            return False

async def get_cached_voices():
    """Get cached voices from Supabase (database-first approach, no expiration)"""
    if not supabase:
        # Try memory cache fallback
        if memory_voice_cache["voices"]:
            print(f"📦 Using memory cache with {len(memory_voice_cache['voices'])} voices")
            return memory_voice_cache["voices"]
        return None
    
    try:
        # Get all active voices from database (no expiration limit)
        result = supabase.table("elevenlabs_voices")\
            .select("*")\
            .eq("is_active", True)\
            .order("name")\
            .execute()
        
        if result.data and len(result.data) > 0:
            print(f"📦 Found {len(result.data)} cached voices in Supabase database")
            # Convert to ElevenLabsVoice format
            voices = []
            for row in result.data:
                voices.append(ElevenLabsVoice(
                    voice_id=row["voice_id"],
                    name=row["name"],
                    description=row.get("description", ""),
                    category=row.get("category", "general"),
                    labels=row.get("labels", []),
                    preview_url=row.get("preview_url"),
                    gender=row.get("gender"),
                    age=row.get("age"),
                    accent=row.get("accent"),
                    use_case=row.get("use_case")
                ))
            return voices
        else:
            print("📦 No cached voices found in database")
            return None
        
    except Exception as e:
        print(f"⚠️ Error getting cached voices from database: {e}")
        return None

async def cleanup_old_voice_cache():
    """Clean up only inactive voice cache entries (for maintenance)"""
    if not supabase:
        return
    
    try:
        # Only remove entries marked as inactive (is_active = false)
        # This preserves all active voices permanently as requested
        result = supabase.table("elevenlabs_voices")\
            .delete()\
            .eq("is_active", False)\
            .execute()
        
        if result.data and len(result.data) > 0:
            print(f"🧹 Cleaned up {len(result.data)} inactive voice cache entries")
        else:
            print("🧹 No inactive voice entries to clean up")
            
    except Exception as e:
        print(f"⚠️ Error cleaning up voice cache: {e}")

async def cache_voices_to_supabase(voices):
    """Cache voices to Supabase database"""
    if not supabase:
        # Fallback to memory cache
        memory_voice_cache["voices"] = voices
        memory_voice_cache["last_updated"] = datetime.now()
        print(f"📦 Cached {len(voices)} voices to memory")
        return
    
    try:
        # Clear existing cache first
        supabase.table("elevenlabs_voices").delete().neq("voice_id", "").execute()
        
        # Insert new voices
        voice_data = []
        for voice in voices:
            voice_data.append({
                "voice_id": voice.voice_id,
                "name": voice.name,
                "preview_url": voice.preview_url,
                "gender": voice.gender,
                "age": voice.age,
                "accent": voice.accent,
                "use_case": voice.use_case,
                "created_at": datetime.now().isoformat()
            })
        
        if voice_data:
            result = supabase.table("elevenlabs_voices").insert(voice_data).execute()
            print(f"📦 Cached {len(voice_data)} voices to Supabase")
            
            # Also update memory cache as backup
            memory_voice_cache["voices"] = voices
            memory_voice_cache["last_updated"] = datetime.now()
            
    except Exception as e:
        print(f"⚠️ Error caching voices to Supabase: {e}")
        # Fallback to memory cache
        memory_voice_cache["voices"] = voices
        memory_voice_cache["last_updated"] = datetime.now()
        print(f"📦 Fallback: Cached {len(voices)} voices to memory")

def get_mock_voices():
    """Provide mock voices for development when ElevenLabs API is unavailable"""
    mock_voices = [
        ElevenLabsVoice(
            voice_id="mock_voice_001",
            name="Sarah - Professional",
            description="Professional female voice, perfect for business content",
            category="professional",
            labels=["professional", "clear", "confident"],
            preview_url=None,
            gender="female",
            age="adult",
            accent="american",
            use_case="corporate"
        ),
        ElevenLabsVoice(
            voice_id="mock_voice_002", 
            name="David - Conversational",
            description="Friendly male voice with conversational tone",
            category="conversational",
            labels=["friendly", "warm", "engaging"],
            preview_url=None,
            gender="male",
            age="adult",
            accent="american",
            use_case="advertising"
        ),
        ElevenLabsVoice(
            voice_id="mock_voice_003",
            name="Emma - Energetic",
            description="Young energetic female voice for dynamic content",
            category="energetic",
            labels=["energetic", "youthful", "enthusiastic"],
            preview_url=None,
            gender="female",
            age="young_adult",
            accent="american",
            use_case="marketing"
        ),
        ElevenLabsVoice(
            voice_id="mock_voice_004",
            name="James - Authoritative",
            description="Deep authoritative male voice for serious content",
            category="authoritative",
            labels=["authoritative", "deep", "commanding"],
            preview_url=None,
            gender="male",
            age="middle_aged",
            accent="british",
            use_case="documentary"
        ),
        ElevenLabsVoice(
            voice_id="mock_voice_005",
            name="Lily - Gentle",
            description="Soft gentle female voice for wellness content",
            category="gentle",
            labels=["gentle", "soothing", "calm"],
            preview_url=None,
            gender="female",
            age="adult",
            accent="australian",
            use_case="wellness"
        ),
        ElevenLabsVoice(
            voice_id="mock_voice_006",
            name="Michael - News Anchor",
            description="Clear articulate male voice for news and information",
            category="news",
            labels=["clear", "articulate", "trustworthy"],
            preview_url=None,
            gender="male",
            age="adult",
            accent="american",
            use_case="news"
        )
    ]
    return mock_voices

async def fetch_elevenlabs_voices():
    """Database-first voice fetching - get from DB, fallback to API if needed"""
    # Always get fresh API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ElevenLabs API key not configured, using mock voices")
        return get_mock_voices()
    
    try:
        # Ensure database table exists
        table_exists = await ensure_voice_cache_table()
        if not table_exists:
            print("⚠️ Voice cache table not available, fetching directly from API")
        
        # Step 1: Try to get voices from database first (database-first approach)
        cached_voices = await get_cached_voices()
        if cached_voices and len(cached_voices) > 0:
            print(f"✅ Retrieved {len(cached_voices)} voices from database")
            return cached_voices[:40]  # Limit to 40 voices as requested
        
        # Step 2: If no cached voices, fetch from ElevenLabs API and store in database
        print("📥 No voices in database, fetching from ElevenLabs API...")
        
        # Clean up old cache entries periodically (optional, for maintenance)
        if table_exists:
            await cleanup_old_voice_cache()
        
        # Fetch from ElevenLabs API
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        print("🔄 Fetching fresh voices from ElevenLabs API...")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ELEVENLABS_API_URL}/voices", headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                voices_data = await response.json()
        voices = []
        current_voice_ids = []
        
        for voice_data in voices_data.get("voices", []):
            current_voice_ids.append(voice_data["voice_id"])
            
            # Generate and cache preview audio
            preview_url = None
            try:
                preview_audio = await generate_voice_preview(voice_data["voice_id"])
                if preview_audio and supabase:
                    # Store preview audio in cache
                    preview_url = f"data:audio/mpeg;base64,{base64.b64encode(preview_audio).decode()}"
            except Exception as e:
                print(f"⚠️ Failed to generate preview for voice {voice_data['voice_id']}: {e}")
            
            # Parse labels safely - handle different formats from ElevenLabs API
            labels = []
            if voice_data.get("labels"):
                label_data = voice_data["labels"]
                if isinstance(label_data, dict):
                    # If labels is a dict, try to get descriptive array
                    labels = label_data.get("descriptive", [])
                    if isinstance(labels, str):
                        labels = [labels]  # Convert single string to list
                elif isinstance(label_data, list):
                    # If labels is already a list, use it directly
                    labels = label_data
                elif isinstance(label_data, str):
                    # If labels is a single string, convert to list
                    labels = [label_data]
            
            # Parse other label properties safely
            gender = None
            age = None
            accent = None
            use_case = None
            
            if voice_data.get("labels") and isinstance(voice_data["labels"], dict):
                gender = voice_data["labels"].get("gender")
                age = voice_data["labels"].get("age") 
                accent = voice_data["labels"].get("accent")
                use_case = voice_data["labels"].get("use_case")
            
            voice = ElevenLabsVoice(
                voice_id=voice_data["voice_id"],
                name=voice_data["name"],
                description=voice_data.get("description", ""),
                category=voice_data.get("category", "general"),
                labels=labels,
                preview_url=preview_url,
                gender=gender,
                age=age,
                accent=accent,
                use_case=use_case
            )
            voices.append(voice)
            
            # Cache voice data with duplicate handling
            if supabase:
                try:
                    print(f"🔍 Caching voice: {voice.voice_id} ({voice.name})")
                    
                    # Step 1: Check if voice already exists
                    print(f"🔍 Step 1: Checking for existing voice {voice.voice_id}...")
                    existing_check = supabase.table("elevenlabs_voices")\
                        .select("voice_id, updated_at")\
                        .eq("voice_id", voice.voice_id)\
                        .execute()
                    print(f"✅ Step 1: Existence check completed, found {len(existing_check.data)} records")
                    
                    # Step 2: Prepare voice data for caching
                    print(f"🔍 Step 2: Preparing voice data for cache...")
                    voice_data_cache = {
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "description": voice.description,
                        "category": voice.category,
                        "labels": voice.labels,
                        "preview_url": preview_url,
                        "gender": voice.gender,
                        "age": voice.age,
                        "accent": voice.accent,
                        "use_case": voice.use_case,
                        "is_active": True
                    }
                    print(f"✅ Step 2: Voice data prepared with {len(voice_data_cache)} fields")
                    
                    # Step 3: Insert or update
                    if existing_check.data and len(existing_check.data) > 0:
                        print(f"🔍 Step 3: Updating existing voice {voice.voice_id}...")
                        update_result = supabase.table("elevenlabs_voices")\
                            .update(voice_data_cache)\
                            .eq("voice_id", voice.voice_id)\
                            .execute()
                        print(f"✅ Step 3: Updated voice {voice.name} - affected rows: {len(update_result.data) if update_result.data else 0}")
                    else:
                        print(f"🔍 Step 3: Inserting new voice {voice.voice_id}...")
                        insert_result = supabase.table("elevenlabs_voices")\
                            .insert(voice_data_cache)\
                            .execute()
                        print(f"✅ Step 3: Inserted voice {voice.name} - new rows: {len(insert_result.data) if insert_result.data else 0}")
                        
                except Exception as cache_error:
                    print(f"❌ Failed to cache voice {voice.voice_id}: {cache_error}")
                    print(f"🔍 Cache error type: {type(cache_error).__name__}")
                    print(f"🔍 Cache error details: {str(cache_error)}")
                    
                    # Check for specific error types
                    if "elevenlabs_voices" in str(cache_error) and "does not exist" in str(cache_error):
                        print("💡 Cache error: TABLE MISSING - Run the migration SQL")
                    elif "column" in str(cache_error).lower():
                        print("💡 Cache error: COLUMN ISSUE - Check table schema")
                    elif "duplicate" in str(cache_error).lower() or "unique" in str(cache_error).lower():
                        print("💡 Cache error: DUPLICATE KEY - This should be handled")
                    else:
                        print("💡 Cache error: UNKNOWN - Check database connection")
                    
                    # Continue processing other voices even if one fails
                    continue
        
        # Update memory cache as well
        memory_voice_cache["voices"] = voices
        memory_voice_cache["last_updated"] = datetime.now()
        print(f"💾 Updated memory cache with {len(voices)} voices")
        
        # Mark voices as inactive if they're no longer available in ElevenLabs
        if supabase and current_voice_ids:
            try:
                # Get all currently active voices in database
                db_voices = supabase.table("elevenlabs_voices")\
                    .select("voice_id")\
                    .eq("is_active", True)\
                    .execute()
                
                if db_voices.data:
                    db_voice_ids = [v["voice_id"] for v in db_voices.data]
                    inactive_voice_ids = [vid for vid in db_voice_ids if vid not in current_voice_ids]
                    
                    if inactive_voice_ids:
                        # Mark removed voices as inactive
                        for voice_id in inactive_voice_ids:
                            supabase.table("elevenlabs_voices")\
                                .update({"is_active": False})\
                                .eq("voice_id", voice_id)\
                                .execute()
                        
                        print(f"🔄 Marked {len(inactive_voice_ids)} voices as inactive")
                        
            except Exception as e:
                print(f"⚠️ Failed to cleanup inactive voices: {e}")
        
        print(f"✅ Fetched and cached {len(voices)} voices from ElevenLabs")
        return voices[:40]  # Limit to 40 voices as requested
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ElevenLabs API error: {e}")
        
        # Check if it's a permissions error and provide mock voices as fallback
        if "401" in str(e) or "missing_permissions" in str(e):
            print("🔄 API key lacks permissions, using mock voices for development")
            return get_mock_voices()
        
        raise HTTPException(status_code=503, detail="Failed to fetch voices from ElevenLabs")
    except Exception as e:
        print(f"❌ Unexpected error fetching voices: {e}")
        print("🔄 Falling back to mock voices for development")
        # Always fallback to mock voices if there's any error
        return get_mock_voices()

async def generate_voice_preview(voice_id: str, text: str = "Hello, this is a preview of my voice") -> bytes:
    """Generate voice preview using ElevenLabs TTS with timeout"""
    # Always get fresh API key
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return None
    
    try:
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)  # 10 second timeout for preview generation
            ) as response:
                response.raise_for_status()
                return await response.read()
            
    except aiohttp.ClientError:
        print(f"⚠️ Voice preview generation failed for {voice_id}")
        return None
    except asyncio.TimeoutError:
        print(f"⚠️ Voice preview generation timed out for {voice_id}")
        return None
    except Exception as e:
        print(f"⚠️ Error generating voice preview: {e}")
        return None

def get_actor_images():
    """Get actor images with descriptions"""
    actors = []
    for filename, info in ACTOR_IMAGES.items():
        actors.append(ActorImage(
            filename=filename,
            name=info["name"],
            description=info["description"],
            category=info["category"]
        ))
    return actors

@router.post("/voice-actor", response_model=VoiceActorResponse)
async def voice_actor(
    request: VoiceActorRequest,
    current_user: dict = Depends(verify_token)
):
    """Get available voices and actors for selection"""
    
    try:
        print(f"🎭 Voice actor request for thread: {request.thread_id}")
        print(f"🔒 User authenticated: {current_user}")
        
        # Fetch ElevenLabs voices (cached)
        print("🔄 Starting to fetch ElevenLabs voices...")
        voices = await fetch_elevenlabs_voices()
        print(f"✅ Retrieved {len(voices)} voices")
        
        # Get actor images
        print("🎨 Getting actor images...")
        actors = get_actor_images()
        print(f"✅ Retrieved {len(actors)} actors")
        
        print("📤 Creating response...")
        response = VoiceActorResponse(
            thread_id=request.thread_id,
            voices=voices,
            actors=actors,
            status="success"
        )
        print(f"🎉 Response created successfully for thread: {request.thread_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in voice_actor: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get voice actors: {str(e)}")

# Audio generation configuration
try:
    AUDIO_CACHE_DIR = Path(__file__).parent / "generated_audio"
    AUDIO_CACHE_DIR.mkdir(exist_ok=True)
    print(f"✅ Audio cache directory initialized: {AUDIO_CACHE_DIR}")
except Exception as e:
    print(f"⚠️ Warning: Could not initialize audio cache directory: {e}")
    # Fallback to current directory
    AUDIO_CACHE_DIR = Path.cwd() / "generated_audio"
    AUDIO_CACHE_DIR.mkdir(exist_ok=True)
    print(f"✅ Using fallback audio cache directory: {AUDIO_CACHE_DIR}")

def generate_content_hash(content: str, voice_id: str) -> str:
    """Generate a hash for content + voice combination for caching"""
    combined = f"{content}|{voice_id}"
    return hashlib.md5(combined.encode()).hexdigest()

def get_cached_audio_path(content_hash: str, audio_type: str) -> Path:
    """Get the path for cached audio file"""
    filename = f"{content_hash}_{audio_type}.mp3"
    try:
        path = AUDIO_CACHE_DIR / filename
        # Ensure the path is absolute and resolved
        path = path.resolve()
        return path
    except Exception as e:
        print(f"⚠️ Error creating cache path: {e}")
        # Return a simple Path object as fallback
        return Path(f"generated_audio/{filename}")

def get_audio_duration(file_path: Path) -> float:
    """Get audio duration in seconds using ffprobe or estimation"""
    try:
        # Try using ffprobe first (most reliable)
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            print(f"✅ Audio duration calculated: {duration:.2f} seconds")
            return duration
    except (subprocess.SubprocessError, FileNotFoundError, ValueError) as e:
        print(f"⚠️ ffprobe not available or failed: {e}")
    
    # Fallback: estimate based on file size (rough approximation for MP3)
    # Average MP3 bitrate is ~128kbps = 16KB/s
    try:
        file_size = file_path.stat().st_size
        # Rough estimate: ~16KB per second for 128kbps MP3
        estimated_duration = file_size / 16000
        duration = max(1.0, estimated_duration)  # Minimum 1 second
        print(f"⚠️ Using estimated duration based on file size: {duration:.2f} seconds")
        return duration
    except Exception as e:
        print(f"❌ Could not estimate duration: {e}")
        return 5.0  # Default fallback duration

async def generate_audio_with_elevenlabs(text: str, voice_id: str, audio_type: str, campaign_id: str = None) -> GeneratedAudio:
    """Generate audio using ElevenLabs TTS API with caching"""
    
    # Always reload API key from environment to ensure we have the latest
    api_key = os.getenv("ELEVENLABS_API_KEY")
    
    if not api_key:
        print(f"⚠️ ElevenLabs API key not configured for {audio_type}")
        raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")
    
    print(f"🔑 Using API key: ***{api_key[-8:]}")
    
    # Validate inputs
    if not text or not voice_id:
        print(f"⚠️ Invalid input for audio generation: text={bool(text)}, voice_id={bool(voice_id)}")
        raise HTTPException(status_code=400, detail="Text and voice_id are required")
    
    # Generate content hash for caching
    content_hash = generate_content_hash(text, voice_id)
    cached_audio_path = get_cached_audio_path(content_hash, audio_type)
    
    print(f"🎵 Generating {audio_type} audio for voice {voice_id}")
    print(f"📝 Content preview: {text[:50] if len(text) > 50 else text}...")
    print(f"🔍 Cache path: {cached_audio_path}")
    print(f"🔍 Cache path type: {type(cached_audio_path)}, Cache exists check...")
    
    # Check if audio is already cached
    try:
        if cached_audio_path and cached_audio_path.exists():
            print(f"✅ Using cached {audio_type} audio: {cached_audio_path.name}")
            file_size = cached_audio_path.stat().st_size
            
            # Calculate duration for cached audio
            duration = get_audio_duration(cached_audio_path)
            
            # Check if we should upload cached file to S3
            if s3_service.enabled:
                # Check if it's already on S3 by trying to upload (it will return existing URL if already there)
                s3_url = s3_service.upload_file(
                    str(cached_audio_path),
                    file_type="audio",
                    campaign_id=campaign_id or "v1"  # Use provided campaign_id or default to v1
                )
                if s3_url:
                    audio_url = s3_url
                    print(f"✅ Using S3 URL for cached audio: {s3_url}")
                else:
                    audio_url = f"/generated_audio/{cached_audio_path.name}"
            else:
                audio_url = f"/generated_audio/{cached_audio_path.name}"
            
            audio_id = f"{audio_type}_{content_hash}"
            
            return GeneratedAudio(
                audio_id=audio_id,
                type=audio_type,
                content=text,
                audio_url=audio_url,
                duration=duration,
                file_size=file_size,
                voice_settings={"voice_id": voice_id, "cached": True}
            )
    except Exception as e:
        print(f"⚠️ Error checking cached audio: {e}")
        # Continue to generate new audio if cache check fails
    
    try:
        # Prepare ElevenLabs API request
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # Common voice settings for good quality
        voice_settings = {
            "stability": 0.75,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        data = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",  # Fast, high-quality model
            "voice_settings": voice_settings
        }
        
        print(f"🔄 Calling ElevenLabs API for {audio_type}...")
        
        # Call ElevenLabs TTS API - ASYNC VERSION
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ ElevenLabs API error: {response.status}")
                    print(f"❌ Error details: {error_text}")
                    print(f"❌ Voice ID used: {voice_id}")
                    print(f"❌ API key used: ***{api_key[-8:]}")
                    
                    if response.status == 401:
                        raise HTTPException(status_code=401, detail=f"ElevenLabs authentication failed. Check API key. Voice ID: {voice_id}")
                    elif response.status == 422:
                        raise HTTPException(status_code=422, detail=f"Voice ID {voice_id} not found in your ElevenLabs account")
                    else:
                        raise HTTPException(status_code=response.status, detail=f"ElevenLabs API error: {error_text}")
                
                audio_content = await response.read()
        
        # Save audio to cache temporarily
        with open(cached_audio_path, 'wb') as f:
            f.write(audio_content)
        
        # Calculate duration for newly generated audio
        duration = get_audio_duration(cached_audio_path)
        
        file_size = len(audio_content)
        
        # Upload to S3 if available
        if s3_service.enabled:
            s3_url = s3_service.upload_file(
                str(cached_audio_path),
                file_type="audio",
                campaign_id=campaign_id or "v1"  # Use provided campaign_id or default to v1
            )
            if s3_url:
                audio_url = s3_url
                print(f"✅ Uploaded audio to S3: {s3_url}")
            else:
                # Fallback to local URL if S3 upload fails
                audio_url = f"/generated_audio/{cached_audio_path.name}"
                print(f"⚠️ S3 upload failed, using local storage")
        else:
            # Use local storage if S3 is not configured
            audio_url = f"/generated_audio/{cached_audio_path.name}"
            print(f"ℹ️ Using local storage (S3 not configured)")
        
        audio_id = f"{audio_type}_{content_hash}"
        
        print(f"✅ Generated and cached {audio_type} audio: {cached_audio_path.name} ({file_size} bytes, {duration:.2f}s)")
        
        return GeneratedAudio(
            audio_id=audio_id,
            type=audio_type,
            content=text,
            audio_url=audio_url,
            duration=duration,
            file_size=file_size,
            voice_settings={"voice_id": voice_id, **voice_settings, "cached": False}
        )
        
    except requests.RequestException as e:
        error_msg = f"Failed to generate {audio_type} audio: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error generating {audio_type} audio: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

def generate_mock_audio(text: str, voice_id: str, audio_type: str = "script") -> GeneratedAudio:
    """Generate mock audio for development when ElevenLabs fails"""
    import tempfile
    import wave
    import numpy as np
    
    # Generate content hash for consistent naming
    content_hash = generate_content_hash(text, voice_id)
    audio_filename = f"{audio_type}_{content_hash}.wav"
    audio_path = Path("generated_audio") / audio_filename
    
    print(f"🎵 Generating mock {audio_type} audio: {audio_filename}")
    print(f"📝 Content: {text[:50]}...")
    
    # Create a simple sine wave audio (like a beep)
    duration = min(len(text) * 0.1, 10.0)  # Duration based on text length, max 10 seconds
    sample_rate = 44100
    frequency = 440  # A4 note
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave_data = np.sin(frequency * 2 * np.pi * t) * 0.3  # Low volume
    
    # Convert to 16-bit PCM
    wave_data = (wave_data * 32767).astype(np.int16)
    
    # Save as WAV file
    with wave.open(str(audio_path), 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(wave_data.tobytes())
    
    file_size = audio_path.stat().st_size
    audio_url = f"/generated_audio/{audio_filename}"
    audio_id = f"{audio_type}_{content_hash}"
    
    print(f"✅ Generated mock {audio_type} audio: {audio_filename} ({file_size} bytes)")
    
    return GeneratedAudio(
        audio_id=audio_id,
        type=audio_type,
        content=text,
        audio_url=audio_url,
        duration=duration,
        file_size=file_size,
        voice_settings={"voice_id": voice_id, "mock": True}
    )

@router.post("/audio", response_model=AudioGenerationResponse)
async def generate_audio(
    request: AudioGenerationRequest,
    current_user: dict = Depends(verify_token)
):
    """Generate audio for scripts and hooks using ElevenLabs TTS"""
    
    try:
        print(f"🎵 Audio generation request for thread: {request.thread_id}")
        
        # Extract data from request
        voice_selection = request.voice_actor_selection
        selected_voice = voice_selection.get("selected_voice", {})
        selected_actor = voice_selection.get("selected_actor", {})
        
        # Get voice ID
        voice_id = selected_voice.get("voice_id")
        print(f"🔍 DEBUG: selected_voice = {selected_voice}")
        print(f"🔍 DEBUG: voice_id = {voice_id}")
        if not voice_id:
            print(f"❌ DEBUG: No voice_id found in selected_voice: {selected_voice}")
            raise HTTPException(status_code=400, detail="No voice selected")
        
        print(f"🎤 Using voice: {selected_voice.get('name', 'Unknown')} ({voice_id})")
        print(f"🎭 Using actor: {selected_actor.get('name', 'Unknown')}")
        
        # Get scripts from campaign_scripts
        campaign_scripts = request.campaign_scripts
        selected_angle = campaign_scripts.get("selected_angle", {})
        scripts = campaign_scripts.get("scripts", [])
        
        if not scripts:
            raise HTTPException(status_code=400, detail="No scripts provided")
        
        print(f"📝 Processing {len(scripts)} scripts for audio generation")
        
        # Generate audio for each script
        scripts_with_audio = []
        total_audios_generated = 0
        
        for script in scripts:
            script_id = script.get("script_id", str(uuid.uuid4()))
            hook = script.get("hook", "")
            body = script.get("body", "")
            selected = script.get("selected", False)
            
            print(f"\n📄 Processing script {script_id}:")
            print(f"   Hook: {hook[:30]}...")
            print(f"   Body: {body[:30]}...")
            
            # Combine hook and script text with natural pause
            combined_text = ""
            if hook.strip() and body.strip():
                # Add natural pause between hook and script (using comma and period)
                combined_text = f"{hook.strip()}. {body.strip()}"
            elif hook.strip():
                combined_text = hook.strip()
            elif body.strip():
                combined_text = body.strip()
            
            # Generate single combined audio
            combined_audio = None
            if combined_text.strip():
                try:
                    combined_audio = await generate_audio_with_elevenlabs(combined_text, voice_id, "combined")
                    total_audios_generated += 1
                    print(f"✅ Generated combined audio for script {script_id}")
                except Exception as e:
                    print(f"⚠️ Failed to generate combined audio for script {script_id}: {e}")
                    # Fallback to mock audio generation
                    combined_audio = generate_mock_audio(combined_text, voice_id, "combined")
                    total_audios_generated += 1
                    print(f"✅ Generated mock combined audio for script {script_id}")
            
            # Create script with combined audio
            script_with_audio = ScriptWithAudio(
                script_id=script_id,
                hook=hook,
                body=body,
                selected=selected,
                combined_audio=combined_audio
            )
            
            scripts_with_audio.append(script_with_audio)
        
        # Prepare voice info for response
        voice_info = {
            "voice": selected_voice,
            "actor": selected_actor
        }
        
        print(f"✅ Audio generation completed: {total_audios_generated} audios generated")
        
        response = AudioGenerationResponse(
            thread_id=request.thread_id,
            selected_angle=selected_angle,
            voice_info=voice_info,
            scripts_with_audio=scripts_with_audio,
            total_audios_generated=total_audios_generated,
            status="success"
        )
        
        # Debug: Log the response structure
        print(f"🔍 DEBUG Response structure:")
        print(f"   Total scripts: {len(response.scripts_with_audio)}")
        for i, script in enumerate(response.scripts_with_audio):
            print(f"   Script {i}: {script.script_id}")
            print(f"     Combined audio: {script.combined_audio is not None}")
            if script.combined_audio:
                print(f"     Combined audio URL: {script.combined_audio.audio_url}")
                print(f"     Combined text length: {len(script.combined_audio.content)} chars")
        print(f"   Total audios in response: {response.total_audios_generated}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in generate_audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate audio: {str(e)}")

# Video Generation Integration
from hedra_client import hedra_generator

@router.post("/video", response_model=VideoGenerationDetailedResponse)
async def generate_video(
    request: VideoGenerationDetailedRequest,
    current_user: dict = Depends(verify_token)
):
    """Generate videos using Hedra API for all hook+script combinations"""
    
    try:
        start_time = time.time()
        user_id = current_user["user_id"]
        thread_id = request.thread_id
        
        print(f"🎬 Video generation request for thread: {thread_id}")
        print(f"👤 User: {user_id}")
        
        if not hedra_generator:
            raise HTTPException(
                status_code=500, 
                detail="Hedra API not configured. Please check HEDRA_API_KEY."
            )
        
        # Extract audio data and actor info
        audio_data = request.audio_data
        actor_image_filename = request.actor_image
        video_settings = request.video_settings or {}
        
        print(f"🎭 Actor image: {actor_image_filename}")
        print(f"🎵 Scripts with audio: {len(audio_data.get('scripts_with_audio', []))}")

        # Get actor image path (handles both dev and production environments)
        try:
            actor_image_path = await actor_image_handler.get_actor_image_path(actor_image_filename)
            print(f"✅ Actor image retrieved: {actor_image_path}")
        except Exception as e:
            print(f"❌ Failed to get actor image: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Actor image not available: {actor_image_filename}"
            )

        # Generate videos using Hedra
        generated_videos_data = await hedra_generator.generate_videos_for_thread(
            thread_id=thread_id,
            audio_data=audio_data,
            actor_image_path=str(actor_image_path)
        )
        
        # Convert to response format
        generated_videos = []
        for video_data in generated_videos_data:
            video = GeneratedVideo(
                video_id=f"{thread_id}_{video_data.get('script_id', 'unknown')}_{video_data.get('video_type', 'combined')}",
                script_id=video_data.get('script_id', ''),
                video_type=video_data.get('video_type', 'combined'),
                hook_text=video_data.get('hook_text', ''),
                script_text=video_data.get('script_text', ''),
                combined_text=video_data.get('combined_text', ''),
                video_url=video_data.get('video_url', ''),
                local_path=video_data.get('local_path'),
                hedra_job_id=video_data.get('hedra_job_id'),
                duration=video_data.get('duration'),
                aspect_ratio=video_settings.get('aspect_ratio', '9:16'),
                quality=video_settings.get('quality', 'low'),
                status=video_data.get('status', 'completed'),
                error=video_data.get('error'),
                created_at=datetime.now().isoformat()
            )
            generated_videos.append(video)
        
        processing_time = time.time() - start_time
        
        print(f"✅ Video generation completed in {processing_time:.2f} seconds")
        print(f"📹 Generated {len(generated_videos)} videos")
        
        return VideoGenerationDetailedResponse(
            thread_id=thread_id,
            actor_info={
                "image": actor_image_filename,
                "path": str(actor_image_path)
            },
            generated_videos=generated_videos,
            total_videos_generated=len(generated_videos),
            processing_time=processing_time,
            status="success"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in generate_video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate video: {str(e)}")

# Static file serving for generated videos
from fastapi.staticfiles import StaticFiles

# NOTE: The audio static file mounting should be done in main.py:
# app.mount("/generated_audio", StaticFiles(directory=AUDIO_CACHE_DIR), name="generated_audio")
