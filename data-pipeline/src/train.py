import os
import subprocess
from pathlib import Path

import joblib
import yaml
import mlflow
import mlflow.sklearn
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier


def git_sha() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True
        ).strip()
        return f"{sha}-dirty" if dirty else sha
    except subprocess.CalledProcessError:
        return "unknown"


def data_hash(dvc_file: str = "data/raw/cancer.csv.dvc") -> str:
    meta = yaml.safe_load(open(dvc_file))
    return meta["outs"][0]["md5"]


load_dotenv()
params = yaml.safe_load(open("params.yaml"))["train"]
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
mlflow.set_experiment("cancer-classifier")

train_df = pd.read_csv("data/processed/train.csv")
X, y = train_df.drop(columns=["target"]), train_df["target"]

with mlflow.start_run():
    mlflow.log_params(params)

    # the lineage tags
    mlflow.set_tags({
        "git_sha": git_sha(),
        "data_md5": data_hash(),
        "data_rows": len(train_df),
        "dvc_stage": "train",
    })

    model = RandomForestClassifier(**params, random_state=42)
    model.fit(X, y)

    mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        signature=mlflow.models.infer_signature(X, model.predict(X)),
    )

# the dvc.yaml stage output, read by the evaluate stage
Path("models").mkdir(exist_ok=True)
joblib.dump(model, "models/model.pkl")
