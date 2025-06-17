from django.shortcuts import render
from .models import Ticket, User  # import your models
from django.views.decorators.cache import never_cache

 
@never_cache # type: ignore
def login_view(request):
    return render(request, 'Freewheel_Portal/login.html')



def home(request):
    current_user = User.objects.get(emp_id=request.session['emp_id'])

    # Define priority of statuses
    status_priority = {
        'Available': 0,
        'Meeting': 1,
        'Back': 2,
        'BRB': 2,
        'Offline': 3
    }

    # Get all other users excluding current user
    users = list(User.objects.exclude(emp_id=current_user.emp_id))

    # Sort users based on status priority
    users.sort(key=lambda user: status_priority.get(user.status, 99))

    context = {
        'users': users,
        'current_user': current_user,
        'tickets': Ticket.objects.all(),
        'open_tickets': Ticket.objects.filter(status='Open'),
        'pending_tickets': Ticket.objects.filter(status='Pending'),
        'hold_tickets': Ticket.objects.filter(status='Hold'),
        'new_tickets': Ticket.objects.filter(status='New'),
    }

    return render(request, 'Freewheel_Portal/home.html', context)



from .models import User  # Make sure Employee is imported
from .models import User
from django.contrib import messages
from django.shortcuts import redirect

def do_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = User.objects.get(user_name=username)
            if user.password == password:
                request.session.flush()  # Clear previous session

                access = [a.lower().strip() for a in user.access]
                request.session['emp_id'] = user.emp_id
                request.session['access'] = access

                return redirect('home')
            else:
                messages.error(request, "Invalid password.")
        except User.DoesNotExist:
            messages.error(request, "User not found.")

    return redirect('login')



from django.http import JsonResponse

def update_status(request):
    if request.method == 'POST':
        status = request.POST.get('status')
        user = User.objects.get(emp_id=request.session['emp_id'])

        if status in dict(User.STATUS_CHOICES):
            user.status = status
            user.save()
            return JsonResponse({'success': True, 'status': status})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid status'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


from django.http import HttpResponse
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
 
def forgot_password(request):
    if request.method == 'POST':
        username = request.POST.get('username')
 
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponse("user_not_found")
 
        # Optionally: You can check access here if you want to restrict certain users
        # For example:
        # if user.access not in ['admin', 'staff', 'guest']:
        #     return HttpResponse("user_not_found")
 
        token = get_random_string(length=48)
        user.reset_token = token
        user.token_created_at = timezone.now()
        user.save()
 
        reset_url = request.build_absolute_uri(
            reverse('reset_password', args=[token])
        )
 
        send_mail(
            subject='Reset Your Password',
            message=f'Click the link to reset your password: {reset_url}',
            from_email='noreply@example.com',
            recipient_list=[user.email],
        )
        return HttpResponse("success")


 
import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from .models import Ticket
from django.utils.timezone import make_aware
 
def upload_excel(request):
    if request.method == 'POST' and request.FILES.get('file'):
        excel_file = request.FILES['file']
        df = pd.read_excel(excel_file)
 
        # Clean DataFrame
        df = df.where(pd.notnull(df), None)
 
 
        column_field_map = {
            'Ticket ID': 'ticket_id',
            'Ticket created - Timestamp': 'created_timestamp',
            'Ticket priority': 'priority',
            'Ticket subject': 'subject',
            'Requester organization name': 'requester_organization',
            'Product Category': 'product_category',
            'Ticket type': 'ticket_type',
            'JIRA Issue ID': 'jira_issue_id',
            'Assignee name': 'assignee_name',
            'Ticket status': 'status',
            'Ticket solved - Timestamp': 'solved_timestamp',
            'Ticket assigned - Timestamp': 'assigned_timestamp',
            'Ticket updated - Timestamp': 'updated_timestamp',
            'Ticket due - Timestamp': 'due_timestamp',
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
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].apply(lambda x: make_aware(x) if pd.notnull(x) and x.tzinfo is None else x)
 
        uploaded_ticket_ids = set()
       
        for _, row in df.iterrows():
            raw_id = row.get('Ticket ID')
            if raw_id is None:
                continue
 
            ticket_id = str(raw_id).strip()
            uploaded_ticket_ids.add(ticket_id)
            data = {}
 
            for excel_col, model_field in column_field_map.items():
                if excel_col in df.columns:
                    value = row[excel_col]
                    data[model_field] = value if pd.notnull(value) else None
                else:
                    data[model_field] = None
 
            ticket, created = Ticket.objects.update_or_create(
                ticket_id=ticket_id,
                defaults=data
            )
 
 
        # 🔥 Delete tickets that are not in Excel
        db_ticket_ids = set(Ticket.objects.values_list('ticket_id', flat=True))
        to_delete = db_ticket_ids - uploaded_ticket_ids
 
        if to_delete:
            Ticket.objects.filter(ticket_id__in=to_delete).delete()
 
        for tid in Ticket.objects.values_list('ticket_id', flat=True):
            print(f"• {tid}", flush=True)
        return HttpResponse("✔️ Tickets uploaded and synced with database.")
   
    return render(request, 'Freewheel_Portal/upload.html')
 
 
