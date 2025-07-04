# Django core imports
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.utils.timezone import now, localdate, localtime, make_aware
from django.utils.crypto import get_random_string
from django.contrib.auth import logout
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.core.mail import send_mail
from django.db.models import Count, Q, Case, When, Value, IntegerField
from django.conf import settings


# DRF imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

# Python stdlib & third-party
import json
import datetime
from datetime import date, datetime, timedelta
import pandas as pd
import os
from collections import defaultdict, OrderedDict
from dateutil import parser

# Local app imports
from .models import (
    Ticket, User, Schedule, Notice,
    TicketReport, GroupAccess, Access,
    ShiftEndTable, ShiftEndTicketDetails, SLABreachedTicket,
    PreviousShiftEndTable, PreviousShiftEndTicketDetails, PreviousSLABreachedTicket
)
from .forms import UserForm
from .constants import SHIFT1_TIMINGS, SHIFT3_TIMINGS, SHIFT6_TIMINGS, ALLOWED_USERS
from .utils import (
    get_today_shift_for_user, populate_summary_data, truncate_shift_end
)

# Cross-app imports
from Freewheel_Portal.models import User as FWUser
from Freewheel_Portal.utils import (
    get_today_shift_for_user as FW_get_today_shift_for_user,
    get_utc_half_hour_distribution,
    get_shifts_for_date,
    get_shifts_for_date_range
)


class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": f"Hello {request.user.username}, you're authenticated via JWT."})







