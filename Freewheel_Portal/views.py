from django.shortcuts import render
from .models import Ticket, User  # import your models
from django.views.decorators.cache import never_cache

 
@never_cache # type: ignore
def login_view(request):
    return render(request, 'Freewheel_Portal/login.html')

from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.timezone import now, localdate, localtime
from .models import Ticket, User, Schedule, Notice
import json
from django.http import JsonResponse
import datetime
from .utils import get_today_shift_for_user
from django.db.models import Count


ALLOWED_USERS = ['anibro', 'Nisha','Harikishore T', 'keerthana', 'kavya_akka']
SHIFT1_TIMINGS = ["7:00 AM", "9:00 AM", "11:00 AM", "1:00 PM", "3:00 PM"]
SHIFT3_TIMINGS = ["5:00 PM", "7:00 PM", "9:00 PM", "11:00 PM"]
SHIFT6_TIMINGS = ["7:00 PM", "8:00 PM", "9:00 PM", "10:00 PM"]  # ✅ Add your Shift 6 timings

def home(request):

    if 'emp_id' not in request.session:
        return redirect('login')
    
    current_user = User.objects.get(emp_id=request.session['emp_id'])
    current_user.dynamic_shift = get_today_shift_for_user(current_user.assignee_name) or current_user.shift
    dynamic_shift = None
    latest_notice = list(Notice.objects.order_by('-posted_at')[:4].values())
    users = list(User.objects.exclude(emp_id=current_user.emp_id))

    for u in users:
        dynamic_shift = get_today_shift_for_user(u.assignee_name) or u.shift
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

    # ✅ Handle Notice POST Actions
    if request.method == 'POST':
        if 'post_notice' in request.POST:
            message = request.POST.get('message', '').strip()
            if message:
                Notice.objects.create(message=message, posted_by=current_user, posted_at=timezone.now())
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

        "today" : datetime.date.today,

        'pending_product_counts': pending_product_counts,
        'hold_product_counts': hold_product_counts,
        'new_product_counts': new_product_counts,
        'open_product_counts ': open_product_counts,
    }

    return render(request, 'Freewheel_Portal/home.html', context)


def notice(request):

    if 'emp_id' not in request.session:
        return redirect('login')
    
    current_user = User.objects.get(emp_id=request.session['emp_id'])
    current_user.dynamic_shift = get_today_shift_for_user(current_user.assignee_name) or current_user.shift
    dynamic_shift = None
    latest_notice = list(Notice.objects.order_by('-posted_at')[:4].values())
    users = list(User.objects.exclude(emp_id=current_user.emp_id))

    for u in users:
        dynamic_shift = get_today_shift_for_user(u.assignee_name) or u.shift
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

        "today" : datetime.date.today,

        'pending_product_counts': pending_product_counts,
        'hold_product_counts': hold_product_counts,
        'new_product_counts': new_product_counts,
        'open_product_counts ': open_product_counts,
    }

    return render(request, 'Freewheel_Portal/notice.html', context)


def notice_sub(request):
        # ✅ Handle Notice POST Actions

    current_user = User.objects.get(emp_id=request.session['emp_id'])

    if request.method == 'POST':
        if 'post_notice' in request.POST:
            message = request.POST.get('message', '').strip()
            print("this is the message",message)
            if message:
                Notice.objects.create(message=message, posted_by=current_user, posted_at=timezone.now())
            return redirect('notice')

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
            return redirect('notice')

        elif 'delete_notice' in request.POST:
            notice_id = request.POST.get('notice_id')
            if notice_id:
                try:
                    notice = Notice.objects.get(id=notice_id, posted_by=current_user)
                    notice.delete()
                except Notice.DoesNotExist:
                    pass
            return redirect('notice')
    return redirect('notice')



# views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Ticket
import json

@csrf_exempt
def reset_ticket_assignee(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ticket_id = data.get("ticket_id")

        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id)
            ticket.assignee_name = ""
            ticket.save()
            return JsonResponse({"success": True})
        except Ticket.DoesNotExist:
            return JsonResponse({"success": False, "error": "Ticket not found"})
    
    return JsonResponse({"success": False, "error": "Invalid request"})





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
    print("Request method:", request.method)
    print("Request POST data:", request.POST)
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
            'Requester organization name' : 'requester_organization',
            'Requester name': 'requester',
            'Product Category': 'product_category',
            'Ticket type': 'ticket_type',
            'JIRA Issue ID': 'jira_issue_id',
            'Assignee name': 'assignee_name',
            'Ticket status': 'status',
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
 


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils import timezone
from .models import Ticket, ShiftEndTable, User

@csrf_exempt
def submit_comment(request):
    if request.method == 'POST':
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

    return JsonResponse({'success': False, 'error': 'Invalid method'})

