from django.utils import timezone
from .models import User
from django.utils.deprecation import MiddlewareMixin
import logging
 
logger = logging.getLogger(__name__)
 
class LeaveStatusMiddleware(MiddlewareMixin):
    def process_request(self, request):
 
        emp_id = request.session.get('emp_id')
        if not emp_id:
            print("⚠️ No emp_id found in session. Skipping LeaveStatusMiddleware.")
            return  # Exit early if not logged in
 
        try:
            current_user = User.objects.get(emp_id=emp_id)
            if current_user.status == "Out Of Office" and current_user.leave_until:
                print(f"⏰ Current Time: {timezone.now()}, Leave Until: {current_user.leave_until}")
                if timezone.now() > current_user.leave_until != None:
                    print("🔁 Switching user back to Offline")
                    current_user.status = "Offline"
                    current_user.leave_until = None
                    current_user.save()
        except User.DoesNotExist:
            print(f"❌ User with emp_id {emp_id} not found.")