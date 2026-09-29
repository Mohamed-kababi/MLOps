import json

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from evidently import Report
from evidently.presets import DataDriftPreset

X, _ = load_breast_cancer(return_X_y=True, as_frame=True)
reference, current = train_test_split(X, test_size=0.5, random_state=42)

shifted = current.copy()
mean_cols = [c for c in shifted.columns if c.startswith("mean ")]
shifted[mean_cols] = shifted[mean_cols] * 1.3        # the world moved

for name, cur in [("same-world", current), ("shifted-world", shifted)]:
    snapshot = Report([DataDriftPreset(method="psi")]).run(cur, reference)
    snapshot.save_html(f"drift-{name}.html")

    metrics = snapshot.dict()["metrics"]
    print(f"\n=== {name}: {len(metrics)} metrics ===")
    print(json.dumps(metrics[:2], indent=2, default=str))