from .utils import populate_summary_data
from .models import PreviousShiftEndTable, PreviousShiftEndTicketDetails, PreviousSLABreachedTicket
from .models import ShiftEndTable, ShiftEndTicketDetails, SLABreachedTicket

 # or wherever you defined it
 
def shift_end_summary(request):

    if 'emp_id' not in request.session:
        return redirect('login')
    
    current_user = User.objects.get(emp_id=request.session['emp_id'])
    current_user.dynamic_shift = get_today_shift_for_user(current_user.assignee_name) or current_user.shift
    dynamic_shift = None
    users = list(User.objects.exclude(emp_id=current_user.emp_id))

    for u in users:
        dynamic_shift = get_today_shift_for_user(u.assignee_name) or u.shift
        u.shift = dynamic_shift
        if u.shift in ['WO', 'CO', 'UL', 'PL']:
            u.status = 'Out Of Office'
        else:
            u.status = 'Offline'
        u.save(update_fields=['shift', 'status'])

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



            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    # ✅ Handle Notice POST Actions
    if request.method == 'POST':
        if 'post_notice' in request.POST:
            message = request.POST.get('message', '').strip()
            if message:
                Notice.objects.create(message=message, posted_by=current_user, posted_at=timezone.now())
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
        'shift6_times': SHIFT6_TIMINGS,  # ✅

        'shift1_status': shift1_status,
        'shift3_status': shift3_status,
        'shift6_status': shift6_status,  # ✅

        'shift1_end_email_id': shift1_end_email_id,
        'shift3_end_email_id': shift3_end_email_id,
        'shift6_end_email_id': shift6_end_email_id,


        'notices': combined_notices,

        'is_allowed': is_allowed,
        'delegated_to_user': delegated_to_user,
        'schedule': schedule,

        'shift1_users': shift1_users,
        'shift3_users': shift3_users,
        'shift6_users': shift6_users,  # ✅
        "delegated_to_user": delegated_to_user,
        "user_assignments": assigned_tasks,

        "today" : datetime.date.today,

        'current_status_summary': ShiftEndTicketDetails.objects.all(),
        'current_sla_breaches': SLABreachedTicket.objects.all(),
        'current_shiftend_details': ShiftEndTable.objects.all(),

        'previous_status_summary': PreviousShiftEndTicketDetails.objects.all(),
        'previous_sla_breaches': PreviousSLABreachedTicket.objects.all(),
        'previous_shiftend_details': PreviousShiftEndTable.objects.all(),
    }

    return render(request, 'Freewheel_Portal/shift-end-mail.html', context)


from django.shortcuts import redirect, render
from django.utils import timezone
from dateutil import parser

def submit_leave(request):
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



def new_tickets_view(request):
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        assignee_emp_id = request.POST.get('assignee_emp_id')

        
        ticket = Ticket.objects.get(id=ticket_id)
        user = User.objects.get(emp_id=assignee_emp_id)

        ticket.assignee_name = user.assignee_name
        ticket.assigned_timestamp = timezone.now()
        ticket.save()


        return redirect('new_tickets')

    # Only show unassigned tickets with status 'New'
    tickets = Ticket.objects.filter(assignee_name__isnull=True, status='New')
    users = User.objects.all()
    return render(request, 'portal_app/new_tickets.html', {'tickets': tickets, 'users': users})

from django.shortcuts import render, redirect
import pandas as pd
import datetime
import os
from django.conf import settings
from django.urls import reverse
 
SHIFT_EXCEL_PATH = os.path.join(settings.BASE_DIR, 'media', 'shifts.xlsx')
 
def filter_by_shift(request):
    employees = []
    selected_shift = request.GET.get('shift', '').strip()
    today = datetime.datetime.now().strftime("%d-%b")
   
    try:
        df = pd.read_excel(SHIFT_EXCEL_PATH)
        df.columns = df.columns.map(str).str.strip()
 
        if today not in df.columns:
            today = today.lstrip("0")
 
        df['Name'] = df['Name'].astype(str).str.strip()
        df[today] = df[today].astype(str).str.strip()
 
        if selected_shift and today in df.columns:
            filtered_df = df[df[today] == selected_shift]
            employees = filtered_df['Name'].tolist()
    except Exception as e:
        return render(request, 'Freewheel_Portal/filter_shift.html', {
            'error': f"Error loading shift data: {str(e)}"
        })
 
    return render(request, 'Freewheel_Portal/filter_shift.html', {
        'employees': employees,
        'selected_shift': selected_shift
    })
 
from django.db.models import Q
from django.contrib import messages
 
