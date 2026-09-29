import json
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

model = joblib.load("models/model.pkl")
test_df = pd.read_csv("data/processed/test.csv")
X, y = test_df.drop(columns=["target"]), test_df["target"]

preds = model.predict(X)
probs = model.predict_proba(X)[:, 1]

metrics = {
    "accuracy": float(accuracy_score(y, preds)),
    "f1": float(f1_score(y, preds)),
    "roc_auc": float(roc_auc_score(y, probs)),
}
json.dump(metrics, open("metrics.json", "w"), indent=2)
print(metrics)
