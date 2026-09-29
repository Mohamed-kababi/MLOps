FROM apache/airflow:3.3.2-python3.12

# pin apache-airflow in the same install so pip cannot upgrade it
RUN pip install --no-cache-dir \
    "apache-airflow==3.3.2" \
    "mlflow-skinny==2.16.2" \
    "scikit-learn==1.5.2" \
    "pandas==2.2.3" \
    "boto3==1.35.36"
