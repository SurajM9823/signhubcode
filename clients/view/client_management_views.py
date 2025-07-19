from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from clients.models import Board, Client, FiscalYear, BoardType, Brand, Transaction
from django.core.exceptions import ValidationError
import json
from django.core.paginator import Paginator
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime
from django.db import transaction

def client_management(request):
    return render(request, 'client_management.html')

@csrf_exempt
def board_types(request):
    if request.method == 'GET':
        fiscal_year = FiscalYear.objects.filter(is_active=True).first()
        if not fiscal_year:
            return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
        board_types = BoardType.objects.filter(fiscal_year=fiscal_year).values('id', 'name', 'rate')
        return JsonResponse(list(board_types), safe=False)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            board_type_id = data.get('id')
            name = data.get('name')
            rate = data.get('rate')
            
            if not name or not rate:
                return JsonResponse({'success': False, 'message': 'Name and rate are required'}, status=400)
            
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            
            if board_type_id:
                board_type = BoardType.objects.get(id=board_type_id, fiscal_year=fiscal_year)
                board_type.name = name
                board_type.rate = rate
            else:
                board_type = BoardType(name=name, rate=rate, fiscal_year=fiscal_year)
            
            board_type.full_clean()
            board_type.save()
            return JsonResponse({'success': True})
        except BoardType.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Board type not found'}, status=404)
        except ValidationError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def delete_board_typePara (request, board_type_id):
    if request.method == 'POST':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            board_type = BoardType.objects.get(id=board_type_id, fiscal_year=fiscal_year)
            board_type.delete()
            return JsonResponse({'success': True})
        except BoardType.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Board type not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@csrf_exempt
