from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
import secrets
import string


class Ticket(models.Model):
    ticket_id = models.BigIntegerField(primary_key=True)
    created_timestamp = models.DateTimeField(null=True, blank=True)
    updated_timestamp = models.DateTimeField(null=True, blank=True)
    due_timestamp = models.DateTimeField(null=True, blank=True)
    solved_timestamp = models.DateTimeField(null=True, blank=True)
    assigned_timestamp = models.DateTimeField(null=True, blank=True)
    assignee_id = models.BigIntegerField(null=True, blank=True)
    assignee_name = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    group = models.CharField(max_length=255, null=True, blank=True)
    form = models.CharField(max_length=255, null=True, blank=True)
    requester_organization = models.CharField(max_length=255, null=True, blank=True)
    comment = models.CharField(max_length=255, null=True, blank=True)
    priority = models.CharField(max_length=20, null=True, blank=True)
    subject = models.TextField(null=True, blank=True)
    requester = models.CharField(max_length=255, null=True, blank=True)
    product_category = models.CharField(max_length=255, null=True, blank=True)
    ticket_type = models.CharField(max_length=50, null=True, blank=True)
    jira_issue_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.ticket_id)


class Access(models.Model):
    access_id = models.AutoField(primary_key=True)
    access_description = models.TextField()

    def __str__(self):
        return self.access_description


class GroupAccess(models.Model):
    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('tc', 'TC'),
        ('staff', 'Staff'),
    ]
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, unique=True)
    availed_access = models.JSONField(default=list)

    def __str__(self):
        return f"{self.get_user_type_display()} Access: {self.availed_access}"


from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, emp_id, password=None, **extra_fields):
        if not emp_id:
            raise ValueError('The emp_id must be set')
        if not password:
            raise ValueError('Password must be set')  # Require password explicitly
        user = self.model(emp_id=emp_id, **extra_fields)
        user.set_password(password)  # Always hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, emp_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(emp_id, password, **extra_fields)



class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('tc', 'TC'),
        ('staff', 'Staff'),
    ]
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Away', 'Away'),
        ('In-Meeting', 'In-Meeting'),
        ('Offline', 'Offline'),
        ('Out Of Office', 'Out Of Office'),
    ]

    emp_id = models.BigIntegerField(primary_key=True, unique=True)
    assignee_name = models.CharField(max_length=100)
    user_name = models.CharField(max_length=100, unique=True, blank=True)
    password = models.CharField(max_length=128, blank=True)
    assignee_id = models.BigIntegerField(blank=True, null=True)
    department = models.CharField(max_length=100)
    work_region = models.CharField(max_length=100, blank=True, null=True)
    BussinessUnit = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)
    repor_manager = models.CharField(max_length=100)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    slack_id = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Offline')
    shift = models.CharField(max_length=20)
    profile_image = models.ImageField(upload_to='profile_images/', default='profile_images/image.png', blank=True, null=True)
    access = models.JSONField(default=list)
    leave_until = models.DateTimeField(null=True, blank=True)
    last_shift_update = models.DateField(null=True, blank=True)
    last_login = models.DateTimeField(default=now)
    working_ticket = models.BigIntegerField(null=True, blank=True)

    USERNAME_FIELD = 'emp_id'
    REQUIRED_FIELDS = []

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.user_name and self.email:
            self.user_name = self.email.split('@')[0]

        # Ensure user_name is unique
        base_username = self.user_name
        counter = 1
        while User.objects.filter(user_name=self.user_name).exclude(emp_id=self.emp_id).exists():
            self.user_name = f"{base_username}{counter}"
            counter += 1

        # Hash the password only if it's not already hashed
        if self.password and not self.password.startswith('pbkdf2_'):
            self.set_password(self.password)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.assignee_name} ({self.emp_id})"

    @property
    def id(self):
        return self.emp_id

class ShiftEndTicketDetails(models.Model):
    status = models.CharField(max_length=50)
    open = models.PositiveIntegerField(default=0)
    pending = models.PositiveIntegerField(default=0)
    solved = models.PositiveIntegerField(default=0)
    hold = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Details - Status: {self.status}, Total: {self.total}"


class PreviousShiftEndTicketDetails(models.Model):
    status = models.CharField(max_length=50)
    open = models.PositiveIntegerField(default=0)
    pending = models.PositiveIntegerField(default=0)
    solved = models.PositiveIntegerField(default=0)
    hold = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Details - Status: {self.status}, Total: {self.total}"