def upload_shift_excel(request):
    if request.method == 'POST' and request.FILES.get('shift_excel'):
        excel_file = request.FILES['shift_excel']
        file_path = os.path.join(settings.MEDIA_ROOT, 'shifts.xlsx')
 
        with open(file_path, 'wb+') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)
 
        try:
            df = pd.read_excel(file_path)
            df.columns = df.columns.map(str).str.strip()
 
            if 'Name' not in df.columns:
                raise KeyError("The uploaded file does not contain a 'Name' column.")
 
            today = datetime.datetime.now().strftime("%d-%b")
            if today not in df.columns:
                today = today.lstrip("0")
 
            if today not in df.columns:
                raise KeyError(f"The Excel file doesn't contain shift data for today ({today})")
 
            df['Name'] = df['Name'].astype(str).str.strip()
            df[today] = df[today].astype(str).str.strip()
 
            updated_count = 0
            for _, row in df.iterrows():
                name = row['Name']
                shift_today = str(row[today]).strip()
 
                user_qs = User.objects.filter(Q(username__iexact=name) | Q(name__iexact=name))
                for user in user_qs:
                    try:
                        user.shift = shift_today
                        user.save(update_fields=['shift'])
                        updated_count += 1
                    except Exception as e:
                        continue
 
            messages.success(request, f"Shift file uploaded and {updated_count} user(s) updated successfully.")
            request.session['shift_file_uploaded'] = True
 
        except Exception as e:
            messages.error(request, f"Error loading shift data: {str(e)}")
 
    return redirect('filter_by_shift')


from django.http import JsonResponse
from .utils import truncate_shift_end

def manual_freeze_view(request):
    if request.method == "POST":
        success = truncate_shift_end()
        return JsonResponse({'success': success})






#bi-hourly report
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UploadExcelForm
from .models import TicketReport, User
from django.utils.timezone import now
from collections import defaultdict
 
def classify_product(row):
    tg = row.get('ticket group', '')
    if tg == "Support Eng":
        return "SH"
    elif tg in ["BW CIEC Onboarding", "BW Support"]:
        return "FW DSP"
    elif tg == "SFX Support":
        return "FW SSP"
    elif tg in ["STRATA CIEC Onboarding", "Adazzle", "OneStrata Support"]:
        return "Strata"
    return None
 
def upload_excel_report(request):
    form = UploadExcelForm()
    report_data = TicketReport.objects.all().order_by('timestamp')  # default load
 
    if request.method == 'POST':
        form = UploadExcelForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            df = pd.read_excel(excel_file)
            df.columns = df.columns.str.strip().str.replace('\xa0', ' ').str.lower()
 
            df['Product'] = df.apply(classify_product, axis=1)
            grouped = df.groupby('Product')
 
            # Get active users from the DB
            active_users = User.objects.exclude(status__in=['Out Of Office', 'Offline'])
            user_status_map = {user.assignee_name.strip().lower(): user for user in active_users}
 
            product_being_worked = defaultdict(int)
 
            # Count open/new tickets per user per product if the user is active
            for _, row in df.iterrows():
                if row['ticket status'] in ['Open', 'New']:
                    assignee = row.get('assignee name', '').strip().lower()
                    product = row.get('Product')
                    if assignee in user_status_map and product:
                        product_being_worked[product] += 1
 
            # Clear current table to load new results
            TicketReport.objects.all().delete()
            report_data = []
 
            for product, group in grouped:
                open_new_tickets = group[group['ticket status'].isin(['Open', 'New'])]
 
                open_count = (group['ticket status'] == 'Open').sum()
                new_count = (group['ticket status'] == 'New').sum()
                urgent_count = (open_new_tickets['ticket priority'] == 'Urgent').sum()
                high_count = (open_new_tickets['ticket priority'] == 'High').sum()
                normal_count = (open_new_tickets['ticket priority'] == 'Normal').sum()
                low_count = (open_new_tickets['ticket priority'] == 'Low').sum()
 
                being_worked = product_being_worked.get(product, 0)
                unattended = (open_count + new_count) - being_worked
 
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
                    engineers=0,
                    ho_followup=0
                )  
                report_data.append(report)
 
    return render(request, 'Freewheel_Portal/report_upload.html', {
        'form': form,
        'report_data': report_data
    })
 
def update_report_row(request, pk):
    report = get_object_or_404(TicketReport, pk=pk)
    if request.method == 'POST':
        report.engineers = int(request.POST.get('engineers', 0))
        report.ho_followup = int(request.POST.get('ho_followup', 0))
        report.unattended = (report.open_count + report.new_count) - report.being_worked
        report.save()
    return redirect('upload_excel_report')
 
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
 
@csrf_exempt
def save_bulk_report_updates(request):
    if request.method == 'POST':
        ids = request.POST.getlist('ids')
        for id in ids:
            report = TicketReport.objects.get(id=id)
            engineers = request.POST.get(f'engineers_{id}')
            ho_followup = request.POST.get(f'ho_followup_{id}')
            if engineers is not None:
                report.engineers = int(engineers)
            if ho_followup is not None:
                report.ho_followup = int(ho_followup)
            report.unattended = (report.open_count + report.new_count) - report.being_worked
            report.save()
    return HttpResponseRedirect(reverse('upload_excel_report'))
 
 