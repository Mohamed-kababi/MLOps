import os
import re
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import dag, task, get_current_context
from airflow.providers.standard.operators.empty import EmptyOperator

MODEL_NAME = "cancer-classifier"
DATA_DIR = Path("/opt/airflow/data")
DVC_POINTER = Path("/opt/airflow/data-pipeline/data/raw/cancer.csv.dvc")


def _run_key() -> str:
    # filesystem-safe key, stable across retries of the same DAG run
    return re.sub(r"[^A-Za-z0-9_-]", "_", get_current_context()["run_id"])


@dag(
    dag_id="ml_training",
    schedule="@weekly",
    start_date=pendulum.datetime(2026, 9, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=30)},
    tags=["mlops", "ct"],
)
def ml_training():

    @task
    def fetch_data() -> dict:
        import boto3
        import yaml

        # handoff 1: the .dvc pointer is the contract; its md5 is the data's identity
        pointer = yaml.safe_load(open(DVC_POINTER))
        md5 = pointer["outs"][0]["md5"]

        path = DATA_DIR / f"cancer_{md5}.csv"      # content-addressed: idempotent by construction
        if not path.exists():
            s3 = boto3.client("s3", endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"])
            key = f"files/md5/{md5[:2]}/{md5[2:]}"   # DVC 3 remote layout
            s3.download_file(os.environ["DVC_BUCKET"], key, str(path))
        return {"path": str(path), "md5": md5}

    @task
    def train(data: dict) -> dict:
        import mlflow
        import mlflow.sklearn
        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split

        if (DATA_DIR / "FAIL_TRAIN").exists():      # failure switch for the retry drill
            raise RuntimeError("FAIL_TRAIN flag is present")

        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment("cancer-classifier")
        key, md5 = _run_key(), data["md5"]

        df = pd.read_csv(data["path"])
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["target"])
        test_path = DATA_DIR / f"test_{md5}.csv"
        test_df.to_csv(test_path, index=False)      # evaluate scores both models on this file

        # idempotent: a retry reuses a finished MLflow run from this DAG run
        done = mlflow.search_runs(
            experiment_names=["cancer-classifier"],
            filter_string=f"tags.airflow_run_key = '{key}' and attributes.status = 'FINISHED'",
        )
        if len(done):
            return {"run_id": done.iloc[0].run_id, "test_path": str(test_path)}

        X, y = train_df.drop(columns=["target"]), train_df["target"]
        params = {"n_estimators": 200, "max_depth": 8}
        conf = get_current_context()["dag_run"].conf or {}
        with mlflow.start_run(run_name=f"airflow-{key}") as run:
            mlflow.set_tags({
                "airflow_run_key": key,
                "airflow_try": get_current_context()["ti"].try_number,
                "data_md5": md5,
                "dvc_file": "data/raw/cancer.csv.dvc",
                "trigger_reason": conf.get("reason", "schedule"),
            })
            mlflow.log_params(params)
            model = RandomForestClassifier(**params, random_state=42).fit(X, y)
            mlflow.sklearn.log_model(model, artifact_path="model",
                                     signature=mlflow.models.infer_signature(X, model.predict(X)))
            return {"run_id": run.info.run_id, "test_path": str(test_path)}

    @task
    def evaluate(trained: dict) -> dict:
        import mlflow
        import mlflow.sklearn
        import pandas as pd
        from mlflow import MlflowClient
        from mlflow.exceptions import MlflowException
        from sklearn.metrics import roc_auc_score

        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        test = pd.read_csv(trained["test_path"])
        X_te, y_te = test.drop(columns=["target"]), test["target"]

        def score(uri: str) -> float:
            m = mlflow.sklearn.load_model(uri)
            return float(roc_auc_score(y_te, m.predict_proba(X_te)[:, 1]))

        candidate = score(f"runs:/{trained['run_id']}/model")
        try:
            MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion")
            champion = score(f"models:/{MODEL_NAME}@champion")   # re-scored on today's data
        except MlflowException:
            champion = None                          # first ever run: no champion yet
        return {"run_id": trained["run_id"], "candidate": candidate, "champion": champion}

    @task.branch
    def decide(result: dict) -> str:
        if result["champion"] is None or result["candidate"] > result["champion"]:
            return "register"
        return "skip"

    @task
    def register(result: dict) -> str:
        import mlflow
        from mlflow import MlflowClient

        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        client = MlflowClient()
        run_id = result["run_id"]

        # idempotent: never register the same run twice
        found = client.search_model_versions(f"name='{MODEL_NAME}' and run_id='{run_id}'")
        version = found[0].version if found else mlflow.register_model(
            f"runs:/{run_id}/model", MODEL_NAME).version

        # handoff 2: the registry records a nominee; only a finished canary crowns a champion
        client.set_model_version_tag(MODEL_NAME, version, "data_md5",
                                     client.get_run(run_id).data.tags["data_md5"])
        client.set_registered_model_alias(MODEL_NAME, "candidate", version)
        return version

    @task
    def open_pr(version: str, result: dict) -> str:
        import base64
        import requests

        repo = os.environ["GITOPS_REPO"]
        api = f"https://api.github.com/repos/{repo}"
        h = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
             "Accept": "application/vnd.github+json"}
        path, branch = os.environ["GITOPS_PATH"], f"model-v{version}"

        # idempotent: a retry finds the open PR instead of opening a second one
        owner = repo.split("/")[0]
        open_prs = requests.get(f"{api}/pulls", headers=h,
                                params={"head": f"{owner}:{branch}", "state": "open"}).json()
        if open_prs:
            return open_prs[0]["html_url"]

        # nothing to propose if main already deploys this version (e.g. v1 on a fresh setup)
        on_main = requests.get(f"{api}/contents/{path}", headers=h, params={"ref": "main"}).json()
        if f'"models:/{MODEL_NAME}/{version}"' in base64.b64decode(on_main["content"]).decode():
            return f"{path} on main already deploys v{version}; no PR needed"

        main_sha = requests.get(f"{api}/git/ref/heads/main", headers=h).json()["object"]["sha"]
        r = requests.post(f"{api}/git/refs", headers=h,
                          json={"ref": f"refs/heads/{branch}", "sha": main_sha})
        if r.status_code not in (201, 422):      # 422: branch left over from an earlier try
            r.raise_for_status()

        f = requests.get(f"{api}/contents/{path}", headers=h, params={"ref": branch}).json()
        old = base64.b64decode(f["content"]).decode()
        new = re.sub(r'(name: MODEL_VERSION\n\s+value: )"[^"]*"', rf'\g<1>"{version}"', old)
        new = re.sub(r'(name: MODEL_URI\n\s+value: )"[^"]*"',
                     rf'\g<1>"models:/{MODEL_NAME}/{version}"', new)
        new = re.sub(r'(name: model-version\n\s+value: )"[^"]*"', rf'\g<1>"{version}"', new)

        if new != old:
            requests.put(f"{api}/contents/{path}", headers=h, json={
                "message": f"model: canary {MODEL_NAME} v{version}",
                "content": base64.b64encode(new.encode()).decode(),
                "sha": f["sha"], "branch": branch,
            }).raise_for_status()

        champ = result["champion"]
        body = (
            f"Candidate **v{version}** passed offline evaluation. Merging starts a canary.\n\n"
            f"| | ROC AUC on today's test set |\n| --- | --- |\n"
            f"| Candidate v{version} | {result['candidate']:.4f} |\n"
            f"| Current champion | {'none' if champ is None else f'{champ:.4f}'} |\n\n"
            f"MLflow run: `{result['run_id']}`"
        )
        pr = requests.post(f"{api}/pulls", headers=h, json={
            "title": f"Canary {MODEL_NAME} v{version}", "head": branch, "base": "main", "body": body,
        })
        pr.raise_for_status()
        return pr.json()["html_url"]

    @task(trigger_rule="none_failed_min_one_success")
    def notify(result: dict) -> None:
        won = result["champion"] is None or result["candidate"] > result["champion"]
        verdict = "candidate proposed" if won else "kept champion"
        print(f"candidate={result['candidate']:.4f} champion={result['champion']} -> {verdict}")

    result = evaluate(train(fetch_data()))
    branch = decide(result)
    registered = register(result)
    proposed = open_pr(registered, result)
    skipped = EmptyOperator(task_id="skip")

    branch >> [registered, skipped]
    [proposed, skipped] >> notify(result)


ml_training()
