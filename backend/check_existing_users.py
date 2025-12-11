#!/usr/bin/env python3
"""Check existing user IDs in campaigns"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check existing campaigns for user IDs
try:
    result = supabase.table("video_ads_v3_campaigns").select("user_id").execute()
    if result.data:
        user_ids = list(set([c['user_id'] for c in result.data if c.get('user_id')]))
        print(f"✅ Found {len(user_ids)} unique user IDs in video_ads_v3_campaigns:")
        for uid in user_ids[:5]:  # Show first 5
            print(f"   - {uid}")
        
        if user_ids:
            print(f"\n✅ You can use this user_id for dev mode:")
            print(f'Update auth.py line 44 to:')
            print(f'    "user_id": "{user_ids[0]}",  # Real user ID for dev mode')
    else:
        print("❌ No campaigns found")
except Exception as e:
    print(f"❌ Error: {e}")

# Also check V2 campaigns
try:
    result = supabase.table("video_ads_v2_campaigns").select("user_id").execute()
    if result.data:
        user_ids = list(set([c['user_id'] for c in result.data if c.get('user_id')]))
        print(f"\n✅ Found {len(user_ids)} unique user IDs in video_ads_v2_campaigns:")
        for uid in user_ids[:5]:  # Show first 5
            print(f"   - {uid}")
except Exception as e:
    print(f"❌ Cannot access V2 campaigns: {e}")