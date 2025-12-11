#!/usr/bin/env python3
"""Get or create a test user for development"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Try to get any existing user
try:
    result = supabase.table("users").select("id").limit(1).execute()
    if result.data and len(result.data) > 0:
        user_id = result.data[0]['id']
        print(f"✅ Found existing user ID: {user_id}")
        print(f"\nUpdate auth.py line 44 to use this user_id:")
        print(f'    "user_id": "{user_id}",  # Real user ID for dev mode')
    else:
        print("❌ No users found in database")
        print("Please create a user through the app first")
except Exception as e:
    # Users table doesn't exist or we don't have access
    # Try auth.users table (Supabase auth schema)
    try:
        # Note: This might not work due to RLS policies
        result = supabase.from_("auth.users").select("id").limit(1).execute()
        if result.data and len(result.data) > 0:
            user_id = result.data[0]['id']
            print(f"✅ Found auth user ID: {user_id}")
            print(f"\nUpdate auth.py line 44 to use this user_id:")
            print(f'    "user_id": "{user_id}",  # Real user ID for dev mode')
        else:
            print("❌ No users found")
    except Exception as e2:
        print(f"❌ Cannot access users table: {e}")
        print(f"❌ Cannot access auth.users table: {e2}")
        print("\nYou need to either:")
        print("1. Create a user through the app")
        print("2. Remove the foreign key constraint from video_ads_v3_campaigns.user_id")
        print("3. Create a test user directly in Supabase")