class SLABreachedTicket(models.Model):
    ticket_id = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    duration = models.CharField(max_length=50)
    duration_of_the_breach = models.CharField(max_length=50)
    reason_for_the_breach = models.TextField()

    def __str__(self):
        return f"SLA Breach - Ticket {self.ticket_id.ticket_id}"


class PreviousSLABreachedTicket(models.Model):
    ticket_id = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    duration = models.CharField(max_length=50)
    duration_of_the_breach = models.CharField(max_length=50)
    reason_for_the_breach = models.TextField()

    def __str__(self):
        return f"SLA Breach - Ticket {self.ticket_id.ticket_id}"


class ShiftEndTable(models.Model):
    ticket_id = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    ticket_subject = models.CharField(max_length=200, null=True, blank=True)
    priority = models.CharField(max_length=20, null=True, blank=True)
    ticket_status = models.CharField(max_length=50, null=True, blank=True)
    customer_organisation = models.CharField(max_length=100, null=True, blank=True)
    asignee_name = models.CharField(max_length=100, null=True, blank=True)
    product = models.CharField(max_length=100, null=True, blank=True)
    ticket_type = models.CharField(max_length=100, null=True, blank=True)
    JIRA_id = models.CharField(max_length=50, null=True, blank=True)
    sla = models.CharField(max_length=50, null=True, blank=True)
    last_comment_time = models.DateTimeField()
    next_comment = models.DateTimeField()
    time_left = models.CharField(max_length=50)
    comment = models.TextField()

    def __str__(self):
        return f"ShiftEnd for Ticket {self.ticket_id.ticket_id}"


class PreviousShiftEndTable(models.Model):
    ticket_id = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    ticket_subject = models.CharField(max_length=200, null=True, blank=True)
    priority = models.CharField(max_length=20, null=True, blank=True)
    ticket_status = models.CharField(max_length=50, null=True, blank=True)
    customer_organisation = models.CharField(max_length=100, null=True, blank=True)
    asignee_name = models.CharField(max_length=100, null=True, blank=True)
    product = models.CharField(max_length=100, null=True, blank=True)
    ticket_type = models.CharField(max_length=100, null=True, blank=True)
    JIRA_id = models.CharField(max_length=50, null=True, blank=True)
    sla = models.CharField(max_length=50, null=True, blank=True)
    last_comment_time = models.DateTimeField()
    next_comment = models.DateTimeField()
    time_left = models.CharField(max_length=50)
    comment = models.TextField()

    def __str__(self):
        return f"ShiftEnd for Ticket {self.ticket_id.ticket_id}"


class Notice(models.Model):
    message = models.TextField(null=True, blank=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    posted_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    priority = models.CharField(
        max_length=10, null=True, blank=True,
        choices=[('Urgent', 'Urgent'), ('Important', 'Important'), ('Normal', 'Normal')]
    )
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Notice {self.id} by {self.posted_by}"


class Schedule(models.Model):
    date = models.DateField(unique=True)
    shift1_status = models.JSONField(default=dict, blank=True)
    shift3_status = models.JSONField(default=dict, blank=True)
    shift6_status = models.JSONField(default=dict, blank=True)

    shift1_end_email = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='shift1_end_user')
    shift3_end_email = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='shift3_end_user')
    shift6_end_email = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='shift6_end_user')

    def __str__(self):
        return f"Schedule for {self.date}"


PRODUCT_CHOICES = [
    ('SH', 'SH'),
    ('FW DSP', 'FW DSP'),
    ('FW SSP', 'FW SSP'),
    ('Strata', 'Strata'),
]

class TicketReport(models.Model):
    timestamp = models.DateTimeField(default=now)
    product = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    open_count = models.IntegerField(default=0)
    new_count = models.IntegerField(default=0)
    urgent_count = models.IntegerField(default=0)
    high_count = models.IntegerField(default=0)
    normal_count = models.IntegerField(default=0)
    low_count = models.IntegerField(default=0)
    being_worked = models.IntegerField(default=0)
    unattended = models.IntegerField(default=0)
    engineers = models.IntegerField(default=0)
    ho_followup = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        self.unattended = max((self.new_count + self.open_count) - self.being_worked, 0)
        super().save(*args, **kwargs)


class SyncTracker(models.Model):
    name = models.CharField(max_length=255, unique=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    is_running = models.BooleanField(default=False)

    def __str__(self):
        return self.name
