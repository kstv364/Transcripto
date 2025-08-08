#!/bin/bash

# Deployment script for DigitalOcean Kubernetes
# Usage: ./deploy.sh [staging|production]

set -e

ENVIRONMENT=${1:-staging}
NAMESPACE="transcripter"
REGISTRY="registry.digitalocean.com/your-registry"
APP_NAME="transcripter"

if [ "$ENVIRONMENT" = "staging" ]; then
    NAMESPACE="transcripter-staging"
fi

echo "🚀 Deploying transcripter to $ENVIRONMENT environment..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if kustomize is available
if ! command -v kustomize &> /dev/null; then
    echo "❌ kustomize not found. Please install kustomize first."
    exit 1
fi

# Check if doctl is available
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl not found. Please install DigitalOcean CLI first."
    exit 1
fi

# Get current context
CURRENT_CONTEXT=$(kubectl config current-context)
echo "📋 Current kubectl context: $CURRENT_CONTEXT"

# Confirm deployment
read -p "🤔 Deploy to $ENVIRONMENT using context '$CURRENT_CONTEXT'? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled."
    exit 1
fi

# Build and push Docker image
echo "🏗️  Building Docker image..."
docker build -t $REGISTRY/$APP_NAME:$ENVIRONMENT -f docker/Dockerfile .

echo "📤 Pushing Docker image to registry..."
docker push $REGISTRY/$APP_NAME:$ENVIRONMENT

# Deploy using kustomize
echo "🚀 Deploying to Kubernetes..."
kustomize build k8s/overlays/$ENVIRONMENT | kubectl apply -f -

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/transcripter-app -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/ollama -n $NAMESPACE

# Check job status
echo "🔍 Checking model initialization job..."
kubectl wait --for=condition=complete --timeout=600s job/ollama-model-init -n $NAMESPACE || true

# Get service information
echo "📋 Deployment Information:"
kubectl get pods -n $NAMESPACE
kubectl get services -n $NAMESPACE
kubectl get ingress -n $NAMESPACE

echo "✅ Deployment complete!"
echo "🌐 Access your application at: https://transcripter.yourdomain.com"

# Show logs for troubleshooting
echo "📝 Recent logs from transcripter-app:"
kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=transcripter-app --tail=20
