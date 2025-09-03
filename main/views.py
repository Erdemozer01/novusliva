import base64
import hashlib
import hmac
import json
import uuid

import requests
from django.contrib.admin.views.decorators import staff_member_required

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib import messages
from django.core.mail import EmailMessage, send_mail
from django.db.models import Q, F
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
import logging
from django.conf import settings
import iyzipay
import random
from django.db import IntegrityError

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from ipware import get_client_ip

from .forms import (
    ContactForm, CommentForm, UserRegisterForm, SubscriberForm,
    UserUpdateForm, ProfileUpdateForm, CheckoutForm as CustomCheckoutForm, DiscountApplyForm, CampaignEmailForm
)
from .models import (
    Service, BlogPost, Tag, PortfolioItem, PortfolioCategory,
    TeamMember, Testimonial, Category, ContactMessage, Skill,
    Client, AboutPage, Order, OrderItem, DiscountCode, Subscriber, Feature
)

logger = logging.getLogger(__name__)


def prepare_iyzico_request(order, user, phone_number, request):
    subtotal = order.get_subtotal_cost()
    total = order.get_total_cost()
    conversation_id = f'ORDER-{order.id}-{random.randint(1000, 9999)}'

    iyzico_request = {
        'locale': 'tr',
        'conversationId': conversation_id,
        'price': str(subtotal),
        'paidPrice': str(total),
        'currency': order.currency,  # Dinamik olarak ayarla
        'basketId': str(order.id),
        'paymentGroup': 'PRODUCT',
        'callbackUrl': request.build_absolute_uri(reverse('iyzico_callback')),
        'enabledInstallments': ['2', '3', '6', '9'],
        'buyer': {
            'id': str(user.id),
            'name': user.first_name or 'N/A',
            'surname': user.last_name or 'N/A',
            'gsmNumber': phone_number or '+905555555555',
            'email': order.billing_email,
            'identityNumber': order.billing_identity_number,  # Yeni alan
            'lastLoginDate': user.last_login.strftime(
                '%Y-%m-%d %H:%M:%S') if user.last_login else timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'registrationDate': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            'registrationAddress': order.billing_address,
            'ip': request.META.get('REMOTE_ADDR'),
            'city': order.billing_city,
            'country': 'Turkey',
            'zipCode': order.billing_postal_code
        },
        'billingAddress': {
            'contactName': order.billing_name,
            'city': order.billing_city,
            'country': 'Turkey',
            'address': order.billing_address,
            'zipCode': order.billing_postal_code
        },
        'shippingAddress': {
            'contactName': order.billing_name,
            'city': order.billing_city,
            'country': 'Turkey',
            'address': order.billing_address,
            'zipCode': order.billing_postal_code
        },
        'basketItems': [
            {
                'id': str(item.portfolio_item.id),
                'name': item.portfolio_item.title,
                'category1': item.portfolio_item.category.name if item.portfolio_item.category else 'General',
                'itemType': 'VIRTUAL',
                'price': str(item.get_cost())
            } for item in order.items.all()
        ]
    }

    return iyzico_request, conversation_id


def initialize_iyzico_payment(iyzico_request, options):
    checkout_form_initialize = iyzipay.CheckoutFormInitialize().create(iyzico_request, options)
    return json.loads(checkout_form_initialize.read().decode("utf-8"))


def verify_iyzico_signature(response, secret_key):
    try:
        signature = response.get('signature')
        if not signature:
            return False

        cf = iyzipay.CheckoutForm()
        paidPrice = cf.strip_zero(str(response.get('paidPrice') or '0'))
        price = cf.strip_zero(str(response.get('price') or '0'))
        fields = [
            str(response.get('paymentStatus') or ''),
            str(response.get('paymentId') or ''),
            str(response.get('currency') or ''),
            str(response.get('basketId') or ''),
            str(response.get('conversationId') or ''),
            paidPrice,
            price,
            str(response.get('token') or ''),
        ]
        cf.verify_signature(fields, secret_key, signature)
        return True
    except Exception as sig_err:
        logger.warning(f"Iyzico signature verify failed: {sig_err}")
        return False


