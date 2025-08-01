from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from clients.models import Board, Client, FiscalYear, BoardType, Brand, Transaction, Municipality, BoardTypeRate
from django.core.exceptions import ValidationError
import json
from django.core.paginator import Paginator
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum
from decimal import Decimal
from datetime import datetime
from django.db import transaction
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

def client_management(request):
    return render(request, 'client_management.html')

@csrf_exempt
def board_types(request):
    if request.method == 'GET':
        fiscal_year = FiscalYear.objects.filter(is_active=True).first()
        if not fiscal_year:
            return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
        board_types = BoardType.objects.filter(fiscal_year=fiscal_year).values('id', 'name')
        return JsonResponse(list(board_types), safe=False)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            board_type_id = data.get('id')
            name = data.get('name')
            
            if not name:
                return JsonResponse({'success': False, 'message': 'Name is required'}, status=400)
            
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            
            if board_type_id:
                board_type = BoardType.objects.get(id=board_type_id, fiscal_year=fiscal_year)
                board_type.name = name
            else:
                board_type = BoardType(name=name, fiscal_year=fiscal_year)
            
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
def delete_board_type(request, board_type_id):
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
def municipalities(request):
    if request.method == 'GET':
        try:
            search_term = request.GET.get('search', '')
            municipalities = Municipality.objects.filter(name__icontains=search_term).values('id', 'name')[:10]
            return JsonResponse(list(municipalities), safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            municipality_id = data.get('id')
            name = data.get('name')
            
            if not name:
                return JsonResponse({'success': False, 'message': 'Municipality name is required'}, status=400)
            
            if municipality_id:
                municipality = Municipality.objects.get(id=municipality_id)
                municipality.name = name
            else:
                municipality = Municipality(name=name)
            
            municipality.full_clean()
            municipality.save()
            return JsonResponse({'success': True})
        except Municipality.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Municipality not found'}, status=404)
        except ValidationError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def delete_municipality(request, municipality_id):
    if request.method == 'POST':
        try:
            municipality = Municipality.objects.get(id=municipality_id)
            municipality.delete()
            return JsonResponse({'success': True})
        except Municipality.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Municipality not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@csrf_exempt
def board_type_rates(request):
    if request.method == 'GET':
        try:
            logger.debug("Fetching active fiscal year")
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                logger.warning("No active fiscal year found")
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            
            logger.debug(f"Querying BoardTypeRate for fiscal year {fiscal_year.id}")
            rates = BoardTypeRate.objects.filter(board_type__fiscal_year=fiscal_year).select_related('board_type', 'municipality').values(
                'board_type_id', 'municipality_id', 'rate',
                board_type_name='board_type__name', municipality_name='municipality__name'
            )
            logger.debug(f"Retrieved {len(rates)} rates")
            return JsonResponse(list(rates), safe=False)
        except FiscalYear.DoesNotExist:
            logger.error("FiscalYear model query failed")
            return JsonResponse({'success': False, 'message': 'Fiscal year query failed'}, status=500)
        except BoardTypeRate.DoesNotExist:
            logger.error("BoardTypeRate model query failed")
            return JsonResponse({'success': False, 'message': 'Board type rate query failed'}, status=500)
        except AttributeError as ae:
            logger.error(f"Attribute error in BoardTypeRate query: {str(ae)}")
            return JsonResponse({'success': False, 'message': f'Invalid model field or relationship: {str(ae)}'}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error in board_type_rates GET: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': f'Internal server error: {str(e)}'}, status=500)
    
    if request.method == 'POST':
        try:
            logger.debug("Processing POST request for board_type_rates")
            data = json.loads(request.body)
            board_type_id = data.get('board_type_id')
            municipality_id = data.get('municipality_id')
            rate = data.get('rate')
            
            if not all([board_type_id, municipality_id, rate]):
                logger.warning("Missing required fields in POST data")
                return JsonResponse({'success': False, 'message': 'Board type, municipality, and rate are required'}, status=400)
            
            logger.debug(f"Fetching fiscal year for board_type_id: {board_type_id}")
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                logger.warning("No active fiscal year found")
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            
            logger.debug(f"Fetching BoardType: {board_type_id}")
            board_type = BoardType.objects.get(id=board_type_id, fiscal_year=fiscal_year)
            logger.debug(f"Fetching Municipality: {municipality_id}")
            municipality = Municipality.objects.get(id=municipality_id)
            
            logger.debug(f"Checking for existing BoardTypeRate for board_type_id: {board_type_id}, municipality_id: {municipality_id}")
            try:
                board_type_rate = BoardTypeRate.objects.get(board_type=board_type, municipality=municipality)
                board_type_rate.rate = Decimal(rate)
                logger.debug(f"Updating existing BoardTypeRate: {board_type_rate.id}")
            except BoardTypeRate.DoesNotExist:
                board_type_rate = BoardTypeRate(board_type=board_type, municipality=municipality, rate=Decimal(rate))
                logger.debug("Creating new BoardTypeRate")
            
            board_type_rate.full_clean()
            board_type_rate.save()
            logger.info(f"BoardTypeRate saved successfully: board_type_id={board_type_id}, municipality_id={municipality_id}, rate={rate}")
            return JsonResponse({'success': True})
        except BoardType.DoesNotExist:
            logger.error(f"BoardType not found: id={board_type_id}")
            return JsonResponse({'success': False, 'message': 'Board type not found'}, status=404)
        except Municipality.DoesNotExist:
            logger.error(f"Municipality not found: id={municipality_id}")
            return JsonResponse({'success': False, 'message': 'Municipality not found'}, status=404)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in board_type_rates POST: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': f'Internal server error: {str(e)}'}, status=500)
        
@csrf_exempt
def delete_board_type_rate(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            board_type_id = data.get('board_type_id')
            municipality_id = data.get('municipality_id')
            
            if not all([board_type_id, municipality_id]):
                return JsonResponse({'success': False, 'message': 'Board type and municipality IDs are required'}, status=400)
            
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            
            board_type_rate = BoardTypeRate.objects.get(
                board_type_id=board_type_id,
                board_type__fiscal_year=fiscal_year,
                municipality_id=municipality_id
            )
            board_type_rate.delete()
            return JsonResponse({'success': True})
        except BoardTypeRate.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Rate not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@csrf_exempt
def board_type_rate(request):
    if request.method == 'GET':
        try:
            board_type_id = request.GET.get('board_type_id')
            municipality_id = request.GET.get('municipality_id')
            
            if not all([board_type_id, municipality_id]):
                return JsonResponse({'success': False, 'message': 'Board type and municipality IDs are required'}, status=400)
            
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            
            try:
                board_type_rate = BoardTypeRate.objects.get(
                    board_type_id=board_type_id,
                    board_type__fiscal_year=fiscal_year,
                    municipality_id=municipality_id
                )
                return JsonResponse({'success': True, 'rate': str(board_type_rate.rate)})
            except BoardTypeRate.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Rate not found for this board type and municipality'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

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
            municipality_id = request.POST.get('municipality_id')
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

            if not all([client_id, municipality_id, address, shop_name, brand_id, board_type_id, length, breadth, quantity, rate]):
                return JsonResponse({'success': False, 'message': 'All fields are required'}, status=400)

            client = Client.objects.get(id=client_id, fiscal_year=fiscal_year)
            brand = Brand.objects.get(id=brand_id, client=client, fiscal_year=fiscal_year)
            board_type = BoardType.objects.get(id=board_type_id, fiscal_year=fiscal_year)
            municipality = Municipality.objects.get(id=municipality_id)

            # Validate rate against BoardTypeRate
            try:
                board_type_rate = BoardTypeRate.objects.get(board_type=board_type, municipality=municipality)
                if Decimal(rate) != board_type_rate.rate:
                    return JsonResponse({'success': False, 'message': 'Rate does not match the defined rate for this board type and municipality'}, status=400)
            except BoardTypeRate.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'No rate defined for this board type and municipality'}, status=400)

            with transaction.atomic():
                if board_id:
                    board = Board.objects.get(id=board_id, client=client, fiscal_year=fiscal_year)
                else:
                    board = Board(client=client, fiscal_year=fiscal_year)

                board.municipality = municipality
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

            print(f"Board {board.id} saved successfully for client {client_id}")
            return JsonResponse({'success': True, 'board_id': board.id})
        except Client.DoesNotExist:
            print(f"Client not found: {client_id}")
            return JsonResponse({'success': False, 'message': 'Client not found for the active fiscal year'}, status=404)
        except Brand.DoesNotExist:
            print(f"Brand not found: {brand_id}")
            return JsonResponse({'success': False, 'message': 'Brand not found for the client and fiscal year'}, status=404)
        except BoardType.DoesNotExist:
            print(f"Board type not found: {board_type_id}")
            return JsonResponse({'success': False, 'message': 'Board type not found for the fiscal year'}, status=404)
        except Municipality.DoesNotExist:
            print(f"Municipality not found: {municipality_id}")
            return JsonResponse({'success': False, 'message': 'Municipality not found'}, status=404)
        except ValidationError as e:
            print(f"Validation error: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        except Exception as e:
            print(f"Unexpected error in board view: {str(e)}")
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
                    'municipality_id': board.municipality.id,
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
            boards = Board.objects.filter(client_id=client_id, fiscal_year=fiscal_year).select_related('client', 'brand', 'board_type', 'municipality').order_by('created_at')

            paginator = Paginator(boards, per_page)
            page_obj = paginator.get_page(page)

            boards_data = [{
                'id': board.id,
                'client_name': board.client.name,
                'municipality_id': board.municipality.id,
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
            print(f"Error in get_boards: {str(e)}")
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

            with transaction.atomic():
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