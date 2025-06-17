from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
import atexit
 
class PortalAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Freewheel_Portal'
 
    def ready(self):
        from Freewheel_Portal.models import ShiftEndTable, SLABreachedTicket, ShiftEndTicketDetails
 
        def truncate_shift_end():
           
            ShiftEndTable.objects.all().delete()
            SLABreachedTicket.objects.all().delete()
            ShiftEndTicketDetails.objects.all().delete()
            print(f"ShiftEndTable truncated at {timezone.now()}")
 
        scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
        scheduler.add_job(truncate_shift_end, 'cron', hour=14, minute=28)
        scheduler.add_job(truncate_shift_end, 'cron', hour=11, minute=17)
        scheduler.add_job(truncate_shift_end, 'cron', hour=11, minute=17)
        scheduler.start()
 
        # Shut down scheduler on Django exit
        atexit.register(lambda: scheduler.shutdown())
 