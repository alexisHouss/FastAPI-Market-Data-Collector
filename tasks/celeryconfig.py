from celery.schedules import crontab
from datetime import timedelta
from kombu import Exchange, Queue
import logging

CELERY_BEAT_SCHEDULE = {
    "market_data_collector": {
        "task": "tasks.market_reader_tasks.get_market_data",
        "schedule": timedelta(minutes=5),  # Run every 5 minutes
    },
}


CELERY_TASK_QUEUES = (Queue("default", Exchange("default"), routing_key="default"),)

CELERY_TASK_ROUTES = {
    "tasks.market_reader_tasks.*": {"queue": "default"},
    "tasks.stocks_tasks.*": {"queue": "default"},
}

CELERY_LOG_LEVEL = logging.CRITICAL
