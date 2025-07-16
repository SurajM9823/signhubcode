from datetime import date
from decimal import Decimal
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from clients.forms import ClientForm, DuesForm, EmailCredentialsForm, EmailScheduleForm, EmailTemplateForm, ManualEmailForm
from .models import Client, Dues, EmailCredentials, EmailLog, EmailSchedule, EmailTemplate
from django.db.models import Sum

from datetime import date, datetime, timedelta
from decimal import Decimal
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.template import Template, Context
from django.db.models import Sum
from .models import Client, Dues, EmailCredentials, EmailTemplate, EmailSchedule, EmailLog
from .forms import ClientForm, DuesForm, EmailCredentialsForm, EmailTemplateForm, EmailScheduleForm, ManualEmailForm
from django.utils import timezone

def custom_login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
        except User.DoesNotExist:
            user = None
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next', request.GET.get('next', 'dashboard'))
            return redirect(next_url)
        else:
            return render(request, 'login.html', {'error': 'Invalid email or password', 'next': request.GET.get('next', '')})
    return render(request, 'login.html', {'next': request.GET.get('next', '')})

@login_required
def dashboard(request):
    clients = Client.objects.all()
    return render(request, 'dashboard.html', {'clients': clients})

@login_required
def client_list(request, pk=None):
    clients = Client.objects.all()
    context = {'clients': clients}

    if pk:
        client = get_object_or_404(Client, pk=pk)
        context['form'] = ClientForm(instance=client)
        context['edit_mode'] = True
        context['client_id'] = pk
    else:
        context['form'] = ClientForm()
        context['edit_mode'] = False

    if request.method == 'POST':
        if pk:
            client = get_object_or_404(Client, pk=pk)
            form = ClientForm(request.POST, instance=client)
            success_message = 'Client updated successfully!'
        else:
            form = ClientForm(request.POST)
            success_message = 'Client added successfully!'

        if form.is_valid():
            form.save()
            context['success_message'] = success_message
            context['form'] = ClientForm()
            context['edit_mode'] = False
            context['client_id'] = None
        else:
            context['error_message'] = 'Invalid form submission.'
            context['form'] = form

        return render(request, 'client_list.html', context)

    return render(request, 'client_list.html', context)