def send_email_wrapper(subject, recipient_list, html_content, plain_content=None):
    if plain_content is None:
        plain_content = strip_tags(html_content)

    try:
        msg = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
        )
        msg.content_subtype = "html"
        msg.send()
        logger.info(f"E-posta başarıyla gönderildi: '{subject}' -> {recipient_list}")
    except Exception as e:
        logger.error(f"E-posta gönderiminde hata oluştu: {e}")


def index_view(request):
    about_content = AboutPage.objects.first()
    latest_portfolio_items = PortfolioItem.objects.all()[:6]
    clients = Client.objects.all()

    context = {
        'about_page': about_content,
        'latest_portfolio_items': latest_portfolio_items,
        'clients': clients,
    }
    return render(request, 'index.html', context)


def about_view(request):
    team_members = TeamMember.objects.all()
    skills = Skill.objects.all()
    clients = Client.objects.all()

    context = {
        'team_members': team_members,
        'skills': skills,
        'clients': clients,
    }
    return render(request, 'about.html', context)


def services_view(request):
    services = Service.objects.all()  # Tüm hizmetleri veritabanından çeker
    features = Feature.objects.all()  # Tüm özellikleri veritabanından çeker

    context = {
        'services': services,
        'features': features,
    }

    return render(request, 'services.html', context)


def portfolio_view(request):
    items = PortfolioItem.objects.all()
    categories = PortfolioCategory.objects.all()

    context = {
        'items': items,
        'categories': categories,
    }
    return render(request, 'portfolio.html', context)


def portfolio_details_view(request, item_id):
    item = get_object_or_404(PortfolioItem, pk=item_id)
    context = {
        'item': item
    }
    return render(request, 'portfolio-details.html', context)


def team_view(request):
    team_members = TeamMember.objects.all()
    context = {
        'team_members': team_members
    }
    return render(request, 'team.html', context)


def testimonials_view(request):
    testimonials = Testimonial.objects.all()
    context = {
        'testimonials': testimonials
    }
    return render(request, 'testimonials.html', context)


def blog_view(request):
    all_posts = BlogPost.objects.filter(status='published').order_by('-created_at')
    paginator = Paginator(all_posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'blog.html', context)


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            ContactMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                subject=form.cleaned_data['subject'],
                message=form.cleaned_data['message']
            )

            subject = f"İletişim Formu: {form.cleaned_data['subject']}"
            html_message = render_to_string('emails/contact_notification.html', {
                'name': form.cleaned_data['name'],
                'email': form.cleaned_data['email'],
                'subject': form.cleaned_data['subject'],
                'message': form.cleaned_data['message']
            })
            send_email_wrapper(
                subject=subject,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                html_content=html_message
            )

            messages.success(request, 'Mesajınız başarıyla gönderildi. Teşekkür ederiz!')
            return redirect('contact')
    else:
        form = ContactForm()

    context = {
        'form': form
    }
    return render(request, 'contact.html', context)


def blog_details_view(request, post_id):
    post = get_object_or_404(BlogPost, pk=post_id, status='published')
    comments = post.comments.filter(active=True)

    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.active = True
            new_comment.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Yorumunuz başarıyla yayınlandı.'
                })

            messages.success(request, 'Yorumunuz başarıyla yayınlandı.')
            return redirect(post.get_absolute_url())
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': comment_form.errors})
    else:
        comment_form = CommentForm()

    recent_posts = BlogPost.objects.filter(status='published').order_by('-created_at')[:5]
    all_tags = Tag.objects.all()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'recent_posts': recent_posts,
        'all_tags': all_tags,
    }
    return render(request, 'blog-details.html', context)


def starter_view(request):
    context = {}
    return render(request, 'starter-page.html', context)


def posts_by_category_view(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    all_posts = BlogPost.objects.filter(category=category, status='published').order_by('-created_at')

    paginator = Paginator(all_posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'category': category,
    }
    return render(request, 'blog.html', context)


def search_view(request):
    query = request.GET.get('q')
    results = []

    if query:
        results = BlogPost.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            status='published'
        ).distinct().order_by('-created_at')

    paginator = Paginator(results, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'query': query,
        'page_obj': page_obj,
    }
    return render(request, 'search_results.html', context)


