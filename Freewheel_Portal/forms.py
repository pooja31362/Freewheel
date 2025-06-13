from django import forms
from .models import User, Access
import secrets
import string
 
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'emp_id', 'assignee_name', 'email', 'department',
            'BussinessUnit', 'job_title', 'repor_manager',
            'user_type', 'contact_number', 'slack_id', 'status',
            'shift', 'access'
        ]
        widgets = {
            'access': forms.CheckboxSelectMultiple
        }
 
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if email:
            user_name = email.split('@')[0]
            if User.objects.filter(user_name=user_name).exists():
                raise forms.ValidationError("A user with this username already exists.")
        return cleaned_data
 
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_name = self.cleaned_data['email'].split('@')[0]
        characters = string.ascii_letters + string.digits
        user.password = ''.join(secrets.choice(characters) for _ in range(10))
 
        if commit:
            user.save()
            self.save_m2m()  # Save many-to-many relations
 
        return user
 