from django.urls import path
from . import views
 
urlpatterns = [
    path('home/', views.home, name='home'),
    path('upload/', views.upload_excel, name='upload_excel'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('create-user/', views.create_user, name='create_user'),
 
]