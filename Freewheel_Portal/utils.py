from .models import ShiftEndTable, ShiftEndTicketDetails, SLABreachedTicket
from django.db.models import Count, F
 
def populate_summary_data():
    ShiftEndTicketDetails.objects.all().delete()
    SLABreachedTicket.objects.all().delete()
 
    # Save ticket status counts
    status_counts = ShiftEndTable.objects.values('ticket_status').annotate(count=Count('ticket_status'))
    total = 0
    for entry in status_counts:
        status = entry['ticket_status'] or "Unknown"
        count = entry['count']
        total += count
 
        ShiftEndTicketDetails.objects.create(
            status=status,
            total=count,
            open=count if status.lower() == 'open' else 0,
            pending=count if status.lower() == 'pending' else 0,
            solved=count if status.lower() == 'solved' else 0,
            hold=count if status.lower() == 'hold' else 0,
        )
                                  
    # Save SLA breaches
    sla_breaches = ShiftEndTable.objects.filter(
        ticket_id__solved_timestamp__isnull=False,
        ticket_id__due_timestamp__isnull=False,
        ticket_id__solved_timestamp__gt=F('ticket_id__due_timestamp')
    )
 
    for entry in sla_breaches:
        SLABreachedTicket.objects.create(
            ticket_id=entry.ticket_id,
            subject=entry.ticket_subject or '',
            duration="N/A",
            duration_of_the_breach="N/A",
            reason_for_the_breach="Auto-detected breach",
        )

import pandas as pd
import datetime
import os
from django.conf import settings
 
SHIFT_EXCEL_PATH = os.path.join(settings.MEDIA_ROOT, 'shifts.xlsx')
 
def get_today_shift_for_user(name):
    try:
        df = pd.read_excel(SHIFT_EXCEL_PATH)
        df.columns = df.columns.map(str).str.strip()
 
        today = datetime.datetime.now().strftime("%d-%b")
        today_alt = today.lstrip("0")  # Handle both "09-Jun" and "9-Jun"
 
        shift_col = today if today in df.columns else today_alt
        if shift_col not in df.columns:
            print(f"[ERROR] Shift column for today ({today}) not found.")
            return None
 
        df['Name'] = df['Name'].astype(str).str.strip().str.lower()
        match = df[df['Name'] == name.strip().lower()]
 
        if not match.empty:
            shift_val = match.iloc[0][shift_col]
            print(f"[DEBUG] Found shift for {name}: {shift_val}")
            return shift_val
 
        print(f"[WARN] No shift match found for name: {name}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to get shift from Excel for {name}: {e}")
        return None