import logging
from django.utils import timezone
from .models import User

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class LeaveStatusMiddleware(MiddlewareMixin):
    def process_request(self, request):
        print("🔥 LeaveStatusMiddleware is active")

        user = User.objects.get(emp_id=request.session['emp_id'])
        print(f"👤 User: {user.assignee_name}, Status: {user.status}")
        if user.status == "Out Of Office" and user.leave_until:
            print(timezone.now())
            print(user.leave_until)
            if timezone.now() > user.leave_until:
                print("🔁 Switching user back to Offline")
                user.status = "Offline"
                user.leave_until = None
                user.save()
