"""One-time bootstrap: crown the first candidate as champion.

On a fresh setup nothing has been promoted yet, and the first rollout skips its analysis
steps, so the promote-in-registry Job never runs. After the first DAG run registers v1 as
`candidate`, run this once. Every later promotion goes through the canary.
"""
import os

from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

NAME = "cancer-classifier"
client = MlflowClient(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))

try:
    current = client.get_model_version_by_alias(NAME, "champion")
    raise SystemExit(f"champion already set (v{current.version}); nothing to do")
except MlflowException:
    pass

mv = client.get_model_version_by_alias(NAME, "candidate")
client.set_registered_model_alias(NAME, "champion", mv.version)
client.delete_registered_model_alias(NAME, "candidate")
client.set_model_version_tag(NAME, mv.version, "promoted_by", "bootstrap")
print(f"champion -> v{mv.version}; set MODEL_VERSION, MODEL_URI and model-version in "
      f"gitops/serving/rollout.yaml to {mv.version} before the first Argo CD sync")
