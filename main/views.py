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
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage

# SimpleCheckoutForm yerine CheckoutForm import edin
from .forms import (
    ContactForm, CommentForm, UserRegisterForm, SubscriberForm,
    UserUpdateForm, ProfileUpdateForm, CheckoutForm  # Bu satırı değiştirin
)
from .models import (
    Service, BlogPost, Tag, PortfolioItem, PortfolioCategory,
    TeamMember, Testimonial, Category, ContactMessage, Skill,
    Client, AboutPage, Order, OrderItem, Profile
)

stripe.api_key = settings.STRIPE_SECRET_KEY


# -----------------------------------------------------------------------------
# Ana Sayfa Görünümü
# Bu view, anasayfadaki "Hizmetler" bölümünü dinamik olarak doldurur.
# -----------------------------------------------------------------------------
def index_view(request):
    about_content = AboutPage.objects.first()
    latest_portfolio_items = PortfolioItem.objects.all()[:6]  # En son 6 projeyi al
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
    """
    Hakkımızda sayfasını render eder. Gerekli tüm dinamik içerikleri
    (ekip üyeleri, yetenekler, müşteriler) şablona gönderir.
    """
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
    """
    Tüm hizmetlerin listelendiği hizmetler sayfasını (services.html) render eder.
    """
    # Anasayfada olduğu gibi, bu sayfada da tüm hizmetleri
    # veritabanından çekip şablona gönderiyoruz.
    services = Service.objects.all()
    context = {
        'services': services
    }
    # NOT: Bu view'un çalışması için "services.html" adında bir şablonunuz olmalı.
    # Elinizdeki şablon dosyalarında bu isimde bir dosya yoksa,
    # "service-details.html" dosyasının bir kopyasını "services.html" olarak
    # adlandırıp içini düzenleyebilirsiniz.
    return render(request, 'services.html', context)


# -----------------------------------------------------------------------------
# Portfolyo Sayfası Görünümü
# -----------------------------------------------------------------------------
def portfolio_view(request):
    """
    Tüm portfolyo projelerini ve kategorilerini veritabanından çeker
    ve portfolio.html şablonuna gönderir.
    """
    items = PortfolioItem.objects.all()  # Tüm portfolyo öğelerini al
    categories = PortfolioCategory.objects.all()  # Tüm kategorileri al

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
    """
    Tüm ekip üyelerini veritabanından çeker ve team.html şablonuna gönderir.
    """
    team_members = TeamMember.objects.all()
    context = {
        'team_members': team_members
    }
    return render(request, 'team.html', context)


# -----------------------------------------------------------------------------
# Müşteri Yorumları Sayfası Görünümü
# -----------------------------------------------------------------------------
def testimonials_view(request):
    """
    Tüm müşteri yorumlarını veritabanından çeker ve testimonials.html
    şablonuna gönderir.
    """
    testimonials = Testimonial.objects.all()
    context = {
        'testimonials': testimonials
    }
    return render(request, 'testimonials.html', context)


# -----------------------------------------------------------------------------
# Blog Sayfası Görünümü
# -----------------------------------------------------------------------------
def blog_view(request):
    """
    Tüm yayınlanmış blog yazılarını çeker ve sayfalamayı (pagination) uygular.
    """
    # Veritabanından tüm yayınlanmış postları çekiyoruz
    all_posts = BlogPost.objects.filter(status='published').order_by('-created_at')

    # Paginator nesnesi oluşturuyoruz: (tüm yazılar, her sayfadaki yazı sayısı)
    # Şablonumuz 3'lü grid yapısında olduğu için 6 veya 9 gibi bir sayı güzel görünür.
    paginator = Paginator(all_posts, 6)

    # URL'den gelen 'page' parametresini alıyoruz (örn: ?page=2)
    page_number = request.GET.get('page')

    # Paginator'dan istenen sayfadaki objeleri alıyoruz
    page_obj = paginator.get_page(page_number)

    # Şablona artık tüm postları değil, sadece o sayfaya ait olan 'page_obj' nesnesini gönderiyoruz
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'blog.html', context)