def brands(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            client_id = data.get('client_id')
            name = data.get('name')
            
            if not client_id or not name:
                return JsonResponse({'success': False, 'message': 'Client and name are required'}, status=400)
            
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            
            client = Client.objects.get(id=client_id)
            brand = Brand(name=name, client=client, fiscal_year=fiscal_year)
            brand.full_clean()
            brand.save()
            return JsonResponse({'success': True})
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client not found'}, status=404)
        except ValidationError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def get_brands(request, client_id):
    if request.method == 'GET':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            brands = Brand.objects.filter(client_id=client_id, fiscal_year=fiscal_year).values('id', 'name')
            return JsonResponse(list(brands), safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def client_detail(request, client_id):
    if request.method == 'GET':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            client = Client.objects.get(id=client_id, fiscal_year=fiscal_year)
            return JsonResponse({
                'success': True,
                'client': {'id': client.id, 'name': client.name}
            })
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def get_clients(request):
    if request.method == 'GET':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            search_term = request.GET.get('search', '')
            clients = Client.objects.filter(
                fiscal_year=fiscal_year,
                name__icontains=search_term
            ).values('id', 'name')[:10]
            return JsonResponse(list(clients), safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def board(request):
    if request.method == 'POST':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)

            client_id = request.POST.get('client_id')
            board_id = request.POST.get('id')
            address = request.POST.get('address')
            shop_name = request.POST.get('shop_name')
            brand_id = request.POST.get('brand_id')
            board_type_id = request.POST.get('board_type_id')
            length = request.POST.get('length')
            breadth = request.POST.get('breadth')
            quantity = request.POST.get('quantity')
            rate = request.POST.get('rate')
            discount = request.POST.get('discount', 0)
            image = request.FILES.get('image')

            if not all([client_id, address, shop_name, brand_id, board_type_id, length, breadth, quantity, rate]):
                return JsonResponse({'success': False, 'message': 'All fields are required'}, status=400)

            client = Client.objects.get(id=client_id, fiscal_year=fiscal_year)
            brand = Brand.objects.get(id=brand_id, client=client, fiscal_year=fiscal_year)
            board_type = BoardType.objects.get(id=board_type_id, fiscal_year=fiscal_year)

            if board_id:
                board = Board.objects.get(id=board_id, client=client, fiscal_year=fiscal_year)
            else:
                board = Board(client=client, fiscal_year=fiscal_year)

            board.address = address
            board.shop_name = shop_name
            board.brand = brand
            board.board_type = board_type
            board.length = Decimal(length)
            board.breadth = Decimal(breadth)
            board.quantity = int(quantity)
            board.rate = Decimal(rate)
            board.discount = Decimal(discount)
            if image:
                board.image = image

            board.full_clean()
            board.save()
            board.update_status()

            # Log success for debugging
            print(f"Board {board.id} saved successfully for client {client_id}")
            return JsonResponse({'success': True, 'board_id': board.id})
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client not found for the active fiscal year'}, status=404)
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Brand not found for the client and fiscal year'}, status=404)
        except BoardType.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Board type not found for the fiscal year'}, status=404)
        except ValidationError as e:
            print(f"Validation error: {str(e)}")  # Log validation errors
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            print(f"Unexpected error in board view: {str(e)}")  # Log unexpected errors
            return JsonResponse({'success': False, 'message': f'Internal server error: {str(e)}'}, status=500)

@csrf_exempt
def get_board(request, board_id):
    if request.method == 'GET':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            board = Board.objects.get(id=board_id, fiscal_year=fiscal_year)
            return JsonResponse({
                'success': True,
                'board': {
                    'id': board.id,
                    'address': board.address,
                    'shop_name': board.shop_name,
                    'brand_id': board.brand.id,
                    'board_type_id': board.board_type.id,
                    'length': str(board.length),
                    'breadth': str(board.breadth),
                    'quantity': board.quantity,
                    'rate': str(board.rate),
                    'discount': str(board.discount)
                }
            })
        except Board.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Board not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def delete_board(request, board_id):
    if request.method == 'POST':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            board = Board.objects.get(id=board_id, fiscal_year=fiscal_year)
            board.delete()
            return JsonResponse({'success': True})
        except Board.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Board not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def get_boards(request, client_id):
    if request.method == 'GET':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)

            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 10))
            boards = Board.objects.filter(client_id=client_id, fiscal_year=fiscal_year).select_related('client', 'brand', 'board_type').order_by('created_at')

            paginator = Paginator(boards, per_page)
            page_obj = paginator.get_page(page)

            boards_data = [{
                'id': board.id,
                'client_name': board.client.name,
                'address': board.address,
                'shop_name': board.shop_name,
                'brand_name': board.brand.name,
                'board_type_name': board.board_type.name,
                'length': str(board.length),
                'breadth': str(board.breadth),
                'area': str(board.area),
                'quantity': board.quantity,
                'rate': str(board.rate),
                'discount': str(board.discount),
                'total_amount': str(board.total_amount),
                'paid_amount': str(board.paid_amount),
                'status': board.status
            } for board in page_obj]

            # Calculate financial summary
            current_year_boards = Board.objects.filter(client_id=client_id, fiscal_year=fiscal_year)
            previous_year_boards = Board.objects.filter(client_id=client_id).exclude(fiscal_year=fiscal_year)

            # Calculate total_amount as (length * breadth * quantity * rate) - discount
            current_year_total = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount) for board in current_year_boards))
            previous_year_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in previous_year_boards))
            current_year_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in current_year_boards))

            financial_summary = {
                'total_boards': current_year_boards.count(),
                'previous_dues': previous_year_remaining if previous_year_remaining > 0 else 0.0,
                'current_year_total': current_year_total if current_year_total > 0 else 0.0,
                'total_dues': current_year_total if current_year_total > 0 else 0.0,
                'total_discount': float(current_year_boards.aggregate(Sum('discount'))['discount__sum'] or 0),
                'total_paid': float(current_year_boards.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0),
                'total_remaining': current_year_remaining if current_year_remaining > 0 else 0.0,
            }

            return JsonResponse({
                'success': True,
                'boards': boards_data,
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count
                },
                'financial_summary': financial_summary
            })
        except Exception as e:
            print(f"Error in get_boards: {str(e)}")  # Log errors
            return JsonResponse({'success': False, 'message': str(e)}, status=500)                        
@csrf_exempt
def apply_payment_discount(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            board_id = data.get('board_id')
            payment_amount = Decimal(data.get('payment_amount', 0))
            discount_amount = Decimal(data.get('discount_amount', 0))

            if payment_amount < 0 or discount_amount < 0:
                return JsonResponse({'success': False, 'message': 'Payment and discount cannot be negative'}, status=400)

            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)

            board = Board.objects.get(id=board_id, fiscal_year=fiscal_year)
            client = board.client

            if discount_amount > 0:
                board.discount += discount_amount
                Transaction.objects.create(
                    client=client,
                    fiscal_year=fiscal_year,
                    board=board,
                    amount=discount_amount,
                    transaction_type='DISCOUNT',
                    description=f'Discount applied to board {board.id}'
                )

            if payment_amount > 0:
                board.paid_amount += payment_amount
                Transaction.objects.create(
                    client=client,
                    fiscal_year=fiscal_year,
                    board=board,
                    amount=payment_amount,
                    transaction_type='PAYMENT',
                    description=f'Payment applied to board {board.id}'
                )

            board.update_status()
            board.save()

            print(f"Payment/Discount applied: Board {board_id}, Payment {payment_amount}, Discount {discount_amount}")
            return JsonResponse({'success': True})
        except Board.DoesNotExist:
            print(f"Board not found: {board_id}")
            return JsonResponse({'success': False, 'message': 'Board not found'}, status=404)
        except Exception as e:
            print(f"Error in apply_payment_discount: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
        