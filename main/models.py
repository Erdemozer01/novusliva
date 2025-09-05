from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import JSONField

# --- E-Ticaret ve Satış Modelleri ---

class DiscountCode(models.Model):
    """Sitede kullanılabilecek indirim kodlarını temsil eder."""
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Discount Code"),
        help_text=_("E.g: FIRST2025, SUMMERDISCOUNT")
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Discount Percentage (%)"),
        help_text=_("Ex: Enter '15.00' for a 15% discount.")
    )
    valid_from = models.DateTimeField(
        verbose_name=_("Valid From")
    )
    valid_to = models.DateTimeField(
        verbose_name=_("Valid To")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active?")
    )
    max_uses = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Maximum Uses"),
        help_text=_("Leave '0' for unlimited use.")
    )
    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Used Count"),
        # NOT: Bu alanın artırılması işleminin race condition'ları önlemek için
        # view katmanında F() ifadeleri ve transaction ile yapılması önerilir.
        editable=False
    )

    def __str__(self):
        return f"{self.code} - %{self.discount_percentage} discount"

    def is_valid(self):
        """Kupon kodunun şu anda geçerli olup olmadığını kontrol eder."""
        now = timezone.now()
        is_active = self.is_active and (self.valid_from <= now <= self.valid_to)
        has_uses_left = (self.max_uses == 0) or (self.used_count < self.max_uses)
        return is_active and has_uses_left

    class Meta:
        verbose_name = _("Discount Code")
        verbose_name_plural = _("Discount Codes")
        ordering = ['-valid_from']


