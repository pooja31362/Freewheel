from django.db import models
 
class Ticket(models.Model):
    ticket_id = models.CharField(max_length=100, unique=True)
    priority = models.CharField(max_length=100, null=True, blank=True)
    subject = models.TextField(null=True, blank=True)
    requester_organization = models.CharField(max_length=255, null=True, blank=True)
    product_category = models.CharField(max_length=255, null=True, blank=True)
    ticket_type = models.CharField(max_length=100, null=True, blank=True)
    jira_issue_id = models.CharField(max_length=100, null=True, blank=True)
    assignee_name = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
 
    # 🕒 Timestamp fields
    created_timestamp = models.DateTimeField(null=True, blank=True)
    solved_timestamp = models.DateTimeField(null=True, blank=True)
    assigned_timestamp = models.DateTimeField(null=True, blank=True)
    updated_timestamp = models.DateTimeField(null=True, blank=True)
    due_timestamp = models.DateTimeField(null=True, blank=True)
 
    def __str__(self):
        return self.ticket_id
 
 
from django.db import models
 
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
    availed_access = models.JSONField(default=list)  # list of access_id integers
 
    def __str__(self):
        return f"{self.get_user_type_display()} Access: {self.availed_access}"
 
 
class User(models.Model):
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
    ]
 
    emp_id = models.CharField(max_length=20, primary_key=True)
    assignee_name = models.CharField(max_length=100)
    user_name = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)
    department = models.CharField(max_length=100)
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
 
    def __str__(self):
        return f"{self.emp_id} - {self.user_name}"