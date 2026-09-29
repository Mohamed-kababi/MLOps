import pendulum
from airflow.sdk import dag, task


@dag(
    dag_id="hello",
    schedule=None,                       # manual trigger only
    start_date=pendulum.datetime(2026, 9, 1, tz="UTC"),
    tags=["lab"],
)
def hello():

    @task
    def extract() -> dict:
        return {"rows": 569, "source": "sklearn"}

    @task
    def report(meta: dict) -> None:
        print(f"received {meta['rows']} rows from {meta['source']}")

    report(extract())


hello()
