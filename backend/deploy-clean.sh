#!/bin/bash

# Clean deployment script for AudienceLab backend
# This ensures a completely fresh build without any cache

echo "Starting clean deployment to AWS Lightsail..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Push latest changes
echo -e "${YELLOW}Pushing latest changes to GitHub...${NC}"
git add -A
git commit -m "Deploy: Clean rebuild with actor image handler" || echo "No changes to commit"
git push origin main

# SSH and deploy
echo -e "${YELLOW}Connecting to AWS Lightsail for clean deployment...${NC}"

ssh -o StrictHostKeyChecking=no ubuntu@54.205.63.40 << 'ENDSSH'
cd /home/ubuntu/audiencelab
echo "Pulling latest changes..."
git pull origin main

cd backend

# Verify the new file exists
echo "Checking for actor_image_handler.py..."
if [ -f actor_image_handler.py ]; then
    echo "actor_image_handler.py found"
    ls -la actor_image_handler.py
else
    echo "actor_image_handler.py NOT FOUND!"
    exit 1
fi

echo "Cleaning Docker system..."
# Stop and remove container
docker-compose down

# Remove the old image completely
docker rmi audiencelab-backend_backend:latest 2>/dev/null || true
docker rmi $(docker images -q audiencelab-backend_backend) 2>/dev/null || true

# Clean build cache
docker system prune -f

echo "Building fresh Docker image (no cache)..."
docker-compose build --no-cache

echo "Starting new container..."
docker-compose up -d

echo "Waiting for container to be healthy..."
sleep 10

echo "Container status:"
docker-compose ps

echo "Verifying actor_image_handler.py is in container..."
docker exec audiencelab-backend ls -la /app/actor_image_handler.py || echo "Warning: File not found in container"

echo "Checking imports in video_ads_v2_routes.py..."
docker exec audiencelab-backend head -20 /app/video_ads_v2_routes.py | grep -E "import|from.*import"

echo "Showing recent logs..."
docker-compose logs --tail=50

echo "Clean deployment complete!"
ENDSSH

echo -e "${GREEN}Deployment finished!${NC}"
echo "The backend has been completely rebuilt without any cache."