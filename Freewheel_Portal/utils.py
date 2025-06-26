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
_cached_shift_timestamp = None
def get_today_shift_for_user(emp_id):
    global _cached_shift_df, _cached_shift_col_index, _cached_shift_timestamp
 
    today = datetime.date.today()
 
    try:
        if not os.path.exists(SHIFT_EXCEL_PATH):
            print(f"[ERROR] Shift Excel file not found at: {SHIFT_EXCEL_PATH}")
            return None
 
        file_timestamp = os.path.getmtime(SHIFT_EXCEL_PATH)
 
        if _cached_shift_df is None or _cached_shift_timestamp != file_timestamp:
            # print(f"[INFO] Reloading Excel file (modified: {file_timestamp})")
            _cached_shift_df = pd.read_excel(SHIFT_EXCEL_PATH, header=None)
            _cached_shift_timestamp = file_timestamp
 
            date_row = _cached_shift_df.iloc[1]
            # print(f"[DEBUG] Raw date row: {list(date_row.values)}")
            dates = pd.to_datetime(date_row, format="%d-%m-%Y",dayfirst=True, errors='coerce').dt.date
 
            try:
                _cached_shift_col_index = dates[dates == today].index[0]
            except IndexError:
                # print(f"[ERROR] Today's date ({today}) not found in Excel.")
                _cached_shift_col_index = None
 
        df = _cached_shift_df
        shift_col_index = _cached_shift_col_index
 
        if shift_col_index is None:
            return None  # avoid accessing invalid column
 
        # Fetch PERNR IDs from Excel
        excel_emp_ids = df.iloc[3:, 1].astype(str).str.strip().str.lower()
        emp_id = emp_id.strip().lower()
        print('-----------------------------------------',emp_id)
 
        if emp_id in excel_emp_ids.values:
            row_index = excel_emp_ids[excel_emp_ids == emp_id].index[0]
            shift_value = str(df.iloc[row_index, shift_col_index]).strip()
 
            if not shift_value or shift_value.lower() == 'nan':
                print(f"[WARN] No shift value found for EMP ID {emp_id} on {today}")
                return None
 
            try:
                user_obj = User.objects.get(emp_id__iexact=emp_id)
                if user_obj.shift != shift_value:
                    user_obj.shift = shift_value
                    user_obj.save(update_fields=['shift'])
                    print(f"[INFO] Updated shift for EMP ID {emp_id} to '{shift_value}' in User model.")
                else:
                    print(f"[INFO] Shift for EMP ID {emp_id} already up to date.")
            except User.DoesNotExist:
                print(f"[WARN] User with employee_id '{emp_id}' not found in database.")
 
            return shift_value
 
        print(f"[WARN] EMP ID {emp_id} not found in Excel.")
        return None
 
    except Exception as e:
        print(f"[ERROR] Failed to fetch shift for EMP ID {emp_id}: {e}")
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



def get_shifts_for_date(date: datetime.date):
    """
    Returns a dictionary {emp_id: shift} for the given date.
    """
    try:
        if not os.path.exists(SHIFT_EXCEL_PATH):
            print(f"[ERROR] Shift Excel file not found at: {SHIFT_EXCEL_PATH}")
            return {}
 
        df = pd.read_excel(SHIFT_EXCEL_PATH, header=None)
        date_row = pd.to_datetime(df.iloc[1], errors='coerce').dt.date  # row with dates
        emp_ids = df.iloc[3:, 1].astype(str).str.strip().str.lower()    # employee IDs (row 4+ col 2)
 
        # Find the column for the given date
        try:
            col_index = date_row[date_row == date].index[0]
        except IndexError:
            print(f"[WARN] Date {date} not found in shift Excel.")
            return {}
 
        shift_map = {}
        for i, emp_id in enumerate(emp_ids, start=3):
            shift = str(df.iloc[i, col_index]).strip()
            if shift and shift.lower() != 'nan':
                shift_map[emp_id] = shift
 
        return shift_map
 
    except Exception as e:
        print(f"[ERROR] Failed to fetch shifts for date {date}: {e}")
        return {}

 
 
from datetime import datetime, timedelta
import pytz
 
