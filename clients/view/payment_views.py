from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal
from datetime import datetime
from clients.models import Client, FiscalYear, Board, Transaction
from django.core.exceptions import ValidationError
import json
from django.template.loader import render_to_string
import subprocess
import os
import tempfile

def payment_management(request):
    return render(request, 'payment_management.html')

@csrf_exempt
def client_detail(request, client_id):
    if request.method == 'GET':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            client = Client.objects.get(id=client_id, fiscal_year=fiscal_year)
            
            # Calculate financial summary
            current_year_boards = Board.objects.filter(client_id=client_id, fiscal_year=fiscal_year)
            previous_year_boards = Board.objects.filter(client_id=client_id).exclude(fiscal_year=fiscal_year)
            
            current_year_total = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount) for board in current_year_boards))
            previous_year_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in previous_year_boards))
            current_year_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in current_year_boards))
            
            previous_dues_details = [
                {'field': f'Board {board.id}', 'value': f'NPR {(board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount):.2f}'}
                for board in previous_year_boards if (board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) > 0
            ]
            current_year_details = [
                {'field': f'Board {board.id}', 'value': f'NPR {(board.length * board.breadth * board.quantity * board.rate - board.discount):.2f}'}
                for board in current_year_boards
            ]
            total_dues_details = previous_dues_details + current_year_details
            total_paid_details = [
                {'field': f'Transaction {t.id} (Board {t.board_id})', 'value': f'NPR {t.amount:.2f}'}
                for t in Transaction.objects.filter(client_id=client_id, transaction_type='PAYMENT')
            ]
            total_discount_details = [
                {'field': f'Transaction {t.id} (Board {t.board_id})', 'value': f'NPR {t.amount:.2f}'}
                for t in Transaction.objects.filter(client_id=client_id, transaction_type='DISCOUNT')
            ]
            total_remaining_details = [
                {'field': f'Board {board.id}', 'value': f'NPR {(board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount):.2f}'}
                for board in Board.objects.filter(client_id=client_id) if (board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) > 0
            ]

            financial_summary = {
                'previous_dues': previous_year_remaining if previous_year_remaining > 0 else 0.0,
                'current_year_total': current_year_total if current_year_total > 0 else 0.0,
                'total_dues': previous_year_remaining + current_year_total if previous_year_remaining + current_year_total > 0 else 0.0,
                'total_discount': float(Transaction.objects.filter(client_id=client_id, transaction_type='DISCOUNT').aggregate(Sum('amount'))['amount__sum'] or 0),
                'total_paid': float(Transaction.objects.filter(client_id=client_id, transaction_type='PAYMENT').aggregate(Sum('amount'))['amount__sum'] or 0),
                'total_remaining': previous_year_remaining + current_year_remaining if previous_year_remaining + current_year_remaining > 0 else 0.0,
                'previous_dues_details': previous_dues_details,
                'current_year_details': current_year_details,
                'total_dues_details': total_dues_details,
                'total_paid_details': total_paid_details,
                'total_discount_details': total_discount_details,
                'total_remaining_details': total_remaining_details
            }

            return JsonResponse({
                'success': True,
                'client': {'id': client.id, 'name': client.name, 'email': client.email, 'address': client.address},
                'financial_summary': financial_summary
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
def get_transactions(request, client_id):
    if request.method == 'GET':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)

            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 10))
            transactions = Transaction.objects.filter(client_id=client_id).order_by('-created_at')

            paginator = Paginator(transactions, per_page)
            page_obj = paginator.get_page(page)

            transactions_data = [{
                'id': t.id,
                'client_id': t.client_id,
                'board_id': t.board_id,
                'transaction_type': t.transaction_type,
                'amount': str(t.amount),
                'payment_type': getattr(t, 'payment_type', None),  # Handle missing payment_type
                'description': t.description,
                'created_at': t.created_at.isoformat()
            } for t in page_obj]

            return JsonResponse({
                'success': True,
                'transactions': transactions_data,
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def get_transaction(request, transaction_id):
    if request.method == 'GET':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            transaction = Transaction.objects.get(id=transaction_id, fiscal_year=fiscal_year)
            return JsonResponse({
                'success': True,
                'transaction': {
                    'id': transaction.id,
                    'client_id': transaction.client_id,
                    'board_id': transaction.board_id,
                    'transaction_type': transaction.transaction_type,
                    'amount': str(transaction.amount),
                    'payment_type': getattr(transaction, 'payment_type', None),  # Handle missing payment_type
                    'description': transaction.description,
                    'created_at': transaction.created_at.isoformat()
                }
            })
        except Transaction.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Transaction not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def apply_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            client_id = data.get('client_id')
            payment_amount = Decimal(data.get('payment_amount', 0))
            discount_amount = Decimal(data.get('discount_amount', 0))
            payment_type = data.get('payment_type')
            cheque_number = data.get('cheque_number')
            transaction_id = data.get('transaction_id')

            if payment_amount < 0 or discount_amount < 0:
                return JsonResponse({'success': False, 'message': 'Payment and discount cannot be negative'}, status=400)

            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)

            client = Client.objects.get(id=client_id, fiscal_year=fiscal_year)
            boards = Board.objects.filter(client_id=client_id).order_by('created_at')

            # Calculate total remaining dues
            total_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in boards))
            if payment_amount + discount_amount > total_remaining:
                return JsonResponse({'success': False, 'message': 'Payment and discount cannot exceed total remaining dues'}, status=400)

            with transaction.atomic():
                if transaction_id:
                    # Update existing transaction
                    trans = Transaction.objects.get(id=transaction_id, client=client)
                    if trans.transaction_type == 'PAYMENT':
                        # Revert previous payment
                        if trans.board:
                            trans.board.paid_amount -= trans.amount
                            trans.board.update_status()
                            trans.board.save()
                        trans.amount = payment_amount
                        trans.payment_type = payment_type
                        trans.cheque_number = cheque_number
                        trans.description = f'Updated payment for client {client.name}'
                    else:
                        # Revert previous discount
                        if trans.board:
                            trans.board.discount -= trans.amount
                            trans.board.update_status()
                            trans.board.save()
                        trans.amount = discount_amount
                        trans.description = f'Updated discount for client {client.name}'
                    trans.save()
                else:
                    # Apply payment to oldest unpaid/partially paid boards
                    if payment_amount > 0:
                        remaining_payment = payment_amount
                        for board in boards:
                            if remaining_payment <= 0:
                                break
                            board_remaining = board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount
                            if board_remaining > 0:
                                payment_to_apply = min(remaining_payment, board_remaining)
                                board.paid_amount += payment_to_apply
                                board.update_status()
                                board.save()
                                Transaction.objects.create(
                                    client=client,
                                    fiscal_year=fiscal_year,
                                    board=board,
                                    amount=payment_to_apply,
                                    transaction_type='PAYMENT',
                                    payment_type=payment_type,
                                    cheque_number=cheque_number,
                                    description=f'Payment applied to board {board.id}'
                                )
                                remaining_payment -= payment_to_apply

                    # Apply discount to oldest unpaid/partially paid boards
                    if discount_amount > 0:
                        remaining_discount = discount_amount
                        for board in boards:
                            if remaining_discount <= 0:
                                break
                            board_remaining = board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount
                            if board_remaining > 0:
                                discount_to_apply = min(remaining_discount, board_remaining)
                                board.discount += discount_to_apply
                                board.update_status()
                                board.save()
                                Transaction.objects.create(
                                    client=client,
                                    fiscal_year=fiscal_year,
                                    board=board,
                                    amount=discount_to_apply,
                                    transaction_type='DISCOUNT',
                                    description=f'Discount applied to board {board.id}'
                                )
                                remaining_discount -= discount_to_apply

                # Fetch the latest transaction for bill generation
                latest_transaction = Transaction.objects.filter(client_id=client_id).order_by('-created_at').first()

            return JsonResponse({
                'success': True,
                'transaction': {
                    'id': latest_transaction.id,
                    'client_id': latest_transaction.client_id,
                    'board_id': latest_transaction.board_id,
                    'transaction_type': latest_transaction.transaction_type,
                    'amount': str(latest_transaction.amount),
                    'payment_type': latest_transaction.payment_type,
                    'cheque_number': latest_transaction.cheque_number,
                    'description': latest_transaction.description,
                    'created_at': latest_transaction.created_at.isoformat()
                }
            })
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client not found'}, status=404)
        except Transaction.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Transaction not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
        
