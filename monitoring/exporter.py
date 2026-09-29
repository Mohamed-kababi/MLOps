import os
import time

import boto3
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from prometheus_client import Gauge, start_http_server
from sklearn.datasets import load_breast_cancer
from evidently import Report
from evidently.presets import DataDriftPreset

WINDOW = int(os.getenv("WINDOW", "300"))
INTERVAL = int(os.getenv("INTERVAL_SECONDS", "30"))
MODE_FILE = "/control/mode"
WATCH = ["mean radius", "mean texture", "mean area"]

DRIFT_SHARE = Gauge("model_drift_share", "Share of columns flagged as drifted")
FEATURE_PSI = Gauge("model_feature_drift_psi", "PSI per watched feature", ["feature"])
PRED_PSI = Gauge("model_prediction_drift_psi", "PSI of the prediction column")
POS_RATE = Gauge("model_positive_rate", "Share of positive predictions in the window")
LAST_RUN = Gauge("model_drift_last_run_timestamp_seconds", "When the drift job last finished")

CHAMPION = Gauge("model_champion_version", "Registry version currently being monitored")

# live = where "production" traffic comes from in this demo
X_live, _ = load_breast_cancer(return_X_y=True, as_frame=True)

client = MlflowClient()
_loaded = {"version": None}


def load_champion():
    """Reload model and reference only when the champion alias has moved."""
    mv = client.get_model_version_by_alias("cancer-classifier", "champion")
    if mv.version == _loaded["version"]:
        return _loaded["model"], _loaded["reference"]

    md5 = mv.tags["data_md5"]                       # lineage written by the training DAG
    path = f"/tmp/ref_{md5}.csv"
    s3 = boto3.client("s3", endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"])
    s3.download_file("dvc-store", f"files/md5/{md5[:2]}/{md5[2:]}", path)

    model = mlflow.sklearn.load_model(f"models:/cancer-classifier/{mv.version}")
    X = pd.read_csv(path).drop(columns=["target"])
    reference = X.assign(prediction=model.predict(X))

    _loaded.update(version=mv.version, model=model, reference=reference)
    CHAMPION.set(int(mv.version))
    return model, reference


def world() -> str:
    try:
        return open(MODE_FILE).read().strip()
    except FileNotFoundError:
        return "normal"


def live_window(rng, model) -> pd.DataFrame:
    # stand-in for reading the last WINDOW rows from a prediction log
    w = X_live.sample(WINDOW, replace=True, random_state=int(rng.integers(1_000_000_000))).copy()
    if world() == "shifted":
        mean_cols = [c for c in w.columns if c.startswith("mean ")]
        w[mean_cols] = w[mean_cols] * 1.3
    return w.assign(prediction=model.predict(w))


def metric_name(m: dict) -> str:
    return str(m.get("metric_id") or m.get("metric_name") or m.get("id") or "")


def publish(snapshot, current) -> float:
    share = float("nan")
    for m in snapshot.dict()["metrics"]:
        name = metric_name(m)
        if "DriftedColumnsCount" in name:
            share = float(m["value"]["share"])
            DRIFT_SHARE.set(share)
        elif "ValueDrift" in name:
            for f in WATCH:
                if f"column={f}" in name:
                    FEATURE_PSI.labels(feature=f).set(float(m["value"]))
            if "column=prediction" in name:
                PRED_PSI.set(float(m["value"]))
    POS_RATE.set(float(current["prediction"].mean()))
    LAST_RUN.set_to_current_time()
    return share


if __name__ == "__main__":
    start_http_server(8000)
    rng = np.random.default_rng()
    while True:
        try:
            model, reference = load_champion()
        except MlflowException:
            print("no champion in the registry yet; waiting")
            time.sleep(INTERVAL)
            continue
        current = live_window(rng, model)
        snapshot = Report([DataDriftPreset(method="psi")]).run(current, reference)
        share = publish(snapshot, current)
        print(f"champion=v{_loaded['version']} world={world():8s} drift_share={share:.2f}")
        time.sleep(INTERVAL)
