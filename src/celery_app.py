import time

from celery import Celery

app = Celery("tasks", broker="redis://127.0.0.1:6379/0")

app.conf.timezone = "Asia/Shanghai"


@app.task
def test() -> None:
    print("I am here..........")
    time.sleep(5)
    print("Completed!!!!!!!!!!")
