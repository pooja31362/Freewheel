from django.shortcuts import render
from .models import Ticket, User  # import your models
from django.views.decorators.cache import never_cache

 
@never_cache # type: ignore
def login_view(request):
    return render(request, 'Freewheel_Portal/login.html')



def home(request):
    current_user = User.objects.get(emp_id=request.session['emp_id'])
    context = {
        'users': User.objects.exclude(emp_id=current_user.emp_id),
        'current_user': current_user,
        'tickets': Ticket.objects.all(),
        'open_tickets': Ticket.objects.filter(status='Open'),
        'pending_tickets': Ticket.objects.filter(status='Pending'),
        'hold_tickets': Ticket.objects.filter(status='Hold'),
        'new_tickets': Ticket.objects.filter(status='New'),
    }
    return render(request, 'Freewheel_Portal/home.html', context)

    context = {
        'users': User.objects.all().values(),
        'current_user': User.objects.get(emp_id=request.session['emp_id']),
        'tickets': Ticket.objects.all().values(),
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
 