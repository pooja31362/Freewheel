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
from Freewheel_Portal.models import User

SHIFT_EXCEL_PATH = os.path.join(settings.MEDIA_ROOT, 'shifts.xlsx')

_cached_shift_df = None
_cached_shift_col_index = None
_cached_shift_timestamp = None  # ← use file modified time as cache key

def get_today_shift_for_user(name):
    global _cached_shift_df, _cached_shift_col_index, _cached_shift_timestamp

    today = datetime.date.today()

    try:
        if not os.path.exists(SHIFT_EXCEL_PATH):
            print(f"[ERROR] Shift Excel file not found at: {SHIFT_EXCEL_PATH}")
            return None

        file_timestamp = os.path.getmtime(SHIFT_EXCEL_PATH)

        if _cached_shift_df is None or _cached_shift_timestamp != file_timestamp:
            print(f"[INFO] Reloading Excel file (modified: {file_timestamp})")
            _cached_shift_df = pd.read_excel(SHIFT_EXCEL_PATH, header=None)
            _cached_shift_timestamp = file_timestamp

            date_row = _cached_shift_df.iloc[1]
            dates = pd.to_datetime(date_row, errors='coerce').dt.date

            try:
                _cached_shift_col_index = dates[dates == today].index[0]
            except IndexError:
                print(f"[ERROR] Today's date ({today}) not found in Excel.")
                return None

        df = _cached_shift_df
        shift_col_index = _cached_shift_col_index

        user_names = df.iloc[4:, 0].astype(str).str.strip().str.lower()
        name = name.strip().lower()

        if name in user_names.values:
            row_index = user_names[user_names == name].index[0]
            shift_value = str(df.iloc[row_index, shift_col_index]).strip()

            if not shift_value or shift_value.lower() == 'nan':
                print(f"[WARN] No shift value found for {name} on {today}")
                return None

            try:
                user_obj = User.objects.get(assignee_name__iexact=name)
                if user_obj.shift != shift_value:
                    user_obj.shift = shift_value
                    user_obj.save(update_fields=['shift'])
                    print(f"[INFO] Updated shift for {name} to '{shift_value}' in User model.")
                else:
                    print(f"[INFO] Shift for {name} already up to date.")
            except User.DoesNotExist:
                print(f"[WARN] User with assignee_name '{name}' not found in database.")

            return shift_value

        print(f"[WARN] No matching user found in Excel for name: {name}")
        return None

    except Exception as e:
        print(f"[ERROR] Failed to fetch shift for {name}: {e}")
        return None




from django.utils.timezone import localtime
from Freewheel_Portal.models import (
    ShiftEndTicketDetails, PreviousShiftEndTicketDetails,
    SLABreachedTicket, PreviousSLABreachedTicket,
    ShiftEndTable, PreviousShiftEndTable
)

def truncate_shift_end():
    try:
        print("🟡 Running shift data transfer at:", localtime())

        PreviousShiftEndTicketDetails.objects.all().delete()

        for item in ShiftEndTicketDetails.objects.all():
            PreviousShiftEndTicketDetails.objects.create(
                status=item.status,
                open=item.open,
                pending=item.pending,
                solved=item.solved,
                hold=item.hold,
                total=item.total
            )
        ShiftEndTicketDetails.objects.all().delete()


        PreviousSLABreachedTicket.objects.all().delete()

        for item in SLABreachedTicket.objects.all():
            PreviousSLABreachedTicket.objects.create(
                ticket_id=item.ticket_id,
                subject=item.subject,
                duration=item.duration,
                duration_of_the_breach=item.duration_of_the_breach,
                reason_for_the_breach=item.reason_for_the_breach,
            )
        SLABreachedTicket.objects.all().delete()

        PreviousShiftEndTable.objects.all().delete()


        for item in ShiftEndTable.objects.all():
            PreviousShiftEndTable.objects.create(
                ticket_id=item.ticket_id,
                start_date=item.start_date,
                ticket_subject=item.ticket_subject,
                priority=item.priority,
                ticket_status=item.ticket_status,
                customer_organisation=item.customer_organisation,
                asignee_name=item.asignee_name,
                product=item.product,
                ticket_type=item.ticket_type,
                JIRA_id=item.JIRA_id,
                sla=item.sla,
                last_comment_time=item.last_comment_time,
                next_comment=item.next_comment,
                time_left=item.time_left,
                comment=item.comment
            )
        ShiftEndTable.objects.all().delete()

        print("✅ Shift data moved successfully.\n")
        return True
    except Exception as e:
        print("❌ Error during shift data move:", e)
        return False

