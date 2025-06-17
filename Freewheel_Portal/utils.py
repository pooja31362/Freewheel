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