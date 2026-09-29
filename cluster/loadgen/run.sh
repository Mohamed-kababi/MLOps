#!/usr/bin/env bash
# Steady, varied traffic for canary analysis: random real rows at 10 req/s for 20 minutes.
set -euo pipefail
cd "$(dirname "$0")"

python3 -c "import json; from sklearn.datasets import load_breast_cancer as l; json.dump(l(return_X_y=True)[0].tolist(), open('rows.json', 'w'))"
kubectl create configmap k6-mix --from-file=load-mix.js --from-file=rows.json \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl delete pod k6 --ignore-not-found
kubectl run k6 --restart=Never --image=grafana/k6:latest \
  --overrides='{"spec":{"volumes":[{"name":"s","configMap":{"name":"k6-mix"}}],"containers":[{"name":"k6","image":"grafana/k6:latest","args":["run","/scripts/load-mix.js"],"volumeMounts":[{"name":"s","mountPath":"/scripts"}]}]}}'
