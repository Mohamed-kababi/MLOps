import yaml
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

params = yaml.safe_load(open("params.yaml"))["prepare"]
df = pd.read_csv("data/raw/cancer.csv")

train_df, test_df = train_test_split(
    df,
    test_size=params["test_size"],
    random_state=params["random_state"],
    stratify=df["target"],
)

Path("data/processed").mkdir(parents=True, exist_ok=True)
train_df.to_csv("data/processed/train.csv", index=False)
test_df.to_csv("data/processed/test.csv", index=False)
print(f"train={len(train_df)} test={len(test_df)}")
