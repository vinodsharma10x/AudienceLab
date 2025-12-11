"""
Actor Image Handler for Production and Development Environments
Handles fetching actor images either from local filesystem (dev) or from frontend URL (production)
"""

import os
import aiohttp
import asyncio
from pathlib import Path
from typing import Optional
import tempfile
import logging

logger = logging.getLogger(__name__)

class ActorImageHandler:
    """Handles actor image retrieval for both development and production environments"""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.temp_dir = tempfile.gettempdir()

    async def get_actor_image_path(self, actor_filename: str) -> str:
        """
        Get the path to an actor image file.
        Always uses backend/actor_images directory which exists in both dev and production
        """

        # Use backend actor_images directory (exists in both dev and production)
        backend_path = Path(__file__).parent / "actor_images" / actor_filename
        if backend_path.exists():
            logger.info(f"Using actor image: {backend_path}")
            return str(backend_path)

        # If the file doesn't exist, raise an error
        raise FileNotFoundError(f"Actor image not found: {actor_filename} in {backend_path.parent}")

    async def _download_actor_image(self, actor_filename: str) -> str:
        """Download actor image from frontend URL and save to temp file"""

        # Construct the URL to the actor image
        image_url = f"{self.frontend_url}/images/actors/{actor_filename}"

        # Create temp file path
        temp_path = Path(self.temp_dir) / f"actor_{actor_filename}"

        # If already downloaded, return existing path
        if temp_path.exists():
            logger.info(f"Using cached actor image: {temp_path}")
            return str(temp_path)

        try:
            logger.info(f"Downloading actor image from: {image_url}")

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        content = await response.read()

                        # Save to temp file
                        with open(temp_path, 'wb') as f:
                            f.write(content)

                        logger.info(f"Actor image downloaded successfully to: {temp_path}")
                        return str(temp_path)
                    else:
                        raise Exception(f"Failed to download actor image: HTTP {response.status}")

        except Exception as e:
            logger.error(f"Error downloading actor image: {str(e)}")

            # Fallback: create a placeholder path (Hedra will handle the error)
            # Or you could return a default actor image if you have one
            raise Exception(f"Could not retrieve actor image {actor_filename}: {str(e)}")

    def cleanup_temp_files(self):
        """Clean up temporary actor image files"""
        try:
            temp_path = Path(self.temp_dir)
            for file in temp_path.glob("actor_*.jpg"):
                file.unlink()
                logger.info(f"Cleaned up temp file: {file}")
            for file in temp_path.glob("actor_*.png"):
                file.unlink()
                logger.info(f"Cleaned up temp file: {file}")
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {str(e)}")

# Global instance
actor_image_handler = ActorImageHandler()