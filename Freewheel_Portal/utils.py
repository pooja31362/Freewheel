import os
import pandas as pd
import datetime
from datetime import date, timedelta, datetime as dt
import pytz

from django.conf import settings
from django.utils.timezone import localtime
from django.db.models import Count, F

from Freewheel_Portal.models import (
    User,
    ShiftEndTable, ShiftEndTicketDetails, SLABreachedTicket,
    PreviousShiftEndTable, PreviousShiftEndTicketDetails, PreviousSLABreachedTicket,
)

# ====================== Shift Excel Helpers ======================

def get_latest_shift_roster_file():
    folder_path = os.path.join(settings.MEDIA_ROOT, 'shift_roster')
    if not os.path.exists(folder_path):
        print(f"[ERROR] shift_roster folder not found at {folder_path}")
        return None

    files = [
        f for f in os.listdir(folder_path)
        if f.startswith('shift_roster_') and f.endswith('.xlsx')
    ]

    def extract_index(filename):
        try:
            return int(filename.split('_')[-1].split('.')[0])
        except:
            return -1

    if not files:
        print(f"[ERROR] No shift roster files found in {folder_path}")
        return None

    latest_file = max(files, key=extract_index)
    return os.path.join(folder_path, latest_file)


# ====================== Cached Shift Reader ======================

_cached_shift_df = None
_cached_shift_col_index = None
_cached_shift_timestamp = None

def get_today_shift_for_user(emp_id):
    global _cached_shift_df, _cached_shift_col_index, _cached_shift_timestamp
    today = date.today()

    try:
        latest_file = get_latest_shift_roster_file()
        if not latest_file or not os.path.exists(latest_file):
            print(f"[ERROR] Latest shift Excel file not found.")
            return None

        file_timestamp = os.path.getmtime(latest_file)

        if _cached_shift_df is None or _cached_shift_timestamp != file_timestamp:
            _cached_shift_df = pd.read_excel(latest_file, header=None)
            _cached_shift_timestamp = file_timestamp
            date_row = _cached_shift_df.iloc[1]
            dates = pd.to_datetime(date_row, format="%d-%m-%Y", dayfirst=True, errors='coerce').dt.date

            try:
                _cached_shift_col_index = dates[dates == today].index[0]
            except IndexError:
                _cached_shift_col_index = None

        if _cached_shift_col_index is None:
            return None

        df = _cached_shift_df
        excel_emp_ids = df.iloc[3:, 1].astype(str).str.strip().str.lower()
        emp_id = emp_id.strip().lower()

        if emp_id in excel_emp_ids.values:
            row_index = excel_emp_ids[excel_emp_ids == emp_id].index[0]
            shift_value = str(df.iloc[row_index, _cached_shift_col_index]).strip()

            if not shift_value or shift_value.lower() == 'nan':
                return None

            try:
                user_obj = User.objects.get(emp_id__iexact=emp_id)
                if user_obj.shift != shift_value:
                    user_obj.shift = shift_value
                    user_obj.save(update_fields=['shift'])
            except User.DoesNotExist:
                print(f"[WARN] User with EMP ID '{emp_id}' not found in DB.")

            return shift_value

        return None

    except Exception as e:
        print(f"[ERROR] Failed to fetch shift for EMP ID {emp_id}: {e}")
        return None


# ====================== Shift Summary ======================

def populate_summary_data():
    ShiftEndTicketDetails.objects.all().delete()
    SLABreachedTicket.objects.all().delete()

    status_counts = ShiftEndTable.objects.values('ticket_status').annotate(count=Count('ticket_status'))

    for entry in status_counts:
        status = entry['ticket_status'] or "Unknown"
        count = entry['count']

        ShiftEndTicketDetails.objects.create(
            status=status,
            total=count,
            open=count if status.lower() == 'open' else 0,
            pending=count if status.lower() == 'pending' else 0,
            solved=count if status.lower() == 'solved' else 0,
            hold=count if status.lower() == 'hold' else 0,
        )

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


def truncate_shift_end():
    try:
        print("🟡 Running shift data transfer at:", localtime())

        # Copy current data to previous
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


