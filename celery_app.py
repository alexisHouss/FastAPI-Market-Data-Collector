from celery import Celery
import os
from tasks.celeryconfig import (
    CELERY_BEAT_SCHEDULE,
    CELERY_TASK_QUEUES,
    CELERY_TASK_ROUTES,
    CELERY_LOG_LEVEL,
)

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")


celery_app = Celery("market_data", broker=CELERY_BROKER_URL, backend=CELERY_BROKER_URL)
celery_app.conf.update(
    task_queues=CELERY_TASK_QUEUES,
    task_routes=CELERY_TASK_ROUTES,
    beat_schedule=CELERY_BEAT_SCHEDULE,
)

celery_app.autodiscover_tasks(
    ["tasks.market_reader_tasks", "tasks.stocks_tasks"],
    force=True,
)
