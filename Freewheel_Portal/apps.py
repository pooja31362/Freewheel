from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils.timezone import localtime
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError
import atexit


class PortalAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Freewheel_Portal'
    