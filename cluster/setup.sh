#!/usr/bin/env bash
# kind cluster for the serving path: Argo CD, Argo Rollouts, Prometheus, and a bridge to MLflow on this machine.
set -euo pipefail
cd "$(dirname "$0")"

kind create cluster --name mlops

# Argo CD — server-side apply, because some CRDs are too large for client-side
kubectl create namespace argocd
kubectl apply -n argocd --server-side \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Argo Rollouts (install the kubectl-argo-rollouts plugin separately)
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts \
  -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Prometheus, server only, 15 s scrape interval
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace \
  --set alertmanager.enabled=false --set prometheus-pushgateway.enabled=false \
  --set kube-state-metrics.enabled=false --set prometheus-node-exporter.enabled=false \
  --set server.persistentVolume.enabled=false --set server.global.scrape_interval=15s

# let pods reach MLflow on this machine as http://mlflow-host:5000
HOST_IP=$(docker network inspect kind -f '{{range .IPAM.Config}}{{.Gateway}} {{end}}' \
  | tr ' ' '\n' | grep -E '^[0-9]+(\.[0-9]+){3}$' | head -n1)
echo "kind gateway: $HOST_IP"
sed "s/HOST_IP/$HOST_IP/" mlflow-host.yaml | kubectl apply -f -
kubectl run curl --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s http://mlflow-host:5000/health        # expect: OK
