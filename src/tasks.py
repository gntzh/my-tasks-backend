from src.celery_app import app

import time


@app.task
def test(a: int, b: int):
    print(f"Computing：{a} + {b} ...")
    time.sleep(3)
    print(f"Result: {a + b}.")