def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Başarıyla kayıt oldunuz ve giriş yaptınız!')
            return redirect('index')
    else:
        form = UserRegisterForm()

    context = {
        'form': form
    }
    return render(request, 'registration/register.html', context)


@require_POST
def subscribe_view(request):
    email = request.POST.get('email')
    if email:
        try:
            # The email address is added to the database. The `unique=True` error is caught.
            Subscriber.objects.create(email=email)
            return JsonResponse({'success': True, 'message': _("You have successfully subscribed to our newsletter!")})
        except IntegrityError:
            # unique constraint error (email is already registered)
            return JsonResponse({'success': False, 'message': _("This email address is already registered.")})
        except Exception:
            # Other potential errors
            return JsonResponse({'success': False, 'message': _("An error occurred. Please try again.")})
    return JsonResponse({'success': False, 'message': _("Please enter a valid email address.")})


def service_details_view(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    all_services = Service.objects.all()
    context = {
        'service': service,
        'all_services': all_services,
    }
    return render(request, 'service-details.html', context)


@login_required
def profile_view(request, username):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            with transaction.atomic():
                u_form.save()
                p_form.save()

            messages.success(request, 'Profiliniz başarıyla güncellendi!')
            return redirect('profile', username=request.user.username)

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'profile.html', context)


@login_required
def order_history_view(request, username):
    orders = Order.objects.filter(user=request.user)
    context = {
        'orders': orders
    }
    return render(request, 'order_history.html', context)


@login_required
def add_to_cart_view(request, item_id):
    item = get_object_or_404(PortfolioItem, id=item_id)
    with transaction.atomic():
        cart, created = Order.objects.get_or_create(user=request.user, status='cart')

        order_item, item_created = OrderItem.objects.get_or_create(
            order=cart,
            portfolio_item=item,
            defaults={'price': item.price or 0, 'quantity': 1}
        )

        if not item_created:
            order_item.quantity += 1
            order_item.save()

    messages.success(request, f'"{item.title}" sepete eklendi. Sepetteki adedi: {order_item.quantity}')
    return redirect('cart_detail')


@login_required
def remove_from_cart_view(request, item_id):
    if request.method == 'POST':
        try:
            order_item = get_object_or_404(
                OrderItem,
                id=item_id,
                order__user=request.user,
                order__status='cart'
            )

            item_title = order_item.portfolio_item.title

            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
                messages.success(request, f'"{item_title}" ürününün adedi bir azaltıldı.')
            else:
                order_item.delete()
                messages.success(request, f'"{item_title}" sepetinizden kaldırıldı.')

        except OrderItem.DoesNotExist:
            messages.error(request, 'Bu ürün sepetinizde bulunmuyor veya silme işlemi başarısız oldu.')

    return redirect('cart_detail')


@login_required
def cart_detail_view(request):
    cart = Order.objects.filter(user=request.user, status='cart').first()
    cart_items = cart.items.all() if cart else []
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'cart_detail.html', context)


