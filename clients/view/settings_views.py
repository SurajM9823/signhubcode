from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from clients.models import FiscalYear, VATRate, Company, EmailCredential, UserProfile
import json

@login_required
def settings(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    return render(request, 'settings.html')

@csrf_exempt
@login_required
def get_vat_rates(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    try:
        vat_rates = VATRate.objects.select_related('fiscal_year').values(
            'id', 'rate', 'is_active', 'fiscal_year__name'
        ).order_by('-fiscal_year__created_at')
        return JsonResponse({'success': True, 'vat_rates': list(vat_rates)}, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
@login_required
def save_vat_rate(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fiscal_year_id = data.get('fiscal_year_id')
            rate = data.get('rate')
            is_active = data.get('is_active', False)
            if not fiscal_year_id or not rate:
                return JsonResponse({'success': False, 'message': 'Fiscal year and VAT rate are required.'}, status=400)
            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            VATRate.objects.create(
                fiscal_year=fiscal_year,
                rate=rate,
                is_active=is_active
            )
            return JsonResponse({'success': True})
        except FiscalYear.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Fiscal year not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

@csrf_exempt
@login_required
def get_company_settings(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    try:
        company = Company.objects.first()
        if company:
            company_data = {
                'name': company.name,
                'email': company.email,
                'phone': company.phone,
                'vat_id': company.vat_id,
                'address': company.address,
                'logo_url': company.logo.url if company.logo else ''
            }
            return JsonResponse({'success': True, 'company': company_data}, safe=False)
        return JsonResponse({'success': True, 'company': None}, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
@login_required
def save_company_settings(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    if request.method == 'POST':
        try:
            company = Company.objects.first()
            if company:
                company.name = request.POST.get('name')
                company.email = request.POST.get('email')
                company.phone = request.POST.get('phone', '')
                company.vat_id = request.POST.get('vat_id', '')
                company.address = request.POST.get('address', '')
                if 'logo' in request.FILES:
                    company.logo = request.FILES['logo']
                company.save()
                # Update superuser's UserProfile with the company
                UserProfile.objects.update_or_create(
                    user=request.user,
                    defaults={'company': company}
                )
            else:
                company = Company.objects.create(
                    name=request.POST.get('name'),
                    email=request.POST.get('email'),
                    phone=request.POST.get('phone', ''),
                    vat_id=request.POST.get('vat_id', ''),
                    address=request.POST.get('address', ''),
                    logo=request.FILES.get('logo')
                )
                UserProfile.objects.update_or_create(
                    user=request.user,
                    defaults={'company': company}
                )
            return JsonResponse({'success': True})
        except ValidationError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

@csrf_exempt
@login_required
def get_email_credentials(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    try:
        company = Company.objects.first()
        if company and company.email_credential:
            credentials = {
                'smtp_host': company.email_credential.smtp_host,
                'smtp_port': company.email_credential.smtp_port,
                'username': company.email_credential.username,
                'from_email': company.email_credential.from_email,
                'use_tls': company.email_credential.use_tls
            }
            return JsonResponse({'success': True, 'credentials': credentials}, safe=False)
        return JsonResponse({'success': True, 'credentials': None}, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
@login_required
def save_email_credentials(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            smtp_host = data.get('smtp_host')
            smtp_port = data.get('smtp_port')
            username = data.get('username')
            password = data.get('password')
            from_email = data.get('from_email')
            use_tls = data.get('use_tls', True)
            if not smtp_host or not smtp_port or not username or not from_email:
                return JsonResponse({'success': False, 'message': 'All required fields must be provided.'}, status=400)
            company = Company.objects.first()
            if not company:
                return JsonResponse({'success': False, 'message': 'Company must be set up first.'}, status=400)
            EmailCredential.objects.update_or_create(
                company=company,
                defaults={
                    'smtp_host': smtp_host,
                    'smtp_port': smtp_port,
                    'username': username,
                    'password': password if password else company.email_credential.password,
                    'from_email': from_email,
                    'use_tls': use_tls
                }
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)