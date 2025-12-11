"""
Mock data loader for fast testing of hooks and scripts generation
"""

import json
from typing import Dict, Any, List
from video_ads_v2_models import (
    MarketingAngleV2,
    AvatarAnalysis,
    JourneyMapping,
    ObjectionsAnalysis,
    AnglesGeneration,
    AngleWithHooksV2,
    # Import all the nested model classes for eval to work
    DemographicData,
    PsychographicFactors,
    PurchasingBehavior,
    RealityExpectations,
    EconomicSensitivity,
    JourneyPhase,
    ObjectionItem
)

def load_mock_angles() -> List[MarketingAngleV2]:
    """Load mock angles data from file"""
    # Read the angles_list.md file and parse it
    with open('/Users/vinodsharma/code/sucana-v4/mock-data/angles_list.md', 'r') as f:
        content = f.read()

    # Create a safe namespace for eval with all necessary classes
    safe_namespace = {
        'MarketingAngleV2': MarketingAngleV2
    }

    # The file contains a Python list representation, we can use eval (safe in this context)
    angles = eval(content, safe_namespace)  # Safe because we control the input file
    return angles


def load_mock_avatars() -> AvatarAnalysis:
    """Load mock avatar analysis from file"""
    with open('/Users/vinodsharma/code/sucana-v4/mock-data/AvatarAnalysis.md', 'r') as f:
        content = f.read()

    # Create a safe namespace for eval with all necessary classes
    safe_namespace = {
        'AvatarAnalysis': AvatarAnalysis,
        'DemographicData': DemographicData,
        'PsychographicFactors': PsychographicFactors,
        'PurchasingBehavior': PurchasingBehavior,
        'RealityExpectations': RealityExpectations,
        'EconomicSensitivity': EconomicSensitivity
    }

    # Parse the content (it's in Python repr format)
    avatar_data = eval(content, safe_namespace)  # Safe because we control the input file
    return avatar_data


def load_mock_journey() -> JourneyMapping:
    """Load mock journey mapping from file"""
    with open('/Users/vinodsharma/code/sucana-v4/mock-data/JourneyMapping.md', 'r') as f:
        content = f.read()

    # Create a safe namespace for eval with all necessary classes
    safe_namespace = {
        'JourneyMapping': JourneyMapping,
        'JourneyPhase': JourneyPhase
    }

    # Parse the content
    journey_data = eval(content, safe_namespace)  # Safe because we control the input file
    return journey_data


def load_mock_objections() -> ObjectionsAnalysis:
    """Load mock objections analysis from file"""
    with open('/Users/vinodsharma/code/sucana-v4/mock-data/ObjectionsAnalysis.md', 'r') as f:
        content = f.read()

    # Create a safe namespace for eval with all necessary classes
    safe_namespace = {
        'ObjectionsAnalysis': ObjectionsAnalysis,
        'ObjectionItem': ObjectionItem
    }

    # Parse the content
    objections_data = eval(content, safe_namespace)  # Safe because we control the input file
    return objections_data


def load_mock_hooks_data() -> List[Dict[str, Any]]:
    """Load mock hooks data for scripts generation testing"""
    # Use hooks_by_angle.md which has all 14 angles
    with open('/Users/vinodsharma/code/sucana-v4/mock-data/hooks_by_angle.md', 'r') as f:
        content = f.read()

    # Create a safe namespace for eval with all necessary classes
    safe_namespace = {
        'AngleWithHooksV2': AngleWithHooksV2,
        'MarketingAngleV2': MarketingAngleV2,
        'HooksByCategoryV2': AngleWithHooksV2.__annotations__.get('hooks_by_category', type(None)).__class__,
        'HookItem': AngleWithHooksV2.__annotations__.get('hooks_by_category', type(None)).__class__
    }

    # Need to import the nested classes too
    from video_ads_v2_models import HooksByCategoryV2, HookItem
    safe_namespace['HooksByCategoryV2'] = HooksByCategoryV2
    safe_namespace['HookItem'] = HookItem

    # Parse the content
    hooks_data = eval(content, safe_namespace)  # Safe because we control the input file

    # Convert to dict format if needed
    if hooks_data and hasattr(hooks_data[0], 'model_dump'):
        return [h.model_dump() for h in hooks_data]
    return hooks_data


# Flags to control mock data usage
USE_MOCK_DATA = False  # Set to True to use mock data for 4 phases (skip 4-phase generation)
SKIP_TO_SCRIPTS = False  # Set to True to skip directly to scripts generation (skip hooks too)