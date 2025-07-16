from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django_cryptography.fields import encrypt
from decimal import Decimal

class Client(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=20, unique=True, help_text="Client's Tax Identification Number")
    registration_date = models.DateField(default=timezone.now)
    last_payment_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, help_text="Additional tax or client notes")

    def __str__(self):
        return self.name

    def total_dues(self):
        dues_records_total = self.dues_records.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        return dues_records_total

class Dues(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Partially Paid', 'Partially Paid'),
        ('Paid', 'Paid'),
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='dues_records')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    payment_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, help_text="Details about the dues (e.g., tax type or period)")

    def __str__(self):
        return f"{self.client.name} - ${self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        self.amount = Decimal(str(self.amount))
        self.paid_amount = Decimal(str(self.paid_amount))
        self.remaining_amount = self.amount - self.paid_amount
        if self.paid_amount >= self.amount:
            self.status = 'Paid'
        elif self.paid_amount > 0:
            self.status = 'Partially Paid'
        else:
            self.status = 'Pending'
        super().save(*args, **kwargs)

class EmailCredentials(models.Model):
    smtp_server = models.CharField(max_length=255)
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=255)
    smtp_password = encrypt(models.CharField(max_length=255))
    sender_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.sender_email} ({self.smtp_server})"

class EmailTemplate(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = models.TextField()  # Supports placeholders: {{client_name}}, {{total_due}}, {{remaining_amount}}, {{due_date}}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

class EmailSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('one_time', 'One-Time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)  # Null for all clients
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    scheduled_time = models.DateTimeField()  # For one-time or start time for recurring
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.template.name} - {self.frequency} for {self.client.name if self.client else 'All Clients'}"

class EmailLog(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Sent', 'Sent'), ('Failed', 'Failed')])
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.client.name} - {self.subject} - {self.sent_at}"