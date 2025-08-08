#!/bin/bash

# Setup script for DigitalOcean Kubernetes deployment
# This script sets up the necessary infrastructure

set -e

echo "🔧 Setting up DigitalOcean Kubernetes infrastructure..."

# Check if doctl is authenticated
if ! doctl auth list > /dev/null 2>&1; then
    echo "❌ Please authenticate with DigitalOcean CLI first:"
    echo "   doctl auth init"
    exit 1
fi

# Variables (update these with your values)
CLUSTER_NAME="transcripter-k8s"
REGION="nyc1"
NODE_SIZE="s-2vcpu-4gb"
NODE_COUNT=3
REGISTRY_NAME="transcripter-registry"

echo "📋 Configuration:"
echo "   Cluster: $CLUSTER_NAME"
echo "   Region: $REGION"
echo "   Node Size: $NODE_SIZE"
echo "   Node Count: $NODE_COUNT"
echo "   Registry: $REGISTRY_NAME"

read -p "🤔 Proceed with infrastructure setup? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Setup cancelled."
    exit 1
fi

# Create Container Registry
echo "🐳 Creating DigitalOcean Container Registry..."
doctl registry create $REGISTRY_NAME --region $REGION || echo "Registry might already exist"

# Create Kubernetes Cluster
echo "☸️  Creating Kubernetes cluster..."
doctl kubernetes cluster create $CLUSTER_NAME \
    --region $REGION \
    --node-pool "name=transcripter-pool;size=$NODE_SIZE;count=$NODE_COUNT;auto-scale=true;min-nodes=1;max-nodes=5" \
    --wait

# Configure kubectl
echo "🔧 Configuring kubectl..."
doctl kubernetes cluster kubeconfig save $CLUSTER_NAME

# Install NGINX Ingress Controller
echo "🌐 Installing NGINX Ingress Controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/do/deploy.yaml

# Wait for NGINX controller to be ready
echo "⏳ Waiting for NGINX controller to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=300s

# Install cert-manager for SSL certificates
echo "🔒 Installing cert-manager..."
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
echo "⏳ Waiting for cert-manager to be ready..."
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=300s

# Create ClusterIssuer for Let's Encrypt
echo "📜 Creating ClusterIssuer for SSL certificates..."
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com  # Update this with your email
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Configure Docker registry authentication
echo "🔑 Configuring Docker registry authentication..."
doctl registry docker-config | kubectl apply -f -

echo "✅ Infrastructure setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update the registry name in k8s/overlays/*/kustomization.yaml"
echo "2. Update the domain name in k8s/base/ingress.yaml"
echo "3. Update the email in the ClusterIssuer above"
echo "4. Run ./scripts/deploy.sh staging to deploy to staging"
echo "5. Run ./scripts/deploy.sh production to deploy to production"
echo ""
echo "🔍 Cluster info:"
doctl kubernetes cluster get $CLUSTER_NAME
