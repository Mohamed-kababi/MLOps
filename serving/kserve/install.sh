#!/usr/bin/env bash
# Install cert-manager and KServe (Standard mode) into the current cluster.
set -euo pipefail

# cert-manager provisions the KServe webhook certificates
helm repo add jetstack https://charts.jetstack.io && helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set crds.enabled=true
kubectl -n cert-manager rollout status deploy/cert-manager-webhook

# KServe controller and CRDs — server-side apply, because the CRD is large
kubectl apply --server-side \
  -f https://github.com/kserve/kserve/releases/download/v0.20.0/kserve.yaml
kubectl -n kserve rollout status deploy/kserve-controller-manager

# the built-in runtimes: MLServer, Triton, the Hugging Face / vLLM runtime
kubectl apply --server-side \
  -f https://github.com/kserve/kserve/releases/download/v0.20.0/kserve-cluster-resources.yaml

# switch the default from Knative to Standard
kubectl patch configmap/inferenceservice-config -n kserve --type=strategic \
  -p '{"data": {"deploy": "{\"defaultDeploymentMode\": \"Standard\"}"}}'

kubectl get clusterservingruntimes
