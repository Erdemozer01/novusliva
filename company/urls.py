"""
URL configuration for company project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from main.sitemaps import StaticViewSitemap, BlogPostSitemap, PortfolioItemSitemap
from django_ckeditor_5.views import upload_file

sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogPostSitemap,
    'portfolio': PortfolioItemSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),

    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('main.urls')),

    path('i18n/', include('django.conf.urls.i18n')),

    path("ckeditor5/", include('django_ckeditor_5.urls')),

    path("ckeditor5_upload_file/", upload_file, name="ckeditor5_upload_file"),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)