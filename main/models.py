from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from django.db.models import JSONField


class DiscountCode(models.Model):
    """Sitede kullanılabilecek indirim kodlarını temsil eder."""
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("İndirim Kodu"),
        help_text=_("Örn: ILK2025, YAZINDIRIMI")
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("İndirim Yüzdesi (%)"),
        help_text=_("Örn: %15 indirim için '15.00' girin.")
    )
    valid_from = models.DateTimeField(
        verbose_name=_("Geçerlilik Başlangıç Tarihi")
    )
    valid_to = models.DateTimeField(
        verbose_name=_("Geçerlilik Bitiş Tarihi")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Aktif mi?")
    )
    max_uses = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Maksimum Kullanım Sayısı"),
        help_text=_("Sınırsız kullanım için '0' olarak bırakın.")
    )
    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Kullanım Sayısı")
    )

    def __str__(self):
        return f"{self.code} - %{self.discount_percentage} indirim"

    def is_valid(self):
        """Kupon kodunun şu an geçerli olup olmadığını kontrol eder."""
        now = timezone.now()
        is_active = self.is_active and (self.valid_from <= now <= self.valid_to)
        has_uses_left = (self.max_uses == 0) or (self.used_count < self.max_uses)
        return is_active and has_uses_left

    class Meta:
        verbose_name = _("İndirim Kodu")
        verbose_name_plural = _("İndirim Kodları")
        ordering = ['-valid_from']


class BankAccount(models.Model):
    """Site sahibinin havale/EFT ödemeleri için banka hesap bilgilerini tutar."""
    bank_name = models.CharField(max_length=100, verbose_name=_("Banka Adı"))
    account_holder = models.CharField(max_length=100, verbose_name=_("Hesap Sahibi"))
    iban = models.CharField(max_length=34, verbose_name=_("IBAN"))
    swift_code = models.CharField(max_length=11, blank=True, verbose_name=_("SWIFT Kodu"))
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Aktif mi?"),
        help_text=_("Sadece bir tane aktif hesap olabilir.")
    )

    def __str__(self):
        return f"{self.bank_name} - {self.account_holder}"

    def clean(self):
        """Sadece bir tane aktif hesap olmasını sağlar."""
        if self.is_active:
            if BankAccount.objects.filter(is_active=True).exclude(pk=self.pk).exists():
                raise ValidationError(
                    _("Aynı anda yalnızca bir banka hesabı aktif olabilir. Lütfen diğerini pasif yapın.")
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Banka Hesabı")
        verbose_name_plural = _("Banka Hesapları")


class Service(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Başlık"))
    description = models.TextField(verbose_name=_("Açıklama"))
    icon_class = models.CharField(max_length=100, verbose_name=_("İkon Sınıfı (Bootstrap Icons)"))
    color_class = models.CharField(max_length=50, verbose_name=_("Renk Sınıfı (örn: item-cyan)"))
    image = models.ImageField(upload_to='service_images/', verbose_name=_("Hizmet Detay Görseli"), blank=True,
                              null=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Hizmet")
        verbose_name_plural = _("Hizmetler")


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Kategori Adı"))
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Blog Kategorisi")
        verbose_name_plural = _("Blog Kategorileri")


class Tag(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Etiket Adı"))
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Etiket")
        verbose_name_plural = _("Etiketler")


class BlogPost(models.Model):
    STATUS_CHOICES = (('draft', _('Taslak')), ('published', _('Yayınlandı')))

    title = models.CharField(max_length=255, verbose_name=_("Başlık"))
    content = models.TextField(verbose_name=_("İçerik"))
    meta_description = models.CharField(max_length=160, blank=True, verbose_name=_("Meta Açıklaması (SEO için)"))
    slug = models.SlugField(max_length=255, unique=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts', verbose_name=_("Yazar"))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='blog_posts',
                                 verbose_name=_("Kategori"))
    tags = models.ManyToManyField(Tag, blank=True, related_name='blog_posts', verbose_name=_("Etiketler"))
    image = models.ImageField(upload_to='blog_images/', verbose_name=_("Görsel"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Oluşturulma Tarihi"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Güncellenme Tarihi"))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name=_("Durum"))

    def get_absolute_url(self):
        return reverse('blog_details', kwargs={'post_id': self.pk})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Blog Yazısı")
        verbose_name_plural = _("Blog Yazıları")


class PortfolioCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Kategori Adı"))
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Portfolyo Kategorisi")
        verbose_name_plural = _("Portfolyo Kategorileri")


class PortfolioItem(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Proje Başlığı"))
    short_description = models.CharField(max_length=255, verbose_name=_("Kısa Açıklama"))
    long_description = models.TextField(verbose_name=_("Uzun Açıklama"))
    client = models.CharField(max_length=200, verbose_name=_("Müşteri"), blank=True)
    meta_description = models.CharField(max_length=160, blank=True, verbose_name=_("Meta Açıklaması"))
    slug = models.SlugField(max_length=255, unique=True)
    category = models.ForeignKey(PortfolioCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='items', verbose_name=_("Kategori"))
    project_date = models.DateField(null=True, blank=True, verbose_name=_("Proje Tarihi"))
    project_url = models.URLField(blank=True, verbose_name=_("Proje Linki"))
    main_image = models.ImageField(upload_to='portfolio_images/', verbose_name=_("Ana Görsel"))
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Fiyat (TL)"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Oluşturulma Tarihi"))

    def get_absolute_url(self):
        return reverse('portfolio_details', kwargs={'item_id': self.pk})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-project_date']
        verbose_name = _("Portfolyo Öğesi")
        verbose_name_plural = _("Portfolyo Öğeleri")


class PortfolioImage(models.Model):
    portfolio_item = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name='images',
                                       verbose_name=_("Ait Olduğu Proje"))
    image = models.ImageField(upload_to='portfolio_images/details/', verbose_name=_("Ek Resim"))

    def __str__(self):
        return f"{self.portfolio_item.title} için resim"

    class Meta:
        verbose_name = _("Proje Resmi")
        verbose_name_plural = _("Proje Resimleri")


class TeamMember(models.Model):
    full_name = models.CharField(max_length=100, verbose_name=_("Adı Soyadı"))
    title = models.CharField(max_length=100, verbose_name=_("Unvanı"))
    photo = models.ImageField(upload_to='team_photos/', verbose_name=_("Fotoğraf"))
    twitter_url = models.URLField(blank=True, verbose_name=_("Twitter Linki"))
    facebook_url = models.URLField(blank=True, verbose_name=_("Facebook Linki"))
    instagram_url = models.URLField(blank=True, verbose_name=_("Instagram Linki"))
    linkedin_url = models.URLField(blank=True, verbose_name=_("LinkedIn Linki"))
    order = models.PositiveIntegerField(default=0, help_text=_("Sıralama için kullanılır (küçük sayı önce gelir)."))

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = _("Ekip Üyesi")
        verbose_name_plural = _("Ekip Üyeleri")
        ordering = ['order', 'full_name']


class Testimonial(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Adı Soyadı"))
    title = models.CharField(max_length=100, verbose_name=_("Unvanı (örn: CEO, Designer)"))
    comment = models.TextField(verbose_name=_("Yorum"))
    photo = models.ImageField(upload_to='testimonials/', verbose_name=_("Fotoğraf"))
    rating = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)],
                                 verbose_name=_("Puan (1-5 arası)"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Oluşturulma Tarihi"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Müşteri Yorumu")
        verbose_name_plural = _("Müşteri Yorumları")
        ordering = ['-created_at']


