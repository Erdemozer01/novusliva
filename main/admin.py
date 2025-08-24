from django.contrib import admin
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
    AboutPage, OrderItem, Order, Profile
)


# users/admin.py veya projenizdeki ilgili admin.py dosyası

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User


# Gelişmiş Kullanıcı Yönetimi için Inline sınıfı
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'
    # Profil formu alanlarını burada özelleştirebilirsiniz
    fields = ('bio', 'city', 'country', 'address', 'phone_number', 'birth_date')

# Django'nun varsayılan UserAdmin sınıfını miras alarak
# yeni profil inline sınıfımızı ekliyoruz
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = BaseUserAdmin.list_display + ('get_profile_bio', 'get_profile_phone')

    def get_profile_bio(self, obj):
        return obj.profile.bio or "-"
    get_profile_bio.short_description = "Bio"

    def get_profile_phone(self, obj):
        return obj.profile.phone_number or "-"
    get_profile_phone.short_description = "Phone"


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
    # HATA DÜZELTİLDİ: 'name_tr' ve 'name_en' yerine 'name' kullanılıyor.
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'status', 'created_at')
    list_filter = ('status', 'category', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    filter_horizontal = ('tags',)

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
    # Fiyat alanını listeye ekliyoruz
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
    # 'is_paid' yerine 'status' alanını gösteriyoruz
    list_display = ['id', 'user', 'created_at', 'status']
    list_filter = ['status', 'created_at']
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
    list_display = ('email', 'created_at')
    search_fields = ('email',)

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
    # Bu modelden sadece 1 tane olmasını sağlamak için
    # admin panelinde ekleme butonunu gizliyoruz.
    def has_add_permission(self, request):
        # Eğer hiç AboutPage objesi yoksa eklemeye izin ver, varsa verme.
        return not AboutPage.objects.exists()
