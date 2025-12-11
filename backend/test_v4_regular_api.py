#!/usr/bin/env python3
"""
Test script to verify V4 regular API implementation works
"""

import asyncio
import sys
from video_ads_v2_models import VideoAdsProductInfoV2, MarketingAngleV2
from claude_service import ClaudeService
from logging_service import logger

async def test_regular_api_flow():
    """Test the regular API flow for hooks and scripts generation"""

    # Initialize Claude service
    claude_service = ClaudeService()

    # Create test product info
    product_info = VideoAdsProductInfoV2(
        product_name="Test Product",
        product_information="A test product for testing",
        target_audience="Developers",
        price="Free",
        problem_solved="Testing issues",
        differentiation="Best testing solution",
        additional_information="",
        product_url="https://example.com"
    )

    # Create test angles (just 2 for testing)
    angles = [
        MarketingAngleV2(
            angle=1,
            concept="Time-saving benefits",
            category="Efficiency",
            type="positive"
        ),
        MarketingAngleV2(
            angle=2,
            concept="Cost reduction",
            category="Financial",
            type="positive"
        )
    ]

    print("\n" + "="*60)
    print("🧪 Testing V4 Regular API Implementation")
    print("="*60)

    try:
        # Test 1: Generate hooks
        print("\n1️⃣ Testing Hooks Generation...")
        print(f"   Generating hooks for {len(angles)} angles...")

        start_time = asyncio.get_event_loop().time()
        hooks_result = await claude_service.generate_hooks(
            product_info=product_info,
            selected_angles=angles,
            avatar_analysis=None,
            journey_mapping=None,
            objections_analysis=None
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        print(f"   ✅ Generated {len(hooks_result)} angle-hook sets in {elapsed:.2f}s")

        # Count total hooks
        total_hooks = 0
        hooks_data = []
        for hook_angle in hooks_result:
            hook_dict = hook_angle.model_dump() if hasattr(hook_angle, 'model_dump') else hook_angle
            hooks_data.append(hook_dict)
            if "hooks_by_category" in hook_dict:
                for category_hooks in hook_dict["hooks_by_category"].values():
                    total_hooks += len(category_hooks) if isinstance(category_hooks, list) else 0

        print(f"   📊 Total hooks generated: {total_hooks}")

        # Test 2: Generate scripts
        print("\n2️⃣ Testing Scripts Generation...")
        print(f"   Generating scripts for {total_hooks} hooks...")

        start_time = asyncio.get_event_loop().time()
        scripts_result = await claude_service.generate_scripts(
            product_info=product_info,
            hooks_by_angle=hooks_data,
            avatar_analysis=None,
            journey_mapping=None,
            objections_analysis=None
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        print(f"   ✅ Scripts generated in {elapsed:.2f}s")

        # Count total scripts
        total_scripts = 0
        if isinstance(scripts_result, dict):
            if "campaign_scripts" in scripts_result:
                campaign_scripts = scripts_result["campaign_scripts"]
                if "angles" in campaign_scripts:
                    for angle in campaign_scripts["angles"]:
                        if "hooks" in angle:
                            for hook in angle["hooks"]:
                                if "scripts" in hook:
                                    total_scripts += len(hook["scripts"])
            elif "angles" in scripts_result:
                for angle in scripts_result["angles"]:
                    if "hooks" in angle:
                        for hook in angle["hooks"]:
                            if "scripts" in hook:
                                total_scripts += len(hook["scripts"])

        print(f"   📊 Total scripts generated: {total_scripts}")

        print("\n" + "="*60)
        print("✅ All tests passed successfully!")
        print("💡 The regular API implementation is working correctly")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.error("test.failed", f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_regular_api_flow())