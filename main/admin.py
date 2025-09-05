from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from .views import send_campaign_email_view
from django.urls import path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from django.urls import reverse

from .models import (
    Service,
    Category,
    Tag,
    BlogPost,
    PortfolioCategory,
    PortfolioItem,
    PortfolioImage,
    TeamMember,
    Testimonial,
    ContactMessage,
    Subscriber,
    SiteSetting,
    Skill,
    Client,
    AboutPage,
    OrderItem,
    Order,
    Profile,
    Comment,
    DiscountCode,
    BankAccount,
    CarouselItem,
)


# Gelişmiş Kullanıcı Yönetimi için Inline sınıfı
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'
    # GÜNCELLENDİ: Stripe Customer ID alanı eklendi
    fields = ('city', 'country', 'address', 'phone_number', 'birth_date', 'postal_code')


# Django'nun varsayılan UserAdmin sınıfını miras alarak
# yeni profil inline sınıfımızı ekliyoruz
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = BaseUserAdmin.list_display


# Django'nun varsayılan User model kaydını kaldır
admin.site.unregister(User)
# Kendi özelleştirdiğimiz UserAdmin ile User modelini yeniden kaydet
admin.site.register(User, UserAdmin)


# Eğer Profile modelini ayrı bir admin sayfasında da görmek isterseniz:
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'country', 'phone_number')
    search_fields = ('user__username', 'city', 'country')
    list_filter = ('country',)


# Service Modeli Admin Ayarları
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon_class', 'color_class')
    list_filter = ('color_class',)
    search_fields = ('title', 'description')