# -----------------------------------------------------------------------------
# İletişim Sayfası Görünümü
# -----------------------------------------------------------------------------
def contact_view(request):
    """
    GET isteği ile boş bir iletişim formu gösterir.
    POST isteği ile gönderilen formu işler, verileri doğrular,
    mesajı veritabanına kaydeder, e-posta olarak gönderir ve başarı mesajı gösterir.
    """
    if request.method == 'POST':
        # Eğer form gönderildiyse, formu POST verisiyle doldur
        form = ContactForm(request.POST)
        if form.is_valid():
            # Form geçerliyse, önce veritabanına kaydet
            ContactMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                subject=form.cleaned_data['subject'],
                message=form.cleaned_data['message']
            )

            # Ardından e-posta içeriğini hazırla
            subject = form.cleaned_data['subject']
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']

            full_message = f"""
            Bir yeni iletişim formu mesajı alındı:

            Gönderen Adı: {name}
            Gönderen E-posta: {email}

            Konu: {subject}
            -------------------------------------
            Mesaj:
            {message}
            """

            # E-postayı gönder
            try:
                send_mail(
                    subject=f"İletişim Formu: {subject}",
                    message=full_message,
                    from_email=os.getenv('EMAIL_HOST_USER'),
                    recipient_list=[os.getenv('EMAIL_HOST_USER')],  # E-postayı kendinize gönderin
                )
                messages.success(request, 'Mesajınız başarıyla gönderildi. Teşekkür ederiz!')
            except Exception as e:
                # E-posta gönderiminde bir hata olursa
                messages.error(request, f'Bir hata oluştu, mesajınız gönderilemedi. Hata: {e}')

            # Başarılı gönderim sonrası boş forma yönlendir
            return redirect('contact')
    else:
        # Eğer sayfa ilk kez açılıyorsa (GET isteği), boş bir form oluştur
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

            # Eğer istek bir AJAX isteği ise, JSON cevabı döndür
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Yorumunuz gönderildi ve onaylandıktan sonra yayınlanacaktır.'
                })

            # Eğer normal bir form gönderimi ise, eski usul yönlendirme yap
            messages.success(request, 'Yorumunuz gönderildi ve onaylandıktan sonra yayınlanacaktır.')
            return redirect(post.get_absolute_url())
        else:
            # Form geçerli değilse ve istek AJAX ise, hataları JSON olarak döndür
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': comment_form.errors})
    else:
        comment_form = CommentForm()

    # Kenar çubuğu için veriler (değişiklik yok)
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
    """
    Belirli bir kategoriye ait yayınlanmış blog yazılarını listeler
    ve bu listeye sayfalama uygular.
    """
    # URL'den gelen slug'a göre kategoriyi bul, yoksa 404 hatası ver
    category = get_object_or_404(Category, slug=category_slug)

    # O kategoriye ait ve durumu 'published' olan tüm yazıları al
    all_posts = BlogPost.objects.filter(category=category, status='published').order_by('-created_at')

    # Paginator nesnesi oluştur
    paginator = Paginator(all_posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # blog.html şablonunu yeniden kullanacağız, ama bu sefer context'e
    # hangi kategoride olduğumuzu da ekliyoruz.
    context = {
        'page_obj': page_obj,
        'category': category,  # Şablonda başlık göstermek için
    }
    return render(request, 'blog.html', context)


def search_view(request):
    """
    URL'den gelen 'q' parametresi ile blog yazılarının başlık ve içeriğinde
    arama yapar ve sonuçları bir sayfada listeler.
    """
    query = request.GET.get('q')
    results = []

    if query:
        # Q nesnesi ile hem başlıkta hem de içerikte arama yapıyoruz (case-insensitive)
        results = BlogPost.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            status='published'
        ).distinct().order_by('-created_at')

    # Arama sonuçlarına da sayfalama uygulayalım
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
            login(request, user)  # Kullanıcıyı oluşturduktan sonra otomatik giriş yaptır.
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
            # Form hatalarını veya e-postanın zaten kayıtlı olduğu mesajını döndür
            message = form.errors.get('email', [_('Invalid email address.')])[0]
            return JsonResponse({'success': False, 'message': message})
    # Sadece POST isteklerine izin ver
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
def create_order_view(request, item_id):
    item = get_object_or_404(PortfolioItem, id=item_id)
    order = Order.objects.create(user=request.user)
    OrderItem.objects.create(order=order,
                             portfolio_item=item,
                             price=item.price)
    messages.success(request, _('Your purchase was successful! You can view it in your purchase history.'))
    return redirect('order_history')


