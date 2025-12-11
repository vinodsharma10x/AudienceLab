"""
Facebook Targeting Mapper
Maps avatar analysis data to Facebook targeting parameters
"""

import re
from typing import Dict, List, Any, Optional
from logging_service import logger


class FacebookTargetingMapper:
    """Maps product research avatar data to Facebook ad targeting parameters"""

    def __init__(self):
        # Common location mappings
        self.location_mappings = {
            'us': 'United States',
            'usa': 'United States',
            'united states': 'United States',
            'uk': 'United Kingdom',
            'united kingdom': 'United Kingdom',
            'canada': 'Canada',
            'australia': 'Australia',
            'germany': 'Germany',
            'france': 'France',
            'spain': 'Spain',
            'italy': 'Italy',
        }

    def map_avatar_to_targeting(self, avatar_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map avatar analysis to Facebook targeting parameters

        Args:
            avatar_data: Avatar analysis from video_ads_v2_documents

        Returns:
            Dictionary with Facebook targeting parameters
        """
        try:
            targeting = {
                'locations': self._extract_locations(avatar_data),
                'age_min': self._extract_age_min(avatar_data),
                'age_max': self._extract_age_max(avatar_data),
                'gender': self._extract_gender(avatar_data),
                'interests': self._extract_interests(avatar_data),
                'job_titles': self._extract_job_titles(avatar_data),
                'income_level': self._extract_income_level(avatar_data),
            }

            logger.info("targeting_mapper.success", f"Mapped avatar to targeting: {len(targeting['locations'])} locations, {len(targeting['interests'])} interests")
            return targeting

        except Exception as e:
            logger.error("targeting_mapper.error", f"Error mapping avatar to targeting: {e}")
            return self._get_default_targeting()

    def _extract_locations(self, avatar_data: Dict[str, Any]) -> List[str]:
        """Extract geographic locations from avatar data"""
        locations = []

        try:
            demographic_data = avatar_data.get('demographic_data', {})
            geo_location = demographic_data.get('geographic_location', '')

            if geo_location:
                # Parse location string
                location_text = geo_location.lower()

                # Check for mapped locations
                for key, value in self.location_mappings.items():
                    if key in location_text:
                        if value not in locations:
                            locations.append(value)

                # If no matches, try to extract capitalized words (country names)
                if not locations:
                    words = geo_location.split()
                    for word in words:
                        if word and word[0].isupper() and len(word) > 2:
                            locations.append(word)

        except Exception as e:
            logger.warning("targeting_mapper.locations.error", f"Error extracting locations: {e}")

        # Default to US if no locations found
        if not locations:
            locations = ['United States']

        return locations

    def _extract_age_min(self, avatar_data: Dict[str, Any]) -> int:
        """Extract minimum age from avatar data"""
        try:
            demographic_data = avatar_data.get('demographic_data', {})
            age_range = demographic_data.get('age_range', '')

            if age_range:
                # Try to extract first number (e.g., "25-40" -> 25)
                numbers = re.findall(r'\d+', age_range)
                if numbers:
                    age_min = int(numbers[0])
                    # Ensure it's at least 18 (Facebook minimum)
                    return max(18, age_min)

        except Exception as e:
            logger.warning("targeting_mapper.age_min.error", f"Error extracting age_min: {e}")

        return 25  # Default

    def _extract_age_max(self, avatar_data: Dict[str, Any]) -> int:
        """Extract maximum age from avatar data"""
        try:
            demographic_data = avatar_data.get('demographic_data', {})
            age_range = demographic_data.get('age_range', '')

            if age_range:
                # Try to extract second number (e.g., "25-40" -> 40)
                numbers = re.findall(r'\d+', age_range)
                if len(numbers) >= 2:
                    age_max = int(numbers[1])
                    # Cap at 65 for practical targeting
                    return min(65, age_max)
                elif len(numbers) == 1:
                    # If only one number, use it + 20
                    return min(65, int(numbers[0]) + 20)

        except Exception as e:
            logger.warning("targeting_mapper.age_max.error", f"Error extracting age_max: {e}")

        return 55  # Default

    def _extract_gender(self, avatar_data: Dict[str, Any]) -> str:
        """Extract gender from avatar data"""
        try:
            demographic_data = avatar_data.get('demographic_data', {})
            # Facebook doesn't always have this, so default to 'all'
            # Could be enhanced to parse from demographic data text

        except Exception as e:
            logger.warning("targeting_mapper.gender.error", f"Error extracting gender: {e}")

        return 'all'  # Default to all genders

    def _extract_interests(self, avatar_data: Dict[str, Any]) -> List[str]:
        """Extract interests from avatar data"""
        interests = []

        try:
            psychographic_factors = avatar_data.get('psychographic_factors', {})
            interests_hobbies = psychographic_factors.get('interests_hobbies', '')

            if interests_hobbies:
                # Split by common delimiters
                raw_interests = re.split(r'[,;.\n]', interests_hobbies)

                # Clean and filter interests
                for interest in raw_interests:
                    cleaned = interest.strip()
                    # Keep interests that are 2-40 characters
                    if 2 < len(cleaned) < 40 and not cleaned.startswith('-'):
                        # Capitalize first letter
                        cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
                        if cleaned not in interests:
                            interests.append(cleaned)

            # Limit to top 10 interests
            interests = interests[:10]

        except Exception as e:
            logger.warning("targeting_mapper.interests.error", f"Error extracting interests: {e}")

        # Add some defaults if none found
        if not interests:
            interests = ['Entrepreneurship', 'Business']

        return interests

    def _extract_job_titles(self, avatar_data: Dict[str, Any]) -> List[str]:
        """Extract job titles from avatar data"""
        job_titles = []

        try:
            demographic_data = avatar_data.get('demographic_data', {})
            employment_situation = demographic_data.get('employment_situation', '')

            if employment_situation:
                # Common job title keywords to extract
                title_keywords = [
                    'founder', 'ceo', 'cto', 'cfo', 'coo',
                    'entrepreneur', 'owner', 'director', 'manager',
                    'executive', 'president', 'vp', 'vice president',
                    'startup', 'freelancer', 'consultant'
                ]

                employment_lower = employment_situation.lower()

                for keyword in title_keywords:
                    if keyword in employment_lower:
                        # Capitalize properly
                        title = keyword.upper() if keyword in ['ceo', 'cto', 'cfo', 'coo', 'vp'] else keyword.capitalize()
                        if title not in job_titles:
                            job_titles.append(title)

        except Exception as e:
            logger.warning("targeting_mapper.job_titles.error", f"Error extracting job titles: {e}")

        # Limit to 5 job titles
        return job_titles[:5]

    def _extract_income_level(self, avatar_data: Dict[str, Any]) -> Optional[str]:
        """Extract income level from avatar data"""
        try:
            demographic_data = avatar_data.get('demographic_data', {})
            socioeconomic_level = demographic_data.get('socioeconomic_level', '')

            if socioeconomic_level:
                level_lower = socioeconomic_level.lower()

                if any(word in level_lower for word in ['high', 'upper', 'affluent', 'wealthy']):
                    return 'high'
                elif any(word in level_lower for word in ['middle', 'moderate']):
                    return 'middle'
                elif any(word in level_lower for word in ['low', 'lower']):
                    return 'low'

        except Exception as e:
            logger.warning("targeting_mapper.income.error", f"Error extracting income level: {e}")

        return None

    def _get_default_targeting(self) -> Dict[str, Any]:
        """Return default targeting parameters if extraction fails"""
        return {
            'locations': ['United States'],
            'age_min': 25,
            'age_max': 55,
            'gender': 'all',
            'interests': ['Entrepreneurship', 'Business'],
            'job_titles': [],
            'income_level': None,
        }


# Create singleton instance
targeting_mapper = FacebookTargetingMapper()


# Convenience function
def map_avatar_to_facebook_targeting(avatar_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to map avatar data to Facebook targeting

    Args:
        avatar_data: Avatar analysis dictionary

    Returns:
        Facebook targeting parameters
    """
    return targeting_mapper.map_avatar_to_targeting(avatar_data)
