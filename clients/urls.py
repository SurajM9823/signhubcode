# clients/urls.py
from django.urls import path
from .views import custom_login, dashboard, client_list, dues_list, email_scheduler

urlpatterns = [
    path('login/', custom_login, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('clients/', client_list, name='client_list'),
    path('clients/edit/<int:pk>/', client_list, name='client_list'),  # Reuse client_list for edit
    path('dues/', dues_list, name='dues_list'),
    path('dues/edit/<int:dues_id>/', dues_list, name='dues_list'),
    path('email-scheduler/', email_scheduler, name='email_scheduler'),
    path('', dashboard, name='home'),  # Root URL redirects to dashboard

]