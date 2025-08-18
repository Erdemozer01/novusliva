# main/models.py

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


# ==============================================================================
# TÜM MODELLERİN TEK DİLLİ YAPIYA GÖRE EKSİKSİZ HALİ
# ==============================================================================

class Service(models.Model):
    title = models.CharField(max_length=200, verbose_name="Başlık")
    description = models.TextField(verbose_name="Açıklama")
    icon_class = models.CharField(max_length=100, verbose_name="İkon Sınıfı (Bootstrap Icons)")
    color_class = models.CharField(max_length=50, verbose_name="Renk Sınıfı (örn: item-cyan)")
    image = models.ImageField(upload_to='service_images/', verbose_name="Hizmet Detay Görseli", blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Hizmet"
        verbose_name_plural = "Hizmetler"


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Blog Kategorisi"
        verbose_name_plural = "Blog Kategorileri"


class Tag(models.Model):
    name = models.CharField(max_length=100, verbose_name="Etiket Adı")
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Etiket"
        verbose_name_plural = "Etiketler"


class BlogPost(models.Model):
    STATUS_CHOICES = (('draft', 'Taslak'), ('published', 'Yayınlandı'))

    title = models.CharField(max_length=255, verbose_name="Başlık")
    content = models.TextField(verbose_name="İçerik")
    meta_description = models.CharField(max_length=160, blank=True, verbose_name="Meta Açıklaması (SEO için)")
    slug = models.SlugField(max_length=255, unique=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='blog_posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='blog_posts')
    image = models.ImageField(upload_to='blog_images/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    def get_absolute_url(self):
        return reverse('blog_details', kwargs={'post_id': self.pk})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class PortfolioCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Portfolyo Kategorisi"
        verbose_name_plural = "Portfolyo Kategorileri"


class PortfolioItem(models.Model):
    title = models.CharField(max_length=255, verbose_name="Proje Başlığı")
    short_description = models.CharField(max_length=255, verbose_name="Kısa Açıklama")
    long_description = models.TextField(verbose_name="Uzun Açıklama")
    client = models.CharField(max_length=200, verbose_name="Müşteri", blank=True)
    meta_description = models.CharField(max_length=160, blank=True, verbose_name="Meta Açıklaması")
    slug = models.SlugField(max_length=255, unique=True)
    category = models.ForeignKey(PortfolioCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='items')
    project_date = models.DateField(null=True, blank=True)
    project_url = models.URLField(blank=True)
    main_image = models.ImageField(upload_to='portfolio_images/')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Fiyat (TL)")
    created_at = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self):
        return reverse('portfolio_details', kwargs={'item_id': self.pk})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-project_date']


class PortfolioImage(models.Model):
    portfolio_item = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name='images',
                                       verbose_name="Ait Olduğu Proje")
    image = models.ImageField(upload_to='portfolio_images/details/', verbose_name="Ek Resim")

    def __str__(self):
        return f"{self.portfolio_item.title} için resim"

    class Meta:
        verbose_name = "Proje Resmi"
        verbose_name_plural = "Proje Resimleri"


class TeamMember(models.Model):
    full_name = models.CharField(max_length=100, verbose_name="Adı Soyadı")
    title = models.CharField(max_length=100, verbose_name="Unvanı")
    photo = models.ImageField(upload_to='team_photos/', verbose_name="Fotoğraf")
    twitter_url = models.URLField(blank=True, verbose_name="Twitter Linki")
    facebook_url = models.URLField(blank=True, verbose_name="Facebook Linki")
    instagram_url = models.URLField(blank=True, verbose_name="Instagram Linki")
    linkedin_url = models.URLField(blank=True, verbose_name="LinkedIn Linki")
    order = models.PositiveIntegerField(default=0, help_text="Sıralama için kullanılır (küçük sayı önce gelir).")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Ekip Üyesi"
        verbose_name_plural = "Ekip Üyeleri"
        ordering = ['order', 'full_name']


class Testimonial(models.Model):
    name = models.CharField(max_length=100, verbose_name="Adı Soyadı")
    title = models.CharField(max_length=100, verbose_name="Unvanı (örn: CEO, Designer)")
    comment = models.TextField(verbose_name="Yorum")
    photo = models.ImageField(upload_to='testimonials/', verbose_name="Fotoğraf")
    rating = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)],
                                 verbose_name="Puan (1-5 arası)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Müşteri Yorumu"
        verbose_name_plural = "Müşteri Yorumları"
        ordering = ['-created_at']


class Skill(models.Model):
    name = models.CharField(max_length=100, verbose_name="Yetenek Adı (örn: HTML)")
    percentage = models.PositiveIntegerField(validators=[MaxValueValidator(100)],
                                             verbose_name="Yüzde Değeri (1-100 arası)")
    order = models.PositiveIntegerField(default=0, help_text="Sıralama için kullanılır.")

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

    class Meta:
        verbose_name = "Yetenek"
        verbose_name_plural = "Yetenekler"
        ordering = ['order']


class Client(models.Model):
    name = models.CharField(max_length=100, verbose_name="Müşteri Adı")
    logo = models.ImageField(upload_to='client_logos/', verbose_name="Müşteri Logosu")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Müşteri"
        verbose_name_plural = "Müşteriler"


