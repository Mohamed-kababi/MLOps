#!/usr/bin/env bash
# Load-test the InferenceService from inside the cluster (not through port-forward).
set -euo pipefail
cd "$(dirname "$0")"

kubectl create configmap k6-scripts \
  --from-file=load.js=../loadtest/load.js --from-file=payload.json=payload-v2.json \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl delete job k6-kserve --ignore-not-found
kubectl apply -f k6-job.yaml
kubectl wait --for=condition=complete job/k6-kserve --timeout=180s
kubectl logs job/k6-kserve
