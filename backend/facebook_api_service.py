# Facebook Marketing API Service for Sucana v4
import os
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.user import User
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.exceptions import FacebookRequestError
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FacebookAPIService:
    """Service for interacting with Facebook Marketing API"""
    
    def __init__(self):
        self.app_id = os.getenv("FACEBOOK_APP_ID")
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET")
        self.redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:3000/facebook/connect")
        
        # Encryption key for storing access tokens
        encryption_key_str = os.getenv("ENCRYPTION_KEY")
        if not encryption_key_str:
            # Generate a key for development (in production, use a fixed key)
            self.encryption_key = Fernet.generate_key()
            logger.warning("⚠️ No ENCRYPTION_KEY found, generating new key for development")
            logger.info(f"Generated ENCRYPTION_KEY: {self.encryption_key.decode()}")
        else:
            # Ensure the key is properly encoded as bytes
            self.encryption_key = encryption_key_str.encode() if isinstance(encryption_key_str, str) else encryption_key_str
        
        self.fernet = Fernet(self.encryption_key)
        
        if not all([self.app_id, self.app_secret]):
            raise ValueError("Facebook App ID and App Secret must be set in environment variables")
        
        logger.info("✅ Facebook API Service initialized")
    
    def get_auth_url(self, state: Optional[str] = None) -> str:
        """Generate Facebook OAuth authorization URL"""
        # Using all permissions - classic app has all permissions
        permissions = [
            "email",
            "public_profile",
            "ads_read",
            "business_management", 
            "read_insights"
        ]
        
        auth_url = (
            f"https://www.facebook.com/v23.0/dialog/oauth?"
            f"client_id={self.app_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={','.join(permissions)}&"
            f"response_type=code"
        )
        
        if state:
            auth_url += f"&state={state}"
        
        return auth_url
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        async with aiohttp.ClientSession() as session:
            token_url = "https://graph.facebook.com/v23.0/oauth/access_token"
            params = {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": self.redirect_uri,
                "code": code
            }
            
            async with session.get(token_url, params=params) as response:
                if response.status != 200:
                    error_data = await response.json()
                    logger.error(f"❌ Token exchange failed: {error_data}")
                    raise Exception(f"Token exchange failed: {error_data}")
                
                token_data = await response.json()
                logger.info("✅ Successfully exchanged code for access token")
                return token_data
    
    async def get_long_lived_token(self, short_token: str) -> Dict[str, Any]:
        """Exchange short-lived token for long-lived token"""
        async with aiohttp.ClientSession() as session:
            token_url = "https://graph.facebook.com/v23.0/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": short_token
            }
            
            async with session.get(token_url, params=params) as response:
                if response.status != 200:
                    error_data = await response.json()
                    logger.error(f"❌ Long-lived token exchange failed: {error_data}")
                    raise Exception(f"Long-lived token exchange failed: {error_data}")
                
                token_data = await response.json()
                logger.info("✅ Successfully got long-lived access token")
                return token_data
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Facebook user information"""
        async with aiohttp.ClientSession() as session:
            user_url = "https://graph.facebook.com/v23.0/me"
            params = {
                "access_token": access_token,
                "fields": "id,name,email"
            }
            
            async with session.get(user_url, params=params) as response:
                if response.status != 200:
                    error_data = await response.json()
                    logger.error(f"❌ User info fetch failed: {error_data}")
                    raise Exception(f"User info fetch failed: {error_data}")
                
                user_data = await response.json()
                logger.info(f"✅ Successfully fetched user info for: {user_data.get('name')}")
                return user_data
    
    async def get_ad_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get all ad accounts accessible to the user"""
        try:
            # Initialize Facebook Ads API
            FacebookAdsApi.init(self.app_id, self.app_secret, access_token)
            
            # Get user and their ad accounts
            user = User(fbid='me')
            ad_accounts = user.get_ad_accounts(fields=[
                'id',
                'name',
                'currency',
                'timezone_name',
                'account_status',
                'business',
                'amount_spent',
                'balance'
            ])
            
            accounts_list = []
            for account in ad_accounts:
                accounts_list.append({
                    'id': account['id'],
                    'name': account.get('name', 'Unnamed Account'),
                    'currency': account.get('currency', 'USD'),
                    'timezone_name': account.get('timezone_name', 'UTC'),
                    'account_status': account.get('account_status', 1),
                    'business': account.get('business', {}),
                    'amount_spent': account.get('amount_spent', '0'),
                    'balance': account.get('balance', '0')
                })
            
            logger.info(f"✅ Successfully fetched {len(accounts_list)} ad accounts")
            return accounts_list
            
        except FacebookRequestError as e:
            logger.error(f"❌ Facebook API error getting ad accounts: {e}")
            raise Exception(f"Facebook API error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error getting ad accounts: {e}")
            raise
    
    async def get_ad_performance_data(
        self, 
        access_token: str, 
        ad_account_id: str,
        date_from: str,
        date_to: str,
        facebook_account_id: str,
        level: str = "ad"  # campaign, adset, or ad
    ) -> List[Dict[str, Any]]:
        """
        Fetch ad performance data from Facebook Marketing API
        
        Args:
            access_token: Facebook access token
            ad_account_id: Facebook ad account ID (format: act_XXXXXXXXX)
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            level: Reporting level (campaign, adset, or ad)
        """
        try:
            # Initialize Facebook Ads API
            FacebookAdsApi.init(self.app_id, self.app_secret, access_token)
            
            # Ensure ad_account_id has the correct format
            if not ad_account_id.startswith('act_'):
                ad_account_id = f'act_{ad_account_id}'
            
            ad_account = AdAccount(ad_account_id)
            
            # Define the fields we want to fetch (only valid Facebook API fields)
            fields = [
                'campaign_name',
                'campaign_id',
                'adset_name', 
                'adset_id',
                'ad_name',
                'ad_id',
                'cpm',
                'reach',
                'impressions',
                'frequency',
                'clicks',
                'cpc',
                'ctr',
                'video_p50_watched_actions',
                'video_p95_watched_actions',
                'actions',  # This includes leads, purchases, etc.
                'cost_per_action_type',
                'action_values',
                'spend',
                'date_start',
                'date_stop'
            ]
            
            # Set up parameters
            params = {
                'time_range': {
                    'since': date_from,
                    'until': date_to
                },
                'level': level,
                'limit': 1000  # Maximum allowed
            }
            
            # Get insights
            insights = ad_account.get_insights(
                fields=fields,
                params=params
            )
            
            performance_data = []
            for insight in insights:
                # Process actions data to extract specific metrics
                actions_data = insight.get('actions', [])
                cost_per_action_data = insight.get('cost_per_action_type', [])
                action_values_data = insight.get('action_values', [])
                
                # Extract specific action metrics
                leads = self._extract_action_value(actions_data, 'lead')
                landing_page_views = self._extract_action_value(actions_data, 'landing_page_view')
                scheduled_actions = self._extract_action_value(actions_data, 'schedule')
                purchases = self._extract_action_value(actions_data, 'purchase')
                
                # Extract cost per action metrics
                cost_per_lead = self._extract_action_value(cost_per_action_data, 'lead')
                cost_per_landing_page_view = self._extract_action_value(cost_per_action_data, 'landing_page_view')
                cost_per_scheduled_action = self._extract_action_value(cost_per_action_data, 'schedule')
                
                # Extract action values (like purchase value)
                purchase_value = self._extract_action_value(action_values_data, 'purchase')
                
                record = {
                    # REQUIRED: Add the IDs to prevent null constraint violations
                    'facebook_account_id': facebook_account_id,
                    'ad_account_id': ad_account_id.replace('act_', ''),  # Remove 'act_' prefix for storage
                    'campaign_id': insight.get('campaign_id'),
                    'campaign_name': insight.get('campaign_name'),
                    'adset_id': insight.get('adset_id'),
                    'adset_name': insight.get('adset_name'),
                    'ad_id': insight.get('ad_id'),
                    'ad_name': insight.get('ad_name'),
                    'date_start': insight.get('date_start'),
                    'date_stop': insight.get('date_stop'),
                    
                    # Basic metrics
                    'delivery_info': None,  # Not available in current API
                    'spend': float(insight.get('spend', 0)),
                    'impressions': self._safe_int(insight.get('impressions', 0)),
                    'reach': self._safe_int(insight.get('reach', 0)),
                    'frequency': float(insight.get('frequency', 0)),
                    
                    # Cost metrics
                    'cpm': float(insight.get('cpm', 0)),
                    'cpc': float(insight.get('cpc', 0)),
                    'ctr': float(insight.get('ctr', 0)),
                    
                    # Click metrics
                    'clicks': self._safe_int(insight.get('clicks', 0)),
                    'outbound_clicks_unique': 0,  # Not available in current API
                    'outbound_clicks_cpc_unique': 0.0,  # Not available in current API
                    'outbound_clicks_ctr_unique': 0.0,  # Not available in current API
                    
                    # Video metrics
                    'video_3s_views': 0,  # Not available in current API
                    'video_p50_watched_actions': self._safe_int(insight.get('video_p50_watched_actions', 0)),
                    'video_p95_watched_actions': self._safe_int(insight.get('video_p95_watched_actions', 0)),
                    
                    # Conversion metrics - use safe int conversion
                    'leads': self._safe_int(leads) if leads is not None else 0,
                    'landing_page_views': self._safe_int(landing_page_views) if landing_page_views is not None else 0,
                    'cost_per_landing_page_view': float(cost_per_landing_page_view) if cost_per_landing_page_view is not None else None,
                    'cost_per_lead': float(cost_per_lead) if cost_per_lead is not None else None,
                    'scheduled_actions': self._safe_int(scheduled_actions) if scheduled_actions is not None else 0,
                    'cost_per_scheduled_action': float(cost_per_scheduled_action) if cost_per_scheduled_action is not None else None,
                    'purchases': self._safe_int(purchases) if purchases is not None else 0,
                    'purchase_value': float(purchase_value) if purchase_value is not None else None,
                    
                    # Store raw data for debugging
                    'raw_data': dict(insight)
                }
                
                performance_data.append(record)
            
            logger.info(f"✅ Successfully fetched {len(performance_data)} performance records for account {ad_account_id}")
            
            if len(performance_data) == 0:
                logger.warning(f"⚠️ No performance data found for account {ad_account_id} in date range {date_from} to {date_to}")
                logger.info(f"💡 This could mean: 1) No ads ran in this period, 2) Account has no spend, or 3) Different date format needed")
            else:
                logger.info(f"📊 Sample record keys: {list(performance_data[0].keys()) if performance_data else 'None'}")
            
            return performance_data
            
        except FacebookRequestError as e:
            logger.error(f"❌ Facebook API error getting performance data: {e}")
            raise Exception(f"Facebook API error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error getting performance data: {e}")
            raise
    
    def _extract_action_value(self, actions_list: List[Dict], action_type: str) -> Optional[float]:
        """Extract specific action value from Facebook actions array"""
        for action in actions_list:
            if action.get('action_type') == action_type:
                return float(action.get('value', 0))
        return None
    
    def _safe_int(self, value) -> int:
        """Safely convert value to int, handling lists and other types"""
        try:
            if isinstance(value, list):
                return len(value)  # Convert list to count
            elif isinstance(value, (int, float)):
                return int(value)
            elif isinstance(value, str):
                return int(float(value))  # Handle string numbers
            else:
                return 0
        except (ValueError, TypeError):
            return 0
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt access token for secure storage"""
        try:
            if not token:
                raise ValueError("Token cannot be empty")
            encrypted_bytes = self.fernet.encrypt(token.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Error encrypting token: {e}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt access token from storage"""
        try:
            if not encrypted_token:
                raise ValueError("Encrypted token cannot be empty")
            decrypted_bytes = self.fernet.decrypt(encrypted_token.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Error decrypting token: {e}")
            raise
    
    async def validate_token(self, access_token: str) -> bool:
        """Validate if access token is still valid"""
        try:
            async with aiohttp.ClientSession() as session:
                debug_url = "https://graph.facebook.com/debug_token"
                params = {
                    "input_token": access_token,
                    "access_token": f"{self.app_id}|{self.app_secret}"
                }
                
                async with session.get(debug_url, params=params) as response:
                    if response.status != 200:
                        return False
                    
                    debug_data = await response.json()
                    data = debug_data.get('data', {})
                    
                    # Check if token is valid and not expired
                    is_valid = data.get('is_valid', False)
                    expires_at = data.get('expires_at', 0)
                    
                    if is_valid and expires_at > 0:
                        # Check if token expires within next 7 days
                        expiry_date = datetime.fromtimestamp(expires_at)
                        warning_date = datetime.now() + timedelta(days=7)
                        
                        if expiry_date < warning_date:
                            logger.warning(f"⚠️ Token expires soon: {expiry_date}")
                    
                    return is_valid
                    
        except Exception as e:
            logger.error(f"❌ Token validation failed: {e}")
            return False
