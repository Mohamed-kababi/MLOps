"""Write the raw dataset that DVC tracks: data/raw/cancer.csv."""
from pathlib import Path

from sklearn.datasets import load_breast_cancer

X, y = load_breast_cancer(return_X_y=True, as_frame=True)
Path("data/raw").mkdir(parents=True, exist_ok=True)
X.assign(target=y).to_csv("data/raw/cancer.csv", index=False)
print("rows:", len(X))
