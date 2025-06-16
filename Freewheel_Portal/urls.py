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

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)