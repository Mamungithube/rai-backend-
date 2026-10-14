import os
import sys
from pathlib import Path
from celery import Celery
from celery.signals import task_failure
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "apps"))
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

logger = logging.getLogger(__name__)

@task_failure.connect
def log_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    logger.error(f"Task {sender.name} (ID: {task_id}) failed: {exception}", exc_info=True)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logger.info(f'Request: {self.request!r}')