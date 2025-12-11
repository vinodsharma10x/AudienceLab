#!/usr/bin/env python3
import requests
import json

# Test the campaigns endpoint
url = "http://localhost:8000/video-ads-v2/campaigns"
headers = {
    "Authorization": "Bearer dev-token"
}

response = requests.get(url, headers=headers)
data = response.json()

print(f"Total campaigns: {data.get('total', 0)}")
print("\n" + "="*80 + "\n")

for campaign in data.get('campaigns', []):
    print(f"Campaign: {campaign.get('campaign_name', 'No name')}")
    print(f"  ID: {campaign.get('campaign_id')}")
    print(f"  Step: {campaign.get('current_step')}")
    print(f"  Status: {campaign.get('status')}")
    print(f"  Has video_url: {'video_url' in campaign}")
    print(f"  Has video_data: {'video_data' in campaign}")

    if 'video_url' in campaign:
        print(f"  Video URL: {campaign['video_url'][:80]}...")

    if 'video_data' in campaign:
        videos = campaign['video_data'].get('generated_videos', [])
        print(f"  Generated videos count: {len(videos)}")
        if videos:
            print(f"  First video URL: {videos[0].get('video_url', 'No URL')[:80]}...")

    print("-" * 40)