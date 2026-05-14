#!/bin/bash

# Configuration - CHANGE THESE
PROJECT_ID="your-project-id"
REGION="us-central1"
SERVICE_NAME="weather-aggregator"
REPOSITORY_NAME="weather-repo"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${SERVICE_NAME}:latest"

echo "🚀 Starting deployment for ${SERVICE_NAME}..."

# 1. Enable necessary services
gcloud services enable artifactregistry.googleapis.com run.googleapis.com cloudbuild.googleapis.com

# 2. Create Artifact Registry repository if it doesn't exist
gcloud artifacts repositories describe ${REPOSITORY_NAME} --location=${REGION} > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "📦 Creating Artifact Registry repository..."
    gcloud artifacts repositories create ${REPOSITORY_NAME} \
        --repository-format=docker \
        --location=${REGION} \
        --description="Docker repository for weather service"
fi

# 3. Build and Push using Cloud Build
# This handles the build on Google's infrastructure (no local docker needed)
echo "🏗️ Building and pushing image to Artifact Registry..."
gcloud builds submit --tag ${IMAGE_NAME} .

# 4. Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --port 8080

echo "✅ Deployment Complete!"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)'