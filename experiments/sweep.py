import os
import mlflow
from dotenv import load_dotenv
from train import train

load_dotenv()
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])

GRID = [
    {"n_estimators": 50,  "max_depth": 3,  "run_name": "small"},
    {"n_estimators": 200, "max_depth": 8,  "run_name": "medium"},
    {"n_estimators": 500, "max_depth": 16, "run_name": "large"},
]

for cfg in GRID:
    train(**cfg)

# select the winner without opening the UI
best = mlflow.search_runs(
    experiment_names=["cancer-classifier"],
    order_by=["metrics.roc_auc DESC"],
    max_results=1,
)

print(best[["run_id", "tags.mlflow.runName",
            "params.n_estimators", "metrics.roc_auc"]])
print("winner:", best.iloc[0].run_id)
