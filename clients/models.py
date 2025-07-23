from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django_cryptography.fields import encrypt
from datetime import datetime

# Custom file path for board images
def board_image_path(instance, filename):
    client_name = instance.client.name.replace(' ', '_').lower()
    date_str = datetime.now().strftime('%Y-%m-%d')
    ext = filename.split('.')[-1]
    return f'boards/{client_name}/{date_str}/{instance.brand.id}_{instance.id}.{ext}'

# Custom file path for company logo
def company_logo_path(instance, filename):
    ext = filename.split('.')[-1]
    return f'company/logo/{instance.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}'

class FiscalYear(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fiscal Year"
        verbose_name_plural = "Fiscal Years"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_active:
            FiscalYear.objects.filter(is_active=True).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)

class VATRate(models.Model):
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='vat_rates')
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('13.00'), validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "VAT Rate"
        verbose_name_plural = "VAT Rates"
        unique_together = ('fiscal_year', 'is_active')

    def __str__(self):
        return f"{self.rate}% ({self.fiscal_year.name})"

    def save(self, *args, **kwargs):
        if self.is_active:
            VATRate.objects.filter(fiscal_year=self.fiscal_year, is_active=True).exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)

class Company(models.Model):
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    vat_id = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Company's Tax Identification Number")
    logo = models.ImageField(upload_to=company_logo_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one company exists
        if Company.objects.exists() and not self.pk:
            raise ValidationError("Only one company can be created.")
        super().save(*args, **kwargs)

class EmailCredential(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='email_credential')
    smtp_host = models.CharField(max_length=100)
    smtp_port = models.PositiveIntegerField()
    username = models.CharField(max_length=100)
    password = encrypt(models.CharField(max_length=100))
    from_email = models.EmailField()
    use_tls = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Email Credential"
        verbose_name_plural = "Email Credentials"

    def __str__(self):
        return f"Email Credential for {self.company.name}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile for {self.user.username}"

class Client(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    vat_id = models.CharField(max_length=20, help_text="Client's Tax Identification Number")
    registration_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, help_text="Additional tax or client notes")
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='clients', null=True, blank=True)

    def __str__(self):
        return self.name

class BoardType(models.Model):
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='board_types')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'fiscal_year')
        verbose_name = "Board Type"
        verbose_name_plural = "Board Types"

    def __str__(self):
        return f"{self.name} ({self.fiscal_year.name})"

class Brand(models.Model):
    name = models.CharField(max_length=100)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='brands')
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='brands')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'client', 'fiscal_year')
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return f"{self.name} ({self.client.name})"

class Board(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='boards')
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='boards')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='boards')
    board_type = models.ForeignKey(BoardType, on_delete=models.CASCADE, related_name='boards')
    address = models.TextField()
    shop_name = models.CharField(max_length=100)
    length = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    breadth = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(default=1)
    rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to=board_image_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid')
    ], default='UNPAID')

    class Meta:
        verbose_name = "Board"
        verbose_name_plural = "Boards"

    def __str__(self):
        return f"Board {self.id} - {self.client.name} - {self.brand.name}"

    @property
    def area(self):
        return self.length * self.breadth

    @property
    def total_amount(self):
        return (self.area * self.quantity * self.rate) - self.discount

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

    def update_status(self):
        if self.paid_amount >= self.total_amount:
            self.status = 'PAID'
        elif self.paid_amount > 0:
            self.status = 'PARTIAL'
        else:
            self.status = 'UNPAID'
        self.save()

class Transaction(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='transactions')
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='transactions')
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    transaction_type = models.CharField(max_length=20, choices=[
        ('PAYMENT', 'Payment'),
        ('DISCOUNT', 'Discount')
    ])
    payment_type = models.CharField(max_length=20, choices=[
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('CHECK', 'Check'),
        ('ONLINE', 'Online')
    ], null=True, blank=True)
    cheque_number = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"{self.transaction_type} - {self.client.name} - ${self.amount}"