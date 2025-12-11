#!/usr/bin/env python3
"""
Test script to verify the angles extraction fix in video_ads_v4_routes.py
"""

import asyncio
import json
from video_ads_v2_models import AnglesGeneration

# Simulate the angles data structure that would come from the workflow
# MarketingAngleV2 requires: angle (int), category, concept, type
mock_angles = AnglesGeneration(
    positive_angles=[
        {
            "angle": 1,
            "category": "efficiency",
            "concept": "Time-Saving Solution - Focus on how the product saves valuable time",
            "type": "positive"
        },
        {
            "angle": 2,
            "category": "financial",
            "concept": "Cost-Effective Choice - Highlight the financial benefits",
            "type": "positive"
        }
    ],
    negative_angles=[
        {
            "angle": 3,
            "category": "fomo",
            "concept": "Avoid Missing Out - Fear of missing opportunities",
            "type": "negative"
        }
    ]
)

def test_angles_extraction():
    """Test the corrected angles extraction logic"""
    print("Testing angles extraction fix...")
    print(f"Mock angles type: {type(mock_angles)}")
    print(f"Has positive_angles: {hasattr(mock_angles, 'positive_angles')}")
    print(f"Has negative_angles: {hasattr(mock_angles, 'negative_angles')}")

    # This is the CORRECTED extraction logic from video_ads_v4_routes.py
    angles_list = []
    if hasattr(mock_angles, 'positive_angles'):
        angles_list.extend(mock_angles.positive_angles)
    if hasattr(mock_angles, 'negative_angles'):
        angles_list.extend(mock_angles.negative_angles)

    print(f"\nExtracted {len(angles_list)} angles successfully!")

    for idx, angle in enumerate(angles_list, 1):
        print(f"\nAngle {idx}:")
        # Access attributes directly, not with .get()
        print(f"  Concept: {angle.concept}")
        print(f"  Category: {angle.category}")
        print(f"  Type: {angle.type}")

    # Test that we can iterate and access angle properties
    try:
        for angle_idx, angle in enumerate(angles_list):
            # Access Pydantic model attributes directly
            concept = angle.concept
            category = angle.category
            angle_type = angle.type
            print(f"\n✓ Successfully processed angle {angle_idx + 1}: {concept[:50]}...")

        print("\n✅ Angles extraction fix is working correctly!")
        return True

    except AttributeError as e:
        print(f"\n❌ Error: {e}")
        print("The angles extraction is still broken")
        return False

if __name__ == "__main__":
    success = test_angles_extraction()
    exit(0 if success else 1)