class AboutPage(models.Model):
    story_title = models.CharField(max_length=200, verbose_name="Hikaye Başlığı")
    story_subtitle = models.CharField(max_length=100, verbose_name="Hikaye Alt Başlığı")
    story_description = models.TextField(verbose_name="Hikaye Açıklaması")
    bullet_point_1 = models.CharField(max_length=255, verbose_name="Madde 1")
    bullet_point_2 = models.CharField(max_length=255, verbose_name="Madde 2")
    bullet_point_3 = models.CharField(max_length=255, verbose_name="Madde 3")
    image = models.ImageField(upload_to='about/', verbose_name="Hakkımızda Sayfası Resmi")
    video_url = models.URLField(verbose_name="Video Linki", blank=True, help_text="YouTube veya Vimeo linki.")

    def __str__(self):
        return "Hakkımızda Sayfası İçeriği"

    class Meta:
        verbose_name = "Hakkımızda Sayfası"
        verbose_name_plural = "Hakkımızda Sayfası"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100, verbose_name="Adı Soyadı")
    email = models.EmailField(verbose_name="E-posta Adresi")
    subject = models.CharField(max_length=200, verbose_name="Konu")
    message = models.TextField(verbose_name="Mesaj")
    is_read = models.BooleanField(default=False, verbose_name="Okundu olarak işaretle")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Gönderilme Tarihi")

    def __str__(self):
        return f"'{self.name}' tarafından gönderilen mesaj: '{self.subject}'"

    class Meta:
        verbose_name = "İletişim Formu Mesajı"
        verbose_name_plural = "İletişim Formu Mesajları"
        ordering = ['-created_at']


class Subscriber(models.Model):
    email = models.EmailField(unique=True, verbose_name="E-posta Adresi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Abonelik Tarihi")

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Bülten Abonesi"
        verbose_name_plural = "Bülten Aboneleri"
        ordering = ['-created_at']


class Comment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments', verbose_name="Yazı")
    name = models.CharField(max_length=100, verbose_name="Adı Soyadı")
    email = models.EmailField(verbose_name="E-posta Adresi")
    body = models.TextField(verbose_name="Yorum")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    active = models.BooleanField(default=False, verbose_name="Aktif (Onaylandı)")

    def __str__(self):
        return f"'{self.post.title}' yazısına '{self.name}' tarafından yapılan yorum"

    class Meta:
        verbose_name = "Yorum"
        verbose_name_plural = "Yorumlar"
        ordering = ['created_at']


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    image = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics',
                              verbose_name="Profil Fotoğrafı")
    bio = models.TextField(blank=True, verbose_name="Hakkında")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Telefon Numarası")
    country = models.CharField(max_length=50, blank=True, verbose_name="Ülke")
    city = models.CharField(max_length=50, blank=True, verbose_name="Şehir")
    address = models.CharField(max_length=255, blank=True, verbose_name="Adres")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Doğum Tarihi")
    postal_code = models.CharField(max_length=10, blank=True, null=True)


    def __str__(self):
        return f"{self.user.username} Profili"

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profiller"


class Order(models.Model):
    """Kullanıcının verdiği siparişleri ve sepetini temsil eder."""
    STATUS_CHOICES = (
        ('cart', _('Sepette')),
        ('pending', _('Ödeme Bekleniyor')),
        ('completed', _('Tamamlandı')),
        ('cancelled', _('İptal Edildi')),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('credit_card', _('Kredi Kartı')),
        ('debit_card', _('Banka Kartı')),
        ('bank_transfer', _('Havale/EFT')),
        ('cash', _('Nakit Ödeme')),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Kullanıcı"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Oluşturulma Tarihi"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Güncellenme Tarihi"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='cart', verbose_name=_("Durum"))
    
    # Ödeme bilgileri
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True, verbose_name=_("Ödeme Yöntemi"))
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Ödeme Tarihi"))
    transaction_id = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("İşlem ID"))
    
    # Fatura bilgileri
    billing_name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Fatura Adı"))
    billing_email = models.EmailField(null=True, blank=True, verbose_name=_("Fatura E-posta"))
    billing_address = models.TextField(null=True, blank=True, verbose_name=_("Fatura Adresi"))
    billing_city = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Şehir"))
    billing_postal_code = models.CharField(max_length=10, null=True, blank=True, verbose_name=_("Posta Kodu"))

    stripe_payment_id = models.CharField(max_length=255, blank=True, null=True)

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def __str__(self):
        return f'{self.user.username} - Sipariş #{self.id} ({self.get_status_display()})'

    class Meta:
        verbose_name = "Sipariş/Sepet"
        verbose_name_plural = "Siparişler/Sepetler"
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    portfolio_item = models.ForeignKey('PortfolioItem', related_name='order_items', on_delete=models.CASCADE,
                                       verbose_name="Proje")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fiyat")

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price


# EKSİK OLAN MODELİ EKLİYORUZ
class SiteSetting(models.Model):
    """Sitenin genel ayarlarını tutan model."""
    address = models.CharField(max_length=255, verbose_name="Adres")
    phone = models.CharField(max_length=20, verbose_name="Telefon Numarası")
    email = models.EmailField(verbose_name="E-posta Adresi")

    # Sosyal Medya Linkleri
    twitter_url = models.URLField(blank=True, null=True, verbose_name="Twitter Linki")
    facebook_url = models.URLField(blank=True, null=True, verbose_name="Facebook Linki")
    instagram_url = models.URLField(blank=True, null=True, verbose_name="Instagram Linki")
    linkedin_url = models.URLField(blank=True, null=True, verbose_name="LinkedIn Linki")

    def __str__(self):
        return "Site Ayarları"

    class Meta:
        verbose_name = "Site Ayarı"
        verbose_name_plural = "Site Ayarları"
