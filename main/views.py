from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db.models import Q, F
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
import logging
from django.conf import settings
import iyzipay
import random

from django.views.decorators.http import require_POST

from .forms import (
    ContactForm, CommentForm, UserRegisterForm, SubscriberForm,
    UserUpdateForm, ProfileUpdateForm, CheckoutForm as CustomCheckoutForm, DiscountApplyForm
)
from .models import (
    Service, BlogPost, Tag, PortfolioItem, PortfolioCategory,
    TeamMember, Testimonial, Category, ContactMessage, Skill,
    Client, AboutPage, Order, OrderItem, DiscountCode
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# E-posta Gönderme Fonksiyonu (DRY Prensibi)
# -----------------------------------------------------------------------------
def send_email_wrapper(subject, recipient_list, html_content, plain_content=None):
    """
    E-posta gönderme işlemini tek bir fonksiyonda toplar.
    """
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


# -----------------------------------------------------------------------------
# Ana Sayfa Görünümü
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Hakkımızda Sayfası Görünümü
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Hizmetler Sayfası Görünümü
# -----------------------------------------------------------------------------
def services_view(request):
    services = Service.objects.all()
    context = {
        'services': services
    }
    return render(request, 'services.html', context)


# -----------------------------------------------------------------------------
# Portfolyo Sayfası Görünümü
# -----------------------------------------------------------------------------
def portfolio_view(request):
    items = PortfolioItem.objects.all()
    categories = PortfolioCategory.objects.all()

    context = {
        'items': items,
        'categories': categories,
    }
    return render(request, 'portfolio.html', context)


# -----------------------------------------------------------------------------
# Portfolyo Detay Sayfası Görünümü
# -----------------------------------------------------------------------------
def portfolio_details_view(request, item_id):
    item = get_object_or_404(PortfolioItem, pk=item_id)

    context = {
        'item': item
    }
    return render(request, 'portfolio-details.html', context)


# -----------------------------------------------------------------------------
# Takım Sayfası Görünümü
# -----------------------------------------------------------------------------
def team_view(request):
    team_members = TeamMember.objects.all()
    context = {
        'team_members': team_members
    }
    return render(request, 'team.html', context)


# -----------------------------------------------------------------------------
# Müşteri Yorumları Sayfası Görünümü
# -----------------------------------------------------------------------------
def testimonials_view(request):
    testimonials = Testimonial.objects.all()
    context = {
        'testimonials': testimonials
    }
    return render(request, 'testimonials.html', context)


# -----------------------------------------------------------------------------
# Blog Sayfası Görünümü
# -----------------------------------------------------------------------------
def blog_view(request):
    all_posts = BlogPost.objects.filter(status='published').order_by('-created_at')
    paginator = Paginator(all_posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'blog.html', context)


# -----------------------------------------------------------------------------
# İletişim Sayfası Görünümü
# -----------------------------------------------------------------------------
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
            new_comment.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Yorumunuz gönderildi ve onaylandıktan sonra yayınlanacaktır.'
                })

            messages.success(request, 'Yorumunuz gönderildi ve onaylandıktan sonra yayınlanacaktır.')
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


