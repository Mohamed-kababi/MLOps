"""Register a model trained on inverted labels.

Point a PR at the version this prints and merge it: the canary stays healthy and fast,
but the prediction-mix analysis fails and the rollout aborts at 25%.
"""
import mlflow
import mlflow.sklearn
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier

mlflow.set_tracking_uri("http://localhost:5000")
X, y = load_breast_cancer(return_X_y=True, as_frame=True)
m = RandomForestClassifier(n_estimators=200, random_state=42).fit(X, 1 - y)   # every label inverted
with mlflow.start_run():
    mlflow.set_tag("data_md5", "drill-flipped-labels")
    info = mlflow.sklearn.log_model(m, "model", signature=mlflow.models.infer_signature(X, m.predict(X)),
                                    registered_model_name="cancer-classifier")
print("registered version:", info.registered_model_version)
