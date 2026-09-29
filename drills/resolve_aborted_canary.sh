#!/usr/bin/env bash
# After an aborted canary: make Git match the cluster, and record the outcome on the model version.
# usage: resolve_aborted_canary.sh <merge-commit-of-the-model-PR> <model-version> [reason]
set -euo pipefail
commit=$1 version=$2 reason=${3:-prediction-mix}

git revert --no-edit "$commit" && git push

MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI:-http://localhost:5000} python3 - "$version" "$reason" <<'PY'
import sys
from mlflow import MlflowClient
version, reason = sys.argv[1], sys.argv[2]
c = MlflowClient()
c.set_model_version_tag("cancer-classifier", version, "canary", f"aborted: {reason}")
c.delete_registered_model_alias("cancer-classifier", "candidate")
print(f"v{version} tagged canary=aborted: {reason}; candidate alias removed")
PY