# Blog Modelleri Admin Ayarları
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    classes = ('collapse',)  # Bu, yorumları varsayılan olarak gizler.
    # Modeldeki doğru alan isimlerini kullanın
    fields = ('name', 'email', 'body', 'created_at', 'active')
    readonly_fields = ('created_at',)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'status', 'created_at')
    list_filter = ('status', 'category', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    filter_horizontal = ('tags',)
    inlines = [CommentInline]


# Portfolyo Modelleri Admin Ayarları
@admin.register(PortfolioCategory)
class PortfolioCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 1


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'client', 'project_date', 'price')
    list_filter = ('category', 'project_date')
    search_fields = ('title', 'client', 'long_description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PortfolioImageInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    # Eğer çok fazla ürününüz varsa, ForeignKey'i dropdown yerine bir arama kutusu yapar. Performansı artırır.
    raw_id_fields = ['portfolio_item']
    # Sipariş oluşturulduktan sonra ürün fiyatının ve miktarının değiştirilmesini engellemek iyi bir fikirdir.
    readonly_fields = ('price', 'quantity')
    # Yeni ürün ekleme seçeneğini kapatır.
    extra = 0
    # Inline'da gösterilecek alanlar
    fields = ('portfolio_item', 'quantity', 'price')

    def has_delete_permission(self, request, obj=None):
        # Sipariş verildikten sonra içinden ürün silinmesini engeller.
        return False

    def has_add_permission(self, request, obj=None):
        # Siparişe sonradan ürün eklenmesini engeller.
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Order modeli için gelişmiş admin arayüzü yapılandırması.
    """

    # 1. Liste Görünümü Ayarları (list_display, list_filter, search_fields)
    # ---------------------------------------------------------------------

    # Liste sayfasında hangi sütunların gösterileceğini belirler.
    list_display = [
        'id',
        'user_link',
        'status_with_style',
        'display_total_cost',
        'payment_method',
        'created_at'
    ]
    # Hangi sütunların tıklanabilir olacağını belirler.
    list_display_links = ['id', 'user_link']

    # Sağ tarafta hangi alanlara göre filtreleme yapılacağını belirler.
    list_filter = ['status', 'payment_method', 'currency', ('created_at', admin.DateFieldListFilter)]

    # Arama çubuğunun hangi alanlarda arama yapacağını belirler.
    # İlişkili modellerde arama yapmak için '__' kullanılır (örn: user__username).
    search_fields = [
        'id',
        'user__username',
        'user__email',
        'billing_name',
        'billing_email',
        'paytr_merchant_oid',
        'iyzi_paymentId'
    ]

    # 2. Detay/Düzenleme Sayfası Ayarları (fieldsets, readonly_fields, inlines)
    # --------------------------------------------------------------------------

    inlines = [OrderItemInline]

    # Sadece okunabilir alanlar. Bu alanlar admin panelinden değiştirilemez.
    # Bu, otomatik oluşturulan veya ödeme ağ geçidinden gelen verilerin bütünlüğünü korur.
    readonly_fields = [
        'created_at', 'updated_at', 'payment_date', 'total_paid',
        'get_subtotal_display', 'get_discount_display', 'get_total_display',
        # Iyzico ve PayTR'dan gelen tüm veriler sadece okunabilir olmalıdır.
        'iyzi_conversation_id', 'iyzi_token_last', 'iyzi_paymentId', 'iyzi_payment_status',
        'iyzi_price', 'iyzi_paid_price', 'iyzi_currency', 'iyzi_installment',
        'iyzi_fraud_status', 'iyzi_bin_number', 'iyzi_card_family', 'iyzi_raw_response',
        'paytr_merchant_oid',
    ]

    # Detay sayfasındaki alanları mantıksal gruplara ayırır.
    # Bu, kalabalık formu çok daha yönetilebilir hale getirir.
    fieldsets = (
        (_('Order Overview'), {
            'fields': ('id', 'user', 'status', ('created_at', 'updated_at'))
        }),
        (_('Order Totals'), {
            'fields': ('get_subtotal_display', 'get_discount_display', 'get_total_display')
        }),
        (_('Payment Information'), {
            'fields': ('payment_method', 'currency', 'payment_date', 'total_paid', 'payment_error_message')
        }),
        (_('Billing Details'), {
            'classes': ('collapse',),  # Bu grup başlangıçta kapalı gelir.
            'fields': ('billing_name', 'billing_email', 'billing_phone_number', 'billing_identity_number',
                       'billing_address', 'billing_city', 'billing_postal_code')
        }),
        (_('Discount'), {
            'classes': ('collapse',),
            'fields': ('discount_code', 'discount_amount')
        }),
        (_('PayTR Gateway Data'), {
            'classes': ('collapse',),
            'fields': ('paytr_merchant_oid',)
        }),
        (_('Iyzico Gateway Data'), {
            'classes': ('collapse',),
            'fields': (
                'iyzi_conversation_id', 'iyzi_paymentId', 'iyzi_payment_status',
                'iyzi_paid_price', 'iyzi_installment', 'iyzi_card_family',
                'iyzi_raw_response'
            )
        }),
    )

    # ID alanı normalde düzenlenemez olduğu için fieldsets içinde göstermek için
    # readonly_fields'e eklememiz gerekir.
    readonly_fields.insert(0, 'id')

    # 3. Özel Metotlar ve Gösterimler
    # ---------------------------------

    @admin.display(description=_('User'))
    def user_link(self, obj):
        """Kullanıcı adını, kullanıcının admin sayfasına link olarak gösterir."""
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "-"

    @admin.display(description=_('Status'), ordering='status')
    def status_with_style(self, obj):
        """Sipariş durumunu renklendirerek gösterir."""
        if obj.status == 'completed':
            color = 'green'
            text = _('Completed')
        elif obj.status == 'payment_failed':
            color = 'red'
            text = _('Payment Failed')
        elif obj.status == 'cancelled':
            color = 'darkred'
            text = _('Cancelled')
        elif obj.status == 'pending':
            color = 'orange'
            text = _('Pending')
        else:  # cart, vs.
            color = 'gray'
            text = obj.get_status_display()

        return format_html('<b style="color: {};">{}</b>', color, text)

    @admin.display(description=_('Total Cost'), ordering='-discount_amount')  # Yaklaşık bir sıralama
    def display_total_cost(self, obj):
        """Toplam tutarı para birimi ile birlikte gösterir."""
        return f"{obj.get_total_cost()} {obj.currency}"

    # Detay sayfasında gösterilecek hesaplanmış alanlar
    @admin.display(description=_('Subtotal'))
    def get_subtotal_display(self, obj):
        return f"{obj.get_subtotal_cost()} {obj.currency}"

    @admin.display(description=_('Discount Amount'))
    def get_discount_display(self, obj):
        return f"- {obj.discount_amount} {obj.currency}"

    @admin.display(description=_('Grand Total'))
    def get_total_display(self, obj):
        return format_html('<strong>{} {}</strong>', obj.get_total_cost(), obj.currency)

    # Toplu işlem (action) yetkilerini kısıtlama
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            # Siparişlerin toplu olarak silinmesini engellemek genellikle iyi bir fikirdir.
            # Bunun yerine 'cancelled' gibi bir duruma çekmek daha güvenlidir.
            del actions['delete_selected']
        return actions


# Diğer Modellerin Admin Ayarları
@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'title', 'order')
    list_editable = ('order',)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('name', 'comment')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    # Modelinizdeki 'created_at' alanını kullanıyoruz. 'is_active' alanı olmadığı için kaldırdık.
    list_display = ('email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('email',)
    actions = ['send_campaign_action']

    def send_campaign_action(self, request, queryset):
        """
        Seçilen abonelere kampanya e-postası göndermek için ara forma yönlendirir.
        """
        redirect_url = reverse('admin:send_campaign_email')
        ids_string = ','.join(str(id) for id in queryset.values_list('id', flat=True))
        return HttpResponseRedirect(f'{redirect_url}?ids={ids_string}')

    # Action'ın admin panelindeki görünen adını ayarlayalım
    send_campaign_action.short_description = "Seçilen Abonelere Kampanya E-postası Gönder"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-campaign-email/', self.admin_site.admin_view(send_campaign_email_view),
                 name='send_campaign_email'),
        ]
        return custom_urls + urls


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'percentage', 'order')
    list_editable = ('order',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name',)


# YENİ EKLENEN HAKKIMIZDA SAYFASI ADMİN AYARI
@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not AboutPage.objects.exists()


# YENİ EKLENEN MODELLER İÇİN ADMIN AYARLARI
@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'is_active', 'valid_from', 'valid_to', 'max_uses', 'used_count')
    list_filter = ('is_active',)
    search_fields = ('code',)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_holder', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('bank_name', 'account_holder')
    actions = ['send_campaign_action']

    def send_campaign_action(self, request, queryset):
        """
        Seçilen abonelere kampanya e-postası göndermek için ara forma yönlendirir.
        """
        # Seçilen abonelerin ID'lerini virgülle ayrılmış bir string'e dönüştür
        selected_ids = queryset.values_list('id', flat=True)
        ids_string = ','.join(str(id) for id in selected_ids)

        # URL'e ID'leri query parameter olarak ekle
        redirect_url = f"{reverse('send_campaign_email')}?ids={ids_string}"

        return HttpResponseRedirect(redirect_url)

    # Action'ın admin panelindeki görünen adını ayarlayalım
    send_campaign_action.short_description = "Seçilen Abonelere Kampanya E-postası Gönder"


@admin.register(CarouselItem)
class CarouselItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title',)