class LoginTemplateView(APIView):
    """
    Only serves the login template view — useful for frontend-rendered pages.
    """
    def get(self, request):
        return Response({"template": "Freewheel_Portal/login.html"}, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    """
    Clears session and sets user status to 'Offline'
    """

    def get(self, request):
        emp_id = request.session.get('emp_id')
        if emp_id:
            try:
                user = User.objects.get(emp_id=emp_id)
                user.status = "Offline"
                user.save(update_fields=['status'])
            except User.DoesNotExist:
                pass

        request.session.flush()  # Clears session data securely
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
    


ALLOWED_USERS = ['anibro', 'Nisha', 'Harikishore T', 'keerthana', 'kavya_akka']
SHIFT1_TIMINGS = ["7:00 AM", "9:00 AM", "11:00 AM", "1:00 PM"]
SHIFT3_TIMINGS = ["3:00 PM", "5:00 PM", "7:00 PM", "9:00 PM"]
SHIFT6_TIMINGS = ["11:00 AM", "1:00 AM", "3:00 AM", "5:00 AM"]

class HomeAPIView(APIView):
    def get_current_user(self, request):
        emp_id = request.session.get('emp_id')
        if not emp_id:
            return None
        return User.objects.get(emp_id=emp_id)

    def post(self, request, *args, **kwargs):
        if 'emp_id' not in request.session:
            return Response({'detail': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

        current_user = self.get_current_user(request)

        try:
            data = request.data
            shift1_status = data.get('shift1_status', {})
            shift3_status = data.get('shift3_status', {})
            shift6_status = data.get('shift6_status', {})

            shift1_end_user = User.objects.filter(emp_id=data.get('shift1_end_email')).first()
            shift3_end_user = User.objects.filter(emp_id=data.get('shift3_end_email')).first()
            shift6_end_user = User.objects.filter(emp_id=data.get('shift6_end_email')).first()

            Schedule.objects.update_or_create(
                date=now().date(),
                defaults={
                    'shift1_status': shift1_status,
                    'shift3_status': shift3_status,
                    'shift6_status': shift6_status,
                    'shift1_end_email': shift1_end_user,
                    'shift3_end_email': shift3_end_user,
                    'shift6_end_email': shift6_end_user,
                }
            )

            Notice.objects.create(
                message=f"📌 Bihourly assigned for {localdate().strftime('%d-%b-%Y')}",
                posted_by=current_user,
                posted_at=now()
            )

            return Response({'success': True})
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        emp_id = request.session.get('emp_id')
        print('SESSION KEY:', request.session.session_key)
        print('emp_id in session:', request.session.get('emp_id'))

        

        if 'emp_id' not in request.session:

            return Response({'detail': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        print('got in to it')
        current_user = self.get_current_user(request)
        current_user.dynamic_shift = get_today_shift_for_user(current_user.emp_id) or current_user.shift
        users = list(User.objects.all())

        for u in users:
            dynamic_shift = get_today_shift_for_user(u.emp_id) or u.shift
            u.shift = dynamic_shift
            if u.shift in ['WO', 'CO', 'UL', 'PL']:
                u.status = 'Out Of Office'
            u.save(update_fields=['shift', 'status'])

        for user in users:
            user.open_ticket_count = Ticket.objects.filter(assignee_name=user.assignee_name, status__iexact='Open').count()
            user.pending_ticket_count = Ticket.objects.filter(assignee_name=user.assignee_name, status__iexact='Pending').count()

        current_user.open_ticket_count = Ticket.objects.filter(assignee_name=current_user.assignee_name, status__iexact='Open').count()
        current_user.pending_ticket_count = Ticket.objects.filter(assignee_name=current_user.assignee_name, status__iexact='Pending').count()

        schedule = Schedule.objects.filter(date=now().date()).first()
        shift1_status = schedule.shift1_status if schedule else {}
        shift3_status = schedule.shift3_status if schedule else {}
        shift6_status = schedule.shift6_status if schedule and hasattr(schedule, 'shift6_status') else {}

        shift1_end_email_id = schedule.shift1_end_email_id if schedule else ""
        shift3_end_email_id = schedule.shift3_end_email_id if schedule else ""
        shift6_end_email_id = schedule.shift6_end_email_id if schedule else ""

        shift1_users = [u.emp_id for u in users if u.shift == 'S1']
        shift3_users = [u.emp_id for u in users if u.shift in ['S2', 'S3']]
        shift6_users = [u.emp_id for u in users if u.shift in ['S5', 'S6']]

        
        assigned_tasks = []
        if schedule:
            for shift, label in [(schedule.shift1_status, "Shift 1"), (schedule.shift3_status, "Shift 3"), (schedule.shift6_status, "Shift 6")]:
                for time, emp_id in shift.items():
                    if emp_id == current_user.emp_id:
                        assigned_tasks.append(f"{label} – {time}")
            for attr, label in [("shift1_end_email_id", "Shift 1"), ("shift3_end_email_id", "Shift 3"), ("shift6_end_email_id", "Shift 6")]:
                if getattr(schedule, attr) == current_user.emp_id:
                    assigned_tasks.append(f"{label} – End Mail")

        combined_notices = list(Notice.objects.order_by('-posted_at').values('id', 'message', 'posted_by__assignee_name', 'posted_at'))

        open_product_counts = {
            entry['group']: entry['count']
            for entry in Ticket.objects.filter(status='Open').values('group').annotate(count=Count('id'))
        }

        return Response({
            'current_user': {
                'emp_id': current_user.emp_id,
                'assignee_name': current_user.assignee_name,
                'open_ticket_count': current_user.open_ticket_count,
                'pending_ticket_count': current_user.pending_ticket_count,
                'is_allowed': current_user.assignee_name in ALLOWED_USERS,
                'status': current_user.status,
            },
            'users': [
                {
                    'emp_id': u.emp_id,
                    'assignee_name': u.assignee_name,
                    'status': u.status,
                    'shift': u.shift,
                    'open_ticket_count': u.open_ticket_count,
                    'pending_ticket_count': u.pending_ticket_count,
                    'job_title': u.job_title,
                    'repor_manager': u.repor_manager,
                } for u in users
            ],
            'shift1_status': shift1_status,
            'shift3_status': shift3_status,
            'shift6_status': shift6_status,
            'shift1_end_email_id': shift1_end_email_id,
            'shift3_end_email_id': shift3_end_email_id,
            'shift6_end_email_id': shift6_end_email_id,
            'shift1_users': shift1_users,
            'shift3_users': shift3_users,
            'shift6_users': shift6_users,
            'user_assignments': assigned_tasks,
            'notices': combined_notices,
            'open_product_counts': open_product_counts,
            "today": datetime.today().date(),
        })




class ResetTicketAssigneeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        if 'emp_id' not in request.session:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        ticket_id = request.data.get("ticket_id")
        if not ticket_id:
            return Response({"error": "ticket_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id)
            ticket.assignee_name = ""
            ticket.save()
            return Response({"success": True})
        except Ticket.DoesNotExist:
            return Response({"success": False, "error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, *args, **kwargs):
        return Response({"success": False, "error": "GET method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)



def get_logged_in_user(request):
    emp_id = request.session.get('emp_id')
    if not emp_id:
        return None
    try:
        return User.objects.get(emp_id=emp_id)
    except User.DoesNotExist:
        return None





class DoLoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        set_available = request.data.get('set_available')  # Optional field

        if not username or not password:
            return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(user_name=username)

            if user.password == password:  # ❗ Replace with secure hash check later
                if request.session.get('emp_id') and request.session['emp_id'] != user.emp_id:
                    request.session.flush()

                request.session.cycle_key()
                request.session['emp_id'] = user.emp_id
                # print('------------------------------------------------------',request.session.get('emp_id'))
                request.session['access'] = [a.lower().strip() for a in user.access]

                if set_available:
                    user.status = 'Available'

                if user.last_shift_update != date.today():
                    get_today_shift_for_user(user.emp_id)
                    user.last_shift_update = date.today()

                user.save(update_fields=['status', 'last_shift_update'])

                return Response({"success": True, "message": "Login successful","emp_id": user.emp_id,}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid password."}, status=status.HTTP_401_UNAUTHORIZED)

        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)




class UpdateStatusAPIView(APIView):
    def post(self, request):
        emp_id = request.session.get('emp_id')
        print('i am in status update',emp_id)

        if 'emp_id' not in request.session:
            return Response({'success': False, 'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        user = User.objects.get(emp_id=emp_id)
        print('checking')
        status_value = request.data.get('status')
        if status_value in dict(User.STATUS_CHOICES):
            user.status = status_value
            user.save()
            return Response({'success': True, 'status': status_value})
        else:
            return Response({'success': False, 'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        return Response({'success': False, 'error': 'GET method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)






class ForgotPasswordAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')

        if not username:
            return Response({'success': False, 'error': 'Username required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        token = get_random_string(length=48)
        user.reset_token = token
        user.token_created_at = timezone.now()
        user.save()

        domain = get_current_site(request).domain
        reset_url = f"http://{domain}{reverse('reset_password', args=[token])}"

        send_mail(
            subject='Reset Your Password',
            message=f'Click the link to reset your password: {reset_url}',
            from_email='noreply@example.com',
            recipient_list=[user.email],
        )

        return Response({'success': True, 'message': 'Reset email sent.'})





class UploadExcelView(View):
    def post(self, request):
        if 'emp_id' not in request.session:
            print("No emp_id in session — redirecting to login.")
            return redirect('login')

        if request.FILES.get('file'):
            print("✅ Excel file received.")
            excel_file = request.FILES['file']

            try:
                df = pd.read_excel(excel_file)
            except Exception as e:
                print(f"❌ Error reading Excel: {e}")
                return HttpResponse(f"Failed to read Excel file: {e}")

            df.columns = df.columns.str.strip()
            df = df.where(pd.notnull(df), None)

            column_field_map = {
                'Ticket ID': 'ticket_id',
                'Ticket priority': 'priority',
                'Ticket subject': 'subject',
                'Requester organization name': 'requester_organization',
                'Requester name': 'requester',
                'Assignee ID': 'assignee_id',
                'Product Category': 'product_category',
                'Ticket type': 'ticket_type',
                'JIRA Issue ID': 'jira_issue_id',
                'Assignee name': 'assignee_name',
                'Ticket status': 'status',
                'Ticket created - Timestamp': 'created_timestamp',
                'Ticket solved - Timestamp': 'solved_timestamp',
                'Ticket assigned - Timestamp': 'assigned_timestamp',
                'Ticket updated - Timestamp': 'updated_timestamp',
                'Ticket due - Timestamp': 'due_timestamp',
                'Ticket group': 'group',
                'Ticket form': 'form',
                'Comment': 'comment',
            }

            timestamp_columns = [
                'Ticket created - Timestamp',
                'Ticket solved - Timestamp',
                'Ticket assigned - Timestamp',
                'Ticket updated - Timestamp',
                'Ticket due - Timestamp',
            ]

            for col in timestamp_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
                    df[col] = df[col].replace('', pd.NA)
                    try:
                        df[col] = pd.to_datetime(df[col], format="%Y-%m-%dT%H:%M:%S", errors='raise')
                    except Exception as e:
                        print(f"⚠️ Failed parsing '{col}' with format: {e}")
                        df[col] = pd.to_datetime(df[col], errors='coerce')

                    df[col] = df[col].apply(lambda x: make_aware(x) if pd.notnull(x) and x.tzinfo is None else x)

            uploaded_ticket_ids = set()

            for index, row in df.iterrows():
                try:
                    raw_id = row.get('Ticket ID')
                    if raw_id is None:
                        print(f"⚠️ Row {index} missing Ticket ID — skipping.")
                        continue

                    ticket_id = str(raw_id).strip()
                    uploaded_ticket_ids.add(ticket_id)
                    data = {}

                    for excel_col, model_field in column_field_map.items():
                        value = row.get(excel_col)

                        if pd.notnull(value):
                            value = str(value).strip()
                        else:
                            value = None

                        data[model_field] = value

                    existing_ticket = Ticket.objects.filter(ticket_id=ticket_id.strip()).first()
                    if existing_ticket:
                        if existing_ticket.assignee_name and data['assignee_name'] and existing_ticket.assignee_name.strip() != data['assignee_name'].strip():
                            print(f"⚠️ Assignee mismatch for ticket {ticket_id}: DB='{existing_ticket.assignee_name}' vs Excel='{data['assignee_name']}'")

                        has_changes = False
                        for field, new_value in data.items():
                            old_value = getattr(existing_ticket, field)
                            if isinstance(old_value, str):
                                old_value = old_value.strip()
                            if isinstance(new_value, str):
                                new_value = new_value.strip()
                            if old_value != new_value:
                                has_changes = True
                                break

                        if has_changes:
                            for field, new_value in data.items():
                                setattr(existing_ticket, field, new_value)
                            existing_ticket.save()
                            print(f"🔁 Updated ticket ID: {ticket_id}")
                        else:
                            print(f"✅ No changes for ticket ID: {ticket_id}")
                    else:
                        Ticket.objects.create(**data)
                        print(f"➕ Created new ticket ID: {ticket_id}")

                except Exception as e:
                    print(f"❌ Error processing ticket ID {ticket_id}: {e}")

            db_ticket_ids = set(Ticket.objects.values_list('ticket_id', flat=True))
            to_delete = db_ticket_ids - uploaded_ticket_ids
            if to_delete:
                Ticket.objects.filter(ticket_id__in=to_delete).delete()
                print(f"🗑️ Deleted {len(to_delete)} tickets not found in Excel: {to_delete}")
            else:
                print("✅ No tickets to delete.")

            print("✅ Ticket upload completed.")
            return redirect('home')

        return redirect('home')

    def get(self, request):
        return redirect('home')




 
def ticket_list(request):
    if 'emp_id' not in request.session:
        return redirect('login')
    tickets = Ticket.objects.all().order_by('ticket_id')  # ascending order
    return render(request, 'Freewheel_Portal/ticket_list.html', {'tickets': tickets})

def test(request):
    if 'emp_id' not in request.session:
        return redirect('login')

    return render(request,'Freewheel_Portal/test.html')
 


class CreateUserView(View):
    def get(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        initial_data = {}
        user_type = request.GET.get('user_type')  # read from query param

        if user_type:
            try:
                group_access = GroupAccess.objects.get(user_type=user_type)
                access_ids = group_access.availed_access
                initial_data['access'] = Access.objects.filter(access_id__in=access_ids)
            except GroupAccess.DoesNotExist:
                pass

        form = UserForm(initial=initial_data)
        return render(request, 'Freewheel_Portal/create_user.html', {'form': form})

    def post(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            form.save_m2m()
            return HttpResponse("User created successfully.")
        
        return render(request, 'Freewheel_Portal/create_user.html', {'form': form})




@method_decorator(csrf_exempt, name='dispatch')
class SubmitCommentView(View):
    def post(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        try:
            data = json.loads(request.body)
            ticket_id = data.get('ticket_id')
            comment = data.get('comment')
            status = data.get('status')
            print(status)

            ticket = Ticket.objects.get(ticket_id=ticket_id)
            ticket.comment = comment
            ticket.updated_timestamp = timezone.now()
            ticket.status = status
            ticket.save()

            # Try to find existing entry manually
            shift_entry = ShiftEndTable.objects.filter(ticket_id=ticket).first()

            if shift_entry:
                shift_entry.comment = comment
                shift_entry.last_comment_time = timezone.now()
                shift_entry.save()
            else:
                ShiftEndTable.objects.create(
                    ticket_id=ticket,
                    start_date=timezone.now(),
                    ticket_subject=ticket.subject,
                    priority=ticket.priority,
                    ticket_status=ticket.status,
                    customer_organisation=ticket.requester_organization,
                    asignee_name=ticket.assignee_name,
                    product=ticket.product_category,
                    ticket_type=ticket.ticket_type,
                    JIRA_id=ticket.jira_issue_id,
                    sla='',
                    last_comment_time=timezone.now(),
                    next_comment=timezone.now(),
                    time_left='',
                    comment=comment,
                )

            return JsonResponse({'success': True})

        except Ticket.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Ticket not found'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    def get(self, request):
        return JsonResponse({'success': False, 'error': 'Invalid method'})








@method_decorator(csrf_exempt, name='dispatch')
class AssignTicketView(View):
    def post(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')
        
        try:
            data = json.loads(request.body)
            ticket_id = data.get('ticket_id')
            emp_id = data.get('assignee_name')

            ticket = Ticket.objects.get(ticket_id=ticket_id)
            user = User.objects.get(emp_id=emp_id)

            ticket.assignee_name = user.assignee_name
            if ticket.status == 'New':
                ticket.status = 'Open'
            ticket.assigned_timestamp = timezone.now()
            ticket.save()

            return JsonResponse({'success': True})

        except Ticket.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Ticket not found'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    def get(self, request):
        return JsonResponse({'success': False, 'error': 'Invalid method'})






@method_decorator(csrf_exempt, name='dispatch')
class ShiftEndSummaryView(View):
    def get(self, request):
        return self.handle_request(request)

    def post(self, request):
        return self.handle_request(request)

    def handle_request(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        current_user = User.objects.get(emp_id=request.session['emp_id'])
        current_user.dynamic_shift = get_today_shift_for_user(current_user.emp_id) or current_user.shift
        dynamic_shift = None
        users = list(User.objects.all())

        for u in users:
            dynamic_shift = get_today_shift_for_user(u.emp_id) or u.shift
            u.shift = dynamic_shift
            if u.shift in ['WO', 'CO', 'UL', 'PL']:
                u.status = 'Out Of Office'
            u.save(update_fields=['shift', 'status'])

        if request.method == 'POST' and request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                shift1_status = data.get('shift1_status', {})
                shift3_status = data.get('shift3_status', {})
                shift6_status = data.get('shift6_status', {})

                shift1_end_email = data.get('shift1_end_email', "")
                shift3_end_email = data.get('shift3_end_email', "")
                shift6_end_email = data.get("shift6_end_email", "")

                shift1_end_user = User.objects.filter(emp_id=shift1_end_email).first()
                shift3_end_user = User.objects.filter(emp_id=shift3_end_email).first()
                shift6_end_user = User.objects.filter(emp_id=shift6_end_email).first()

                Schedule.objects.update_or_create(
                    date=now().date(),
                    defaults={
                        'shift1_status': shift1_status,
                        'shift3_status': shift3_status,
                        'shift1_end_email': shift1_end_user,
                        'shift3_end_email': shift3_end_user,
                        'shift6_status': shift6_status,
                        'shift6_end_email': shift6_end_user,
                    }
                )

                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)

        if request.method == 'POST':
            if 'post_notice' in request.POST:
                message = request.POST.get('message', '').strip()
                if message:
                    Notice.objects.create(message=message, posted_by=current_user, posted_at=now())
                return redirect('home')

            elif 'edit_notice' in request.POST:
                notice_id = request.POST.get('notice_id')
                new_message = request.POST.get('message', '').strip()
                if notice_id and new_message:
                    try:
                        notice = Notice.objects.get(id=notice_id, posted_by=current_user)
                        notice.message = new_message
                        notice.save()
                    except Notice.DoesNotExist:
                        pass
                return redirect('home')

            elif 'delete_notice' in request.POST:
                notice_id = request.POST.get('notice_id')
                if notice_id:
                    try:
                        notice = Notice.objects.get(id=notice_id, posted_by=current_user)
                        notice.delete()
                    except Notice.DoesNotExist:
                        pass
                return redirect('home')

        schedule = Schedule.objects.filter(date=now().date()).first()
        shift1_status = schedule.shift1_status if schedule else {}
        shift3_status = schedule.shift3_status if schedule else {}
        shift6_status = schedule.shift6_status if schedule and hasattr(schedule, 'shift6_status') else {}

        shift1_end_email_id = schedule.shift1_end_email_id if schedule else ""
        shift3_end_email_id = schedule.shift3_end_email_id if schedule else ""
        shift6_end_email_id = schedule.shift6_end_email_id if schedule else ""

        shift_notices = [f"📌 Bihourly Allocation for {localdate().strftime('%d-%b-%Y')}"]

        def add_shift_details(shift_name, shift_data):
            for time, emp_id in shift_data.items():
                try:
                    user = User.objects.get(emp_id=emp_id)
                    shift_notices.append(f"{shift_name} — {time}: {user.assignee_name}")
                except User.DoesNotExist:
                    shift_notices.append(f"{shift_name} — {time}: Not Assigned")

        add_shift_details("Shift 1", shift1_status)
        add_shift_details("Shift 3", shift3_status)
        add_shift_details("Shift 6", shift6_status)

        shift_notices.append("📬 Shift-end Email Allocation")

        for shift, email_id, label in [
            (shift1_end_email_id, shift1_end_email_id, "Shift 1 End Mail"),
            (shift3_end_email_id, shift3_end_email_id, "Shift 3 End Mail"),
            (shift6_end_email_id, shift6_end_email_id, "Shift 6 End Mail"),
        ]:
            if email_id:
                try:
                    user = User.objects.get(emp_id=email_id)
                    shift_notices.append(f"{label}: {user.assignee_name}")
                except User.DoesNotExist:
                    shift_notices.append(f"{label}: [Unknown ID: {email_id}]")
            else:
                shift_notices.append(f"{label}: Not Assigned")

        combined_notices = [{
            "message": msg,
            "posted_by": None,
            "posted_at": localtime(now()),
        } for msg in shift_notices]

        for note in Notice.objects.order_by('-posted_at'):
            combined_notices.append({
                "id": note.id,
                "message": note.message,
                "posted_by": note.posted_by,
                "posted_at": localtime(note.posted_at),
            })

        is_allowed = current_user.assignee_name in ALLOWED_USERS

        assigned_tasks = []

        if schedule:
            for time, emp_id in schedule.shift1_status.items():
                if emp_id == current_user.emp_id:
                    assigned_tasks.append(f"Shift 1 – {time}")
            for time, emp_id in schedule.shift3_status.items():
                if emp_id == current_user.emp_id:
                    assigned_tasks.append(f"Shift 3 – {time}")
            for time, emp_id in schedule.shift6_status.items():
                if emp_id == current_user.emp_id:
                    assigned_tasks.append(f"Shift 6 – {time}")
            if schedule.shift1_end_email_id == current_user.emp_id:
                assigned_tasks.append("Shift 1 – End Mail")
            if schedule.shift3_end_email_id == current_user.emp_id:
                assigned_tasks.append("Shift 3 – End Mail")
            if schedule.shift6_end_email_id == current_user.emp_id:
                assigned_tasks.append("Shift 6 – End Mail")

        delegated_to_user = bool(assigned_tasks)

        shift1_users = [user for user in users if user.shift == 'S1']
        shift3_users = [user for user in users if user.shift in ['S2', 'S3']]
        shift6_users = [user for user in users if user.shift in ['S5', 'S6']]

        status_priority = {'Available': 0, 'In-Meeting': 1, 'Away': 2, 'Offline': 3, 'Out Of Office': 4}
        users.sort(key=lambda user: status_priority.get(user.status, 99))

        populate_summary_data()

        context = {
            'users': users,
            'current_user': current_user,
            'tickets': Ticket.objects.all(),
            'open_tickets': Ticket.objects.filter(status='Open'),
            'pending_tickets': Ticket.objects.filter(status='Pending'),
            'hold_tickets': Ticket.objects.filter(status='Hold'),
            'new_tickets': Ticket.objects.filter(status='New'),

            'shift1_times': SHIFT1_TIMINGS,
            'shift3_times': SHIFT3_TIMINGS,
            'shift6_times': SHIFT6_TIMINGS,

            'shift1_status': shift1_status,
            'shift3_status': shift3_status,
            'shift6_status': shift6_status,

            'shift1_end_email_id': shift1_end_email_id,
            'shift3_end_email_id': shift3_end_email_id,
            'shift6_end_email_id': shift6_end_email_id,

            'notices': combined_notices,

            'is_allowed': is_allowed,
            'delegated_to_user': delegated_to_user,
            'schedule': schedule,

            'shift1_users': shift1_users,
            'shift3_users': shift3_users,
            'shift6_users': shift6_users,
            "user_assignments": assigned_tasks,

            "today": datetime.today().date(),

            'current_status_summary': ShiftEndTicketDetails.objects.all(),
            'current_sla_breaches': SLABreachedTicket.objects.all(),
            'current_shiftend_details': ShiftEndTable.objects.all(),

            'previous_status_summary': PreviousShiftEndTicketDetails.objects.all(),
            'previous_sla_breaches': PreviousSLABreachedTicket.objects.all(),
            'previous_shiftend_details': PreviousShiftEndTable.objects.all(),
        }

        return render(request, 'Freewheel_Portal/shift-end-mail.html', context)




def submit_leave(request):
    if 'emp_id' not in request.session:
        return redirect('login')

    if request.method == "POST":
        leave_until_str = request.POST.get('leave_until')

        if leave_until_str:
            leave_until = parser.parse(leave_until_str)

            user = User.objects.get(emp_id=request.session['emp_id'])
            user.status = "Out Of Office"
            user.leave_until = leave_until
            user.save()

            return redirect('home')  # ✅ Success: redirect to homepage or dashboard

        # Optional: handle missing or invalid date input
        return render(request, 'error.html', {'message': 'Leave date required'})  # or redirect

    # If GET request, maybe show the form or block it
    return redirect('home')  # ✅ fallback for non-POST requests





class NewTicketsView(View):
    template_name = 'portal_app/new_tickets.html'

    def get(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        tickets = Ticket.objects.filter(assignee_name__isnull=True, status='New')
        users = User.objects.all()
        return render(request, self.template_name, {'tickets': tickets, 'users': users})

    def post(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        ticket_id = request.POST.get('ticket_id')
        assignee_emp_id = request.POST.get('assignee_emp_id')

        try:
            ticket = Ticket.objects.get(id=ticket_id)
            user = User.objects.get(emp_id=assignee_emp_id)

            ticket.assignee_name = user.assignee_name
            ticket.assigned_timestamp = timezone.now()
            ticket.save()
        except (Ticket.DoesNotExist, User.DoesNotExist):
            # Optional: Handle missing ticket/user gracefully
            pass

        return redirect('new_tickets')



SHIFT_EXCEL_PATH = os.path.join(settings.MEDIA_ROOT, 'shifts.xlsx')


class FilterByShiftView(View):
    template_name = 'Freewheel_Portal/filter_shift.html'

    def get(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        employees = []
        selected_shift = request.GET.get('shift', '').strip()
        today_day = datetime.datetime.now().day

        try:
            df = pd.read_excel(SHIFT_EXCEL_PATH, header=None)
            date_row = df.iloc[1]  # second row (index 1)

            shift_col_index = None
            for col_index, cell in enumerate(date_row):
                try:
                    parsed_date = pd.to_datetime(str(cell), errors='coerce')
                    if not pd.isna(parsed_date) and parsed_date.day == today_day:
                        shift_col_index = col_index
                        break
                except:
                    continue

            if shift_col_index is None:
                raise KeyError(f"Today's date ({today_day}) not found in Excel.")

            for i in range(4, len(df)):
                emp_id_excel = str(df.iloc[i, 1]).strip().lower()
                shift = str(df.iloc[i, shift_col_index]).strip()

                if shift == selected_shift:
                    try:
                        user = User.objects.get(emp_id__iexact=emp_id_excel)
                        employees.append(user.name)
                    except User.DoesNotExist:
                        employees.append(f"Unknown (ID: {emp_id_excel})")

        except Exception as e:
            return render(request, self.template_name, {
                'error': f"Error loading shift data: {str(e)}"
            })

        return render(request, self.template_name, {
            'employees': employees,
            'selected_shift': selected_shift
        })



 



@method_decorator(csrf_exempt, name='dispatch')
class UploadShiftExcelView(View):
    def post(self, request):
        if request.FILES.get('excel_file'):
            uploaded_file = request.FILES['excel_file']
            folder_path = os.path.join(settings.MEDIA_ROOT, 'shift_roster')
            os.makedirs(folder_path, exist_ok=True)

            existing_files = [
                f for f in os.listdir(folder_path)
                if f.startswith('shift_roster_') and f.endswith('.xlsx')
            ]
            indices = []
            for f in existing_files:
                try:
                    indices.append(int(f.split('_')[-1].split('.')[0]))
                except:
                    continue
            next_index = max(indices + [0]) + 1
            new_filename = f"shift_roster_{next_index}.xlsx"
            file_path = os.path.join(folder_path, new_filename)

            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

        return redirect('home')

    def get(self, request):
        return redirect('home')



def manual_freeze_view(request):


    if 'emp_id' not in request.session:
        return redirect('login')
    if request.method == "POST":
        success = truncate_shift_end()
        return JsonResponse({'success': success})









def classify_product(ticket):
    tg = ticket.group
    if tg == "Support Eng":
        return "SH"
    elif tg in ["BW CIEC Onboarding", "BW Support"]:
        return "FW DSP"
    elif tg == "SFX Support":
        return "FW SSP"
    elif tg in ["STRATA CIEC Onboarding", "Adazzle", "OneStrata Support"]:
        return "Strata"
    return None


class UploadExcelReportView(View):
    def get(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        # Store existing engineer/followup values
        existing_reports = TicketReport.objects.all()
        engineers_map = {}
        for report in existing_reports:
            key = f"{report.product}|{report.timestamp.date()}"
            engineers_map[key] = {
                "engineers": report.engineers,
                "ho_followup": report.ho_followup
            }

        # Get and classify tickets
        tickets = Ticket.objects.all()
        for t in tickets:
            t.Product = classify_product(t)

        grouped = defaultdict(list)
        for t in tickets:
            if t.Product:
                grouped[t.Product].append(t)

        active_users = User.objects.exclude(status__in=['Out Of Office', 'Offline'])
        user_status_map = {user.assignee_name.strip().lower(): user for user in active_users}

        product_being_worked = defaultdict(int)
        for t in tickets:
            if t.status in ['Open', 'New']:
                assignee = (t.assignee_name or '').strip().lower()
                if assignee in user_status_map and t.Product:
                    product_being_worked[t.Product] += 1

        # Delete old reports
        TicketReport.objects.all().delete()

        # Recreate reports
        report_data = []
        for product, group in grouped.items():
            open_count = sum(1 for t in group if t.status == 'Open')
            new_count = sum(1 for t in group if t.status == 'New')
            open_new = [t for t in group if t.status in ['Open', 'New']]

            urgent_count = sum(1 for t in open_new if t.priority == 'Urgent')
            high_count = sum(1 for t in open_new if t.priority == 'High')
            normal_count = sum(1 for t in open_new if t.priority == 'Normal')
            low_count = sum(1 for t in open_new if t.priority == 'Low')

            being_worked = product_being_worked.get(product, 0)
            unattended = (open_count + new_count) - being_worked

            key = f"{product}|{now().date()}"
            engineers = engineers_map.get(key, {}).get("engineers", 0)
            ho_followup = engineers_map.get(key, {}).get("ho_followup", 0)

            current_user = User.objects.get(emp_id=request.session['emp_id'])

            report = TicketReport.objects.create(
                timestamp=now(),
                product=product,
                open_count=open_count,
                new_count=new_count,
                urgent_count=urgent_count,
                high_count=high_count,
                normal_count=normal_count,
                low_count=low_count,
                being_worked=being_worked,
                unattended=unattended,
                engineers=engineers,
                ho_followup=ho_followup
            )
            report_data.append(report)

        current_user = User.objects.get(emp_id=request.session['emp_id'])

        return render(request, 'Freewheel_Portal/report_upload.html', {
            'report_data': report_data,
            'current_user': current_user,
        })


class UpdateReportRowView(View):
    def post(self, request, pk):
        report = get_object_or_404(TicketReport, pk=pk)
        report.engineers = int(request.POST.get('engineers', 0))
        report.ho_followup = int(request.POST.get('ho_followup', 0))
        report.unattended = (report.open_count + report.new_count) - report.being_worked
        report.save()
        return redirect('upload_excel_report')







 



@method_decorator(csrf_exempt, name='dispatch')
class SaveBulkReportUpdatesView(View):
    def post(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        ids = request.POST.getlist('ids')
        for id in ids:
            try:
                report = TicketReport.objects.get(id=id)
                engineers = request.POST.get(f'engineers_{id}')
                ho_followup = request.POST.get(f'ho_followup_{id}')
                if engineers is not None:
                    report.engineers = int(engineers)
                if ho_followup is not None:
                    report.ho_followup = int(ho_followup)
                report.unattended = (report.open_count + report.new_count) - report.being_worked
                report.save()
            except TicketReport.DoesNotExist:
                continue  # skip invalid IDs safely

        return HttpResponseRedirect(reverse('upload_excel_report'))



class CreateEmpView(View):
    template_name = 'Freewheel_Portal/create_user.html'

    def get(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        context = self.build_context(request)
        return render(request, self.template_name, context)

    def post(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        if request.content_type == 'application/json':
            return self.handle_json_delegation(request)

        context = self.build_context(request)
        return render(request, self.template_name, context)

    def handle_json_delegation(self, request):
        try:
            current_user = User.objects.get(emp_id=request.session['emp_id'])
            data = json.loads(request.body)

            shift1_status = data.get('shift1_status', {})
            shift3_status = data.get('shift3_status', {})
            shift6_status = data.get('shift6_status', {})

            shift1_end_user = User.objects.filter(emp_id=data.get('shift1_end_email', "")).first()
            shift3_end_user = User.objects.filter(emp_id=data.get('shift3_end_email', "")).first()
            shift6_end_user = User.objects.filter(emp_id=data.get('shift6_end_email', "")).first()

            Schedule.objects.update_or_create(
                date=now().date(),
                defaults={
                    'shift1_status': shift1_status,
                    'shift3_status': shift3_status,
                    'shift1_end_email': shift1_end_user,
                    'shift3_end_email': shift3_end_user,
                    'shift6_status': shift6_status,
                    'shift6_end_email': shift6_end_user,
                }
            )

            Notice.objects.create(
                message=f"📌 Bihourly assigned for {localdate().strftime('%d-%b-%Y')}",
                posted_by=current_user,
                posted_at=now()
            )

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    def build_context(self, request):
        current_user = User.objects.get(emp_id=request.session['emp_id'])
        current_user.dynamic_shift = get_today_shift_for_user(current_user.emp_id) or current_user.shift

        users = list(User.objects.all())
        for u in users:
            dynamic_shift = get_today_shift_for_user(u.emp_id) or u.shift
            u.shift = dynamic_shift
            if u.shift in ['WO', 'CO', 'UL', 'PL']:
                u.status = 'Out Of Office'
            u.save(update_fields=['shift', 'status'])

        for user in users:
            user.open_ticket_count = Ticket.objects.filter(assignee_name=user.assignee_name, status__iexact='Open').count()
            user.pending_ticket_count = Ticket.objects.filter(assignee_name=user.assignee_name, status__iexact='Pending').count()

        current_user.open_ticket_count = Ticket.objects.filter(assignee_name=current_user.assignee_name, status__iexact='Open').count()
        current_user.pending_ticket_count = Ticket.objects.filter(assignee_name=current_user.assignee_name, status__iexact='Pending').count()

        schedule = Schedule.objects.filter(date=now().date()).first()
        shift1_status = schedule.shift1_status if schedule else {}
        shift3_status = schedule.shift3_status if schedule else {}
        shift6_status = schedule.shift6_status if schedule and hasattr(schedule, 'shift6_status') else {}

        shift1_end_email_id = schedule.shift1_end_email_id if schedule else ""
        shift3_end_email_id = schedule.shift3_end_email_id if schedule else ""
        shift6_end_email_id = schedule.shift6_end_email_id if schedule else ""

        shift_notices = [f"📌 Bihourly Allocation for {localdate().strftime('%d-%b-%Y')}"]
        for shift_name, shift_data in [("Shift 1", shift1_status), ("Shift 3", shift3_status), ("Shift 6", shift6_status)]:
            for time, emp_id in shift_data.items():
                try:
                    user = User.objects.get(emp_id=emp_id)
                    shift_notices.append(f"{shift_name} — {time}: {user.assignee_name}")
                except User.DoesNotExist:
                    shift_notices.append(f"{shift_name} — {time}: Not Assigned")

        shift_notices.append("📬 Shift-end Email Allocation")
        for label, emp_id in [("Shift 1", shift1_end_email_id), ("Shift 3", shift3_end_email_id), ("Shift 6", shift6_end_email_id)]:
            try:
                user = User.objects.get(emp_id=emp_id)
                shift_notices.append(f"{label} End Mail: {user.assignee_name}")
            except:
                shift_notices.append(f"{label} End Mail: Not Assigned")

        combined_notices = [{"message": msg, "posted_by": None, "posted_at": localtime(now())} for msg in shift_notices]
        combined_notices += [{
            "id": note.id,
            "message": note.message,
            "posted_by": note.posted_by,
            "posted_at": localtime(note.posted_at),
        } for note in Notice.objects.order_by('-posted_at')]

        is_allowed = current_user.assignee_name in ALLOWED_USERS
        assigned_tasks = []
        if schedule:
            for time, emp_id in schedule.shift1_status.items():
                if emp_id == current_user.emp_id:
                    assigned_tasks.append(f"Shift 1 – {time}")
            for time, emp_id in schedule.shift3_status.items():
                if emp_id == current_user.emp_id:
                    assigned_tasks.append(f"Shift 3 – {time}")
            for time, emp_id in schedule.shift6_status.items():
                if emp_id == current_user.emp_id:
                    assigned_tasks.append(f"Shift 6 – {time}")

            for shift, emp_id in [
                ("Shift 1", schedule.shift1_end_email_id),
                ("Shift 3", schedule.shift3_end_email_id),
                ("Shift 6", schedule.shift6_end_email_id),
            ]:
                if emp_id == current_user.emp_id:
                    assigned_tasks.append(f"{shift} – End Mail")

        delegated_to_user = bool(assigned_tasks)

        status_priority = {'Available': 0, 'In-Meeting': 1, 'Away': 2, 'Offline': 3, 'Out Of Office': 4}
        users.sort(key=lambda u: status_priority.get(u.status, 99))

        return {
            'users': users,
            'current_user': current_user,
            'tickets': Ticket.objects.all(),
            'open_tickets': Ticket.objects.filter(status='Open'),
            'pending_tickets': Ticket.objects.filter(status='Pending'),
            'hold_tickets': Ticket.objects.filter(status='Hold'),
            'new_tickets': Ticket.objects.filter(status='New'),
            'unassigned_tickets': Ticket.objects.filter(assignee_name="").exclude(status="New"),

            'shift1_times': SHIFT1_TIMINGS,
            'shift3_times': SHIFT3_TIMINGS,
            'shift6_times': SHIFT6_TIMINGS,

            'shift1_status': shift1_status,
            'shift3_status': shift3_status,
            'shift6_status': shift6_status,

            'shift1_end_email_id': shift1_end_email_id,
            'shift3_end_email_id': shift3_end_email_id,
            'shift6_end_email_id': shift6_end_email_id,

            'all_notices': Notice.objects.select_related('posted_by').order_by('-posted_at'),

            'is_allowed': is_allowed,
            'delegated_to_user': delegated_to_user,
            'schedule': schedule,

            'shift1_users': [u for u in users if u.shift == 'S1'],
            'shift3_users': [u for u in users if u.shift in ['S2', 'S3']],
            'shift6_users': [u for u in users if u.shift in ['S5', 'S6']],
            "user_assignments": assigned_tasks,
            "today": datetime.today().date(),

            'pending_product_counts': Ticket.objects.filter(status='Pending').values('product_category').annotate(count=Count('id')).order_by('-count'),
            'hold_product_counts': Ticket.objects.filter(status='Hold').values('product_category').annotate(count=Count('id')).order_by('-count'),
            'new_product_counts': Ticket.objects.filter(status='New').values('product_category').annotate(count=Count('id')).order_by('-count'),
            'open_product_counts ': Ticket.objects.filter(status='Open').values('product_category').annotate(count=Count('id')).order_by('-count'),
        }



class CreateEmployeeView(View):
    def get(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')
        return redirect('home')  # You are redirecting instead of rendering a form

    def post(self, request):
        if 'emp_id' not in request.session:
            return redirect('login')

        try:
            emp_id = request.POST['emp_id']
            assignee_name = request.POST['full_name']
            department = request.POST.get('department', '')
            BussinessUnit = request.POST.get('business_unit', '')
            job_title = request.POST.get('job_title', '')
            repor_manager = request.POST.get('reporting_manager', '')
            user_type = request.POST.get('user_type', 'staff')
            contact_number = request.POST.get('contact_number', '')
            email = request.POST.get('email', '')
            slack_id = request.POST.get('slack_channel', '')
            work_region = request.POST.get('region', '')

            # Create the user
            User.objects.create(
                emp_id=emp_id,
                assignee_name=assignee_name,
                department=department,
                BussinessUnit=BussinessUnit,
                job_title=job_title,
                repor_manager=repor_manager,
                user_type=user_type,
                contact_number=contact_number,
                email=email,
                slack_id=slack_id,
                work_region=work_region,
                status='Offline',
                shift='',
                access=[],
            )

            messages.success(request, "✅ Employee created successfully!")
            return redirect('create_emp')  # Or wherever your employee form is located

        except Exception as e:
            messages.error(request, f"❌ Failed to create employee: {e}")
            return redirect('home')  # Fallback redirect


















 
def health_check(request):              # edited
    return HttpResponse("OK")








 



def view_shift_day(request):
    hour_distribution = {}
    try:
        if request.method == 'POST':
            date_str = request.POST.get('selected_date')
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = datetime.today().date()
 
        selected_date_str = selected_date.strftime('%Y-%m-%d')
        prev_day = selected_date - timedelta(days=1)
        next_day = selected_date + timedelta(days=1)
 
        shift_data_today = get_shifts_for_date(selected_date)
        shift_data_prev = get_shifts_for_date(prev_day)
        shift_data_next = get_shifts_for_date(next_day)
 
        hour_distribution = get_utc_half_hour_distribution(
            shift_data_today, shift_data_prev, shift_data_next, selected_date
        )
        print("[DEBUG] UTC Hour Distribution:", hour_distribution)
 
    except Exception as e:
        messages.error(request, f"Invalid date input: {str(e)}")
        selected_date_str = ''
    current_user = User.objects.get(emp_id=request.session['emp_id'])

    return render(request, 'Freewheel_Portal/view_shift_range.html', {
        'shift_data': shift_data_today if hour_distribution else {},
        'hour_distribution': json.dumps(hour_distribution),
        'selected_date': selected_date_str,
        'current_user': current_user,

    })





 
SHIFT_LABELS_ORDERED = OrderedDict([
    ("S1", "S1 (6:30am - 3:30pm)"),
    ("S2", "S2 (11am - 8pm)"),
    ("S3", "S3 (1:30pm - 10:30pm)"),
    ("S5", "S5 (6pm - 3am)"),
    ("S4", "S4 (3pm - 12am)"),
    ("S6", "S6 (10pm - 7am)"),
    ("PL", "PL (Planned Leave)"),
    ("UL", "UL (Unplanned Leave)"),
    ("CL", "CL (Casual Leave)"),
    ("SL", "SL (Sick Leave)"),
    ("WO", "WO (Week Off)"),
    ("CO", "CO (Comp Off)")
])
 
def view_shift(request):
    shift_data = {}
    shift_counts_by_day = {code: defaultdict(int) for code in SHIFT_LABELS_ORDERED}
    all_dates = set()
 
    from_date_str = request.POST.get('from_date', '')
    to_date_str = request.POST.get('to_date', '')
 
    if request.method == 'POST' and from_date_str and to_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
 
            shift_data = get_shifts_for_date_range(from_date, to_date)
 
            for user, shifts in shift_data.items():
                for date, shift in shifts.items():
                    shift = shift.strip().upper()
                    if shift in SHIFT_LABELS_ORDERED:
                        shift_counts_by_day[shift][date] += 1
                        all_dates.add(date)
 
            sorted_dates = sorted(all_dates)
 
            shift_count_rows = []
            for code, label in SHIFT_LABELS_ORDERED.items():
                row = {"label": label, "counts": [shift_counts_by_day[code].get(str(dt), 0) for dt in sorted_dates]}
                shift_count_rows.append(row)
 
            return render(request, 'Freewheel_Portal/view_shift.html', {
                'shift_data': shift_data,
                'shift_count_rows': shift_count_rows,
                'date_headers': sorted_dates,
                'shift_labels': SHIFT_LABELS_ORDERED,
                'from_date': from_date_str,
                'to_date': to_date_str,
            })
 
        except Exception as e:
            messages.error(request, f"Invalid date input: {str(e)}")
 
    current_user = User.objects.get(emp_id=request.session['emp_id'])

    return render(request, 'Freewheel_Portal/view_shift.html', {
        'from_date': from_date_str,
        'to_date': to_date_str,
        'current_user': current_user,
    })





 
def upload_profile_image(request):
    if 'emp_id' not in request.session:
        return redirect('login')
    print("Request method:", request.method)
    print("Is authenticated:", request.user.is_authenticated)
    print("Files:", request.FILES)
 
    if request.method == "POST" and request.FILES.get("profile_image"):
        print("Processing profile image upload")
        profile_image = request.FILES["profile_image"]
        current_user = User.objects.get(emp_id=request.session['emp_id'])
        current_user.profile_image = profile_image
        current_user.save(update_fields=["profile_image"])
        return JsonResponse({"success": True, "image_url": current_user.profile_image.url})
 
    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)






 
def notice_view(request):
    # All notices sorted by priority and time
    all_notices = Notice.objects.all().order_by(
        Case(
            When(priority='Urgent', then=Value(1)),
            When(priority='Important', then=Value(2)),
            When(priority='Normal', then=Value(3)),
            default=Value(4),
            output_field=IntegerField()
        ),
        '-posted_at'
    )
    return render(request, 'Freewheel_Portal/view_notice.html', {
        'all_notices': all_notices
    })
 
def notice_add(request):
    if 'emp_id' not in request.session:
        return redirect('login')
 
    current_user = User.objects.get(emp_id=request.session['emp_id'])
    all_notices = Notice.objects.filter(posted_by=current_user).order_by(
        Case(
            When(priority='Urgent', then=Value(1)),
            When(priority='Important', then=Value(2)),
            When(priority='Normal', then=Value(3)),
            default=Value(4),
            output_field=IntegerField()
        ),
        '-posted_at'
    )
 
    return render(request, 'Freewheel_Portal/notice.html', {
        'all_notices': all_notices,
        'current_user': current_user,
    })
 
def notice_sub(request):
    if 'emp_id' not in request.session:
        return redirect('login')
 
    current_user = User.objects.get(emp_id=request.session['emp_id'])
 
    if request.method == 'POST':
        if 'post_notice' in request.POST:
            message = request.POST.get('message', '').strip()
            priority = request.POST.get('priority', '').strip().capitalize()
            end_date_str = request.POST.get('end_date', '').strip()
 
            end_date = None
            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
 
            if message and priority:
                Notice.objects.create(
                    message=message,
                    posted_by=current_user,
                    posted_at=timezone.now(),
                    priority=priority,
                    end_date=end_date
                )
            return redirect('notice_add')
       
 
def edit_notice(request, notice_id):
    if 'emp_id' not in request.session:
        return redirect('login')
 
    current_user = User.objects.get(emp_id=request.session['emp_id'])
 
    notice = get_object_or_404(Notice, id=notice_id, posted_by=current_user)
 
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if message:
            notice.message = message
            notice.save()
    return redirect('notice_add')
 
def delete_notice(request, notice_id):
    if 'emp_id' not in request.session:
        return redirect('login')
 
    notice = get_object_or_404(Notice, id=notice_id)
    current_user = User.objects.get(emp_id=request.session['emp_id'])
 
    if notice.posted_by == current_user and request.method == 'POST':
        notice.delete()
    return redirect('notice_add')





 
def notice(request):
 
    if 'emp_id' not in request.session:
        return redirect('login')
   
    current_user = User.objects.get(emp_id=request.session['emp_id'])
    current_user.dynamic_shift = get_today_shift_for_user(current_user.emp_id) or current_user.shift
    dynamic_shift = None
    latest_notice = Notice.objects.filter(message__icontains='urgent').order_by('-posted_at')[:4]    
    users = list(User.objects.all())
 
    for u in users:
        dynamic_shift = get_today_shift_for_user(u.emp_id) or u.shift
        u.shift = dynamic_shift
        if u.shift in ['WO', 'CO', 'UL', 'PL']:
            u.status = 'Out Of Office'
        u.save(update_fields=['shift', 'status'])
 
    for user in users:
        user.open_ticket_count = Ticket.objects.filter(
            assignee_name=user.assignee_name,
            status__iexact='Open'
        ).count()
 
        user.pending_ticket_count = Ticket.objects.filter(
            assignee_name=user.assignee_name,
            status__iexact='Pending'
        ).count()
 
        current_user.open_ticket_count = Ticket.objects.filter(
            assignee_name=current_user.assignee_name,
            status__iexact='Open'
        ).count()
 
        current_user.pending_ticket_count = Ticket.objects.filter(
            assignee_name=current_user.assignee_name,
            status__iexact='Pending'
        ).count()
 
 
 
 
    # ✅ Handle JSON delegation submission
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            shift1_status = data.get('shift1_status', {})
            shift3_status = data.get('shift3_status', {})
            shift6_status = data.get('shift6_status', {})  # ✅ NEW
 
            shift1_end_email = data.get('shift1_end_email', "")
            shift3_end_email = data.get('shift3_end_email', "")
            shift6_end_email = data.get("shift6_end_email", "")
 
            shift1_end_user = User.objects.filter(emp_id=shift1_end_email).first()
            shift3_end_user = User.objects.filter(emp_id=shift3_end_email).first()
            shift6_end_user = User.objects.filter(emp_id=shift6_end_email).first()
           
 
            Schedule.objects.update_or_create(
                date=now().date(),
                defaults={
                    'shift1_status': shift1_status,
                    'shift3_status': shift3_status,
                    'shift1_end_email': shift1_end_user,
                    'shift3_end_email': shift3_end_user,
                    'shift6_status': shift6_status, # ✅ store shift6
                    'shift6_end_email': shift6_end_user,
                }
            )
 
            # Add notice for bihourly assignment
            Notice.objects.create(
            message=f"📌 Bihourly assigned for {localdate().strftime('%d-%b-%Y')}",
            posted_by=current_user,
            posted_at=timezone.now()
            )
 
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
 
 
 
    # ✅ Get today's schedule
    schedule = Schedule.objects.filter(date=now().date()).first()
    shift1_status = schedule.shift1_status if schedule else {}
    shift3_status = schedule.shift3_status if schedule else {}
    shift6_status = schedule.shift6_status if schedule and hasattr(schedule, 'shift6_status') else {}  # ✅
 
    shift1_end_email_id = schedule.shift1_end_email_id if schedule else ""
    shift3_end_email_id = schedule.shift3_end_email_id if schedule else ""
    shift6_end_email_id = schedule.shift6_end_email_id if schedule else ""
 
    # ✅ Notices
    shift_notices = []
    today_str = localdate().strftime('%d-%b-%Y')
    shift_notices.append(f"📌 Bihourly Allocation for {today_str}")
 
    def add_shift_details(shift_name, shift_data):
        for time, emp_id in shift_data.items():
            try:
                user = User.objects.get(emp_id=emp_id)
                shift_notices.append(f"{shift_name} — {time}: {user.assignee_name}")
            except User.DoesNotExist:
                shift_notices.append(f"{shift_name} — {time}: Not Assigned")
 
    add_shift_details("Shift 1", shift1_status)
    add_shift_details("Shift 3", shift3_status)
    add_shift_details("Shift 6", shift6_status)  # ✅
 
    shift_notices.append("📬 Shift-end Email Allocation")
    if shift1_end_email_id:
        try:
            user = User.objects.get(emp_id=shift1_end_email_id)
            shift_notices.append(f"Shift 1 End Mail: {user.assignee_name}")
        except User.DoesNotExist:
            shift_notices.append(f"Shift 1 End Mail: [Unknown ID: {shift1_end_email_id}]")
    else:
        shift_notices.append("Shift 1 End Mail: Not Assigned")
 
    if shift3_end_email_id:
        try:
            user = User.objects.get(emp_id=shift3_end_email_id)
            shift_notices.append(f"Shift 3 End Mail: {user.assignee_name}")
        except User.DoesNotExist:
            shift_notices.append(f"Shift 3 End Mail: [Unknown ID: {shift3_end_email_id}]")
    else:
        shift_notices.append("Shift 3 End Mail: Not Assigned")
 
    if shift6_end_email_id:
        try:
            user = User.objects.get(emp_id=shift6_end_email_id)
            shift_notices.append(f"Shift 6 End Mail: {user.assignee_name}")
        except User.DoesNotExist:
            shift_notices.append(f"Shift 6 End Mail: [Unknown ID: {shift6_end_email_id}]")
    else:
        shift_notices.append("Shift 6 End Mail: Not Assigned")
 
 
    # ✅ Combine notices
    combined_notices = []
    for msg in shift_notices:
        combined_notices.append({
            "message": msg,
            "posted_by": None,
            "posted_at": localtime(timezone.now()),
        })
 
    for note in Notice.objects.order_by('-posted_at'):
        combined_notices.append({
            "id": note.id,
            "message": note.message,
            "posted_by": note.posted_by,
            "posted_at": localtime(note.posted_at),
        })
 
    is_allowed = current_user.assignee_name in ALLOWED_USERS
 
    delegated_to_user = any(
        emp_id == current_user.emp_id
        for emp_id in list(shift1_status.values()) + list(shift3_status.values()) + list(shift6_status.values())  # ✅
    )
 
    # ✅ Split shift-specific users
    shift1_users = [user for user in users if user.shift == 'S1']
    shift3_users = [user for user in users if user.shift in ['S2','S3']]
    shift6_users = [user for user in users if user.shift in ['S5','S6']]  # ✅
 
 
 
 
 
    assigned_tasks = []  # Collect messages like: "Shift 1 – 9:00 AM", or "Shift 3 – End Mail"
 
    if schedule:
        for time, emp_id in schedule.shift1_status.items():
            if emp_id == current_user.emp_id:
                assigned_tasks.append(f"Shift 1 – {time}")
        for time, emp_id in schedule.shift3_status.items():
            if emp_id == current_user.emp_id:
                assigned_tasks.append(f"Shift 3 – {time}")
        for time, emp_id in schedule.shift6_status.items():
            if emp_id == current_user.emp_id:
                assigned_tasks.append(f"Shift 6 – {time}")
 
        if schedule.shift1_end_email_id == current_user.emp_id:
            assigned_tasks.append("Shift 1 – End Mail")
        if schedule.shift3_end_email_id == current_user.emp_id:
            assigned_tasks.append("Shift 3 – End Mail")
        if schedule.shift6_end_email_id == current_user.emp_id:
            assigned_tasks.append("Shift 6 – End Mail")
 
# Pass it to the template
    delegated_to_user = bool(assigned_tasks)
 
    # ✅ Sort users by status
    status_priority = {'Available': 0, 'In-Meeting': 1, 'Away': 2, 'Offline': 3, 'Out Of Office': 4}
    users.sort(key=lambda user: status_priority.get(user.status, 99))
 
    hold_product_counts = (
        Ticket.objects.filter(status='Hold')
        .values('product_category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    new_product_counts = (
        Ticket.objects.filter(status='New')
        .values('product_category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    pending_product_counts = (
        Ticket.objects.filter(status='Pending')
        .values('product_category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
 
    open_product_counts = (
        Ticket.objects.filter(status='Open')
        .values('product_category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
 
    context = {
        'users': users,
        'current_user': current_user,
        'tickets': Ticket.objects.all(),
        'open_tickets': Ticket.objects.filter(status='Open'),
        'pending_tickets': Ticket.objects.filter(status='Pending'),
        'hold_tickets': Ticket.objects.filter(status='Hold'),
        'new_tickets': Ticket.objects.filter(status='New'),
        'unassigned_tickets': Ticket.objects.filter(assignee_name="",).exclude(status="New"),
 
        'shift1_times': SHIFT1_TIMINGS,
        'shift3_times': SHIFT3_TIMINGS,
        'shift6_times': SHIFT6_TIMINGS,  # ✅
 
        'shift1_status': shift1_status,
        'shift3_status': shift3_status,
        'shift6_status': shift6_status,  # ✅
 
        'shift1_end_email_id': shift1_end_email_id,
        'shift3_end_email_id': shift3_end_email_id,
        'shift6_end_email_id': shift6_end_email_id,
 
        'all_notices': Notice.objects.select_related('posted_by').order_by('-posted_at'),
 
 
        'latest_notice': latest_notice,
        'notices': combined_notices,
        'is_allowed': is_allowed,
        'delegated_to_user': delegated_to_user,
        'schedule': schedule,
 
        'shift1_users': shift1_users,
        'shift3_users': shift3_users,
        'shift6_users': shift6_users,  # ✅
        "delegated_to_user": delegated_to_user,
        "user_assignments": assigned_tasks,
 
        "today": datetime.today().date(),
 
        'pending_product_counts': pending_product_counts,
        'hold_product_counts': hold_product_counts,
        'new_product_counts': new_product_counts,
        'open_product_counts ': open_product_counts,
    }
 
    return render(request, 'Freewheel_Portal/notice.html', context)
 

 
def notice_board(request):
    if 'emp_id' not in request.session:
        return redirect('login')
 
    notice = Notice.objects.all().order_by('-posted_at')
 
    notice_priority = {'Urgent': 0, 'Important': 1, 'Normal': 2}
    notice.sort(key=lambda notice: notice_priority.get(notice.priority, 99))
 
    return render(request, 'Freewheel_Portal/notice.html', {
        'all_notices': notice,
    })




 
@csrf_exempt
def reset_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
       
        # Assuming session stores emp_id of logged-in user
        emp_id = request.session.get("emp_id")
       
        if not emp_id:
            return HttpResponse("Unauthorized", status=401)
       
        user = get_object_or_404(User, emp_id=emp_id)
       
        if user.password != current_password:
            return HttpResponse("Incorrect current password", status=400)
       
        user.password = new_password
        user.save()
       
        return redirect("home")  # Or return HttpResponse("Password updated successfully")
   
    return HttpResponse("Invalid Request", status=400)







def working_ticket(request):
    if 'emp_id' not in request.session:
        return redirect('login')
    
    if request.method == 'POST':
        print("[DEBUG] POST request received at /working-ticket")

        data = json.loads(request.body)
        ticket_id = data.get("ticket_id")

        print(f"[DEBUG] Raw payload: {data}")
        print(f"[INFO] User {request.user.username} selected working_ticket: {ticket_id}")

        current_user = User.objects.get(emp_id=request.session['emp_id'])

        # Save to user model
        current_user.working_ticket = ticket_id  # can be None
        current_user.save(update_fields=['working_ticket'])

        print(f"[DEBUG] Saved to user.working_ticket = {current_user.working_ticket}")

        return JsonResponse({"success": True})
        

    print("[WARN] Non-POST request received")
    return JsonResponse({"success": False, "error": "Invalid request method"})




def get_all_user_statuses(request):
    users = User.objects.all().values('emp_id', 'status')
    status_data = {}

    for user in users:
        icon = ""
        status = user['status']

        if status == 'Available':
            icon = '<i class="fa-solid fa-circle-check" style="color: #4CAF50;"></i>'
        elif status == 'Away':
            icon = '<i class="fa-solid fa-clock" style="color: #FFC107;"></i>'
        elif status == 'In-Meeting':
            icon = '<i class="fa-solid fa-phone" style="color: #F44336;"></i>'
        elif status == 'Offline':
            icon = '<i class="fa-solid fa-circle-xmark" style="color: #7f7f7f;"></i>'
        elif status == 'Out Of Office':
            icon = '<i class="fa-solid fa-circle-arrow-right" style="color: #c235e0;"></i>'

        status_data[str(user['emp_id'])] = f"{icon} {status}"

    return JsonResponse(status_data)




def get_ticket_updates(request):
    tickets = Ticket.objects.all().values('ticket_id', 'subject', 'status', 'priority', 'requester_organization', 'group')

    data = {}
    for ticket in tickets:
        html = f"""
          <a href='https://freewheel.zendesk.com/agent/tickets/{ticket['ticket_id']}' target='_blank'>
            {ticket['ticket_id']}
          </a>
          <div>{ticket['subject'] or 'N/A'}</div>
          <div>{ticket['status']}</div>
          <div>{ticket['priority'] or 'Normal'}</div>
          <div>{ticket['requester_organization'] or 'Unknown'}</div>
          <div>{ticket['group']}</div>
          <div><button class='comment-btn'><i class='fa-solid fa-comments' style='color: black;'></i></button></div>
          <div><button class='assign-btn'><i class='fa-solid fa-id-badge' style='color: black;'></i></button></div>
        """
        data[str(ticket['ticket_id'])] = html

    return JsonResponse(data)
