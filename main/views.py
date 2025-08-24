import os
import uuid
from datetime import datetime
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import logging

from .forms import (
    ContactForm, CommentForm, UserRegisterForm, SubscriberForm,
    UserUpdateForm, ProfileUpdateForm, CheckoutForm
)
from .models import (
    Service, BlogPost, Tag, PortfolioItem, PortfolioCategory,
    TeamMember, Testimonial, Category, ContactMessage, Skill,
    Client, AboutPage, Order, OrderItem, Profile, BankAccount
)

stripe.api_key = settings.STRIPE_SECRET_KEY
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

            # DÜZELTİLDİ: E-posta gönderme için send_email_wrapper kullanıldı.
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


# -----------------------------------------------------------------------------
# Sepete Ürün Ekleme View'ı
# -----------------------------------------------------------------------------
@login_required
def add_to_cart_view(request, item_id):
    item = get_object_or_404(PortfolioItem, id=item_id)
    with transaction.atomic():
        cart, created = Order.objects.get_or_create(user=request.user, status='cart')

        # Ürün sepette zaten varsa miktarını artır
        order_item, item_created = OrderItem.objects.get_or_create(
            order=cart,
            portfolio_item=item,
            defaults={'price': item.price or 0, 'quantity': 1}
        )

        if not item_created:
            # Ürün zaten sepetteydi, miktarını 1 artır
            order_item.quantity += 1
            order_item.save()

    messages.success(request, f'"{item.title}" sepete eklendi. Sepetteki adedi: {order_item.quantity}')
    return redirect('cart_detail')


# -----------------------------------------------------------------------------
# DÜZELTİLDİ: remove_from_cart_view fonksiyonunun ikinci tanımı kaldırıldı.
# İlk tanım ile birleştirildi. Şimdi sadece bir tanım var.
# Bu fonksiyon, sepetteki ürünün adedini azaltır, 1 adet kalınca siler.
# -----------------------------------------------------------------------------
@login_required
def remove_from_cart_view(request, item_id):
    if request.method == 'POST':
        try:
            # Buradaki 'item_id', OrderItem'ın kendi ID'si olmalı
            order_item = get_object_or_404(
                OrderItem,
                id=item_id,
                order__user=request.user,
                order__status='cart'
            )

            item_title = order_item.portfolio_item.title

            if order_item.quantity > 1:
                # Miktar 1'den fazlaysa, sadece bir adet azalt
                order_item.quantity -= 1
                order_item.save()
                messages.success(request, f'"{item_title}" ürününün adedi bir azaltıldı.')
            else:
                # Miktar 1 ise, ürünü tamamen sil
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
@login_required
def checkout_view(request):
    cart = Order.objects.filter(user=request.user, status='cart').first()

    if not cart or not cart.items.exists():
        messages.error(request, 'Sepetiniz boş. Lütfen önce ürün ekleyin.')
        return redirect('portfolio')

    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                order = cart
                # Formdan gelen verileri siparişe kaydet
                order.payment_method = form.cleaned_data['payment_method']
                order.billing_name = form.cleaned_data['billing_name']
                order.billing_email = form.cleaned_data['billing_email']
                order.billing_address = form.cleaned_data['billing_address']
                order.billing_city = form.cleaned_data['billing_city']
                order.billing_postal_code = form.cleaned_data['billing_postal_code']
                order.save()

                # Kredi Kartı/Banka Kartı ile ödeme
                if order.payment_method in ['credit_card', 'debit_card']:
                    try:
                        MIN_STRIPE_AMOUNT_CENTS = 1700
                        total_amount_cents = int(order.get_total_cost() * 100)

                        if total_amount_cents < MIN_STRIPE_AMOUNT_CENTS:
                            messages.error(
                                request,
                                f"Ödeme tutarı çok düşük. En az {MIN_STRIPE_AMOUNT_CENTS / 100} TL'lik bir sipariş vermelisiniz."
                            )
                            return redirect('cart_detail')

                        line_items = [{
                            'price_data': {
                                'currency': 'try',
                                'product_data': {'name': item.portfolio_item.title},
                                'unit_amount': int(item.price * 100),
                            },
                            'quantity': item.quantity,
                        } for item in order.items.all()]

                        checkout_session = stripe.checkout.Session.create(
                            line_items=line_items,
                            mode='payment',
                            success_url=request.build_absolute_uri(reverse('payment_success')),
                            cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
                            client_reference_id=str(order.id),
                            customer_email=order.billing_email,
                            metadata={
                                'billing_name': order.billing_name,
                                'billing_email': order.billing_email,
                                'billing_address': order.billing_address,
                                'billing_city': order.billing_city,
                                'billing_postal_code': order.billing_postal_code,
                            }
                        )
                        return redirect(checkout_session.url, code=303)

                    except Exception as e:
                        logger.error(f"Ödeme oturumu oluşturulurken bir hata oluştu: {e}")
                        messages.error(request, "Ödeme oturumu oluşturulurken bir hata oluştu.")
                        return redirect('cart_detail')

                # Havale/EFT ve Nakit ödeme
                elif order.payment_method in ['bank_transfer', 'cash']:
                    order.status = 'pending'
                    order.save()
                    messages.success(request, 'Siparişiniz alındı. Ödeme bilgileri e-postanıza gönderildi.')

                    # Aktif banka hesabını veritabanından çekme
                    try:
                        active_bank_account = BankAccount.objects.get(is_active=True)
                    except BankAccount.DoesNotExist:
                        active_bank_account = None
                        logger.error("Aktif bir banka hesabı bulunamadı. Lütfen kontrol edin.")
                    except BankAccount.MultipleObjectsReturned:
                        active_bank_account = BankAccount.objects.filter(is_active=True).first()
                        logger.warning("Birden fazla aktif banka hesabı bulundu. Sadece ilki kullanıldı.")

                    # E-posta gönderme (Havale/EFT bilgileri için)
                    context = {
                        'order': order,
                        'user': order.user,
                        'bank_details': active_bank_account
                    }
                    html_message = render_to_string('emails/invoice.html', context)
                    send_email_wrapper(
                        subject=f"Siparişiniz Beklemede - #{order.id}",
                        recipient_list=[order.billing_email],
                        html_content=html_message
                    )

                    return redirect('order_history')

        else:
            messages.error(request, 'Lütfen tüm gerekli alanları doğru şekilde doldurun.')
    else:
        # Formun ilk yüklenmesinde verileri doldurma
        form = CheckoutForm(user=request.user)
        if cart and cart.billing_name:
            form.fields['billing_name'].initial = cart.billing_name
            form.fields['billing_email'].initial = cart.billing_email
            form.fields['billing_address'].initial = cart.billing_address
            form.fields['billing_city'].initial = cart.billing_city
            form.fields['billing_postal_code'].initial = cart.billing_postal_code
        elif request.user.is_authenticated:
            form.fields['billing_name'].initial = request.user.get_full_name() or request.user.username
            form.fields['billing_email'].initial = request.user.email
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                form.fields['billing_address'].initial = profile.address
                form.fields['billing_city'].initial = profile.city

    context = {
        'cart': cart,
        'form': form,
        'total': cart.get_total_cost() if cart else 0
    }
    return render(request, 'checkout.html', context)

