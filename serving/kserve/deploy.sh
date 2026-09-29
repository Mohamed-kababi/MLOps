#!/usr/bin/env bash
# In-cluster MinIO, a seeded model, and the InferenceService that serves it.
set -euo pipefail
cd "$(dirname "$0")"

kubectl apply -f minio.yaml
kubectl rollout status deploy/minio
kubectl apply -f seeder.yaml
kubectl wait --for=condition=complete job/model-seeder --timeout=300s
kubectl logs job/model-seeder | tail -n 1 > payload-v2.json

kubectl apply -f s3-access.yaml -f isvc.yaml
kubectl wait --for=condition=Ready inferenceservice/cancer-classifier --timeout=300s

echo "Try it:"
echo "  kubectl port-forward svc/cancer-classifier-predictor 8080:80 &"
echo "  curl -s -X POST http://localhost:8080/v2/models/cancer-classifier/infer -H 'Content-Type: application/json' -d @payload-v2.json"