@login_required
def profile_view(request):
    """
    Sadece giriş yapmış kullanıcıların erişebileceği profil sayfasını yönetir.
    GET isteği ile kullanıcının mevcut bilgilerini ve düzenleme formlarını gösterir.
    POST isteği ile gönderilen form verilerini doğrular ve kullanıcı bilgilerini günceller.
    """
    # HATA DÜZELTMESİ: Kullanıcının profili yoksa, o anda oluştur.
    # Bu satır, sinyal sisteminden önce oluşturulmuş kullanıcılar için
    # profilin var olmasını garanti eder.
    Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, _('Your account has been updated!'))
            return redirect('profile')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'profile.html', context)


# ==============================================================================
# SATIN ALMA GEÇMİŞİ SAYFASI VIEW'I (EKSİKSİZ HALİ)
# ==============================================================================
@login_required
def order_history_view(request):
    """
    Sadece giriş yapmış kullanıcının kendi sipariş geçmişini listeler.
    Order modelini, o anki kullanıcıya göre filtreler.
    """
    orders = Order.objects.filter(user=request.user)
    context = {
        'orders': orders
    }
    return render(request, 'order_history.html', context)


# ==============================================================================
# SİPARİŞ OLUŞTURMA VIEW'I (İLGİLİ FONKSİYON)
# ==============================================================================
@login_required
def create_order_view(request, item_id):
    """
    Kullanıcı bir projeyi "satın aldığında" yeni bir Order ve OrderItem oluşturur.
    """
    item = get_object_or_404(PortfolioItem, id=item_id)
    order = Order.objects.create(user=request.user)
    OrderItem.objects.create(order=order,
                             portfolio_item=item,
                             price=item.price)
    messages.success(request, _('Your purchase was successful! You can view it in your purchase history.'))
    return redirect('order_history')


@login_required
def add_to_cart_view(request, item_id):
    item = get_object_or_404(PortfolioItem, id=item_id)

    with transaction.atomic():
        cart = Order.objects.filter(user=request.user, status='cart').order_by('id').first()
        if cart is None:
            cart = Order.objects.create(user=request.user, status='cart')

        # Add the item to the cart via OrderItem
        OrderItem.objects.create(
            order=cart,
            portfolio_item=item,
            price=item.price or 0  # price None ise 0 kullan
        )

    return redirect('cart_detail')


@login_required
def cart_detail_view(request):
    # Kullanıcıya ait mevcut cart'i güvenli şekilde alın
    cart = Order.objects.filter(user=request.user, status='cart').first()

    # Debug için - sepette ne olduğunu kontrol edin
    cart_items = []
    if cart:
        cart_items = cart.items.all()
        print(f"Cart found: {cart.id}, Items count: {cart_items.count()}")
        for item in cart_items:
            print(f"Item: {item.portfolio_item.title}, Price: {item.price}")  # Changed 'name' to 'title'
    else:
        print("No cart found for user")

    context = {
        'cart': cart,
        'cart_items': cart_items,  # Ekstra güvenlik için
    }
    return render(request, 'cart_detail.html', context)


