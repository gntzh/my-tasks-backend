import time
import os
from celery import Celery
from src import celery_config

app = Celery(broker=os.environ["CELERY_BROKEY_URL"])

app.config_from_object(celery_config)


@app.task
def test() -> None:
    print("I am here..........")
    time.sleep(5)
    print("Completed!!!!!!!!!!")