@login_required
def dues_list(request, dues_id=None):
    dues = Dues.objects.all()
    clients = Client.objects.all()
    client_data = []
    for client in clients:
        total_paid = client.dues_records.aggregate(total_paid=Sum('paid_amount'))['total_paid'] or Decimal('0')
        total_dues = client.total_dues()  # Use Client.total_dues method
        total_remaining = total_dues - total_paid
        latest_due = client.dues_records.order_by('-due_date').first()
        oldest_due = client.dues_records.filter(status__in=['Pending', 'Partially Paid']).order_by('due_date').first()
        latest_due_date = latest_due.due_date if latest_due else client.registration_date
        latest_payment = client.dues_records.filter(payment_date__isnull=False).order_by('-payment_date').first()
        latest_payment_date = latest_payment.payment_date if latest_payment else None
        status = 'Paid' if total_paid >= total_dues else 'Partially Paid' if total_paid > 0 else 'Pending'
        latest_due_id = latest_due.pk if latest_due else 0
        oldest_due_id = oldest_due.pk if oldest_due else 0
        total_pending_amount = (
            client.dues_records.filter(status__in=['Pending', 'Partially Paid']).aggregate(total_pending=Sum('remaining_amount'))['total_pending'] or Decimal('0')
        )
        client_data.append({
            'client': client,
            'total_dues': total_dues,
            'total_paid': total_paid,
            'total_remaining': total_remaining,
            'latest_due_date': latest_due_date,
            'latest_payment_date': latest_payment_date,
            'status': status,
            'latest_due_id': latest_due_id,
            'oldest_due_id': oldest_due_id,
            'total_pending_amount': total_pending_amount,
        })
    context = {'dues': dues, 'client_data': client_data}

    if dues_id:
        due = get_object_or_404(Dues, pk=dues_id)
        context['form'] = DuesForm(instance=due)
        context['edit_mode'] = True
        context['dues_id'] = dues_id
    else:
        context['form'] = DuesForm()
        context['edit_mode'] = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            due = get_object_or_404(Dues, pk=request.POST.get('dues_id'))
            due.delete()
            context['success_message'] = 'Dues deleted successfully!'
            context['form'] = DuesForm()
            context['edit_mode'] = False
        elif action == 'mark_paid':
            try:
                payment_amount_str = request.POST.get('payment_amount', '0').strip()
                if not payment_amount_str or not payment_amount_str.replace('.', '').isdigit():
                    context['error_message'] = 'Payment amount must be a valid number.'
                else:
                    payment_amount = Decimal(payment_amount_str)
                    if payment_amount <= 0:
                        context['error_message'] = 'Payment amount must be positive.'
                    else:
                        client_id = request.POST.get('client_id')
                        client = get_object_or_404(Client, pk=client_id)
                        total_pending = (
                            client.dues_records.filter(status__in=['Pending', 'Partially Paid']).aggregate(total_pending=Sum('remaining_amount'))['total_pending'] or Decimal('0')
                        )
                        if payment_amount > total_pending:
                            context['error_message'] = 'Payment amount exceeds total pending dues.'
                        else:
                            remaining_payment = payment_amount
                            dues = client.dues_records.filter(status__in=['Pending', 'Partially Paid']).order_by('due_date')
                            for due in dues:
                                if remaining_payment <= 0:
                                    break
                                amount_to_apply = min(remaining_payment, due.remaining_amount)
                                due.paid_amount += amount_to_apply
                                due.remaining_amount = due.amount - due.paid_amount
                                due.status = 'Paid' if due.remaining_amount == 0 else 'Partially Paid'
                                due.payment_date = date.today()
                                due.save()
                                remaining_payment -= amount_to_apply
                            
                            if remaining_payment > 0:
                                context['error_message'] = 'Excess payment not applied; all dues are managed via Dues records.'
                            else:
                                client.last_payment_date = date.today()
                                client.save()
                            
                            context['success_message'] = 'Payment recorded successfully!'
                            context['form'] = DuesForm()
                            context['edit_mode'] = False
            except ValueError:
                context['error_message'] = 'Invalid payment amount format. Please enter a valid decimal number.'
        else:
            if dues_id:
                due = get_object_or_404(Dues, pk=dues_id)
                form = DuesForm(request.POST, instance=due)
                success_message = 'Dues updated successfully!'
            else:
                form = DuesForm(request.POST)
                success_message = 'Dues added successfully!'

            if form.is_valid():
                form.save()
                context['success_message'] = success_message
                context['form'] = DuesForm()
                context['edit_mode'] = False
                context['dues_id'] = None
            else:
                context['error_message'] = 'Invalid form submission.'
                context['form'] = form

        return render(request, 'dues.html', context)

    return render(request, 'dues.html', context)

