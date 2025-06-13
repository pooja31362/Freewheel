from django.shortcuts import render
from .models import Ticket, User  # import your models
 
def home(request):
    context = {
        'users': User.objects.all(),
        'tickets': Ticket.objects.all().values(),
        'open_tickets': Ticket.objects.filter(status='Open'),
        'pending_tickets': Ticket.objects.filter(status='Pending'),
        'hold_tickets': Ticket.objects.filter(status='Hold'),
        'new_tickets': Ticket.objects.filter(status='New'),
    }

    ticket1 = context['hold_tickets']
    print('hiiiiiiiii',ticket1)
    return render(request, 'Freewheel_Portal/home.html', context)
 
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
 
        print("📊 Excel Columns:", df.columns.tolist(), flush=True)
 
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
                print("⚠️ Skipping row: No Ticket ID", flush=True)
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
 
            print(f"{'✅ Created' if created else '♻️ Updated'} Ticket ID: {ticket_id}", flush=True)
 
        # 🔥 Delete tickets that are not in Excel
        db_ticket_ids = set(Ticket.objects.values_list('ticket_id', flat=True))
        to_delete = db_ticket_ids - uploaded_ticket_ids
 
        if to_delete:
            Ticket.objects.filter(ticket_id__in=to_delete).delete()
            print(f"🗑️ Deleted Ticket IDs not in Excel: {to_delete}", flush=True)
 
        print("📋 Current Ticket IDs in DB:")
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
 