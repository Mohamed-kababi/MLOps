import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

np.random.seed(42)
rows = []
for customer_id in range(1001, 1011):
    for day in range(30):
        ts = datetime(2026, 9, 1) + timedelta(days=day)
        rows.append({
            "customer_id": customer_id,
            "event_timestamp": ts,
            "created": ts,
            "avg_txn_30d": float(np.random.uniform(50, 5000)),
            "txn_count_7d": int(np.random.randint(0, 40)),
            "chargeback_rate": float(np.random.uniform(0, 0.15)),
        })

Path("feature_repo/data").mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_parquet("feature_repo/data/customer_features.parquet")
print("wrote 300 rows across 10 customers and 30 days")
