#!/usr/bin/env python3
"""
Script to check if AWS S3 credentials are properly configured
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🔍 Checking AWS S3 Configuration...")
print("=" * 50)

# Check required AWS variables
aws_vars = {
    "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "AWS_REGION": os.getenv("AWS_REGION", "us-east-2"),
    "S3_BUCKET_NAME": os.getenv("S3_BUCKET_NAME", "sucana-media")
}

missing_vars = []
for var_name, var_value in aws_vars.items():
    if var_name in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"] and not var_value:
        missing_vars.append(var_name)
        print(f"❌ {var_name}: NOT SET")
    elif var_value:
        if "SECRET" in var_name or "KEY" in var_name:
            print(f"✅ {var_name}: ***{var_value[-4:] if len(var_value) > 4 else '***'}")
        else:
            print(f"✅ {var_name}: {var_value}")
    else:
        print(f"⚠️  {var_name}: Using default")

print("=" * 50)

if missing_vars:
    print(f"\n❌ Missing required AWS credentials: {', '.join(missing_vars)}")
    print("\nTo fix this, add the following to your .env or .env.production file:")
    for var in missing_vars:
        print(f"{var}=your_{var.lower()}_here")
    print("\nS3 uploads will not work without these credentials!")
    sys.exit(1)
else:
    print("\n✅ All AWS credentials are configured!")

    # Try to import and test S3 service
    try:
        from s3_service import s3_service
        if s3_service.enabled:
            print("✅ S3 service is enabled and ready!")
        else:
            print("❌ S3 service is disabled - check credentials")
    except Exception as e:
        print(f"⚠️  Could not test S3 service: {e}")