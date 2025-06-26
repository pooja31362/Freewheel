from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


 
urlpatterns = [
    path('logout/', views.logout_view, name='logout'),
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
    path('submit-leave/', views.submit_leave, name='submit_leave'),
    path('manual-freeze/', views.manual_freeze_view, name='manual-freeze'),
    path("reset-ticket-assignee/", views.reset_ticket_assignee, name="reset_ticket_assignee"),
    path('upload_bihourly/', views.upload_excel_report, name='upload_excel_report'),
    path('update/<int:pk>/', views.update_report_row, name='update_report_row'),
    path('save-updates/', views.save_bulk_report_updates, name='save_bulk_report_updates'),
    # path('notice/', views.notice, name='notice'),
    path('notice/submit/', views.notice_sub, name='notice_sub'),  # 👈 this name must match
    path('create-emp/', views.create_emp, name='create_emp'),
    path('create-employee/', views.create_employee, name='create_employee'),
    path('health/', views.health_check),          # edited  
    path('view_shift_range/', views.view_shift_day, name='view_shift_range'),
    path('view_shift/', views.view_shift, name='view_shift'),  
    path('upload-profile-image/', views.upload_profile_image, name='upload_profile_image'),
    path('view-notice/', views.notice_view, name='view_notice'),
    path('add-notice/', views.notice_add, name='add_notice'),
    path('notice/add/', views.notice_add, name='notice_add'),
    path('notice/edit/<int:notice_id>/', views.edit_notice, name='edit_notice'),
    path('notice/delete/<int:notice_id>/', views.delete_notice, name='delete_notice'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # edited