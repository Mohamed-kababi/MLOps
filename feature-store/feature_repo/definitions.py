from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64

customer = Entity(
    name="customer",
    join_keys=["customer_id"],
    description="the account a transaction belongs to",
)

source = FileSource(
    path="data/customer_features.parquet",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

customer_stats = FeatureView(
    name="customer_stats",
    entities=[customer],
    ttl=timedelta(days=7),
    schema=[
        Field(name="avg_txn_30d", dtype=Float32),
        Field(name="txn_count_7d", dtype=Int64),
        Field(name="chargeback_rate", dtype=Float32),
    ],
    source=source,
    online=True,
)
