#!/bin/bash

echo "Deploying AudienceLab backend with AWS S3 configuration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Commit and push changes
echo -e "${YELLOW}Committing and pushing changes...${NC}"
cd /Users/vinodsharma/code/AudienceLab
git add -A
git commit -m "fix: Update docker-compose to use .env file with AWS credentials"
git push origin develop

# Step 2: Merge to main
echo -e "${YELLOW}Merging to main branch...${NC}"
git checkout main
git pull origin main
git merge develop
git push origin main

# Step 3: Deploy to AWS Lightsail
echo -e "${YELLOW}Deploying to AWS Lightsail...${NC}"

# SSH into server and deploy
ssh -o StrictHostKeyChecking=no ubuntu@52.15.175.113 << 'ENDSSH'
cd /home/ubuntu/audiencelab
echo "Pulling latest changes..."
git pull origin main

# Copy the local .env file if it exists
if [ -f backend/.env ]; then
    echo ".env file found"
else
    echo "Warning: .env file not found in backend/"
fi

cd backend

echo "Building Docker container..."
docker-compose build

echo "Stopping old container..."
docker-compose down

echo "Starting new container..."
docker-compose up -d

echo "Waiting for container to start..."
sleep 5

echo "Container status:"
docker-compose ps

echo "Checking AWS credentials inside container..."
docker exec audiencelab-backend python check_aws_creds.py || echo "Note: check_aws_creds.py not found, checking environment directly..."

echo "Checking environment variables..."
docker exec audiencelab-backend sh -c 'if [ -n "$AWS_ACCESS_KEY_ID" ]; then echo "AWS_ACCESS_KEY_ID is set"; else echo "AWS_ACCESS_KEY_ID is NOT set"; fi'
docker exec audiencelab-backend sh -c 'if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then echo "AWS_SECRET_ACCESS_KEY is set"; else echo "AWS_SECRET_ACCESS_KEY is NOT set"; fi'
docker exec audiencelab-backend sh -c 'if [ -n "$S3_BUCKET_NAME" ]; then echo "S3_BUCKET_NAME: $S3_BUCKET_NAME"; else echo "S3_BUCKET_NAME not set (will use default)"; fi'

echo "Recent logs:"
docker-compose logs --tail=30

echo "Deployment complete!"
ENDSSH

echo -e "${GREEN}Backend deployment finished!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Check if AWS credentials are loaded correctly above"
echo "2. If not, SSH into the server and add them to backend/.env"
echo "3. Test document upload in production at your deployed URL"