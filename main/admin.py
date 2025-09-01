from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from .views import send_campaign_email_view
from django.urls import path

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
    raw_id_fields = ['portfolio_item']
    readonly_fields = ('price',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # GÜNCELLENDİ: list_display'e yeni alanlar eklendi
    list_display = ['id', 'user', 'created_at', 'status', 'identity_number', 'currency']
    list_filter = ['status', 'created_at', 'currency']  # GÜNCELLENDİ: currency filtresi eklendi
    # GÜNCELLENDİ: search_fields'e yeni alanlar eklendi
    search_fields = ['user__username', 'id', 'identity_number']
    inlines = [OrderItemInline]


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