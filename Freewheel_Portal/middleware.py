from django.utils import timezone
from .models import User
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class LeaveStatusMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/static/') or request.path in ['/login/', '/favicon.ico']:
            return  # Skip session check for static and login paths

        emp_id = request.session.get('emp_id')
        if not emp_id:
            print("⚠️ No emp_id found in session. Skipping LeaveStatusMiddleware.")
            return

        try:
            current_user = User.objects.get(emp_id=emp_id)
            if current_user.status == "Out Of Office" and current_user.leave_until:
                if timezone.now() > current_user.leave_until:
                    current_user.status = "Offline"
                    current_user.leave_until = None
                    current_user.save()
        except User.DoesNotExist:
            print(f"❌ User with emp_id {emp_id} not found.")
