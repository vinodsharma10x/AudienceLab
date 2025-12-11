"""
S3 Service for handling all AWS S3 operations
Single bucket approach: sucana-media
"""

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path
from typing import Optional, Tuple
import mimetypes
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class S3Service:
    """Service for managing file uploads to AWS S3"""
    
    def __init__(self):
        """Initialize S3 client with credentials from environment"""
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "sucana-media")
        self.region = os.getenv("AWS_REGION", "us-east-2")
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=self.region
            )
            
            # Test connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ S3 Service initialized successfully with bucket: {self.bucket_name}")
            self.enabled = True
            
        except NoCredentialsError:
            logger.warning("⚠️ AWS credentials not found. S3 uploads will be disabled.")
            self.enabled = False
            self.s3_client = None
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.error(f"❌ S3 bucket '{self.bucket_name}' not found")
            else:
                logger.error(f"❌ S3 initialization error: {e}")
            self.enabled = False
            self.s3_client = None
        except Exception as e:
            logger.error(f"❌ Unexpected S3 initialization error: {e}")
            self.enabled = False
            self.s3_client = None
    
    def upload_file(
        self, 
        file_path: str, 
        file_type: str = "audio",
        campaign_id: str = None,
        user_id: str = None,
        custom_key: str = None
    ) -> Optional[str]:
        """
        Upload a file to S3 and return the public URL
        
        Args:
            file_path: Local path to the file
            file_type: Type of file ('audio', 'video', 'upload')
            campaign_id: Campaign ID for organization
            user_id: User ID for uploads
            custom_key: Custom S3 key (overrides auto-generated key)
            
        Returns:
            S3 URL of the uploaded file or None if upload fails
        """
        if not self.enabled or not self.s3_client:
            logger.warning("S3 service is not enabled")
            return None
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Generate S3 key
            if custom_key:
                s3_key = custom_key
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = file_path.name
                
                # Log filename for debugging
                logger.info(f"📁 Original filename: {filename}")
                
                if file_type == "audio" and campaign_id:
                    s3_key = f"audio/{campaign_id}/{timestamp}_{filename}"
                elif file_type == "video" and campaign_id:
                    s3_key = f"videos/{campaign_id}/{timestamp}_{filename}"
                elif file_type == "upload" and user_id:
                    s3_key = f"uploads/{user_id}/{timestamp}_{filename}"
                else:
                    # Fallback path
                    s3_key = f"{file_type}/{timestamp}_{filename}"
                
                logger.info(f"🔑 Generated S3 key: {s3_key}")
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                if file_type == "audio":
                    content_type = "audio/mpeg"
                elif file_type == "video":
                    content_type = "video/mp4"
                else:
                    content_type = "application/octet-stream"
            
            # Upload file (bucket policy handles public access)
            logger.info(f"📤 Uploading to S3: {s3_key}")
            
            with open(file_path, 'rb') as file_data:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=file_data,
                    ContentType=content_type
                    # Removed ACL parameter - bucket policy handles public access
                )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            logger.info(f"✅ Successfully uploaded to S3")
            logger.info(f"📍 Full S3 URL: {s3_url}")
            print(f"🔗 S3 URL being returned: {s3_url}")  # Extra print for debugging
            return s3_url
            
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            return None
    
    def upload_file_object(
        self,
        file_obj,
        filename: str,
        file_type: str = "upload",
        campaign_id: str = None,
        user_id: str = None
    ) -> Optional[Tuple[str, str]]:
        """
        Upload a file object (from form upload) to S3
        
        Args:
            file_obj: File object from FastAPI UploadFile
            filename: Original filename
            file_type: Type of file
            campaign_id: Campaign ID for organization
            user_id: User ID for uploads
            
        Returns:
            Tuple of (S3 URL, S3 key) or (None, None) if upload fails
        """
        if not self.enabled or not self.s3_client:
            logger.warning("S3 service is not enabled")
            return None, None
        
        try:
            # Generate S3 key
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            
            if file_type == "upload" and user_id:
                s3_key = f"uploads/{user_id}/{timestamp}_{safe_filename}"
            elif campaign_id:
                s3_key = f"{file_type}/{campaign_id}/{timestamp}_{safe_filename}"
            else:
                s3_key = f"{file_type}/{timestamp}_{safe_filename}"
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = "application/octet-stream"
            
            # Upload directly from file object
            logger.info(f"📤 Uploading file object to S3: {s3_key}")
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_obj,
                ContentType=content_type
                # Removed ACL parameter - bucket policy handles public access
            )
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            logger.info(f"✅ Successfully uploaded file object to S3: {s3_url}")
            return s3_url, s3_key
            
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Unexpected error during S3 file object upload: {e}")
            return None, None
    
    def upload_file_from_bytes(
        self,
        file_content: bytes,
        s3_key: str,
        content_type: str = None
    ) -> Optional[str]:
        """
        Upload file content directly from bytes to S3

        Args:
            file_content: File content as bytes
            s3_key: S3 key for the file
            content_type: MIME type of the file

        Returns:
            S3 URL of the uploaded file or None if upload fails
        """
        if not self.enabled or not self.s3_client:
            logger.warning("S3 service is not enabled")
            return None

        try:
            # Upload file to S3
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                **extra_args
            )

            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"

            logger.info(f"✅ Successfully uploaded bytes to S3: {s3_url}")
            return s3_url

        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during S3 bytes upload: {e}")
            return None

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3
        
        Args:
            s3_key: The S3 key of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.enabled or not self.s3_client:
            logger.warning("S3 service is not enabled")
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"🗑️ Successfully deleted from S3: {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 deletion error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 deletion: {e}")
            return False
    
    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for temporary access to a private file
        
        Args:
            s3_key: The S3 key of the file
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL or None if generation fails
        """
        if not self.enabled or not self.s3_client:
            logger.warning("S3 service is not enabled")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            return None
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3
        
        Args:
            s3_key: The S3 key to check
            
        Returns:
            True if file exists, False otherwise
        """
        if not self.enabled or not self.s3_client:
            return False
        
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
        except Exception:
            return False

# Create a singleton instance
s3_service = S3Service()