from feast import FeatureStore

store = FeatureStore(repo_path="feature_repo")

features = store.get_online_features(
    features=[
        "customer_stats:avg_txn_30d",
        "customer_stats:txn_count_7d",
    ],
    entity_rows=[{"customer_id": 1001}, {"customer_id": 1002}],
).to_dict()

print(features)
