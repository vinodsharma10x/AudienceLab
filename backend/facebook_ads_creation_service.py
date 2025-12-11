# Facebook Ads Creation Service for Sucana v4
import os
import asyncio
import aiohttp
import aiofiles
import boto3
import logging
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.adobjects.adimage import AdImage
from facebook_business.exceptions import FacebookRequestError

from facebook_ad_creation_models import (
    CampaignCreateRequest, AdSetCreateRequest, CreativeCreateRequest,
    AdCreateRequest, VideoAdCreateRequest, VideoAdCreationResponse,
    TargetingSpec, CampaignObjective, OptimizationGoal, AdStatus,
    TestStructure, VideoAdSelection
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FacebookAdsCreationService:
    """Service for creating Facebook ads programmatically"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.s3_client = boto3.client('s3')
        logger.info("✅ Facebook Ads Creation Service initialized")
    
    def init_api(self, access_token: str):
        """Initialize Facebook Ads API with access token"""
        FacebookAdsApi.init(self.app_id, self.app_secret, access_token)
    
    # ==================== Video Upload Methods ====================
    
    async def upload_video_to_facebook(
        self,
        s3_url: str,
        ad_account_id: str,
        video_title: str,
        access_token: str
    ) -> Tuple[str, str]:
        """
        Upload video from S3 or direct URL to Facebook with retry logic for transient errors
        Returns: (video_id, video_url)
        """
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                self.init_api(access_token)

                # Ensure ad_account_id has correct format
                if not ad_account_id.startswith('act_'):
                    ad_account_id = f'act_{ad_account_id}'

                # Download video to temp file
                if s3_url.startswith('s3://') or 's3.amazonaws.com' in s3_url:
                    # Download from S3
                    temp_video_path = await self._download_from_s3(s3_url)
                else:
                    # Download from direct URL
                    temp_video_path = await self._download_from_url(s3_url)

                try:
                    # Upload to Facebook
                    video = AdVideo(parent_id=ad_account_id)
                    video[AdVideo.Field.filepath] = temp_video_path
                    video[AdVideo.Field.title] = video_title
                    video[AdVideo.Field.description] = f"Video for {video_title}"

                    # Start upload (async process)
                    video.remote_create()
                    video_id = video['id']

                    logger.info(f"✅ Video upload initiated: {video_id}")

                    # Wait for video to be ready (Facebook processes async)
                    video_url = await self._wait_for_video_ready(video_id, access_token)

                    return video_id, video_url

                finally:
                    # Clean up temp file
                    if os.path.exists(temp_video_path):
                        os.remove(temp_video_path)

            except FacebookRequestError as e:
                # Check if it's a transient error that we should retry
                if hasattr(e, 'api_error_code') and e.api_error_code() in [2, 1, 17]:  # Common transient error codes
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Transient Facebook error (attempt {attempt + 1}/{max_retries}): {e}")
                        logger.info(f"⏳ Waiting {retry_delay} seconds before retry...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error(f"❌ Max retries exceeded for video upload: {e}")
                        raise
                else:
                    # Non-transient error, don't retry
                    logger.error(f"❌ Non-transient Facebook error uploading video: {e}")
                    raise

            except Exception as e:
                logger.error(f"❌ Error uploading video to Facebook: {e}")
                raise
    
    async def _download_from_s3(self, s3_url: str) -> str:
        """Download video from S3 to temporary file"""
        try:
            # Parse S3 URL to get bucket and key
            # Format: https://bucket.s3.region.amazonaws.com/key or s3://bucket/key
            if s3_url.startswith('s3://'):
                parts = s3_url[5:].split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ''
            else:
                # Parse HTTPS URL
                import urllib.parse
                parsed = urllib.parse.urlparse(s3_url)
                bucket = parsed.netloc.split('.')[0]
                key = parsed.path.lstrip('/')

            # Create temp file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"fb_video_{uuid.uuid4()}.mp4")

            # Download from S3
            logger.info(f"📥 Downloading from S3: bucket={bucket}, key={key}")
            self.s3_client.download_file(bucket, key, temp_file)

            return temp_file

        except Exception as e:
            logger.error(f"❌ Error downloading from S3: {e}")
            raise

    async def _download_from_url(self, url: str) -> str:
        """Download video from direct URL to temporary file"""
        try:
            # Create temp file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"fb_video_{uuid.uuid4()}.mp4")

            # Download video
            logger.info(f"📥 Downloading video from URL: {url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()

                    # Write to temp file
                    async with aiofiles.open(temp_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)

            logger.info(f"✅ Downloaded video to: {temp_file}")
            return temp_file

        except Exception as e:
            logger.error(f"❌ Error downloading from URL: {e}")
            raise
    
    async def _wait_for_video_ready(
        self,
        video_id: str,
        access_token: str,
        max_wait: int = 300,
        check_interval: int = 10
    ) -> str:
        """Wait for Facebook to finish processing video"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < max_wait:
            try:
                # Check video status
                async with aiohttp.ClientSession() as session:
                    url = f"https://graph.facebook.com/v18.0/{video_id}"
                    params = {
                        'fields': 'status,source,thumbnails',
                        'access_token': access_token
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            status = data.get('status', {})
                            
                            if status.get('video_status') == 'ready':
                                logger.info(f"✅ Video {video_id} is ready")
                                return data.get('source', '')
                            elif status.get('video_status') == 'error':
                                error_msg = status.get('error_message', 'Unknown error')
                                raise Exception(f"Video processing failed: {error_msg}")
                            else:
                                logger.info(f"⏳ Video {video_id} status: {status.get('video_status', 'processing')}")
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error checking video status: {e}")
                await asyncio.sleep(check_interval)
        
        raise TimeoutError(f"Video {video_id} processing timeout after {max_wait} seconds")
    
    # ==================== Campaign Creation Methods ====================
    
    async def create_campaign(
        self,
        request: CampaignCreateRequest,
        ad_account_id: str,
        access_token: str
    ) -> Dict[str, Any]:
        """Create a new Facebook campaign"""
        try:
            self.init_api(access_token)
            
            if not ad_account_id.startswith('act_'):
                ad_account_id = f'act_{ad_account_id}'
            
            ad_account = AdAccount(ad_account_id)
            
            params = {
                Campaign.Field.name: request.name,
                Campaign.Field.objective: request.objective.value,
                Campaign.Field.status: request.status.value,
                Campaign.Field.special_ad_categories: request.special_ad_categories,
            }
            
            if request.spend_cap:
                params[Campaign.Field.spend_cap] = request.spend_cap
            
            if request.daily_spend_cap:
                params[Campaign.Field.daily_spend_cap] = request.daily_spend_cap
            
            campaign = ad_account.create_campaign(params=params)

            logger.info(f"✅ Campaign created: {campaign['id']} - {request.name}")

            return {
                'id': campaign['id'],
                'name': campaign.get('name', request.name),  # Use FB response or fallback to request
                'objective': campaign.get('objective', request.objective.value),
                'status': campaign.get('status', request.status.value)
            }
            
        except FacebookRequestError as e:
            logger.error(f"❌ Facebook API error creating campaign: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error creating campaign: {e}")
            raise
    
    # ==================== Ad Set Creation Methods ====================
    
    async def create_adset(
        self,
        campaign_id: str,
        targeting: TargetingSpec,
        budget: int,
        optimization_goal: OptimizationGoal,
        ad_account_id: str,
        access_token: str,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new ad set"""
        try:
            self.init_api(access_token)
            
            if not ad_account_id.startswith('act_'):
                ad_account_id = f'act_{ad_account_id}'
            
            ad_account = AdAccount(ad_account_id)
            
            # Build targeting spec
            targeting_spec = self._build_targeting_spec(targeting)
            
            params = {
                AdSet.Field.name: name or f"AdSet - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                AdSet.Field.campaign_id: campaign_id,
                AdSet.Field.daily_budget: budget,
                AdSet.Field.billing_event: 'IMPRESSIONS',
                AdSet.Field.optimization_goal: optimization_goal.value,
                AdSet.Field.bid_strategy: 'LOWEST_COST_WITHOUT_CAP',  # Use automatic bidding
                AdSet.Field.targeting: targeting_spec,
                AdSet.Field.status: 'PAUSED',
                AdSet.Field.start_time: datetime.now().isoformat(),
            }
            
            adset = ad_account.create_ad_set(params=params)
            
            logger.info(f"✅ Ad Set created: {adset['id']}")
            
            return {
                'id': adset['id'],
                'name': adset.get('name', name or f"AdSet - {datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                'campaign_id': adset.get('campaign_id', campaign_id),
                'status': adset.get('status', 'PAUSED')
            }
            
        except FacebookRequestError as e:
            logger.error(f"❌ Facebook API error creating ad set: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error creating ad set: {e}")
            raise
    
    def _build_targeting_spec(self, targeting: TargetingSpec) -> Dict[str, Any]:
        """Build Facebook targeting specification from our model"""
        spec = {
            'geo_locations': {
                'countries': targeting.geo_locations.countries or ['US']
            },
            'age_min': targeting.age_min,
            'age_max': targeting.age_max,
        }
        
        if targeting.genders:
            spec['genders'] = targeting.genders
        
        if targeting.detailed_targeting:
            detailed = {}
            if targeting.detailed_targeting.interests:
                detailed['interests'] = targeting.detailed_targeting.interests
            if targeting.detailed_targeting.behaviors:
                detailed['behaviors'] = targeting.detailed_targeting.behaviors
            if detailed:
                spec['flexible_spec'] = [detailed]
        
        if targeting.device_platforms:
            spec['device_platforms'] = targeting.device_platforms
        
        if targeting.publisher_platforms:
            spec['publisher_platforms'] = targeting.publisher_platforms
        else:
            # Default to Facebook and Instagram
            spec['publisher_platforms'] = ['facebook', 'instagram']
        
        if targeting.facebook_positions:
            spec['facebook_positions'] = targeting.facebook_positions
        
        if targeting.instagram_positions:
            spec['instagram_positions'] = targeting.instagram_positions
        
        return spec
    
    # ==================== Creative Creation Methods ====================
    
    async def create_video_creative(
        self,
        video_id: str,
        page_id: str,
        message: str,
        headline: str,
        cta_type: str,
        link_url: str,
        thumbnail_url: Optional[str],
        ad_account_id: str,
        access_token: str
    ) -> str:
        """Create ad creative with video"""
        try:
            self.init_api(access_token)
            
            if not ad_account_id.startswith('act_'):
                ad_account_id = f'act_{ad_account_id}'
            
            creative = AdCreative(parent_id=ad_account_id)
            creative[AdCreative.Field.name] = f"Creative - {headline[:50]}"
            
            # Build object story spec
            video_data = {
                'video_id': video_id,
                'message': message,
                'title': headline,
                'call_to_action': {
                    'type': cta_type,
                    'value': {
                        'link': link_url
                    }
                }
            }

            # Add image_url (required for video ads)
            # Facebook requires either image_url or image_hash for video thumbnails
            if thumbnail_url and thumbnail_url.strip():
                # Use provided thumbnail if available
                video_data['image_url'] = thumbnail_url
                logger.info(f"Using provided thumbnail: {thumbnail_url[:50]}...")
            else:
                # Use the placeholder image from S3
                logger.info("No thumbnail URL provided, using placeholder from S3")
                video_data['image_url'] = 'https://sucana-media.s3.us-east-2.amazonaws.com/videos/placeholder-thumbnail.png'
                # Alternative: Use the Facebook image hash (faster, no download needed)
                # video_data['image_hash'] = '2670785663276631'  # Your uploaded image ID

            object_story_spec = {
                'page_id': page_id,
                'video_data': video_data
            }
            
            creative[AdCreative.Field.object_story_spec] = object_story_spec
            creative.remote_create()
            
            logger.info(f"✅ Creative created: {creative['id']}")
            
            return creative['id']
            
        except FacebookRequestError as e:
            logger.error(f"❌ Facebook API error creating creative: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error creating creative: {e}")
            raise
    
    # ==================== Ad Creation Methods ====================
    
    async def create_ad(
        self,
        adset_id: str,
        creative_id: str,
        name: str,
        ad_account_id: str,
        access_token: str,
        status: str = 'PAUSED'
    ) -> Dict[str, Any]:
        """Create an ad"""
        try:
            self.init_api(access_token)
            
            if not ad_account_id.startswith('act_'):
                ad_account_id = f'act_{ad_account_id}'
            
            ad_account = AdAccount(ad_account_id)
            
            params = {
                Ad.Field.name: name,
                Ad.Field.adset_id: adset_id,
                Ad.Field.creative: {'creative_id': creative_id},
                Ad.Field.status: status,
            }
            
            ad = ad_account.create_ad(params=params)
            
            logger.info(f"✅ Ad created: {ad['id']} - {name}")
            
            return {
                'id': ad['id'],
                'name': ad.get('name', name),  # Use the name parameter as fallback
                'adset_id': ad.get('adset_id', adset_id),
                'creative_id': ad.get('creative_id', creative_id),
                'status': ad.get('status', status)
            }
            
        except FacebookRequestError as e:
            logger.error(f"❌ Facebook API error creating ad: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error creating ad: {e}")
            raise
    
    # ==================== Main Video Ad Creation Flow ====================
    
    async def create_ads_from_videos(
        self,
        request: VideoAdCreateRequest,
        ad_account_id: str,
        page_id: str,
        access_token: str
    ) -> VideoAdCreationResponse:
        """
        Main method to create Facebook ads from video selections
        """
        try:
            errors = []
            warnings = []
            ads_created = []
            video_upload_status = {}
            
            # Step 1: Upload all videos to Facebook
            logger.info(f"📤 Uploading {len(request.video_ad_selections)} videos to Facebook")
            
            video_uploads = {}
            for video_selection in request.video_ad_selections:
                try:
                    video_id, video_url = await self.upload_video_to_facebook(
                        s3_url=video_selection.video_url,
                        ad_account_id=ad_account_id,
                        video_title=f"{video_selection.hook[:50]}",
                        access_token=access_token
                    )
                    video_uploads[video_selection.video_ad_id] = {
                        'facebook_video_id': video_id,
                        'facebook_video_url': video_url,
                        'status': 'ready'
                    }
                    video_upload_status[video_selection.video_ad_id] = 'ready'
                except Exception as e:
                    logger.error(f"Failed to upload video {video_selection.video_ad_id}: {e}")
                    errors.append(f"Video upload failed for {video_selection.video_ad_id}: {str(e)}")
                    video_upload_status[video_selection.video_ad_id] = 'failed'
                    continue
            
            if not video_uploads:
                return VideoAdCreationResponse(
                    success=False,
                    campaign_id='',
                    adset_id='',
                    ads_created=[],
                    video_upload_status=video_upload_status,
                    errors=errors
                )
            
            # Step 2: Handle campaign creation/selection
            if request.campaign_strategy == 'new':
                logger.info("🎯 Creating new campaign")
                campaign_result = await self.create_campaign(
                    request=request.new_campaign_settings,
                    ad_account_id=ad_account_id,
                    access_token=access_token
                )
                campaign_id = campaign_result['id']
            else:
                campaign_id = request.existing_campaign_id
                logger.info(f"📌 Using existing campaign: {campaign_id}")
            
            # Step 3: Handle ad set creation/selection
            if request.adset_strategy == 'new':
                logger.info("📊 Creating new ad set")
                
                # Use provided targeting or create default
                if request.targeting:
                    targeting = request.targeting
                else:
                    # Create smart default based on video content
                    from facebook_ad_creation_models import GeoLocation
                    targeting = TargetingSpec(
                        geo_locations=GeoLocation(countries=['US']),
                        age_min=25,
                        age_max=55
                    )
                
                adset_result = await self.create_adset(
                    campaign_id=campaign_id,
                    targeting=targeting,
                    budget=request.daily_budget or 2000,  # Default $20
                    optimization_goal=OptimizationGoal.LINK_CLICKS,
                    ad_account_id=ad_account_id,
                    access_token=access_token,
                    name=f"AdSet - {datetime.now().strftime('%Y%m%d')}"
                )
                adset_id = adset_result['id']
            else:
                adset_id = request.existing_adset_id
                logger.info(f"📌 Using existing ad set: {adset_id}")
            
            # Step 4: Create ads based on test structure
            if request.test_structure == TestStructure.SPLIT_TEST:
                logger.info("🔬 Creating split test structure")
                # TODO: Implement split test creation
                warnings.append("Split test structure not yet implemented, creating individual ads instead")
            
            # Create individual ads for each video
            for video_selection in request.video_ad_selections:
                if video_selection.video_ad_id not in video_uploads:
                    continue  # Skip videos that failed to upload
                
                try:
                    upload_info = video_uploads[video_selection.video_ad_id]
                    
                    # Create creative
                    creative_id = await self.create_video_creative(
                        video_id=upload_info['facebook_video_id'],
                        page_id=page_id,
                        message=video_selection.script,
                        headline=video_selection.hook,
                        cta_type=self._map_cta_type(video_selection.cta_text),
                        link_url=video_selection.landing_url or '',
                        thumbnail_url=video_selection.thumbnail_url,
                        ad_account_id=ad_account_id,
                        access_token=access_token
                    )
                    
                    # Generate ad name
                    if request.auto_generate_names:
                        ad_name = f"{video_selection.angle_type.title()} - {video_selection.hook[:30]}"
                    else:
                        ad_name = f"Ad - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    # Create ad
                    ad_result = await self.create_ad(
                        adset_id=adset_id,
                        creative_id=creative_id,
                        name=ad_name,
                        ad_account_id=ad_account_id,
                        access_token=access_token,
                        status='PAUSED' if request.start_ads_paused else 'ACTIVE'
                    )
                    
                    ads_created.append({
                        'video_ad_id': video_selection.video_ad_id,
                        'facebook_ad_id': ad_result['id'],
                        'facebook_creative_id': creative_id,
                        'facebook_video_id': upload_info['facebook_video_id'],
                        'name': ad_name,
                        'status': ad_result['status']
                    })
                    
                    logger.info(f"✅ Ad created successfully: {ad_result['id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to create ad for video {video_selection.video_ad_id}: {e}")
                    errors.append(f"Ad creation failed for {video_selection.video_ad_id}: {str(e)}")
            
            # Generate preview URLs
            preview_urls = []
            for ad in ads_created:
                preview_url = f"https://www.facebook.com/ads/manager/summary/?act={ad_account_id.replace('act_', '')}&selected_ad_ids={ad['facebook_ad_id']}"
                preview_urls.append(preview_url)
            
            return VideoAdCreationResponse(
                success=len(ads_created) > 0,
                campaign_id=campaign_id,
                adset_id=adset_id,
                ads_created=ads_created,
                video_upload_status=video_upload_status,
                errors=errors if errors else None,
                warnings=warnings if warnings else None,
                preview_urls=preview_urls
            )
            
        except Exception as e:
            logger.error(f"❌ Error in create_ads_from_videos: {e}")
            return VideoAdCreationResponse(
                success=False,
                campaign_id='',
                adset_id='',
                ads_created=[],
                video_upload_status={},
                errors=[str(e)]
            )
    
    def _map_cta_type(self, cta_text: Optional[str]) -> str:
        """Map CTA text to Facebook CTA type"""
        if not cta_text:
            return 'LEARN_MORE'
        
        cta_lower = cta_text.lower()
        
        mapping = {
            'learn': 'LEARN_MORE',
            'shop': 'SHOP_NOW',
            'buy': 'SHOP_NOW',
            'sign': 'SIGN_UP',
            'register': 'SIGN_UP',
            'download': 'DOWNLOAD',
            'book': 'BOOK_NOW',
            'schedule': 'BOOK_NOW',
            'contact': 'CONTACT_US',
            'apply': 'APPLY_NOW',
            'get': 'GET_OFFER',
            'watch': 'WATCH_MORE'
        }
        
        for key, value in mapping.items():
            if key in cta_lower:
                return value
        
        return 'LEARN_MORE'
    
    # ==================== Helper Methods ====================
    
    async def get_existing_campaigns(
        self,
        ad_account_id: str,
        access_token: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of existing campaigns"""
        try:
            self.init_api(access_token)
            
            if not ad_account_id.startswith('act_'):
                ad_account_id = f'act_{ad_account_id}'
            
            ad_account = AdAccount(ad_account_id)
            campaigns = ad_account.get_campaigns(
                fields=[
                    Campaign.Field.id,
                    Campaign.Field.name,
                    Campaign.Field.objective,
                    Campaign.Field.status,
                    Campaign.Field.created_time
                ],
                params={'limit': limit}
            )
            
            return [
                {
                    'id': c['id'],
                    'name': c['name'],
                    'objective': c['objective'],
                    'status': c['status'],
                    'created_time': c['created_time']
                }
                for c in campaigns
            ]
            
        except Exception as e:
            logger.error(f"Error getting campaigns: {e}")
            return []
    
    async def get_existing_adsets(
        self,
        campaign_id: str,
        access_token: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get list of existing ad sets for a campaign"""
        try:
            self.init_api(access_token)
            
            campaign = Campaign(campaign_id)
            adsets = campaign.get_ad_sets(
                fields=[
                    AdSet.Field.id,
                    AdSet.Field.name,
                    AdSet.Field.status,
                    AdSet.Field.daily_budget,
                    AdSet.Field.lifetime_budget,
                    AdSet.Field.created_time
                ],
                params={'limit': limit}
            )
            
            return [
                {
                    'id': a['id'],
                    'name': a['name'],
                    'status': a['status'],
                    'daily_budget': a.get('daily_budget'),
                    'lifetime_budget': a.get('lifetime_budget'),
                    'created_time': a['created_time']
                }
                for a in adsets
            ]
            
        except Exception as e:
            logger.error(f"Error getting ad sets: {e}")
            return []