@login_required
def payment_success_view(request):
    messages.success(request, 'Ödeme talebiniz işleniyor. Siparişinizin durumu en kısa sürede güncellenecektir.')
    return redirect('order_history', username=request.user.username)


@login_required
def payment_cancel_view(request):
    messages.error(request, _('Your payment was canceled or failed. Please try again.'))
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
def stripe_webhook_view(request):
    """
    Stripe'tan gelen olayları (event) işler.
    Ödeme başarıyla tamamlandığında siparişin durumunu günceller.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None
    logger.info("--- Webhook Olayı Alındı ---")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Payload Hatası: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"İmza Doğrulama Hatası: {e}")
        return HttpResponse(status=400)

    # Ödeme başarılı olduğunda tetiklenen olay
    if event['type'] == 'checkout.session.completed':
        logger.info("checkout.session.completed olayı yakalandı.")
        session = event['data']['object']
        client_reference_id = session.get('client_reference_id')

        if client_reference_id:
            with transaction.atomic():
                try:
                    order = Order.objects.get(id=client_reference_id)
                    user = order.user

                    # Kullanıcının Stripe Customer ID'sini profil modeline kaydet
                    try:
                        profile = user.profile
                        if not profile.stripe_customer_id:
                            customer_id = session.get('customer')
                            if customer_id:
                                profile.stripe_customer_id = customer_id
                                profile.save()
                                logger.info(f"Stripe Customer ID {customer_id} kullanıcıya kaydedildi.")
                    except Profile.DoesNotExist:
                        logger.warning(f"Kullanıcı {user.username} için profil bulunamadı.")

                    # Sipariş durumunu güncelle
                    if order.status in ['cart', 'pending']:
                        order.status = 'completed'
                        order.stripe_payment_id = session.id
                        order.payment_date = timezone.now()
                        order.save()

                        logger.info(f"Sipariş {order.id} veritabanında tamamlandı olarak güncellendi.")

                        # Fatura e-postasını gönder
                        context = {
                            'order': order,
                            'user': order.user,
                            'items': order.items.all(),
                        }
                        html_message = render_to_string('emails/invoice.html', context)
                        send_email_wrapper(
                            subject=f"Sipariş Faturanız - #{order.id}",
                            recipient_list=[order.billing_email],
                            html_content=html_message
                        )
                    else:
                        logger.warning(f"Sipariş {order.id} zaten tamamlanmış durumda. İşlem tekrar edilmiyor.")

                except Order.DoesNotExist:
                    logger.error(f"HATA: client_reference_id {client_reference_id} ile eşleşen bir sipariş bulunamadı.")
        else:
            logger.error("HATA: client_reference_id bulunamadı.")
    else:
        logger.info(f"İşlem yapılmayan olay tipi: {event['type']}")

    return HttpResponse(status=200)


@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'invoice.html', context)