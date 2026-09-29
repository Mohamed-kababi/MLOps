import os
import mlflow
import mlflow.sklearn
from dotenv import load_dotenv
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

load_dotenv()
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
mlflow.set_experiment("cancer-classifier")


def train(n_estimators: int = 100, max_depth: int = 5, run_name: str = "baseline"):
    X, y = load_breast_cancer(return_X_y=True, as_frame=True)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    with mlflow.start_run(run_name=run_name) as run:
        # 1. what you chose
        mlflow.log_params({
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "random_state": 42,
        })

        model = RandomForestClassifier(
            n_estimators=n_estimators, max_depth=max_depth, random_state=42
        )
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]

        # 2. what you got
        mlflow.log_metrics({
            "accuracy": accuracy_score(y_test, preds),
            "f1": f1_score(y_test, preds),
            "roc_auc": roc_auc_score(y_test, probs),
        })

        # 3. the model itself, with a signature and an input example
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            signature=mlflow.models.infer_signature(X_train, preds),
            input_example=X_train.head(3),
        )

        # 4. context a reviewer will want
        mlflow.set_tags({
            "dataset": "sklearn.breast_cancer",
            "owner": "platform",
            "stage": "experiment",
        })

        print(f"run_id={run.info.run_id}")
        return run.info.run_id


if __name__ == "__main__":
    train()
