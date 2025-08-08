#!/bin/bash

# Monitoring and logging setup script
# Installs Prometheus, Grafana, and logging stack

set -e

echo "📊 Setting up monitoring and logging..."

# Install Prometheus using Helm
echo "📈 Installing Prometheus..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --create-namespace \
    --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
    --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
    --wait

# Install Loki for log aggregation
echo "📝 Installing Loki..."
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
    --namespace monitoring \
    --set promtail.enabled=true \
    --set loki.persistence.enabled=true \
    --set loki.persistence.size=10Gi \
    --wait

# Create ServiceMonitor for the transcripter app
echo "🔍 Creating ServiceMonitor..."
cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: transcripter-monitor
  namespace: transcripter
  labels:
    app.kubernetes.io/name: transcripter
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: transcripter-app
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
EOF

echo "✅ Monitoring setup complete!"
echo ""
echo "🌐 Access Grafana:"
echo "kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80"
echo "Default login: admin/prom-operator"
