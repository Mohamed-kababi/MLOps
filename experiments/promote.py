import os
import mlflow
from mlflow import MlflowClient
from dotenv import load_dotenv

load_dotenv()
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
client = MlflowClient()

MODEL_NAME = "cancer-classifier"
METRIC = "roc_auc"

# 1. find the best run
best = mlflow.search_runs(
    experiment_names=["cancer-classifier"],
    order_by=[f"metrics.{METRIC} DESC"],
    max_results=1,
).iloc[0]
candidate_score = float(best[f"metrics.{METRIC}"])

# 2. register it as a new version
version = mlflow.register_model(
    model_uri=f"runs:/{best.run_id}/model",
    name=MODEL_NAME,
)
print(f"registered version {version.version} from run {best.run_id}")

# 3. describe it, so a reviewer knows what this version is
client.update_model_version(
    name=MODEL_NAME,
    version=version.version,
    description=f"RandomForest, {METRIC}={candidate_score:.4f}",
)
client.set_model_version_tag(
    MODEL_NAME, version.version, "validated_by", "sweep.py"
)

# 4. promote only if it beats the incumbent
try:
    current = client.get_model_version_by_alias(MODEL_NAME, "champion")
    current_run = client.get_run(current.run_id)
    current_score = current_run.data.metrics[METRIC]
except Exception:
    current, current_score = None, -1.0

if candidate_score > current_score:
    if current is not None:
        client.set_registered_model_alias(
            MODEL_NAME, "previous", current.version
        )
    client.set_registered_model_alias(
        MODEL_NAME, "champion", version.version
    )
    print(f"promoted v{version.version} ({candidate_score:.4f} > {current_score:.4f})")
else:
    client.set_registered_model_alias(
        MODEL_NAME, "challenger", version.version
    )
    print(f"held back v{version.version}; champion stays at v{current.version}")