@csrf_exempt
def delete_transaction(request, transaction_id):
    if request.method == 'POST':
        try:
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            trans = Transaction.objects.get(id=transaction_id, fiscal_year=fiscal_year)
            if trans.board:
                if trans.transaction_type == 'PAYMENT':
                    trans.board.paid_amount -= trans.amount
                else:
                    trans.board.discount -= trans.amount
                trans.board.update_status()
                trans.board.save()
            trans.delete()
            return JsonResponse({'success': True})
        except Transaction.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Transaction not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def generate_bill(request, client_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transaction_id = data.get('transaction_id')
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            client = Client.objects.get(id=client_id, fiscal_year=fiscal_year)
            transaction = Transaction.objects.get(id=transaction_id, client=client)
            
            # Calculate financial summary for bill
            current_year_boards = Board.objects.filter(client_id=client_id, fiscal_year=fiscal_year)
            previous_year_boards = Board.objects.filter(client_id=client_id).exclude(fiscal_year=fiscal_year)
            previous_year_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in previous_year_boards))
            current_year_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in current_year_boards))

            bill_html = f"""
                <div class='text-center mb-6'>
                    <h2 class='text-2xl font-bold'>SignHub Pvt Ltd</h2>
                    <p>Gausala, Kathmandu, Nepal</p>
                    <p>Bill No: {transaction.id}</p>
                    <p>Date: {transaction.created_at.strftime('%Y-%m-%d')}</p>
                </div>
                <div class='mb-4'>
                    <h3 class='text-lg font-semibold'>Client Details</h3>
                    <p>Name: {client.name}</p>
                    <p>Email: {client.email}</p>
                    <p>Address: {client.address}</p>
                </div>
                <div class='mb-4'>
                    <h3 class='text-lg font-semibold'>Transaction Details</h3>
                    <table class='w-full border-collapse'>
                        <thead class='bg-gray-50'>
                            <tr>
                                <th class='px-4 py-2 text-left font-medium text-gray-600 border-b'>Field</th>
                                <th class='px-4 py-2 text-left font-medium text-gray-600 border-b'>Value</th>
                            </tr>
                        </thead>
                        <tbody class='divide-y divide-gray-200'>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Transaction ID</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>{transaction.id}</td>
                            </tr>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Type</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>{transaction.transaction_type}</td>
                            </tr>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Amount</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>NPR {transaction.amount:.2f}</td>
                            </tr>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Payment Type</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>{getattr(transaction, 'payment_type', '-')}</td>
                            </tr>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Board ID</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>{transaction.board_id or '-'}</td>
                            </tr>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Description</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>{transaction.description}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class='mb-4'>
                    <h3 class='text-lg font-semibold'>Financial Summary</h3>
                    <table class='w-full border-collapse'>
                        <thead class='bg-gray-50'>
                            <tr>
                                <th class='px-4 py-2 text-left font-medium text-gray-600 border-b'>Field</th>
                                <th class='px-4 py-2 text-left font-medium text-gray-600 border-b'>Amount (NPR)</th>
                            </tr>
                        </thead>
                        <tbody class='divide-y divide-gray-200'>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Previous Dues</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>{previous_year_remaining:.2f}</td>
                            </tr>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Current Year Dues</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>{current_year_remaining:.2f}</td>
                            </tr>
                            <tr>
                                <td class='px-4 py-2 text-gray-600 border-b'>Total Remaining</td>
                                <td class='px-4 py-2 text-gray-600 border-b'>{(previous_year_remaining + current_year_remaining):.2f}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            """

            return JsonResponse({
                'success': True,
                'bill_html': bill_html
            })
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client not found'}, status=404)
        except Transaction.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Transaction not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def download_bill(request, client_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transaction_id = data.get('transaction_id')
            fiscal_year = FiscalYear.objects.filter(is_active=True).first()
            if not fiscal_year:
                return JsonResponse({'success': False, 'message': 'No active fiscal year found'}, status=400)
            client = Client.objects.get(id=client_id, fiscal_year=fiscal_year)
            transaction = Transaction.objects.get(id=transaction_id, client=client)
            
            # Calculate financial summary for bill
            current_year_boards = Board.objects.filter(client_id=client_id, fiscal_year=fiscal_year)
            previous_year_boards = Board.objects.filter(client_id=client_id).exclude(fiscal_year=fiscal_year)
            previous_year_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in previous_year_boards))
            current_year_remaining = float(sum((board.length * board.breadth * board.quantity * board.rate - board.discount - board.paid_amount) for board in current_year_boards))

            # LaTeX template for the bill
            latex_content = render_to_string('bill_template.tex', {
                'client_name': client.name,
                'client_email': client.email,
                'client_address': client.address,
                'bill_no': transaction.id,
                'date': transaction.created_at.strftime('%Y-%m-%d'),
                'transaction_id': transaction.id,
                'transaction_type': transaction.transaction_type,
                'amount': f'{transaction.amount:.2f}',
                'payment_type': getattr(transaction, 'payment_type', '-'),  # Handle missing payment_type
                'board_id': transaction.board_id or '-',
                'description': transaction.description,
                'previous_dues': f'{previous_year_remaining:.2f}',
                'current_year_dues': f'{current_year_remaining:.2f}',
                'total_remaining': f'{(previous_year_remaining + current_year_remaining):.2f}',
            })

            # Create a temporary file for LaTeX processing
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False) as tex_file:
                tex_file.write(latex_content)
                tex_file_path = tex_file.name

            # Compile LaTeX to PDF
            output_dir = tempfile.gettempdir()
            output_pdf = os.path.join(output_dir, f'bill_{client_id}_{transaction_id}.pdf')
            try:
                subprocess.run(
                    ['latexmk', '-pdf', '-interaction=nonstopmode', f'-output-directory={output_dir}', tex_file_path],
                    check=True, capture_output=True
                )
            except subprocess.CalledProcessError as e:
                return JsonResponse({'success': False, 'message': 'Failed to generate PDF'}, status=500)

            # Read the generated PDF
            with open(output_pdf, 'rb') as pdf_file:
                pdf_content = pdf_file.read()

            # Clean up temporary files
            for ext in ['.tex', '.aux', '.log', '.pdf', '.fls', '.fdb_latexmk']:
                try:
                    os.remove(tex_file_path.replace('.tex', ext))
                except OSError:
                    pass

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="bill_{client_id}_{transaction_id}.pdf"'
            response.write(pdf_content)
            return response
        except Client.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Client not found'}, status=404)
        except Transaction.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Transaction not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)