class Skill(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Yetenek Adı (örn: HTML)"))
    percentage = models.PositiveIntegerField(validators=[MaxValueValidator(100)],
                                             verbose_name=_("Yüzde Değeri (1-100 arası)"))
    order = models.PositiveIntegerField(default=0, help_text=_("Sıralama için kullanılır."))

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

    class Meta:
        verbose_name = _("Yetenek")
        verbose_name_plural = _("Yetenekler")
        ordering = ['order']


class Client(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Müşteri Adı"))
    logo = models.ImageField(upload_to='client_logos/', verbose_name=_("Müşteri Logosu"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Müşteri")
        verbose_name_plural = _("Müşteriler")


class AboutPage(models.Model):
    story_title = models.CharField(max_length=200, verbose_name=_("Hikaye Başlığı"))
    story_subtitle = models.CharField(max_length=100, verbose_name=_("Hikaye Alt Başlığı"))
    story_description = models.TextField(verbose_name=_("Hikaye Açıklaması"))
    bullet_point_1 = models.CharField(max_length=255, verbose_name=_("Madde 1"))
    bullet_point_2 = models.CharField(max_length=255, verbose_name=_("Madde 2"))
    bullet_point_3 = models.CharField(max_length=255, verbose_name=_("Madde 3"))
    image = models.ImageField(upload_to='about/', verbose_name=_("Hakkımızda Sayfası Resmi"))
    video_url = models.URLField(verbose_name=_("Video Linki"), blank=True, help_text=_("YouTube veya Vimeo linki."))

    def __str__(self):
        return "Hakkımızda Sayfası İçeriği"

    class Meta:
        verbose_name = _("Hakkımızda Sayfası")
        verbose_name_plural = _("Hakkımızda Sayfası")


class ContactMessage(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Adı Soyadı"))
    email = models.EmailField(verbose_name=_("E-posta Adresi"))
    subject = models.CharField(max_length=200, verbose_name=_("Konu"))
    message = models.TextField(verbose_name=_("Mesaj"))
    is_read = models.BooleanField(default=False, verbose_name=_("Okundu olarak işaretle"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Gönderilme Tarihi"))

    def __str__(self):
        return f"'{self.name}' tarafından gönderilen mesaj: '{self.subject}'"

    class Meta:
        verbose_name = _("İletişim Formu Mesajı")
        verbose_name_plural = _("İletişim Formu Mesajları")
        ordering = ['-created_at']


class Subscriber(models.Model):
    email = models.EmailField(unique=True, verbose_name=_("E-posta Adresi"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Abonelik Tarihi"))

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _("Bülten Abonesi")
        verbose_name_plural = _("Bülten Aboneleri")
        ordering = ['-created_at']


class Comment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments', verbose_name=_("Yazı"))
    name = models.CharField(max_length=100, verbose_name=_("Adı Soyadı"))
    email = models.EmailField(verbose_name=_("E-posta Adresi"))
    body = models.TextField(verbose_name=_("Yorum"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Oluşturulma Tarihi"))
    active = models.BooleanField(default=False, verbose_name=_("Aktif (Onaylandı)"))

    def __str__(self):
        return f"'{self.post.title}' yazısına '{self.name}' tarafından yapılan yorum"

    class Meta:
        verbose_name = _("Yorum")
        verbose_name_plural = _("Yorumlar")
        ordering = ['created_at']


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("Kullanıcı"))
    bio = models.TextField(blank=True, verbose_name=_("Hakkında"))
    phone_number = models.CharField(max_length=20, blank=True, verbose_name=_("Telefon Numarası"))
    country = models.CharField(max_length=50, blank=True, verbose_name=_("Ülke"))
    city = models.CharField(max_length=50, blank=True, verbose_name=_("Şehir"))
    address = models.CharField(max_length=255, blank=True, verbose_name=_("Adres"))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("Doğum Tarihi"))
    postal_code = models.CharField(max_length=10, blank=True, null=True, verbose_name=_("Posta Kodu"))
    stripe_customer_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Stripe Müşteri ID")
    )

    def __str__(self):
        return f"{self.user.username} Profili"

    class Meta:
        verbose_name = _("Profil")
        verbose_name_plural = _("Profiller")


# models.py dosyanızda Order modelini bulun ve aşağıdaki gibi güncelleyin

class Order(models.Model):
    """Kullanıcının verdiği siparişleri ve sepetini temsil eder."""
    STATUS_CHOICES = (
        ('cart', _('Sepette')),
        ('pending', _('Ödeme Bekleniyor')),
        # PayTR kaldırıldığı için bu satır da temizlenebilir
        ('pending_iyzico_approval', _('Iyzico Onayı Bekleniyor')),
        ('completed', _('Tamamlandı')),
        ('payment_failed', _('Ödeme Başarısız')),
        ('cancelled', _('İptal Edildi')),
    )

    # PayTR kaldırıldığı için bu choices da temizlenebilir
    PAYMENT_METHOD_CHOICES = (
        ('iyzico', _('Iyzico (Kredi/Banka Kartı)')),
        ('bank_transfer', _('Havale/EFT')),
        ('cash', _('Nakit Ödeme')),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Kullanıcı"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Oluşturulma Tarihi"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Güncellenme Tarihi"))
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='cart', verbose_name=_("Durum"))

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True,
                                      verbose_name=_("Ödeme Yöntemi"))
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Ödeme Tarihi"))

    # Iyzico alanları
    iyzi_conversation_id = models.CharField(
        max_length=64, blank=True, null=True, unique=True,
        help_text="CF-Initialize sırasında üretilen conversationId"
    )
    iyzi_token_last = models.CharField(
        max_length=64, blank=True, null=True,
        help_text="CF-Initialize sonrası callback'e gelecek son token (opsiyonel)"
    )
    iyzi_paymentId = models.CharField(
        max_length=255, blank=True, null=True, unique=True,
        help_text="CF-Retrieve ile dönen nihai paymentId (unique)"
    )
    iyzi_payment_status = models.CharField(
        max_length=32, blank=True, null=True,
        help_text="CF-Retrieve paymentStatus: SUCCESS/FAILURE/INIT_THREEDS/..."
    )
    iyzi_price = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        help_text="CF-Initialize 'price' (kalemlerin toplamı)"
    )
    iyzi_paid_price = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        help_text="CF-Retrieve 'paidPrice' (taksit komisyonu dahil son tahsilat)"
    )
    iyzi_currency = models.CharField(
        max_length=3, blank=True, null=True, default="TRY",
        help_text="TRY / USD / EUR / GBP (yurtdışı satışta önemli)"
    )
    iyzi_installment = models.PositiveSmallIntegerField(
        blank=True, null=True, help_text="Gerçekleşen taksit sayısı (1,2,3,6,9,12)"
    )
    iyzi_fraud_status = models.SmallIntegerField(
        blank=True, null=True,
        help_text="CF-Retrieve fraudStatus: -2/-1/0/1/2"
    )
    iyzi_bin_number = models.CharField(
        max_length=6, blank=True, null=True, help_text="kartın ilk 6 hanesi (BIN)"
    )
    iyzi_card_family = models.CharField(
        max_length=32, blank=True, null=True, help_text="Bonus/Axess/World/Maximum/Paraf/..."
    )
    iyzi_raw_response = JSONField(
        blank=True, null=True,
        help_text="Son CF-Retrieve (veya webhook) JSON yanıtı (debug/raporlama)"
    )

    # paytr_merchant_oid alanı artık kaldırılabilir

    billing_name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Fatura Adı"))
    billing_email = models.EmailField(null=True, blank=True, verbose_name=_("Fatura E-posta"))
    billing_address = models.TextField(null=True, blank=True, verbose_name=_("Fatura Adresi"))
    billing_city = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Şehir"))
    billing_postal_code = models.CharField(max_length=10, null=True, blank=True, verbose_name=_("Posta Kodu"))
    billing_phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("Fatura Telefon Numarası"))


    # YENİ ALANLAR
    discount_code = models.ForeignKey(
        'DiscountCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name=_("İndirim Kodu")
    )

    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )

    # --- YENİ ALANLAR BİTTİ ---

    def get_subtotal_cost(self):
        """İndirim uygulanmamış ara toplamı döndürür."""
        return sum(item.get_cost() for item in self.items.all())

    def get_total_cost(self):
        """İndirim sonrası ödenecek nihai tutarı döndürür."""
        subtotal = self.get_subtotal_cost()
        # İndirimin ara toplamdan fazla olmasını engelle
        total = subtotal - self.discount_amount
        return max(total, 0)

    def apply_iyzico_result(self, result: dict):
        """CF-Retrieve (veya webhook) sonucunu modele uygular."""
        self.iyzi_payment_status = result.get("paymentStatus")
        self.iyzi_paymentId = result.get("paymentId") or self.iyzi_paymentId
        self.iyzi_paid_price = result.get("paidPrice") or self.iyzi_paid_price
        self.iyzi_currency = result.get("currency") or self.iyzi_currency
        self.iyzi_installment = result.get("installment") or self.iyzi_installment
        self.iyzi_fraud_status = result.get("fraudStatus") or self.iyzi_fraud_status
        self.iyzi_bin_number = result.get("binNumber") or self.iyzi_bin_number
        self.iyzi_card_family = result.get("cardFamily") or self.iyzi_card_family
        self.iyzi_raw_response = result
        # Durum güncelle
        if self.iyzi_payment_status == "SUCCESS":
            self.status = "completed"
            self.payment_date = timezone.now()
        elif self.iyzi_payment_status == "FAILURE":
            self.status = "payment_failed"

    def __str__(self):
        return f'{self.user.username} - Sipariş #{self.id} ({self.get_status_display()})'

    class Meta:
        verbose_name = _("Sipariş/Sepet")
        verbose_name_plural = _("Siparişler/Sepetler")
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name=_("Sipariş"))
    portfolio_item = models.ForeignKey('PortfolioItem', related_name='order_items', on_delete=models.CASCADE,
                                       verbose_name=_("Proje"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Birim Fiyat"))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Adet"))

    def get_cost(self):
        """Bu kalemdeki toplam maliyeti hesaplar."""
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.portfolio_item.title}"

    class Meta:
        verbose_name = _("Sipariş Kalemi")
        verbose_name_plural = _("Sipariş Kalemleri")


class SiteSetting(models.Model):
    """Sitenin genel ayarlarını tutan model."""
    address = models.CharField(max_length=255, verbose_name=_("Adres"))
    phone = models.CharField(max_length=20, verbose_name=_("Telefon Numarası"))
    email = models.EmailField(verbose_name=_("E-posta Adresi"))

    twitter_url = models.URLField(blank=True, null=True, verbose_name=_("Twitter Linki"))
    facebook_url = models.URLField(blank=True, null=True, verbose_name=_("Facebook Linki"))
    instagram_url = models.URLField(blank=True, null=True, verbose_name=_("Instagram Linki"))
    linkedin_url = models.URLField(blank=True, null=True, verbose_name=_("LinkedIn Linki"))

    def __str__(self):
        return _("Site Ayarları")

    class Meta:
        verbose_name = _("Site Ayarı")
        verbose_name_plural = _("Site Ayarları")