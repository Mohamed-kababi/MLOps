import os
import mlflow
import pandas as pd
from dotenv import load_dotenv
from sklearn.datasets import load_breast_cancer

load_dotenv()
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])

MODEL_URI = "models:/cancer-classifier@champion"

model = mlflow.pyfunc.load_model(MODEL_URI)
print("loaded:", MODEL_URI)
print("signature:", model.metadata.signature)

X, _ = load_breast_cancer(return_X_y=True, as_frame=True)
sample = X.head(5)

preds = model.predict(sample)
print(pd.DataFrame({"prediction": preds}))
