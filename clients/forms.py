from decimal import Decimal
from django import forms
from .models import Client, Dues, EmailCredentials, EmailSchedule, EmailTemplate

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'email', 'phone', 'address', 'tax_id', 'last_payment_date', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring focus:ring-indigo-200',
                'placeholder': 'Full Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring focus:ring-indigo-200',
                'placeholder': 'Email Address',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring focus:ring-indigo-200',
                'placeholder': 'Phone Number',
            }),
            'address': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring focus:ring-indigo-200',
                'placeholder': 'Mailing Address',
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring focus:ring-indigo-200',
                'placeholder': 'Tax ID',
            }),
            'last_payment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring focus:ring-indigo-200',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring focus:ring-indigo-200',
                'rows': 3,
                'placeholder': 'Additional Notes',
            }),
        }

class DuesForm(forms.ModelForm):
    class Meta:
        model = Dues
        fields = ['client', 'amount', 'due_date', 'status', 'payment_date', 'description']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        return amount.quantize(Decimal('0.01'))

    def clean_paid_amount(self):
        paid_amount = self.cleaned_data.get('paid_amount', Decimal('0.00'))
        return paid_amount.quantize(Decimal('0.01'))

class EmailCredentialsForm(forms.ModelForm):
    class Meta:
        model = EmailCredentials
        fields = ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'sender_email']
        widgets = {
            'smtp_server': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'border rounded p-2 w-full'}),
            'smtp_username': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
            'smtp_password': forms.PasswordInput(attrs={'class': 'border rounded p-2 w-full'}),
            'sender_email': forms.EmailInput(attrs={'class': 'border rounded p-2 w-full'}),
        }

class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'body']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
            'subject': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
            'body': forms.Textarea(attrs={'class': 'border rounded p-2 w-full', 'rows': 6}),
        }

class EmailScheduleForm(forms.ModelForm):
    class Meta:
        model = EmailSchedule
        fields = ['client', 'template', 'frequency', 'scheduled_time', 'is_active']
        widgets = {
            'client': forms.Select(attrs={'class': 'border rounded p-2 w-full'}),
            'template': forms.Select(attrs={'class': 'border rounded p-2 w-full'}),
            'frequency': forms.Select(attrs={'class': 'border rounded p-2 w-full'}),
            'scheduled_time': forms.DateTimeInput(attrs={'class': 'border rounded p-2 w-full', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4'}),
        }

class ManualEmailForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.all(), widget=forms.Select(attrs={'class': 'border rounded p-2 w-full'}))
    template = forms.ModelChoiceField(queryset=EmailTemplate.objects.all(), widget=forms.Select(attrs={'class': 'border rounded p-2 w-full'}))