from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


 
urlpatterns = [
    path('home/', views.home, name='home'),
    path('upload/', views.upload_excel, name='upload_excel'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('create-user/', views.create_user, name='create_user'),
    path('', views.login_view, name='login'),
    path('do-login/', views.do_login, name='do_login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('update-status/', views.update_status, name='status_update'),
    path('submit-comment/', views.submit_comment, name='submit_comment'),
    path('shift-end-summary/', views.shift_end_summary, name='shift_end_summary'),
    path('assign-ticket/', views.assign_ticket, name='assign_ticket'),
    path('new-tickets/', views.new_tickets_view, name='new_tickets'),
    path('test/', views.test, name='test'),
    path('filter-shift/', views.filter_by_shift, name='filter_by_shift'),
    path('upload-shift-excel/', views.upload_shift_excel, name='upload_shift_excel'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)