from django.http import HttpResponse
from django.urls import path
from .views import custom_login, dashboard
from clients.view.office_management_views import office_management, create_user, delete_user, get_user, update_user
from clients.view.client_management_views import client_management, board_types, delete_board_typePara, brands, get_brands, get_clients, client_detail, board, get_board, delete_board, get_boards, apply_payment_discount
from clients.view.dashboard_views import fiscal_year_management, add_fiscal_year, set_fiscal_year_active
from clients.view.add_cleint_views import client_list, add_edit_client, delete_client, upload_client_excel, download_client_template
from clients.view.payment_views import payment_management, client_detail as payment_client_detail, get_clients as payment_get_clients, get_transactions, get_transaction, apply_payment, delete_transaction, generate_bill, download_bill
from clients.view.reports_views import reports_management, get_fiscal_years, generate_statement, get_user_details 
from clients.view.settings_views import settings, get_vat_rates, save_vat_rate, get_company_settings, save_company_settings, get_email_credentials, save_email_credentials
from clients.view.excel_upload import excel_upload, download_excel_template, upload_excel
urlpatterns = [
    path('.well-known/appspecific/com.chrome.devtools.json', lambda request: HttpResponse(status=204)),
    path('login/', custom_login, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    
    path('office-management/', office_management, name='office_management'),
    path('create-user/', create_user, name='create_user'),
    path('delete-user/', delete_user, name='delete_user'),
    path('get-user/', get_user, name='get_user'),
    path('update-user/', update_user, name='update_user'),
    path('add-client/', client_list, name='client_list'),
    path('client/add-edit/', add_edit_client, name='add_edit_client'),
    path('client/delete/<int:client_id>/', delete_client, name='delete_client'),
    path('upload_excel/', upload_client_excel, name='upload_client_excel'),
    path('download_template/', download_client_template, name='download_client_template'),

    
    path('client-management/', client_management, name='client_management'),
    path('client-management/board-types/', board_types, name='board_types'),
    path('client-management/board-types/delete/<int:board_type_id>/', delete_board_typePara, name='delete_board_type'),
    path('client-management/brands/', brands, name='brands'),
    path('client-management/brands/<int:client_id>/', get_brands, name='get_brands'),
    path('client-management/clients/', get_clients, name='get_clients'),
    path('client-management/client/<int:client_id>/', client_detail, name='client_detail'),
    path('client-management/board/', board, name='board'),
    path('client-management/board/<int:board_id>/', get_board, name='get_board'),
    path('client-management/board/delete/<int:board_id>/', delete_board, name='delete_board'),
    path('client-management/boards/<int:client_id>/', get_boards, name='get_boards'),
    path('client-management/board/apply-payment-discount/', apply_payment_discount, name='apply_payment_discount'),
    
    
    path('fiscal-years/', fiscal_year_management, name='fiscal_year_management'),
    path('fiscal-years/add/',add_fiscal_year, name='add_fiscal_year'),
    path('fiscal-years/set-active/<int:fiscal_year_id>/',set_fiscal_year_active, name='set_fiscal_year_active'),

    path('payment-management/', payment_management, name='payment_management'),
    path('payment-management/client/<int:client_id>/', payment_client_detail, name='payment_client_detail'),
    path('payment-management/clients/', payment_get_clients, name='payment_get_clients'),
    path('payment-management/transactions/<int:client_id>/', get_transactions, name='get_transactions'),
    path('payment-management/transaction/<int:transaction_id>/', get_transaction, name='get_transaction'),
    path('payment-management/apply-payment/', apply_payment, name='apply_payment'),
    path('payment-management/transaction/delete/<int:transaction_id>/', delete_transaction, name='delete_transaction'),
    path('payment-management/generate-bill/<int:client_id>/', generate_bill, name='generate_bill'),
    path('payment-management/download-bill/<int:client_id>/', download_bill, name='download_bill'),

   path('reports-management/', reports_management, name='reports_management'),
   path('reports-management/fiscal-years/', get_fiscal_years, name='get_fiscal_years'),
   path('reports-management/statement/', generate_statement, name='generate_statement'),
   path('client-management/clients/', get_clients, name='get_clients'),

    path('reports-management/', reports_management, name='reports_management'),
    path('reports-management/fiscal-years/', get_fiscal_years, name='get_fiscal_years'),
    path('reports-management/statement/', generate_statement, name='generate_statement'),
    path('reports-management/user-details/', get_user_details, name='get_user_details'),
    path('client-management/clients/', get_clients, name='get_clients'),

    path('settings/', settings, name='settings'),
    path('settings/vat-rates/', get_vat_rates, name='get_vat_rates'),
    path('settings/save-vat-rate/', save_vat_rate, name='save_vat_rate'),
    path('settings/company/', get_company_settings, name='get_company_settings'),
    path('settings/save-company/', save_company_settings, name='save_company_settings'),
    path('settings/email-credentials/', get_email_credentials, name='get_email_credentials'),
    path('settings/save-email-credentials/', save_email_credentials, name='save_email_credentials'),

    
    path('client-management/excel-upload/', excel_upload, name='excel_upload'),
    path('client-management/download-excel-template/', download_excel_template, name='download_excel_template'),
    path('client-management/upload-excel/', upload_excel, name='upload_excel'),
    path('client-management/clients/', get_clients, name='get_clients'),
]