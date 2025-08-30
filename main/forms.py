# forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import ContactMessage, Comment, Subscriber, Profile, Order


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Your Name'),
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Your Email'),
                'required': True
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Subject'),
                'required': True
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': _('Message'),
                'rows': 7,
                'required': True
            }),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('name', 'email', 'body')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Your Name*')}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Your Email*')}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Your Comment*')}),
        }


class SubscriberForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email'),
            'required': True
        }),
        label=_('Email')
    )

    class Meta:
        model = Subscriber
        fields = ['email']


class UserRegisterForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter your username')})
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter your first name')})
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Enter your last name')})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Enter your email address')})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        labels = {
            'username': _('Username'),
            'first_name': _('First Name'),
            'last_name': _('Last Name'),
            'email': _('Email Address'),
        }
        widgets = {
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class DiscountApplyForm(forms.Form):
    code = forms.CharField(
        label=_("İndirim Kodu"),
        widget=forms.TextInput(attrs={
            'placeholder': _('İndirim kodunuzu girin'),
            'class': 'form-control'
        })
    )


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'country', 'city', 'address', 'birth_date']
        labels = {

            'phone_number': _('Phone Number'),
            'country': _('Country'),
            'city': _('City'),
            'address': _('Address'),
            'birth_date': _('Birth Date'),
        }
        widgets = {

            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Your phone number')}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Country you live in')}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('City you live in')}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Your full address')}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class CheckoutForm(forms.ModelForm):
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        label="Telefon Numarası",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Telefon numaranızı girin',
        })
    )

    identity_number = forms.CharField(
        max_length=11,
        required=True,
        label="Kimlik Numarası",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kimlik numaranızı girin'
        })
    )

    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='iyzico',
        label="Ödeme Yöntemi"
    )

    currency = forms.ChoiceField(
        choices=Order.CURRENCY_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='TRY',
        label="Para Birimi"
    )

    class Meta:
        model = Order
        fields = [
            'billing_name',
            'billing_email',
            'phone_number',
            'identity_number',
            'billing_address',
            'billing_city',
            'billing_postal_code',
            'payment_method',
            'currency',
        ]
        widgets = {
            'billing_name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Adınızı ve soyadınızı girin'
            }),
            'billing_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'E-posta adresinizi girin'
            }),
            'billing_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'required': True,
                'placeholder': 'Tam adresinizi girin'
            }),
            'billing_city': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Şehir adını girin'
            }),
            'billing_postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'Posta kodunu girin'
            }),
        }
        labels = {
            'billing_name': 'Ad Soyad',
            'billing_email': 'E-posta Adresi',
            'billing_address': 'Adres',
            'billing_city': 'Şehir',
            'billing_postal_code': 'Posta Kodu',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Alanları sırasını belirleyelim
        self.order_fields([
            'payment_method',
            'currency',
            'billing_name',
            'billing_email',
            'phone_number',
            'identity_number',
            'billing_address',
            'billing_city',
            'billing_postal_code',
        ])

        if user:
            full_name = f"{user.first_name} {user.last_name}".strip()
            self.fields['billing_name'].initial = full_name or user.username
            self.fields['billing_email'].initial = user.email
            if hasattr(user, 'profile'):
                self.fields['phone_number'].initial = user.profile.phone_number