# ====================== Shift Distribution ======================

def get_shifts_for_date(target_date: date):
    try:
        latest_file = get_latest_shift_roster_file()
        if not latest_file:
            return {}

        df = pd.read_excel(latest_file, header=None)
        date_row = pd.to_datetime(df.iloc[1], errors='coerce').dt.date
        emp_ids = df.iloc[3:, 1].astype(str).str.strip().str.lower()

        try:
            col_index = date_row[date_row == target_date].index[0]
        except IndexError:
            print(f"[WARN] Date {target_date} not found in shift Excel.")
            return {}

        shift_map = {}
        for i, emp_id in enumerate(emp_ids, start=3):
            shift = str(df.iloc[i, col_index]).strip()
            if shift and shift.lower() != 'nan':
                shift_map[emp_id] = shift

        return shift_map

    except Exception as e:
        print(f"[ERROR] Failed to fetch shifts for date {target_date}: {e}")
        return {}


def get_shifts_for_date_range(from_date: date, to_date: date):
    try:
        latest_file = get_latest_shift_roster_file()
        if not latest_file:
            return {}

        df = pd.read_excel(latest_file, header=None)
        raw_date_row = df.iloc[1]
        parsed_dates = pd.to_datetime(raw_date_row, errors='coerce', dayfirst=True)
        valid_date_indices = [i for i, d in enumerate(parsed_dates) if pd.notna(d)]
        valid_dates = [parsed_dates[i].date() for i in valid_date_indices]

        name_column = df.iloc[3:, 0].astype(str).str.strip()
        shift_map = {}

        for row_idx, name in enumerate(name_column, start=3):
            lower_name = name.lower()
            if (
                not name or name == "nan" or
                any(x in lower_name for x in ["leave", "off", "-", "dinesh", "rama"]) or
                lower_name.startswith(('s1(', 's2(', 's3(', 's4(', 's6(', 'g(')) or
                lower_name in ("s1", "s2", "s3", "s4", "s6", "g")
            ):
                continue

            shift_map[name] = {}
            for idx, day in zip(valid_date_indices, valid_dates):
                if from_date <= day <= to_date:
                    shift = str(df.iloc[row_idx, idx]).strip()
                    if shift and shift.lower() != 'nan':
                        shift_map[name][str(day)] = shift

        return shift_map

    except Exception as e:
        print(f"[ERROR] Failed to fetch shifts for date range: {e}")
        return {}


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
    utc_day_start = dt.combine(date, dt.min.time()).replace(tzinfo=UTC)

    for i in range(48):
        slot_time = utc_day_start + timedelta(minutes=30 * i)
        label = slot_time.strftime('%H:%M')
        slot_distribution[label] = 0

    def add_shifts_to_distribution(shift_data, shift_day, allowed_shifts=None):
        for name, shift in shift_data.items():
            shift = shift.upper().strip()
            if shift not in shift_times or (allowed_shifts and shift not in allowed_shifts):
                continue

            start_str, end_str = shift_times[shift]
            start_time = dt.strptime(start_str, "%H:%M").time()
            end_time = dt.strptime(end_str, "%H:%M").time()

            shift_start = IST.localize(dt.combine(shift_day, start_time))
            shift_end = IST.localize(dt.combine(shift_day + timedelta(days=(end_time <= start_time),), end_time))

            start_utc = shift_start.astimezone(UTC)
            end_utc = shift_end.astimezone(UTC)

            for i in range(48):
                slot_start = utc_day_start + timedelta(minutes=30 * i)
                slot_end = slot_start + timedelta(minutes=30)
                if start_utc < slot_end and end_utc > slot_start:
                    label = slot_start.strftime('%H:%M')
                    slot_distribution[label] += 1

    add_shifts_to_distribution(shift_data_prev, date - timedelta(days=1), allowed_shifts=['S5', 'S6'])
    add_shifts_to_distribution(shift_data_today, date)
    add_shifts_to_distribution(shift_data_next, date + timedelta(days=1), allowed_shifts=['S6'])

    return slot_distribution
