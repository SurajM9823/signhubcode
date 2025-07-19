from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from django.template import Template, Context
from django.db.models import Sum, Q
from django.contrib import messages
from clients.models import Client, FiscalYear
from .forms import ClientForm
from datetime import date
from decimal import Decimal
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
    active_fiscal_year = FiscalYear.objects.filter(is_active=True).first()
    clients = Client.objects.all()  # Show all clients across all fiscal years
    return render(request, 'dashboard.html', {'clients': clients, 'active_fiscal_year': active_fiscal_year})
