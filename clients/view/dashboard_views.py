from django.shortcuts import render, redirect
from django.contrib import messages
from clients.models import FiscalYear
from django.http import JsonResponse

def fiscal_year_management(request):
    fiscal_years = FiscalYear.objects.all().order_by('-created_at')
    return render(request, 'fiscal_year_management.html', {'fiscal_years': fiscal_years})

def add_fiscal_year(request):
    if request.method == 'POST':
        name = request.POST.get('fiscal_year_name', '').strip()
        if not name:
            messages.error(request, 'Fiscal year name is required.')
            return redirect('fiscal_year_management')
        if FiscalYear.objects.filter(name=name).exists():
            messages.error(request, 'A fiscal year with this name already exists.')
            return redirect('fiscal_year_management')
        
        # Create new fiscal year and set it as active
        FiscalYear.objects.create(name=name, is_active=True)
        messages.success(request, f'Fiscal year {name} created and set as active.')
        return redirect('fiscal_year_management')
    
    return redirect('fiscal_year_management')

def set_fiscal_year_active(request, fiscal_year_id):
    try:
        fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
        fiscal_year.is_active = True
        fiscal_year.save()
        messages.success(request, f'Fiscal year {fiscal_year.name} set as active.')
        return JsonResponse({'status': 'success'})
    except FiscalYear.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Fiscal year not found.'}, status=404)