def subscribe_view(request):
    if request.method == 'POST':
        form = SubscriberForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'message': _('Thank you for subscribing!')
            })
        else:
            message = form.errors.get('email', [_('Invalid email address.')])[0]
            return JsonResponse({'success': False, 'message': message})
    return JsonResponse({'success': False, 'message': _('Invalid request.')})


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
                order.payment_method = form.cleaned_data['payment_method']
                order.billing_name = form.cleaned_data['billing_name']
                order.billing_email = form.cleaned_data['billing_email']
                order.billing_address = form.cleaned_data['billing_address']
                order.billing_city = form.cleaned_data['billing_city']
                order.billing_postal_code = form.cleaned_data['billing_postal_code']

                # Yeni: Formdan telefon numarasını al
                phone_number = form.cleaned_data.get('phone_number')

                order.save()

                # Iyzico ödeme yönlendirmesi
                if order.payment_method == 'iyzico':
                    options = {
                        'api_key': settings.IYZICO_API_KEY,
                        'secret_key': settings.IYZICO_SECRET_KEY,
                        'base_url': settings.IYZICO_BASE_URL
                    }

                    subtotal = cart.get_subtotal_cost()
                    total = cart.get_total_cost()
                    conversation_id = f'ORDER-{order.id}-{random.randint(1000, 9999)}'

                    iyzico_request = {
                        'locale': 'tr',
                        'conversationId': conversation_id,
                        'price': str(subtotal),
                        'paidPrice': str(total),
                        'currency': 'TRY',
                        'basketId': str(order.id),
                        'paymentGroup': 'PRODUCT',
                        'callbackUrl': request.build_absolute_uri(reverse('iyzico_callback')),
                        'enabledInstallments': ['2', '3', '6', '9'],
                    }

                    # Alıcı (Buyer) bilgileri - Güncellendi
                    buyer = {
                        'id': str(request.user.id),
                        'name': request.user.first_name or 'N/A',
                        'surname': request.user.last_name or 'N/A',
                        # Yeni: Kullanıcıdan alınan numarayı kullan
                        'gsmNumber': phone_number or '+905555555555',
                        'email': order.billing_email,
                        'identityNumber': '11111111111',
                        'lastLoginDate': request.user.last_login.strftime(
                            '%Y-%m-%d %H:%M:%S') if request.user.last_login else timezone.now().strftime(
                            '%Y-%m-%d %H:%M:%S'),
                        'registrationDate': request.user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                        'registrationAddress': order.billing_address,
                        'ip': request.META.get('REMOTE_ADDR'),
                        'city': order.billing_city,
                        'country': 'Turkey',
                        'zipCode': order.billing_postal_code
                    }
                    iyzico_request['buyer'] = buyer

                    billing_address = {
                        'contactName': order.billing_name,
                        'city': order.billing_city,
                        'country': 'Turkey',
                        'address': order.billing_address,
                        'zipCode': order.billing_postal_code
                    }
                    iyzico_request['billingAddress'] = billing_address
                    iyzico_request['shippingAddress'] = billing_address

                    basket_items = []
                    for item in cart.items.all():
                        basket_items.append({
                            'id': str(item.portfolio_item.id),
                            'name': item.portfolio_item.title,
                            'category1': item.portfolio_item.category.name if item.portfolio_item.category else 'General',
                            'itemType': 'VIRTUAL',
                            'price': str(item.get_cost())
                        })
                    iyzico_request['basketItems'] = basket_items

                    try:
                        checkout_form_initialize = iyzipay.CheckoutFormInitialize().create(iyzico_request, options)
                        response = checkout_form_initialize.json()

                        if response.get('status') == 'success':
                            order.status = 'pending_iyzico_approval'
                            order.iyzi_paymentId = response.get('paymentId')
                            order.save()
                            return redirect(response.get('paymentPageUrl'))
                        else:
                            error_message = response.get('errorMessage', 'Iyzico ile ödeme başlatılamadı.')
                            messages.error(request, error_message)
                            logger.error(f"Iyzico ödeme başlatma hatası: {response}")
                            return redirect('checkout')

                    except Exception as e:
                        messages.error(request,
                                       'Ödeme işlemi sırasında bir sunucu hatası oluştu. Lütfen tekrar deneyin.')
                        logger.error(f"Iyzico API isteği sırasında genel hata: {e}")
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
        if request.user.is_authenticated:
            form.fields['billing_name'].initial = request.user.get_full_name() or request.user.username
            form.fields['billing_email'].initial = request.user.email
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                form.fields['billing_address'].initial = profile.address
                form.fields['billing_city'].initial = profile.city
                form.fields['billing_postal_code'].initial = profile.postal_code
                # Yeni: Telefon numarasını form alanına ekle
                form.fields['phone_number'].initial = profile.phone_number

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


