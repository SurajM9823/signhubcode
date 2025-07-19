from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from clients.models import Client, FiscalYear
from clients.forms import ClientForm
from django.views.decorators.csrf import csrf_exempt
import json
import pandas as pd
from openpyxl import Workbook
from datetime import datetime

def client_list(request):
    clients = Client.objects.all()
    form = ClientForm()
    return render(request, 'client_list.html', {'clients': clients, 'form': form})

@csrf_exempt
def add_edit_client(request):
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        if client_id:
            client = get_object_or_404(Client, id=client_id)
            form = ClientForm(request.POST, instance=client)
        else:
            form = ClientForm(request.POST)
        
        if form.is_valid():
            client = form.save(commit=False)
            active_fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if active_fiscal_year:
                client.fiscal_year = active_fiscal_year
            else:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found. Please set an active fiscal year.'})
            client.save()
            return JsonResponse({'success': True})
        else:
            errors = form.errors.as_json()
            return JsonResponse({'success': False, 'message': 'Form validation failed', 'errors': json.loads(errors)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
def delete_client(request, client_id):
    if request.method == 'POST':
        try:
            client = get_object_or_404(Client, id=client_id)
            client.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
def upload_client_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            return JsonResponse({'success': False, 'message': 'No file uploaded'})
        
        try:
            df = pd.read_excel(excel_file)
            required_columns = ['Name', 'Email', 'VAT ID', 'Registration Date']
            if not all(col in df.columns for col in required_columns):
                return JsonResponse({'success': False, 'message': 'Missing required columns in Excel file'})
            
            active_fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not active_fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'})
            
            for _, row in df.iterrows():
                try:
                    registration_date = pd.to_datetime(row['Registration Date']).date()
                except:
                    return JsonResponse({'success': False, 'message': f'Invalid date format for {row["Name"]}'})
                
                client = Client(
                    name=row['Name'],
                    email=row['Email'],
                    phone=row.get('Phone', ''),
                    vat_id=row['VAT ID'],
                    registration_date=registration_date,
                    address=row.get('Address', ''),
                    notes=row.get('Notes', ''),
                    fiscal_year=active_fiscal_year
                )
                client.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error processing file: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def download_client_template(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Clients"
    headers = ['Name', 'Email', 'Phone', 'VAT ID', 'Registration Date', 'Address', 'Notes']
    ws.append(headers)
    
    # Sample data
    sample_data = [
        ['John Doe', 'john@example.com', '+1234567890', 'VAT123', '2023-01-01', '123 Main St', 'Sample note'],
        ['Jane Smith', 'jane@example.com', '+0987654321', 'VAT456', '2023-02-01', '456 Oak Ave', 'Another note']
    ]
    for row in sample_data:
        ws.append(row)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=client_template.xlsx'
    wb.save(response)
    return response