@login_required
def checkout_view(request):
    cart = Order.objects.filter(user=request.user, status='cart').first()
    discount_form = DiscountApplyForm()

    if not cart or not cart.items.exists():
        messages.error(request, 'Sepetiniz boş. Lütfen önce ürün ekleyin.')
        return redirect('portfolio')

    if request.method == 'POST':
        form = CustomCheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                order = cart
                # Siparişin fatura bilgilerini kaydet
                order.billing_name = form.cleaned_data['billing_name']
                order.billing_email = form.cleaned_data['billing_email']
                order.billing_address = form.cleaned_data['billing_address']
                order.billing_city = form.cleaned_data['billing_city']
                order.billing_postal_code = form.cleaned_data['billing_postal_code']
                order.billing_phone_number = form.cleaned_data['phone_number']
                order.billing_identity_number = form.cleaned_data.get('identity_number')
                order.payment_method = form.cleaned_data['payment_method']
                order.currency = form.cleaned_data['currency']
                order.save()

                # --- IYZICO ENTEGRASYON BLOĞU ---
                if order.payment_method == 'iyzico':
                    try:
                        options = {
                            'api_key': settings.IYZICO_API_KEY,
                            'secret_key': settings.IYZICO_SECRET_KEY,
                            'base_url': settings.IYZICO_BASE_URL,
                        }
                        iyzico_request, conversation_id = prepare_iyzico_request(order, request.user,
                                                                                 order.billing_phone_number, request)
                        init_data = initialize_iyzico_payment(iyzico_request, options)

                        if init_data.get('status') == 'success':
                            order.status = 'pending_iyzico_approval'
                            order.iyzi_conversation_id = conversation_id
                            order.save()

                            payment_url = init_data.get('paymentPageUrl')
                            if payment_url:
                                return redirect(payment_url)
                            else:
                                request.session['iyzico_checkout_html'] = init_data.get('checkoutFormContent')
                                return redirect('iyzico_checkout_embed')
                        else:
                            error_message = init_data.get('errorMessage', 'Iyzico ile ödeme başlatılamadı.')
                            messages.error(request, error_message)
                            logger.error(f"Iyzico ödeme başlatma hatası: {init_data}")
                            return redirect('checkout')
                    except Exception as e:
                        messages.error(request, 'Iyzico ödeme işlemi sırasında bir hata oluştu. Lütfen tekrar deneyin.')
                        logger.exception("Iyzico API isteği sırasında genel hata")
                        return redirect('checkout')

                # --- PAYTR ENTEGRASYON BLOĞU ---
                elif order.payment_method == 'paytr':
                    try:
                        # IP adresini django-ipware ile güvenli bir şekilde alın
                        client_ip, is_routable = get_client_ip(request)
                        if client_ip is None:
                            # IP adresi tespit edilemezse, hata ver ve işlemi durdur
                            messages.error(request,
                                           'IP adresiniz tespit edilemediği için ödeme işlemine devam edilemiyor.')
                            logger.warning("PayTR işlemi için IP adresi tespit edilemedi.")
                            return redirect('checkout')

                        # Kodun geri kalanı client_ip değişkenini kullanacak
                        user_ip = client_ip

                        merchant_oid = f'{order.id}{uuid.uuid4().hex}'
                        email = order.billing_email

                        if order.currency != 'TRY':
                            messages.error(request, 'PayTR sadece Türk Lirası (TRY) para birimini destekler.')
                            return redirect('checkout')

                        payment_amount = int(order.get_total_cost() * 100)

                        basket_items = [[item.portfolio_item.title, str(int(item.get_cost() * 100)), item.quantity] for
                                        item in order.items.all()]
                        user_basket_base64 = base64.b64encode(json.dumps(basket_items).encode()).decode('utf-8')

                        no_installment = "0"
                        max_installment = "0"
                        test_mode = "1" if settings.DEBUG else "0"

                        # Okunabilirlik için f-string kullanımı daha iyi olabilir
                        hash_str = f"{settings.PAYTR_MERCHANT_ID}{user_ip}{merchant_oid}{email}{payment_amount}{user_basket_base64}{no_installment}{max_installment}{order.currency}{test_mode}{settings.PAYTR_MERCHANT_SALT}"

                        hash_bytes = hmac.new(settings.PAYTR_MERCHANT_KEY.encode('utf-8'), hash_str.encode('utf-8'),
                                              hashlib.sha256).digest()
                        paytr_token = base64.b64encode(hash_bytes).decode('utf-8')

                        post_data = {
                            'merchant_id': settings.PAYTR_MERCHANT_ID,
                            'user_ip': user_ip,
                            'merchant_oid': merchant_oid,
                            'email': email,
                            'payment_amount': payment_amount,
                            'paytr_token': paytr_token,
                            'user_basket': user_basket_base64,
                            'currency': order.currency,
                            'no_installment': int(no_installment),
                            'max_installment': int(max_installment),
                            'test_mode': int(test_mode),
                            'user_name': order.billing_name,
                            'user_address': order.billing_address,
                            'user_phone': order.billing_phone_number,
                            'merchant_ok_url': request.build_absolute_uri(reverse('paytr_callback')),
                            'merchant_fail_url': request.build_absolute_uri(reverse('payment_cancel')),
                            'timeout_limit': 30,
                            'lang': 'tr',
                        }

                        response = requests.post(settings.PAYTR_API_URL, post_data)

                        response_data = response.json()

                        if response_data.get('status') == 'success':
                            token = response_data.get('token')
                            request.session['paytr_token'] = token
                            order.status = 'pending_paytr_approval'
                            order.paytr_merchant_oid = merchant_oid
                            order.save()
                            return redirect('paytr_checkout_embed')
                        else:
                            error_message = response_data.get('reason', 'PayTR ile ödeme başlatılamadı.')
                            messages.error(request, error_message)
                            logger.error(f"PayTR API hatası: {response_data}")
                            return redirect('checkout')

                    except requests.exceptions.RequestException as req_err:
                        messages.error(request, 'PayTR sunucusuna bağlanırken bir hata oluştu. Lütfen tekrar deneyin.')
                        logger.exception(f"PayTR bağlantı hatası: {req_err}")
                        return redirect('checkout')
                    except Exception as e:
                        messages.error(request, 'PayTR ödeme işlemi sırasında beklenmedik bir hata oluştu.')
                        logger.exception("PayTR API isteği sırasında genel hata")
                        return redirect('checkout')

                elif order.payment_method in ['bank_transfer', 'cash']:
                    order.status = 'pending'
                    order.save()
                    messages.success(request, 'Siparişiniz alındı. Ödeme bilgileri e-postanıza gönderildi.')
                    return redirect('order_history', username=request.user.username)

        else:
            messages.error(request, 'Lütfen tüm gerekli alanları doğru şekilde doldurun.')
    else:
        form = CustomCheckoutForm(user=request.user)

    context = {
        'cart': cart,
        'form': form,
        'discount_form': discount_form,
        'total': cart.get_total_cost() if cart else 0,
        'subtotal': cart.get_subtotal_cost() if cart else 0,
    }
    return render(request, 'checkout.html', context)


