from django.utils import timezone
from .models import User
from django.utils.deprecation import MiddlewareMixin
import logging
 
logger = logging.getLogger(__name__)
 
class LeaveStatusMiddleware(MiddlewareMixin):
    def process_request(self, request):
        print("🔥 LeaveStatusMiddleware is active")
 
        emp_id = request.session.get('emp_id')
        if not emp_id:
            print("⚠️ No emp_id found in session. Skipping LeaveStatusMiddleware.")
            return  # Exit early if not logged in
 
        try:
            user = User.objects.get(emp_id=emp_id)
            print(f"👤 User: {user.assignee_name}, Status: {user.status}")
            if user.status == "Out Of Office" and user.leave_until:
                print(f"⏰ Current Time: {timezone.now()}, Leave Until: {user.leave_until}")
                if timezone.now() > user.leave_until:
                    print("🔁 Switching user back to Offline")
                    user.status = "Offline"
                    user.leave_until = None
                    user.save()
        except User.DoesNotExist:
            print(f"❌ User with emp_id {emp_id} not found.")