class BankAccount(models.Model):
    """Banka havalesi ödemeleri için banka hesap bilgilerini tutar."""
    bank_name = models.CharField(max_length=100, verbose_name=_("Bank Name"))
    account_holder = models.CharField(max_length=100, verbose_name=_("Account Holder"))
    iban = models.CharField(max_length=34, verbose_name=_("IBAN"))
    swift_code = models.CharField(max_length=11, blank=True, verbose_name=_("SWIFT Code"))
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Is Active?"),
        help_text=_("Only one account can be active at a time.")
    )

    def __str__(self):
        return f"{self.bank_name} - {self.account_holder}"

    def clean(self):
        """Sadece bir hesabın aktif olmasını sağlar."""
        if self.is_active:
            if BankAccount.objects.filter(is_active=True).exclude(pk=self.pk).exists():
                raise ValidationError(
                    _("Only one bank account can be active at a time. Please deactivate the other one.")
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Bank Account")
        verbose_name_plural = _("Bank Accounts")

# --- İçerik ve Portfolyo Modelleri ---

class Service(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))
    icon_class = models.CharField(max_length=100, verbose_name=_("Icon Class (Bootstrap Icons)"))
    color_class = models.CharField(max_length=50, verbose_name=_("Color Class (e.g: item-cyan)"))
    image = models.ImageField(upload_to='service_images/', verbose_name=_("Service Detail Image"), blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Category Name"))
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Blog Category")
        verbose_name_plural = _("Blog Categories")


class Tag(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Tag Name"))
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class BlogPost(models.Model):
    STATUS_CHOICES = (('draft', _('Draft')), ('published', _('Published')))

    title = models.CharField(max_length=255, verbose_name=_("Title"))
    # ÖNERİ: django-ckeditor gibi bir paketle bu alanı zengin metin editörüne çevirebilirsiniz.
    content = models.TextField(verbose_name=_("Content"))
    meta_description = models.CharField(max_length=160, blank=True, verbose_name=_("Meta Description (for SEO)"))
    slug = models.SlugField(max_length=255, unique=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts', verbose_name=_("Author"))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='blog_posts', verbose_name=_("Category"))
    tags = models.ManyToManyField(Tag, blank=True, related_name='blog_posts', verbose_name=_("Tags"))
    # ÖNERİ: django-imagekit ile resim optimizasyonu yapabilirsiniz.
    image = models.ImageField(upload_to='blog_images/', verbose_name=_("Image"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name=_("Status"))

    def get_absolute_url(self):
        return reverse('blog_details', kwargs={'slug': self.slug}) # slug kullanmak daha SEO dostudur

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Blog Post")
        verbose_name_plural = _("Blog Posts")


class PortfolioCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Category Name"))
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Portfolio Category")
        verbose_name_plural = _("Portfolio Categories")


class PortfolioItem(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Project Title"))
    short_description = models.CharField(max_length=255, verbose_name=_("Short Description"))
    long_description = models.TextField(verbose_name=_("Long Description"))
    client = models.CharField(max_length=200, verbose_name=_("Client"), blank=True)
    meta_description = models.CharField(max_length=160, blank=True, verbose_name=_("Meta Description"))
    slug = models.SlugField(max_length=255, unique=True)
    category = models.ForeignKey(PortfolioCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items', verbose_name=_("Category"))
    project_date = models.DateField(null=True, blank=True, verbose_name=_("Project Date"))
    project_url = models.URLField(blank=True, verbose_name=_("Project Link"))
    main_image = models.ImageField(upload_to='portfolio_images/', verbose_name=_("Main Image"))
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Price (TL)"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    def get_absolute_url(self):
        return reverse('portfolio_details', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-project_date']
        verbose_name = _("Portfolio Item")
        verbose_name_plural = _("Portfolio Items")


class PortfolioImage(models.Model):
    portfolio_item = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name='images', verbose_name=_("Belongs to Project"))
    image = models.ImageField(upload_to='portfolio_images/details/', verbose_name=_("Additional Image"))

    def __str__(self):
        return f"Image for {self.portfolio_item.title}"

    class Meta:
        verbose_name = _("Project Image")
        verbose_name_plural = _("Project Images")

# --- Site ve Şirket Tanıtım Modelleri ---

class TeamMember(models.Model):
    full_name = models.CharField(max_length=100, verbose_name=_("Full Name"))
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    photo = models.ImageField(upload_to='team_photos/', verbose_name=_("Photo"))
    twitter_url = models.URLField(blank=True, verbose_name=_("Twitter Link"))
    facebook_url = models.URLField(blank=True, verbose_name=_("Facebook Link"))
    instagram_url = models.URLField(blank=True, verbose_name=_("Instagram Link"))
    linkedin_url = models.URLField(blank=True, verbose_name=_("LinkedIn Link"))
    order = models.PositiveIntegerField(default=0, help_text=_("Used for sorting (a smaller number comes first)."))

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = _("Team Member")
        verbose_name_plural = _("Team Members")
        ordering = ['order', 'full_name']


class Testimonial(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Full Name"))
    title = models.CharField(max_length=100, verbose_name=_("Title (e.g: CEO, Designer)"))
    comment = models.TextField(verbose_name=_("Comment"))
    photo = models.ImageField(upload_to='testimonials/', verbose_name=_("Photo"))
    rating = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name=_("Rating (1-5)"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Customer Testimonial")
        verbose_name_plural = _("Customer Testimonials")
        ordering = ['-created_at']


class Skill(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Skill Name (e.g: HTML)"))
    percentage = models.PositiveIntegerField(validators=[MaxValueValidator(100)], verbose_name=_("Percentage Value (1-100)"))
    order = models.PositiveIntegerField(default=0, help_text=_("Used for sorting."))

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

    class Meta:
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")
        ordering = ['order']


class Client(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Client Name"))
    logo = models.ImageField(upload_to='client_logos/', verbose_name=_("Client Logo"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")


class AboutPage(models.Model):
    # ÖNERİ: Bu modelden sadece 1 tane olmalı. django-solo paketi ile bunu garantileyebilirsiniz.
    story_title = models.CharField(max_length=200, verbose_name=_("Story Title"))
    story_subtitle = models.CharField(max_length=100, verbose_name=_("Story Subtitle"))
    story_description = models.TextField(verbose_name=_("Story Description"))
    bullet_point_1 = models.CharField(max_length=255, verbose_name=_("Bullet Point 1"))
    bullet_point_2 = models.CharField(max_length=255, verbose_name=_("Bullet Point 2"))
    bullet_point_3 = models.CharField(max_length=255, verbose_name=_("Bullet Point 3"))
    image = models.ImageField(upload_to='about/', verbose_name=_("About Page Image"))
    video_url = models.URLField(verbose_name=_("Video Link"), blank=True, help_text=_("YouTube or Vimeo link."))

    def __str__(self):
        return str(_("About Page Content"))

    class Meta:
        verbose_name = _("About Page")
        verbose_name_plural = _("About Page")

# --- Kullanıcı Etkileşim Modelleri ---

class ContactMessage(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Full Name"))
    email = models.EmailField(verbose_name=_("Email Address"))
    subject = models.CharField(max_length=200, verbose_name=_("Subject"))
    message = models.TextField(verbose_name=_("Message"))
    is_read = models.BooleanField(default=False, verbose_name=_("Mark as Read"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Sent Date"))

    def __str__(self):
        return f"Message from '{self.name}': '{self.subject}'"

    class Meta:
        verbose_name = _("Contact Form Message")
        verbose_name_plural = _("Contact Form Messages")
        ordering = ['-created_at']


class Subscriber(models.Model):
    email = models.EmailField(unique=True, verbose_name=_("Email Address"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Subscription Date"))

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _("Newsletter Subscriber")
        verbose_name_plural = _("Newsletter Subscribers")
        ordering = ['-created_at']


class Comment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments', verbose_name=_("Post"))
    name = models.CharField(max_length=100, verbose_name=_("Full Name"))
    email = models.EmailField(verbose_name=_("Email Address"))
    body = models.TextField(verbose_name=_("Comment"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    active = models.BooleanField(default=False, verbose_name=_("Active (Approved)"))

    def __str__(self):
        return f"Comment by '{self.name}' on '{self.post.title}'"

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        ordering = ['created_at']


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("User"))
    phone_number = models.CharField(max_length=20, blank=True, verbose_name=_("Phone Number"))
    country = models.CharField(max_length=50, blank=True, verbose_name=_("Country"))
    city = models.CharField(max_length=50, blank=True, verbose_name=_("City"))
    address = models.CharField(max_length=255, blank=True, verbose_name=_("Address"))
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("Birth Date"))
    postal_code = models.CharField(max_length=10, blank=True, null=True, verbose_name=_("Postal Code"))

    def __str__(self):
        return f"{self.user.username} Profile"

    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")

# --- Sipariş ve Sepet Sistemi ---

class Order(models.Model):

    STATUS_CHOICES = (
        ('cart', _('In Cart')),
        ('pending', _('Payment Pending')),
        ('pending_iyzico_approval', _('Pending Iyzico Approval')),
        ('pending_paytr_approval', _('Pending PayTR Approval')),
        ('completed', _('Completed')),
        ('payment_failed', _('Payment Failed')),
        ('cancelled', _('Cancelled')),
    )

    PAYMENT_METHOD_CHOICES = (
        ('iyzico', _('Iyzico (Credit/Debit Card)')),
        ('paytr', _('PayTR (Credit/Debit Card)')),
        ('bank_transfer', _('Bank Transfer')),
        ('cash', _('Cash Payment')),
    )

    CURRENCY_CHOICES = (
        ('TRY', _('Turkish Lira')),
        ('USD', _('US Dollar')),
        ('EUR', _('Euro')),
        ('GBP', _('Pound Sterling')),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='cart', verbose_name=_("Status"))

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True, verbose_name=_("Payment Method"))
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Payment Date"))

    # --- PAYTR CALLBACK İÇİN EKLENEN ALANLAR ---
    total_paid = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name=_("Total Amount Paid"),
        help_text=_("The final amount paid by the customer, confirmed by the payment gateway.")
    )
    payment_error_message = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_("Payment Error Message"),
        help_text=_("Error message returned from the payment gateway on failure.")
    )
    # --- EKLENEN ALANLARIN SONU ---

    # Iyzico fields
    iyzi_conversation_id = models.CharField(max_length=64, blank=True, null=True, unique=True, help_text="ConversationId generated during CF-Initialize")
    iyzi_token_last = models.CharField(max_length=64, blank=True, null=True, help_text="Last token that will come to the callback after CF-Initialize (optional)")
    iyzi_paymentId = models.CharField(max_length=255, blank=True, null=True, unique=True, help_text="Final paymentId returned by CF-Retrieve (unique)")
    iyzi_payment_status = models.CharField(max_length=32, blank=True, null=True, help_text="CF-Retrieve paymentStatus: SUCCESS/FAILURE/INIT_THREEDS/...")
    iyzi_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="CF-Initialize 'price' (sum of items)")
    iyzi_paid_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="CF-Retrieve 'paidPrice' (final collection including installment commission)")
    iyzi_currency = models.CharField(max_length=3, blank=True, null=True, default="TRY", help_text="TRY / USD / EUR / GBP (important for international sales)")
    iyzi_installment = models.PositiveSmallIntegerField(blank=True, null=True, help_text="Number of installments (1,2,3,6,9,12)")
    iyzi_fraud_status = models.SmallIntegerField(blank=True, null=True, help_text="CF-Retrieve fraudStatus: -2/-1/0/1/2")
    iyzi_bin_number = models.CharField(max_length=6, blank=True, null=True, help_text="First 6 digits of the card (BIN)")
    iyzi_card_family = models.CharField(max_length=32, blank=True, null=True, help_text="Bonus/Axess/World/Maximum/Paraf/...")
    iyzi_raw_response = JSONField(blank=True, null=True, help_text="Final CF-Retrieve (or webhook) JSON response (for debug/reporting)")

    # PayTR field
    paytr_merchant_oid = models.CharField(max_length=255, null=True, blank=True, unique=True, verbose_name=_("PayTR Order ID"))

    # Common order information
    billing_name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Billing Name"))
    billing_email = models.EmailField(null=True, blank=True, verbose_name=_("Billing Email"))
    billing_address = models.TextField(null=True, blank=True, verbose_name=_("Billing Address"))
    billing_city = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("City"))
    billing_postal_code = models.CharField(max_length=10, null=True, blank=True, verbose_name=_("Postal Code"))
    billing_phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("Billing Phone Number"))
    billing_identity_number = models.CharField(max_length=11, null=True, blank=True, verbose_name=_("Identity Number"))
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='TRY', verbose_name=_("Currency"))

    discount_code = models.ForeignKey('DiscountCode', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name=_("Discount Code"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    def get_subtotal_cost(self) -> Decimal:
        """İndirimler hariç alt toplamı döndürür."""
        # related_name='items' olan OrderItem modeline erişim
        return sum(item.get_cost() for item in self.items.all())

    def get_total_cost(self) -> Decimal:
        """İndirim sonrası ödenecek nihai tutarı döndürür."""
        subtotal = self.get_subtotal_cost()
        total = subtotal - self.discount_amount
        return max(total, Decimal('0.00'))

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

        if self.iyzi_payment_status == "SUCCESS":
            self.status = "completed"
            self.payment_date = timezone.now()
            # Ödeme başarılı olduğunda genel `total_paid` alanını da güncelleyebiliriz
            self.total_paid = self.iyzi_paid_price
            self.payment_error_message = "" # Hata mesajını temizle
        elif self.iyzi_payment_status == "FAILURE":
            self.status = "payment_failed"

    def __str__(self):
        return f'{self.user.username} - Order #{self.id} ({self.get_status_display()})'

    class Meta:
        verbose_name = _("Order/Cart")
        verbose_name_plural = _("Orders/Carts")
        ordering = ['-created_at']

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name=_("Order"))
    portfolio_item = models.ForeignKey('PortfolioItem', related_name='order_items', on_delete=models.CASCADE, verbose_name=_("Project"))
    # NOT: Fiyatın burada saklanması çok önemlidir. Ana ürünün fiyatı değişse bile siparişin tutarı sabit kalır.
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Unit Price"))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))

    def get_cost(self) -> Decimal:
        """Bu kalem için toplam maliyeti hesaplar."""
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.portfolio_item.title}"

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")


# --- Genel Site ve Arayüz Modelleri ---

class Feature(models.Model):
    title = models.CharField(max_length=200)
    icon_class = models.CharField(max_length=50)  # Bootstrap ikon sınıfı

    def __str__(self):
        return self.title


class CarouselItem(models.Model):
    title = models.CharField(max_length=100, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))
    image = models.ImageField(upload_to='carousel/', verbose_name=_("Image"))
    button_text = models.CharField(max_length=50, default=_("Read More"), verbose_name=_("Button Text"))
    button_url = models.CharField(max_length=200, default='/about', verbose_name=_("Button URL"))
    is_active = models.BooleanField(default=False, verbose_name=_("Is Active?"))
    order = models.IntegerField(default=0, verbose_name=_("Order"))

    class Meta:
        ordering = ['order']
        verbose_name = _("Carousel Item")
        verbose_name_plural = _("Carousel Items")

    def __str__(self):
        return self.title


class SiteSetting(models.Model):
    """Genel site ayarlarını tutmak için bir model."""
    # ÖNERİ: Bu modelden sadece 1 tane olmalı. django-solo paketi ile bunu garantileyebilirsiniz.
    address = models.CharField(max_length=255, verbose_name=_("Address"))
    phone = models.CharField(max_length=20, verbose_name=_("Phone Number"))
    email = models.EmailField(verbose_name=_("Email Address"))
    twitter_url = models.URLField(blank=True, null=True, verbose_name=_("Twitter Link"))
    facebook_url = models.URLField(blank=True, null=True, verbose_name=_("Facebook Link"))
    instagram_url = models.URLField(blank=True, null=True, verbose_name=_("Instagram Link"))
    linkedin_url = models.URLField(blank=True, null=True, verbose_name=_("LinkedIn Link"))

    def __str__(self):
        return str(_("Site Settings"))

    class Meta:
        verbose_name = _("Site Setting")
        verbose_name_plural = _("Site Settings")