def get_utc_half_hour_distribution(shift_data_today, shift_data_prev, shift_data_next, date):
    IST = pytz.timezone('Asia/Kolkata')
    UTC = pytz.utc
 
    shift_times = {
        'S1': ('06:30', '15:30'),
        'G':  ('09:30', '18:30'),
        'S2': ('11:00', '20:00'),
        'S3': ('13:30', '22:30'),
        'S4': ('15:00', '00:00'),
        'S5': ('18:00', '03:00'),
        'S6': ('22:00', '07:00'),
    }
 
    slot_distribution = {}
    utc_day_start = datetime.combine(date, datetime.min.time()).replace(tzinfo=UTC)
 
    # Initialize 48 half-hour slots for the selected UTC day
    for i in range(48):
        slot_time = utc_day_start + timedelta(minutes=30 * i)
        label = slot_time.strftime('%H:%M')
        slot_distribution[label] = 0
 
    def add_shifts_to_distribution(shift_data, shift_day, allowed_shifts=None):
        for name, shift in shift_data.items():
            shift = shift.upper().strip()
            if shift not in shift_times:
                continue
 
            if allowed_shifts and shift not in allowed_shifts:
                continue
 
            start_str, end_str = shift_times[shift]
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
 
            shift_start = IST.localize(datetime.combine(shift_day, start_time))
            # Handle shifts that end next day
            if end_time <= start_time:
                shift_end = IST.localize(datetime.combine(shift_day + timedelta(days=1), end_time))
            else:
                shift_end = IST.localize(datetime.combine(shift_day, end_time))
 
            start_utc = shift_start.astimezone(UTC)
            end_utc = shift_end.astimezone(UTC)
 
            for i in range(48):
                slot_start = utc_day_start + timedelta(minutes=30 * i)
                slot_end = slot_start + timedelta(minutes=30)
                if start_utc < slot_end and end_utc > slot_start:
                    label = slot_start.strftime('%H:%M')
                    slot_distribution[label] += 1
 
    # Add previous day's S5/S6
    add_shifts_to_distribution(shift_data_prev, date - timedelta(days=1), allowed_shifts=['S5', 'S6'])
 
    # Add today's all shifts
    add_shifts_to_distribution(shift_data_today, date)
 
    # Add next day's S6
    add_shifts_to_distribution(shift_data_next, date + timedelta(days=1), allowed_shifts=['S6'])
 
    return slot_distribution
 


def get_shifts_for_date_range(from_date: datetime.date, to_date: datetime.date):
    """
    Returns a dictionary of shifts for each user between from_date and to_date.
    {
        'john': {'2025-06-20': 'S1', '2025-06-21': 'S2'},
        ...
    }
    """
    try:
        if not os.path.exists(SHIFT_EXCEL_PATH):
            print(f"[ERROR] Shift Excel not found at: {SHIFT_EXCEL_PATH}")
            return {}
 
        df = pd.read_excel(SHIFT_EXCEL_PATH, header=None)
        date_row = pd.to_datetime(df.iloc[1], errors='coerce').dt.date  # second row contains dates
        name_column = df.iloc[3:, 0].astype(str).str.strip().str.lower()  # names from row 5 onward
 
        shift_map = {}  # result dictionary
 
        for row_idx, name in enumerate(name_column, start=3):
            name = str(name).strip().lower()
 
            # Stop if we hit garbage footer data
            if (
                not name or
                name == "nan" or
                any(keyword in name for keyword in [
                    "total staffing", "planned leave", "casual leave", "earned leave",
                    "unplanned leave", "sick leave", "compensation off", "pl -", "cl -", "el -", "ul -", "sl -", "co -"
                ]) or
                name.startswith(('s1(', 's2(', 's3(', 's4(', 's6(', 'g(')) or
                name.isdigit()
            ):
                continue
 
            shift_map[name] = {}
            for col_idx, date in enumerate(date_row):
                if pd.isna(date):
                    continue
                if from_date <= date <= to_date:
                    shift = str(df.iloc[row_idx, col_idx]).strip()
                    if shift and shift.lower() != 'nan':
                        shift_map[name][str(date)] = shift
 
        return shift_map
 
    except Exception as e:
        print(f"[ERROR] Failed to fetch shifts for date range: {e}")
        return {}

