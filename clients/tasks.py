from celery import shared_task
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.template import Template, Context
from django.utils import timezone
from .models import Client, Dues, EmailCredentials, EmailTemplate, EmailSchedule, EmailLog
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum

@shared_task
def send_due_date_emails():
    today = timezone.now().date()
    dues = Dues.objects.filter(due_date=today, status__in=['Pending', 'Partially Paid'])
    for due in dues:
        client = due.client
        credentials = EmailCredentials.objects.filter(created_by__isnull=True).first() or EmailCredentials.objects.first()
        template = EmailTemplate.objects.filter(created_by__isnull=True).first() or EmailTemplate.objects.first()
        if not credentials or not template:
            continue
        total_due = client.total_dues()
        remaining_amount = total_due - (client.dues_records.aggregate(total_paid=Sum('paid_amount'))['total_paid'] or Decimal('0'))
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
                'due_date': due.due_date,
            }))
            body = Template(template.body).render(Context({
                'client_name': client.name,
                'total_due': total_due,
                'remaining_amount': remaining_amount,
                'due_date': due.due_date,
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
        except Exception as e:
            EmailLog.objects.create(
                client=client,
                template=template,
                subject=subject,
                body=body,
                status='Failed',
                error_message=str(e),
            )

@shared_task
def send_scheduled_emails():
    now = timezone.now()
    schedules = EmailSchedule.objects.filter(is_active=True)
    for schedule in schedules:
        should_send = False
        if schedule.frequency == 'one_time' and now >= schedule.scheduled_time and now <= schedule.scheduled_time + timedelta(minutes=5):
            should_send = True
        elif schedule.frequency == 'daily' and now.time() >= schedule.scheduled_time.time():
            should_send = True
        elif schedule.frequency == 'weekly' and now.time() >= schedule.scheduled_time.time() and now.weekday() == schedule.scheduled_time.weekday():
            should_send = True
        elif schedule.frequency == 'monthly' and now.time() >= schedule.scheduled_time.time() and now.day == schedule.scheduled_time.day:
            should_send = True

        if should_send:
            clients = [schedule.client] if schedule.client else Client.objects.all()
            credentials = EmailCredentials.objects.filter(created_by=schedule.created_by).first()
            if not credentials:
                continue
            for client in clients:
                if not client.dues_records.filter(status__in=['Pending', 'Partially Paid']).exists():
                    continue
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
                    subject = Template(schedule.template.subject).render(Context({
                        'client_name': client.name,
                        'total_due': total_due,
                        'remaining_amount': remaining_amount,
                        'due_date': latest_due_date,
                    }))
                    body = Template(schedule.template.body).render(Context({
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
                        template=schedule.template,
                        subject=subject,
                        body=body,
                        status='Sent',
                    )
                except Exception as e:
                    EmailLog.objects.create(
                        client=client,
                        template=schedule.template,
                        subject=subject,
                        body=body,
                        status='Failed',
                        error_message=str(e),
                    )