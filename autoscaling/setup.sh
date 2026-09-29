#!/usr/bin/env bash
# metrics-server, Prometheus (server only, 15 s scrape), KEDA, the stand-in inference server and its load generator.
set -euo pipefail
cd "$(dirname "$0")"

kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
# lab clusters use self-signed kubelet certs
kubectl -n kube-system patch deploy metrics-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add kedacore https://kedacore.github.io/charts
helm repo update

helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace \
  --set alertmanager.enabled=false \
  --set prometheus-pushgateway.enabled=false \
  --set kube-state-metrics.enabled=false \
  --set prometheus-node-exporter.enabled=false \
  --set server.persistentVolume.enabled=false \
  --set server.global.scrape_interval=15s

helm upgrade --install keda kedacore/keda --namespace keda --create-namespace

kubectl apply -f fake-infer.yaml
kubectl rollout status deploy/fake-infer

echo '{"x": 1}' > payload.json
kubectl create configmap k6-infer --from-file=load.js=../serving/loadtest/load.js --from-file=payload.json \
  --dry-run=client -o yaml | kubectl apply -f -