@login_required
def email_scheduler(request):
    credentials = EmailCredentials.objects.filter(created_by=request.user)
    templates = EmailTemplate.objects.filter(created_by=request.user)
    schedules = EmailSchedule.objects.filter(created_by=request.user)
    logs = EmailLog.objects.all().order_by('-sent_at')

    context = {
        'credentials_form': EmailCredentialsForm(),
        'template_form': EmailTemplateForm(),
        'schedule_form': EmailScheduleForm(),
        'manual_email_form': ManualEmailForm(),
        'credentials': credentials,
        'templates': templates,
        'schedules': schedules,
        'logs': logs,
    }

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_credentials':
            form = EmailCredentialsForm(request.POST)
            if form.is_valid():
                credentials = form.save(commit=False)
                credentials.created_by = request.user
                credentials.save()
                context['success_message'] = 'Email credentials added successfully!'
            else:
                context['error_message'] = 'Invalid credentials form submission.'
                context['credentials_form'] = form
        elif action == 'add_template':
            form = EmailTemplateForm(request.POST)
            if form.is_valid():
                template = form.save(commit=False)
                template.created_by = request.user
                template.save()
                context['success_message'] = 'Email template added successfully!'
            else:
                context['error_message'] = 'Invalid template form submission.'
                context['template_form'] = form
        elif action == 'add_schedule':
            form = EmailScheduleForm(request.POST)
            if not EmailCredentials.objects.filter(created_by=request.user).exists():
                context['error_message'] = 'Please configure email credentials first.'
            elif form.is_valid():
                schedule = form.save(commit=False)
                schedule.created_by = request.user
                schedule.save()
                context['success_message'] = 'Email schedule added successfully!'
            else:
                context['error_message'] = 'Invalid schedule form submission.'
                context['schedule_form'] = form
        elif action == 'send_manual_email':
            form = ManualEmailForm(request.POST)
            if not EmailCredentials.objects.filter(created_by=request.user).exists():
                context['error_message'] = 'Please configure email credentials first.'
            elif form.is_valid():
                client = form.cleaned_data['client']
                template = form.cleaned_data['template']
                credentials = EmailCredentials.objects.filter(created_by=request.user).first()
                total_due = client.total_dues()
                remaining_amount = total_due - (client.dues_records.aggregate(total_paid=Sum('paid_amount'))['total_paid'] or Decimal('0'))
                latest_due_date = client.dues_records.order_by('-due_date').first().due_date if client.dues_records.exists() else client.registration_date
                try:
                    backend = EmailBackend(
                        host=credentials.smtp_server,
                        port=credentials.smtp_port,
                        username=credentials.smtp_username,
                        password=credentials.smtp_password,
                        use_tls=True,
                    )
                    subject = Template(template.subject).render(Context({
                        'client_name': client.name,
                        'total_due': total_due,
                        'remaining_amount': remaining_amount,
                        'due_date': latest_due_date,
                    }))
                    body = Template(template.body).render(Context({
                        'client_name': client.name,
                        'total_due': total_due,
                        'remaining_amount': remaining_amount,
                        'due_date': latest_due_date,
                    }))
                    send_mail(
                        subject,
                        body,
                        credentials.sender_email,
                        [client.email],
                        connection=backend,
                    )
                    EmailLog.objects.create(
                        client=client,
                        template=template,
                        subject=subject,
                        body=body,
                        status='Sent',
                    )
                    context['success_message'] = f'Email sent to {client.name} successfully!'
                except Exception as e:
                    EmailLog.objects.create(
                        client=client,
                        template=template,
                        subject=subject,
                        body=body,
                        status='Failed',
                        error_message=str(e),
                    )
                    context['error_message'] = f'Failed to send email: {str(e)}'
            else:
                context['error_message'] = 'Invalid manual email form submission.'
                context['manual_email_form'] = form
        elif action == 'delete_credentials':
            credentials = get_object_or_404(EmailCredentials, pk=request.POST.get('credentials_id'), created_by=request.user)
            credentials.delete()
            context['success_message'] = 'Email credentials deleted successfully!'
        elif action == 'delete_template':
            template = get_object_or_404(EmailTemplate, pk=request.POST.get('template_id'), created_by=request.user)
            template.delete()
            context['success_message'] = 'Email template deleted successfully!'
        elif action == 'delete_schedule':
            schedule = get_object_or_404(EmailSchedule, pk=request.POST.get('schedule_id'), created_by=request.user)
            schedule.delete()
            context['success_message'] = 'Email schedule deleted successfully!'

        return render(request, 'email_scheduler.html', context)

    return render(request, 'email_scheduler.html', context)