from django.shortcuts import render
from .models import Ticket
 
def ticket_list(request):
    tickets = Ticket.objects.all().order_by('ticket_id')  # ascending order
    return render(request, 'Freewheel_Portal/ticket_list.html', {'tickets': tickets})

def test(request):
    return render(request,'Freewheel_Portal/test.html')
 
 
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import UserForm
from .models import GroupAccess, Access
 
def create_user(request):
    initial_data = {}
 
    if request.method == 'GET':
        user_type = request.GET.get('user_type')  # read from query param
        if user_type:
            try:
                group_access = GroupAccess.objects.get(user_type=user_type)
                access_ids = group_access.availed_access
                initial_data['access'] = Access.objects.filter(access_id__in=access_ids)
            except GroupAccess.DoesNotExist:
                pass
 
        form = UserForm(initial=initial_data)
 
    elif request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            form.save_m2m()
            return HttpResponse("User created successfully.")
 
    return render(request, 'Freewheel_Portal/create_user.html', {'form': form})
 
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def shift_end_mail(request):
    if request.method == 'POST':
        summary = request.POST.get('summary')
        issues = request.POST.get('issues')
        plans = request.POST.get('plans')

        user = User.objects.get(emp_id=request.session['emp_id'])

        message_body = f"""
Shift End Mail from {user.name} ({user.emp_id})

📝 Summary of Work:
{summary or 'N/A'}

⚠️ Issues Faced:
{issues or 'None'}

📅 Plan for Tomorrow:
{plans or 'N/A'}
        """

        send_mail(
            subject=f"[Shift End] Update from {user.name}",
            message=message_body,
            from_email='noreply@yourdomain.com',
            recipient_list=['teamlead@example.com'],  # <-- change to your recipient
        )

        return HttpResponse("Mail sent successfully.")
    
    return render(request, 'Freewheel_Portal/shift_end_mail.html')



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils import timezone
from .models import Ticket, ShiftEndTable

@csrf_exempt
def submit_comment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ticket_id = data.get('ticket_id')
            comment = data.get('comment')

            ticket = Ticket.objects.get(ticket_id=ticket_id)
            ticket.comment = comment
            ticket.updated_timestamp = timezone.now()
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

    return JsonResponse({'success': False, 'error': 'Invalid method'})

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.utils import timezone
from .models import Ticket, User

@csrf_exempt
def assign_ticket(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ticket_id = data.get('ticket_id')
            emp_id = data.get('assignee_name')

            ticket = Ticket.objects.get(ticket_id=ticket_id)
            user = User.objects.get(emp_id=emp_id)

            ticket.assignee_name = user.assignee_name
            ticket.assigned_timestamp = timezone.now()
            ticket.save()

            return JsonResponse({'success': True})
        except Ticket.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Ticket not found'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid method'})

from .utils import populate_summary_data
from .models import ShiftEndTable, ShiftEndTicketDetails, SLABreachedTicket
 # or wherever you defined it
 
def shift_end_summary(request):
    populate_summary_data()  # ⚠️ Remove this after testing
 
    # Now pull from stored data
    status_summary = ShiftEndTicketDetails.objects.all()
    sla_breaches = SLABreachedTicket.objects.all()
    shiftend_details = ShiftEndTable.objects.all()
 
    return render(request, 'portal_app/shift_end_summary.html', {
        'status_summary': status_summary,
        'sla_breaches': sla_breaches,
        'shiftend_details': shiftend_details,
    })
 

def new_tickets_view(request):
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        assignee_emp_id = request.POST.get('assignee_emp_id')

        try:
            ticket = Ticket.objects.get(id=ticket_id)
            user = User.objects.get(emp_id=assignee_emp_id)

            ticket.assignee_name = user.assignee_name
            ticket.assigned_timestamp = timezone.now()
            ticket.save()
        except Ticket.DoesNotExist:
            print(f"Ticket with ID {ticket_id} not found.")
        except User.DoesNotExist:
            print(f"User with emp_id {assignee_emp_id} not found.")

        return redirect('new_tickets')

    # Only show unassigned tickets with status 'New'
    tickets = Ticket.objects.filter(assignee_name__isnull=True, status='New')
    users = User.objects.all()
    return render(request, 'portal_app/new_tickets.html', {'tickets': tickets, 'users': users})
