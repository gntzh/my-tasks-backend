import time

from celery import Celery
from src import celery_config

app = Celery(broker="redis://127.0.0.1:6379/0")

app.config_from_object(celery_config)


@app.task
def test() -> None:
    print("I am here..........")
    time.sleep(5)
    print("Completed!!!!!!!!!!")
