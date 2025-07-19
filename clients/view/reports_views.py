from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from decimal import Decimal
from datetime import datetime
from dateutil.relativedelta import relativedelta
from clients.models import Client, Company, FiscalYear, Board, Transaction
from django.core.exceptions import ValidationError
import json
import os
from django.conf import settings

@login_required
def reports_management(request):
    return render(request, 'reports_management.html')

@csrf_exempt
def get_fiscal_years(request):
    if request.method == 'GET':
        try:
            fiscal_years = FiscalYear.objects.all().values('id', 'name', 'is_active', 'created_at')
            return JsonResponse({'success': True, 'fiscal_years': list(fiscal_years)}, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def get_user_details(request):
    if request.method == 'GET':
        try:
            user = request.user
            if not user.is_authenticated:
                return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
            user_data = {
                'is_superuser': user.is_superuser,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'email': user.email or request.session.get('login_email', 'Unknown')
            }
            return JsonResponse({'success': True, 'user': user_data}, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def generate_statement(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fiscal_year_id = data.get('fiscal_year_id')
            include_previous_dues = data.get('include_previous_dues', False)
            client_id = data.get('client_id')
            month = data.get('month')

            if not fiscal_year_id:
                return JsonResponse({'success': False, 'message': 'Fiscal year is required'}, status=400)
            if not client_id:
                return JsonResponse({'success': False, 'message': 'Client is required'}, status=400)

            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            client = Client.objects.get(id=client_id)

            query = Q(client=client)
            if not include_previous_dues:
                query &= Q(fiscal_year=fiscal_year)

            if month:
                year = int(fiscal_year.created_at.strftime('%Y'))
                start_date = f"{year}-{month}-01"
                end_date = (datetime(year, int(month), 1) + relativedelta(months=1) - relativedelta(days=1)).strftime('%Y-%m-%d')
                query &= Q(created_at__range=[start_date, end_date])

            boards = Board.objects.filter(query).select_related('brand', 'board_type').order_by('created_at')
            transactions = Transaction.objects.filter(client=client).order_by('created_at')
            if month:
                transactions = transactions.filter(created_at__range=[start_date, end_date])

            board_data = []
            total_charges = 0
            total_payments = 0
            total_discounts = 0

            for board in boards:
                area = board.length * board.breadth
                amount = float(area * board.quantity * board.rate)
                total_charges += amount
                board_data.append({
                    'id': board.id,
                    'client_name': board.client.name,
                    'shop_name': board.shop_name,
                    'brand_name': board.brand.name,
                    'board_type_name': board.board_type.name,
                    'address': board.address,
                    'length': str(board.length),
                    'breadth': str(board.breadth),
                    'quantity': board.quantity,
                    'area': str(area),
                    'rate': str(board.rate),
                    'amount': str(amount),
                    'discount': str(board.discount),
                    'paid_amount': str(board.paid_amount),
                    'remaining_amount': str(amount - float(board.discount) - float(board.paid_amount)),
                    'fiscal_year': board.fiscal_year.name
                })

            total_payments = float(sum(t.amount for t in transactions if t.transaction_type == 'PAYMENT'))
            total_discounts = float(sum(t.amount for t in transactions if t.transaction_type == 'DISCOUNT'))
            vat_amount = total_charges * 0.13
            grand_total = total_charges + vat_amount - total_payments - total_discounts
            balance = grand_total

            summary = {
                'total_boards': len(boards),
                'total_charges': total_charges,
                'total_payments': total_payments,
                'total_discounts': total_discounts,
                'vat_amount': vat_amount,
                'grand_total': grand_total,
                'balance': balance
            }

            # Fetch company details from the database
            company = Company.objects.first()
            company_data = {
                'name': company.name if company else 'SignHub Pvt Ltd',
                'address': company.address if company else 'Gausala, Kathmandu, Nepal',
                'email': company.email if company else 'info@signhub.com',
                'phone': company.phone if company else '+977-1-1234567',
                'vat_id': company.vat_id if company else '123456',
                'logo_url': company.logo.url if company and company.logo else ''
            }

            return JsonResponse({
                'success': True,
                'client': {
                    'name': client.name,
                    'email': client.email,
                    'address': client.address,
                    'vat_id': client.vat_id
                },
                'boards': board_data,
                'summary': summary,
                'company': company_data
            })
        except FiscalYear.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Fiscal year not found'}, status=404)
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fiscal_year_id = data.get('fiscal_year_id')
            include_previous_dues = data.get('include_previous_dues', False)
            client_id = data.get('client_id')
            month = data.get('month')

            if not fiscal_year_id:
                return JsonResponse({'success': False, 'message': 'Fiscal year is required'}, status=400)
            if not client_id:
                return JsonResponse({'success': False, 'message': 'Client is required'}, status=400)

            fiscal_year = FiscalYear.objects.get(id=fiscal_year_id)
            client = Client.objects.get(id=client_id)

            query = Q(client=client)
            if not include_previous_dues:
                query &= Q(fiscal_year=fiscal_year)

            if month:
                year = int(fiscal_year.created_at.strftime('%Y'))
                start_date = f"{year}-{month}-01"
                end_date = (datetime(year, int(month), 1) + relativedelta(months=1) - relativedelta(days=1)).strftime('%Y-%m-%d')
                query &= Q(created_at__range=[start_date, end_date])

            boards = Board.objects.filter(query).select_related('brand', 'board_type').order_by('created_at')
            transactions = Transaction.objects.filter(client=client).order_by('created_at')
            if month:
                transactions = transactions.filter(created_at__range=[start_date, end_date])

            board_data = []
            total_charges = 0
            total_payments = 0
            total_discounts = 0

            for board in boards:
                area = board.length * board.breadth
                amount = float(area * board.quantity * board.rate)
                total_charges += amount
                board_data.append({
                    'id': board.id,
                    'client_name': board.client.name,
                    'shop_name': board.shop_name,
                    'brand_name': board.brand.name,
                    'board_type_name': board.board_type.name,
                    'address': board.address,
                    'length': str(board.length),
                    'breadth': str(board.breadth),
                    'quantity': board.quantity,
                    'area': str(area),
                    'rate': str(board.rate),
                    'amount': str(amount),
                    'discount': str(board.discount),
                    'paid_amount': str(board.paid_amount),
                    'remaining_amount': str(amount - float(board.discount) - float(board.paid_amount)),
                    'fiscal_year': board.fiscal_year.name
                })

            total_payments = float(sum(t.amount for t in transactions if t.transaction_type == 'PAYMENT'))
            total_discounts = float(sum(t.amount for t in transactions if t.transaction_type == 'DISCOUNT'))
            vat_amount = total_charges * 0.13
            grand_total = total_charges + vat_amount - total_payments - total_discounts
            balance = grand_total

            # Define the summary dictionary
            summary = {
                'total_boards': len(boards),
                'total_charges': total_charges,
                'total_payments': total_payments,
                'total_discounts': total_discounts,
                'vat_amount': vat_amount,
                'grand_total': grand_total,
                'balance': balance
            }

            # Add company details (same as get_company_settings)
            company = {
                'name': 'SignHub Pvt Ltd',
                'address': 'Gausala, Kathmandu, Nepal',
                'email': 'info@signhub.com',
                'phone': '+977-1-1234567',
                'vat_id': '123456',
                'logo_url': '/media/company/logo/1_20250719152004.png'  # Ensure this matches the saved logo path
            }

            return JsonResponse({
                'success': True,
                'client': {
                    'name': client.name,
                    'email': client.email,
                    'address': client.address,
                    'vat_id': client.vat_id
                },
                'boards': board_data,
                'summary': summary,
                'company': company
            })
        except FiscalYear.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Fiscal year not found'}, status=404)
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)