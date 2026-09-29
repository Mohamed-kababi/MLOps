import pandas as pd
from datetime import datetime
from feast import FeatureStore

store = FeatureStore(repo_path="feature_repo")

# labels with the date each one was observed
entity_df = pd.DataFrame({
    "customer_id": [1001, 1002, 1003],
    "event_timestamp": [
        datetime(2026, 9, 10),
        datetime(2026, 9, 20),
        datetime(2026, 9, 25),
    ],
    "label": [0, 1, 0],
})

training_df = store.get_historical_features(
    entity_df=entity_df,
    features=[
        "customer_stats:avg_txn_30d",
        "customer_stats:txn_count_7d",
        "customer_stats:chargeback_rate",
    ],
).to_df()

print(training_df)
