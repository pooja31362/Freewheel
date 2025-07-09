from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import LoginTemplateView, LogoutAPIView, HomeAPIView, ResetTicketAssigneeAPIView, DoLoginAPIView, UpdateStatusAPIView, UploadExcelView,CreateUserView, SubmitCommentView, CreateEmployeeView
from .views import AssignTicketView,ForgotPasswordAPIView,UserStatusAPIView, ShiftEndSummaryView, NewTicketsView, FilterByShiftView, UploadShiftExcelView,UploadExcelReportView, UpdateReportRowView,SaveBulkReportUpdatesView,CreateEmpView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)




urlpatterns = [
    path('api/login-template/', LoginTemplateView.as_view(), name='login-template'),
    path('api/logout/', LogoutAPIView.as_view(), name='logout-api'),
    path('api/home/', HomeAPIView.as_view(), name='home'),
    path('reset-ticket/', ResetTicketAssigneeAPIView.as_view(), name='reset_ticket_assignee'),
    path('api/login/', DoLoginAPIView.as_view(), name='api_login'),
    path('api/update-status/', UpdateStatusAPIView.as_view(), name='update_status_api'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password_api'),
    path('api/user-status/<int:pk>/', UserStatusAPIView.as_view(), name='user-status'),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # login
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # refresh token
    path("sync-tickets/", views.get_zendesk_tickets, name="sync_tickets"),

    # path('login/', LoginView.as_view(), name='login'),
    # path('do-login/', DoLoginView.as_view(), name='do_login'),
    # path('update-status/', UpdateStatusView.as_view(), name='status_update'),
    path('upload/', UploadExcelView.as_view(), name='upload_excel'),
    path('create-user/', CreateUserView.as_view(), name='create_user'),
    path('submit-comment/', SubmitCommentView.as_view(), name='submit_comment'),
    path('assign-ticket/', AssignTicketView.as_view(), name='assign_ticket'),
    path('shift-end-summary/', ShiftEndSummaryView.as_view(), name='shift_end_summary'),
    path('new-tickets/', NewTicketsView.as_view(), name='new_tickets'),
    path('filter-shift/', FilterByShiftView.as_view(), name='filter_by_shift'),
    path('upload-shift-excel/', UploadShiftExcelView.as_view(), name='upload_shift_excel'),
    path('upload_bihourly/', UploadExcelReportView.as_view(), name='upload_excel_report'),
    path('update/<int:pk>/', UpdateReportRowView.as_view(), name='update_report_row'),
    path('save-updates/', SaveBulkReportUpdatesView.as_view(), name='save_bulk_report_updates'),
    path('create-emp/', CreateEmpView.as_view(), name='create_emp'),
    path('create-employee/', CreateEmployeeView.as_view(), name='create_emp'),


    


    path('tickets/', views.ticket_list, name='ticket_list'),
    
    
    
    # path('forgot-password/', views.forgot_password, name='forgot_password'),
    
    
    
    
    
    path('test/', views.test, name='test'),
    
    
    path('submit-leave/', views.submit_leave, name='submit_leave'),
    path('manual-freeze/', views.manual_freeze_view, name='manual-freeze'),
    
    
    
    
    # path('notice/', views.notice, name='notice'),
    path('notice/submit/', views.notice_sub, name='notice_sub'),  # 👈 this name must match
    
    
    path('health/', views.health_check),          # edited  
    path('view_shift_range/', views.view_shift_day, name='view_shift_range'),
    path('view_shift/', views.view_shift, name='view_shift'),  
    path('upload-profile-image/', views.upload_profile_image, name='upload_profile_image'),
    path('view-notice/', views.notice_view, name='view_notice'),
    path('add-notice/', views.notice_add, name='add_notice'),
    path('notice/add/', views.notice_add, name='notice_add'),
    path('notice/edit/<int:notice_id>/', views.edit_notice, name='edit_notice'),
    path('notice/delete/<int:notice_id>/', views.delete_notice, name='delete_notice'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('working-ticket/', views.working_ticket, name='working_ticket'),
    path('get-user-statuses/', views.get_all_user_statuses, name='get-user-statuses'),
    path('get-ticket-updates/', views.get_ticket_updates, name='get-ticket-updates'),




] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # edited