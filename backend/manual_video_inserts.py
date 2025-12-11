#!/usr/bin/env python3
"""
Manual data insertion script for video_ads_v3_videos table
"""

import os
from datetime import datetime
from dotenv import load_dotenv
import uuid
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def insert_videos():
    """Insert manual video entries into video_ads_v3_videos table"""

    # Create Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    try:
        # Video data to insert (matching the actual table structure)
        videos = [
            {
                'id': str(uuid.uuid4()),
                'campaign_id': 'd4276d43-4ad0-4fec-bc57-63079cab28b3',
                'video_number': 1,
                'video_url': 'https://sucana-media.s3.us-east-2.amazonaws.com/videos/d4276d43-4ad0-4fec-bc57-63079cab28b3/20250830_190555_angle_10_1_1_combined.mp4',
                'audio_url': '',  # Can be empty
                'angle_data': {
                    'type': 'positive',
                    'concept': 'Great value proposition'
                },
                'hook_data': {
                    'hook_text': 'Amazing product that will change your life!'
                },
                'script_data': {
                    'script_text': 'This is the full script text for the first video.',
                    'cta': 'Shop Now'
                },
                'voice_data': {
                    'voice_name': 'Default Voice'
                },
                'actor_data': {
                    'actor_name': 'Default Actor'
                },
                'status': 'completed'
            },
            {
                'id': str(uuid.uuid4()),
                'campaign_id': 'cbe484dd-6d13-495f-ad10-47bb57123b0f',
                'video_number': 1,
                'video_url': 'https://sucana-media.s3.us-east-2.amazonaws.com/videos/fd6455d8-f609-475a-90a5-1964da6da92c/20250829_120641_angle_3_1_1_combined.mp4',
                'audio_url': '',  # Can be empty
                'angle_data': {
                    'type': 'positive',
                    'concept': 'Problem solver'
                },
                'hook_data': {
                    'hook_text': 'Stop wasting time with inferior products!'
                },
                'script_data': {
                    'script_text': 'This is the full script text for the second video.',
                    'cta': 'Learn More'
                },
                'voice_data': {
                    'voice_name': 'Default Voice'
                },
                'actor_data': {
                    'actor_name': 'Default Actor'
                },
                'status': 'completed'
            }
        ]

        # Insert each video
        for video in videos:
            result = supabase.table('video_ads_v3_videos').upsert(video).execute()
            if result.data:
                print(f"✅ Inserted video for campaign {video['campaign_id']}")
                print(f"   Video URL: {video['video_url']}")
                print(f"   Video ID: {video['id']}")
            else:
                print(f"❌ Failed to insert video for campaign {video['campaign_id']}")

        # Also update the campaigns to mark them as having videos (step 8)
        campaign_ids = [
            'd4276d43-4ad0-4fec-bc57-63079cab28b3',
            'cbe484dd-6d13-495f-ad10-47bb57123b0f'
        ]

        for campaign_id in campaign_ids:
            update_result = supabase.table('video_ads_v3_campaigns').update({
                'current_step': 8,
                'status': 'completed'
            }).eq('campaign_id', campaign_id).execute()

            if update_result.data:
                print(f"✅ Updated campaign {campaign_id} to step 8 with status completed")
            else:
                print(f"⚠️  Could not update campaign {campaign_id} - it may not exist")

        print("\n🎉 Successfully inserted video data!")

    except Exception as e:
        print(f"❌ Error inserting videos: {e}")
        raise

if __name__ == "__main__":
    insert_videos()