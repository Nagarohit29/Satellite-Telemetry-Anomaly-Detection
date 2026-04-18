#!/bin/bash

# Configuration
USERNAME="nagarohit"
IMAGE_NAME="satellite-telemetry-full"
VERSION="0"

echo "🚀 Starting MONOLITHIC build and push for version $VERSION..."

# Build the monolithic image
echo "📦 Building Combined Image..."
docker build -t $USERNAME/$IMAGE_NAME:$VERSION -t $USERNAME/$IMAGE_NAME:latest .

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
else
    echo "❌ Build failed!"
    exit 1
fi

# Push to Docker Hub
echo "☁️ Pushing to Docker Hub..."
docker push $USERNAME/$IMAGE_NAME:$VERSION
docker push $USERNAME/$IMAGE_NAME:latest

echo "🎉 Done! Image is available at $USERNAME/$IMAGE_NAME:$VERSION"