# -----------------------------------------------------------------------------
# Iyzico Ödeme Akışı
# -----------------------------------------------------------------------------
@login_required
def iyzico_callback_view(request):
    """
    Iyzico'dan dönen kullanıcıyı karşılar ve ödeme sonucunu doğrular.
    """
    token = request.GET.get('token')
    if not token:
        messages.error(request, 'Geçersiz Iyzico geri dönüş isteği. Token bulunamadı.')
        return redirect('checkout')

    options = {
        'api_key': settings.IYZICO_API_KEY,
        'secret_key': settings.IYZICO_SECRET_KEY,
        'base_url': settings.IYZICO_BASE_URL
    }

    iyzico_request = {
        'locale': 'tr',
        'token': token,
    }

    try:
        # Token ile ödeme sonucunu Iyzico'dan doğrula
        checkout_form_result = iyzipay.CheckoutForm().retrieve(iyzico_request, options)
        response = checkout_form_result.json()
        payment_id = response.get('paymentId')

        if response.get('status') == 'success' and payment_id:
            with transaction.atomic():
                # Bizim sistemimizdeki siparişi bul
                order = get_object_or_404(Order, iyzi_paymentId=payment_id)

                payment_status = response.get('paymentStatus')
                if payment_status == 'SUCCESS':
                    # Sipariş zaten tamamlanmadıysa işlemleri yap
                    if order.status != 'completed':
                        order.status = 'completed'
                        order.payment_date = timezone.now()
                        order.save()

                        # Eğer siparişte indirim kodu kullanıldıysa, kullanım sayısını artır
                        if order.discount_code:
                            # F() expression, olası race condition'ları önler
                            order.discount_code.used_count = F('used_count') + 1
                            order.discount_code.save()

                    messages.success(request, f"#{order.id} numaralı siparişinizin ödemesi başarıyla tamamlandı.")
                    return redirect('order_history', username=request.user.username)
                else:
                    # Ödeme Iyzico tarafında başarısız olduysa
                    if order.status != 'payment_failed':
                        order.status = 'payment_failed'
                        order.save()
                    messages.error(request, f"Ödemeniz onaylanmadı. Durum: {payment_status}")
                    return redirect('checkout')
        else:
            # Token doğrulanamadıysa
            error_message = response.get('errorMessage', 'Ödeme sonucu doğrulanırken bir hata oluştu.')
            messages.error(request, error_message)
            logger.error(f"Iyzico callback doğrulama hatası: {response}")
            return redirect('checkout')

    except Exception as e:
        messages.error(request, 'Ödeme sonucu doğrulanırken bir sunucu hatası oluştu.')
        logger.error(f"Iyzico callback sırasında genel hata: {e}")
        return redirect('checkout')


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

            if not discount_code.is_valid():
                return JsonResponse({'success': False, 'message': _("Bu kod artık geçerli değil.")})

            # İndirimi uygula
            subtotal = cart.get_subtotal_cost()
            discount_amount = (subtotal * discount_code.discount_percentage) / 100

            cart.discount_code = discount_code
            cart.discount_amount = discount_amount
            cart.save()

            return JsonResponse({
                'success': True,
                'message': _("İndirim kodu başarıyla uygulandı."),
                'subtotal': f"{cart.get_subtotal_cost():.2f}",
                'discount_amount': f"{cart.discount_amount:.2f}",
                'total': f"{cart.get_total_cost():.2f}",
            })

        except DiscountCode.DoesNotExist:
            return JsonResponse({'success': False, 'message': _("Geçersiz indirim kodu.")})
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': _("Sepetiniz bulunamadı.")})

    return JsonResponse({'success': False, 'message': _("Lütfen bir kod girin.")})


@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'invoice.html', context)