@login_required
def checkout_view(request):
    """
    Kullanıcının sepetindeki ürünler için ödeme sayfasına yönlendirir.
    """
    # Mevcut sepeti bul
    cart = Order.objects.filter(user=request.user, status='cart').first()

    if not cart or not cart.items.exists():
        messages.error(request, 'Sepetiniz boş. Lütfen önce ürün ekleyin.')
        return redirect('portfolio')

    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)

        # İşlem bütünlüğünü sağlamak için veritabanı işlemlerini atomik hale getirir
        with transaction.atomic():
            if form.is_valid():
                order = cart
                # Formdan gelen fatura bilgilerini sipariş nesnesine kaydet
                order.payment_method = form.cleaned_data['payment_method']
                order.billing_name = form.cleaned_data['billing_name']
                order.billing_email = form.cleaned_data['billing_email']
                order.billing_address = form.cleaned_data['billing_address']
                order.billing_city = form.cleaned_data['billing_city']
                order.billing_postal_code = form.cleaned_data['billing_postal_code']
                order.save()

                try:
                    MIN_STRIPE_AMOUNT_CENTS = 1700  # 17.00 TL'ye eşittir

                    total_amount_cents = int(order.get_total_cost() * 100)

                    if total_amount_cents < MIN_STRIPE_AMOUNT_CENTS:
                        messages.error(
                            request,
                            f"Ödeme tutarı çok düşük. En az {MIN_STRIPE_AMOUNT_CENTS / 100} TL'lik bir sipariş vermelisiniz."
                        )
                        return redirect('cart_detail')

                    # Stripe Line Items oluştur
                    line_items = []
                    for item in order.items.all():
                        line_items.append({
                            'price_data': {
                                'currency': 'try',
                                'product_data': {
                                    'name': item.portfolio_item.title,
                                },
                                'unit_amount': int(item.price * 100),
                            },
                            'quantity': 1,
                        })

                    # Stripe Checkout Session'ı oluştur
                    checkout_session = stripe.checkout.Session.create(
                        payment_method_types=['card'],
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
                    messages.error(request, f"Ödeme oturumu oluşturulurken bir hata oluştu: {e}")
                    print(f"Stripe hata mesajı: {e}")
                    return redirect('cart_detail')
            else:
                messages.error(request, 'Lütfen tüm gerekli alanları doğru şekilde doldurun.')

    else:  # GET isteği için
        form = CheckoutForm(user=request.user)
        # Eğer daha önce fatura bilgileri girilmişse, formu önceden doldur
        if cart and cart.billing_name:
            form.fields['billing_name'].initial = cart.billing_name
            form.fields['billing_email'].initial = cart.billing_email
            form.fields['billing_address'].initial = cart.billing_address
            form.fields['billing_city'].initial = cart.billing_city
            form.fields['billing_postal_code'].initial = cart.billing_postal_code
        # Aksi halde, kullanıcı profilinden varsayılan bilgileri al
        elif request.user.is_authenticated:
            form.fields['billing_name'].initial = request.user.get_full_name() or request.user.username
            form.fields['billing_email'].initial = request.user.email
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                form.fields['billing_address'].initial = profile.address
                form.fields['billing_city'].initial = profile.city
                # Postal code'un profil modelinde olmadığını varsayarak bu satırı eklemedik.

    context = {
        'cart': cart,
        'form': form,
        'total': cart.get_total_cost() if cart else 0
    }
    return render(request, 'checkout.html', context)


@login_required
def payment_success_view(request):
    # Gerçek bir uygulamada bu işlem Stripe'tan gelen Webhook ile doğrulanmalıdır.
    # Bu, güvenlik için basitleştirilmiş bir simülasyondur.
    cart = Order.objects.filter(user=request.user, status='cart').first()
    if cart:
        # Ödeme kimliğini (gerçekte webhook'tan gelir) ve durumu güncelle
        cart.stripe_payment_id = request.GET.get('payment_intent')
        cart.status = 'completed'
        cart.save()
        messages.success(request, _('Your purchase was successful! You can view it in your purchase history.'))
    return redirect('order_history')


@login_required
def payment_cancel_view(request):
    messages.error(request, _('Your payment was canceled or failed. Please try again.'))
    return redirect('cart_detail')


def send_order_confirmation_email(order):
    """Sipariş onay e-postası gönderir"""
    try:
        subject = f"Sipariş Onayı #{order.id}"
        message = f"""
        Sayın {order.billing_name or order.user.username},

        Siparişiniz başarıyla alınmıştır.

        Sipariş Detayları:
        - Sipariş No: #{order.id}
        - İşlem ID: {order.transaction_id}
        - Toplam Tutar: {order.get_total_cost()} TL
        - Ödeme Yöntemi: {'Kartla Ödeme' if order.payment_method == 'card' else 'Belirtilmemiş'}

        Sipariş İçeriği:
        """

        for item in order.items.all():
            message += f"- {item.portfolio_item.title}: {item.price} TL\n"

        message += "\n\nHizmetlerimizi tercih ettiğiniz için teşekkür ederiz!"

        send_mail(
            subject=subject,
            message=message,
            from_email=os.getenv('EMAIL_HOST_USER', 'noreply@company.com'),
            recipient_list=[order.billing_email or order.user.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"E-posta gönderme hatası: {e}")


@login_required
def remove_from_cart_view(request, item_id):
    """
    Kullanıcının sepetinden bir ürünü siler.
    """
    if request.method == 'POST':
        try:

            item = get_object_or_404(OrderItem, id=item_id)

            # Bu öğenin kullanıcının mevcut sepetine ait olduğunu doğrula
            # Bu, güvenlik için çok önemli bir kontrol!
            if item.order.user == request.user and item.order.status == 'cart':
                item.delete()
                messages.success(request, 'Ürün sepetinizden başarıyla silindi.')
            else:
                messages.error(request, 'Bu ürün sepetinizde bulunmuyor veya silme işlemi başarısız oldu.')

        except OrderItem.DoesNotExist:
            messages.error(request, 'Bu ürün sepetinizde bulunmuyor.')

    return redirect('cart_detail')


def send_invoice_email(order):
    """
    Sipariş tamamlandığında müşteriye fatura e-postası gönderir.
    """
    subject = f"Fatura: Sipariş #{order.id}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = order.billing_email

    # Fatura görüntüleme linkini oluştur (Bu linkin çalışması için urls.py'de 'invoice_view' tanımlı olmalı)
    invoice_url = settings.BASE_URL + reverse('invoice_view', args=[order.id])

    # HTML içeriğini oluştur
    html_content = render_to_string('emails/invoice.html', {
        'order': order,
        'site_name': 'Sitenizin Adı',  # Buraya sitenizin adını yazın
        'invoice_url': invoice_url
    })

    msg = EmailMessage(subject, html_content, from_email, [to_email])
    msg.content_subtype = "html"  # Ana içeriğin HTML olduğunu belirtir
    msg.send()


@csrf_exempt
def stripe_webhook_view(request):
    print("--- Webhook Olayı Alındı ---")
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        print(f"Payload Hatası: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print(f"İmza Doğrulama Hatası: {e}")
        return HttpResponse(status=400)

    print(f"Olay Tipi: {event['type']}")

    if event['type'] == 'checkout.session.completed':
        print("checkout.session.completed olayı yakalandı.")
        session = event['data']['object']
        client_reference_id = session.get('client_reference_id')

        if client_reference_id:
            try:
                order = Order.objects.get(id=client_reference_id)

                # Sipariş durumunu tamamlandı olarak güncelle
                order.status = 'completed'
                order.stripe_payment_id = session.id
                order.payment_date = timezone.now()  # Ödeme tarihini kaydet
                order.save()

                print(f"Sipariş {order.id} veritabanına kaydedildi.")

                # E-POSTA GÖNDERME KISMI
                try:
                    context = {
                        'order': order,
                        'user': order.user,
                        'items': order.items.all(),
                    }
                    html_message = render_to_string('emails/invoice.html', context)
                    plain_message = strip_tags(html_message)

                    send_mail(
                        'Sipariş Faturanız',
                        plain_message,
                        settings.EMAIL_HOST_USER,
                        [order.billing_email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    print(f"Sipariş {order.id} için fatura e-postası başarıyla gönderildi.")
                except Exception as e:
                    print(f"E-posta gönderiminde hata oluştu: {e}")

                print(f"Sipariş {order.id} başarıyla tamamlandı.")

            except Order.DoesNotExist:
                print(f"HATA: client_reference_id {client_reference_id} ile eşleşen bir sipariş bulunamadı.")

    return HttpResponse(status=200)

@login_required
def invoice_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    context = {
        'order': order,
    }
    return render(request, 'invoice.html', context)