@login_required
def payment_success_view(request):
    messages.success(request, 'Ödeme işleminiz başarıyla tamamlandı. Siparişinizin durumu güncelleniyor.')
    return redirect('order_history', username=request.user.username)


@login_required
def payment_cancel_view(request):
    messages.error(request, 'Ödeme işleminiz iptal edildi. Lütfen tekrar deneyin.')
    return redirect('cart_detail')


@login_required
def remove_item_view(request, item_id):
    if request.method == 'POST':
        try:
            order_item = get_object_or_404(
                OrderItem,
                id=item_id,
                order__user=request.user,
                order__status='cart'
            )
            item_title = order_item.portfolio_item.title
            order_item.delete()
            messages.success(request, f'"{item_title}" sepetinizden tamamen kaldırıldı.')
        except OrderItem.DoesNotExist:
            messages.error(request, 'Bu ürün sepetinizde bulunmuyor veya silme işlemi başarısız oldu.')

    return redirect('cart_detail')


@csrf_exempt
def iyzico_callback_view(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    token = request.POST.get('token')
    if not token:
        messages.error(request, 'Geçersiz Iyzico geri dönüş isteği. Token bulunamadı.')
        return redirect('checkout')

    options = {
        'api_key': settings.IYZICO_API_KEY,
        'secret_key': settings.IYZICO_SECRET_KEY,
        'base_url': settings.IYZICO_BASE_URL,
    }

    iyzico_request = {
        'locale': 'tr',
        'token': token,
    }

    try:
        checkout_form_result = iyzipay.CheckoutForm().retrieve(iyzico_request, options)
        response = json.loads(checkout_form_result.read().decode('utf-8'))

        status_ok = response.get('status') == 'success'
        payment_status = response.get('paymentStatus')
        basket_id = response.get('basketId')
        conversation_id = response.get('conversationId')

        # Siparişi bul
        order = None
        if basket_id:
            order = get_object_or_404(Order, id=basket_id)
        elif conversation_id:
            order = get_object_or_404(Order, iyzi_conversation_id=conversation_id)

        if not status_ok:
            error_message = response.get('errorMessage', 'Ödeme sonucu doğrulanırken bir hata oluştu.')
            messages.error(request, error_message)
            logger.error(f"Iyzico callback doğrulama hatası: {response}")
            return redirect('checkout')

        # İmza doğrulama
        if not verify_iyzico_signature(response, options['secret_key']):
            logger.warning(f"İmza doğrulaması başarısız: Order #{order.id if order else 'Unknown'}")
            messages.error(request, 'Ödeme doğrulaması başarısız. Lütfen tekrar deneyin.')
            return redirect('checkout')

        with transaction.atomic():
            # Eğer ödeme durumu zaten güncellenmişse tekrar işlem yapma
            if order.status != 'completed':
                order.apply_iyzico_result(response)
                order.iyzi_token_last = token
                order.save()

                if order.status == 'completed' and order.discount_code_id:
                    order.discount_code.used_count = F('used_count') + 1
                    order.discount_code.save(update_fields=['used_count'])

            if order.status == 'completed':
                messages.success(request, f"#{order.id} numaralı siparişinizin ödemesi başarıyla tamamlandı.")
                if request.user.is_authenticated:
                    return redirect('order_history', username=request.user.username)
                return redirect('order_success', order_id=order.id)
            else:
                messages.error(request, f"Ödemeniz onaylanmadı. Durum: {payment_status}")
                return redirect('checkout')

    except Exception as e:
        messages.error(request, 'Ödeme sonucu doğrulanırken bir sunucu hatası oluştu.')
        logger.exception("Iyzico callback sırasında genel hata")
        return redirect('checkout')


@login_required
def order_success_view(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
    except Exception as e:
        return HttpResponse("Sipariş bulunamadı.", status=404)

    # E-posta içeriği için HTML şablonunu render et
    email_body = render_to_string('emails/order_confirmation_email.html', {'order': order})

    # E-posta gönderme işlemi
    try:
        send_mail(
            "Sipariş Onayınız - " + str(order.id),  # E-posta başlığı
            '',  # E-posta gövdesi (HTML formatında olduğu için burası boş)
            settings.DEFAULT_FROM_EMAIL,  # Gönderen e-posta adresi
            [order.billing_email],  # Alıcı e-posta adresi
            html_message=email_body,  # HTML e-posta içeriği
            fail_silently=False,  # Hata durumunda hata fırlat
        )
    except Exception as e:
        # E-posta gönderme hatasını loglayabilirsiniz
        print(f"E-posta gönderilirken bir hata oluştu: {e}")

    # Sipariş başarı sayfasını render et
    return render(request, 'order_success.html', {'order': order})


@login_required
@require_POST
def apply_discount_view(request):
    form = DiscountApplyForm(request.POST)
    now = timezone.now()
    if form.is_valid():
        code_text = form.cleaned_data['code']
        try:
            discount_code = DiscountCode.objects.get(code__iexact=code_text)
            cart = Order.objects.get(user=request.user, status='cart')

            # Yeni ve daha spesifik hata kontrolleri
            if not discount_code.is_active:
                return JsonResponse({'success': False, 'message': _("This code is not active.")})

            if discount_code.valid_from and now < discount_code.valid_from:
                return JsonResponse({'success': False, 'message': _("This code's usage date has not yet started.")})

            if discount_code.valid_to and now > discount_code.valid_to:
                return JsonResponse({'success': False, 'message': _("This code has expired.")})

            if discount_code.max_uses and discount_code.used_count >= discount_code.max_uses:
                return JsonResponse({'success': False, 'message': _("This code's usage limit has been reached.")})

            # Eğer zaten bir indirim kodu uygulanmışsa
            if cart.discount_code:
                return JsonResponse(
                    {'success': False, 'message': _("A discount code has already been applied to the cart.")})

            # İndirimi uygula
            subtotal = cart.get_subtotal_cost()
            discount_amount = (subtotal * discount_code.discount_percentage) / 100

            cart.discount_code = discount_code
            cart.discount_amount = discount_amount
            cart.save()

            return JsonResponse({
                'success': True,
                'message': _("Discount code applied successfully."),
                'subtotal': f"{cart.get_subtotal_cost():.2f}",
                'discount_amount': f"{cart.discount_amount:.2f}",
                'total': f"{cart.get_total_cost():.2f}",
            })

        except DiscountCode.DoesNotExist:
            return JsonResponse({'success': False, 'message': _("Invalid discount code.")})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': _("Your cart could not be found.")})

    return JsonResponse({'success': False, 'message': _("Please enter a code.")})


@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'invoice.html', context)


@csrf_exempt
@require_POST
def paytr_callback_view(request):
    """
    Bu view, PayTR'dan gelen ödeme sonuç bildirimlerini işler.
    Dökümantasyondaki "2. ADIM"a karşılık gelir.
    """
    post_data = request.POST

    # --- HASH KONTROLÜ ---
    # PayTR'dan gelen hash'i, kendi oluşturacağımız hash ile karşılaştıracağız.
    # Bu kontrol, bildirimin gerçekten PayTR'dan geldiğini ve değiştirilmediğini doğrular.
    # Bu adımı atlamak ciddi güvenlik zaafiyetlerine yol açar.

    merchant_key = settings.PAYTR_MERCHANT_KEY
    merchant_salt = settings.PAYTR_MERCHANT_SALT

    # Hash oluşturmak için kullanılacak metin
    hash_str = (
            post_data.get('merchant_oid', '') +
            merchant_salt +
            post_data.get('status', '') +
            post_data.get('total_amount', '')
    )

    # Kendi hash'imizi HMAC-SHA256 ile oluşturuyoruz
    calculated_hash_bytes = hmac.new(merchant_key.encode('utf-8'), hash_str.encode('utf-8'), hashlib.sha256).digest()
    calculated_hash = base64.b64encode(calculated_hash_bytes).decode('utf-8')

    # Hash'ler eşleşmiyorsa, işlemi reddet
    if calculated_hash != post_data.get('hash'):
        logger.warning(f"PayTR callback HASH MISMATCH for merchant_oid: {post_data.get('merchant_oid')}")
        # PayTR'a hatalı bildirim olduğunu belirtmek için metin dönebilirsiniz.
        # "OK" dışında dönen her şey, PayTR'ın bildirimi tekrar göndermesine neden olabilir.
        # Genellikle loglamak ve işlemi sonlandırmak yeterlidir.
        return HttpResponse("PAYTR notification failed: bad hash", status=400)

    # --- SİPARİŞ İŞLEMLERİ ---

    merchant_oid = post_data.get('merchant_oid')

    try:
        # 1. ADIM: merchant_oid ile ilgili siparişi veritabanından bul.
        order = get_object_or_404(Order, paytr_merchant_oid=merchant_oid)

        # 2. ADIM: Siparişin durumunu kontrol et (Mükerrer bildirim önleme).
        # Eğer sipariş zaten 'completed' veya 'failed' ise, aynı bildirimin tekrar
        # gelmesi ihtimaline karşı tekrar işlem yapma.
        if order.status in ['completed', 'failed']:
            logger.info(
                f"PayTR callback received for an already processed order: {merchant_oid}, Status: {order.status}"
            )
            return HttpResponse("OK")

        # Veritabanı işlemlerini güvenli bir blok içine alıyoruz
        with transaction.atomic():
            if post_data.get('status') == 'success':
                # ÖDEME BAŞARILI
                order.status = 'completed'

                # Güncel ödeme tutarını `total_amount` üzerinden al (kuruş cinsindendir)
                final_amount = float(post_data.get('total_amount')) / 100.0
                order.total_paid = final_amount
                order.payment_date = timezone.now()

                logger.info(f"Order {order.id} payment successful via PayTR. Amount: {final_amount}")

                order.save()

                # İndirim kodu kullanıldıysa kullanım sayısını artır
                if order.discount_code:
                    order.discount_code.used_count = F('used_count') + 1
                    order.discount_code.save(update_fields=['used_count'])

                # Müşteriye sipariş onayı e-postası / SMS gönderimi gibi işlemler
                # bu blokta tetiklenmelidir.
                # send_order_confirmation_email(order)

            else:
                # ÖDEME BAŞARISIZ
                order.status = 'failed'
                error_code = post_data.get('failed_reason_code')
                error_message = post_data.get('failed_reason_msg')
                order.payment_error_message = f"Code: {error_code}, Msg: {error_message}"
                logger.error(f"Order {order.id} payment failed via PayTR. Reason: {error_message}")

            order.save()

    except Order.DoesNotExist:
        # merchant_oid ile bir sipariş bulunamazsa, bu durumu logla.
        logger.error(f"PayTR callback received for a non-existent merchant_oid: {merchant_oid}")
        # Yine de PayTR'a 'OK' dönerek bildirimi sonlandırması istenir.
        return HttpResponse("OK")
    except Exception as e:
        # Beklenmedik bir hata oluşursa logla
        logger.exception(
            f"An unexpected error occurred during PayTR callback processing for merchant_oid: {merchant_oid}"
        )
        # Hata durumunda 500 dönebilirsiniz, bu PayTR'ın bildirimi tekrar denemesini sağlar.
        return HttpResponse("An internal error occurred.", status=500)

    # 3. ADIM: PayTR sistemine işlemin başarıyla alındığını bildir.
    # Bu 'OK' yanıtı gönderilmezse, PayTR aynı bildirimi belirli aralıklarla tekrar gönderir.
    return HttpResponse("OK")


@login_required
def paytr_checkout_embed_view(request):
    paytr_token = request.session.get('paytr_token')
    if not paytr_token:
        messages.error(request, 'Ödeme oturumu bulunamadı veya süresi doldu.')
        return redirect('checkout')

    # Token'ı template'e gönder
    context = {
        'paytr_token': paytr_token
    }
    return render(request, 'paytr_checkout_embed.html', context)


@login_required
def iyzico_checkout_embed_view(request):
    html_content = request.session.get('iyzico_checkout_html')
    if not html_content:
        messages.error(request, 'Ödeme işlemi başlatılamadı veya oturum süreniz doldu.')
        return redirect('checkout')

    return render(request, 'iyzico_checkout_embed.html', {'checkout_form_content': html_content})


@staff_member_required
def send_campaign_email_view(request):
    if request.method == 'POST':
        form = CampaignEmailForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message_content = form.cleaned_data['message']
            subscriber_ids_str = form.cleaned_data['subscribers']

            # ID string'ini listeye çevir
            subscriber_ids = [int(sid) for sid in subscriber_ids_str.split(',')]

            # Veritabanından ilgili abonelerin e-posta adreslerini al
            recipients = list(Subscriber.objects.filter(id__in=subscriber_ids).values_list('email', flat=True))

            if recipients:
                try:
                    # E-posta içeriğini HTML şablonu ile render et
                    html_content = render_to_string('emails/campaign_email.html', {
                        'subject': subject,
                        'message_content': message_content,
                    })

                    # Mevcut e-posta gönderme fonksiyonunuzu kullanın
                    send_email_wrapper(
                        subject=subject,
                        recipient_list=recipients,
                        html_content=html_content
                    )

                    messages.success(request, f"{len(recipients)} aboneye kampanya e-postası başarıyla gönderildi.")
                except Exception as e:
                    logger.error(f"Kampanya e-postası gönderilirken hata oluştu: {e}")
                    messages.error(request, f"E-posta gönderimi sırasında bir hata oluştu: {e}")
            else:
                messages.warning(request, "E-posta gönderilecek geçerli abone bulunamadı.")

            # Admini abone listesi sayfasına geri yönlendir
            return redirect(reverse('admin:main_subscriber_changelist'))

    else:
        # GET isteği ile gelen abone ID'lerini al
        subscriber_ids = request.GET.get('ids')
        if not subscriber_ids:
            messages.error(request, "Lütfen en az bir abone seçin.")
            return redirect(reverse('admin:YOUR_APP_NAME_subscriber_changelist'))

        form = CampaignEmailForm(initial={'subscribers': subscriber_ids})

    context = {
        'form': form,
        'title': 'Kampanya E-postası Gönder',
        'opts': Subscriber._meta,  # Admin template'i için gerekli
    }
    return render(request, 'emails/send_campaign_email.html', context)
