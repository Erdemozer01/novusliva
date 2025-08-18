from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import BlogPost, PortfolioItem

class StaticViewSitemap(Sitemap):
    """Statik sayfalar için site haritası"""
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        # Site haritasına eklemek istediğimiz statik sayfaların URL adları
        return ['index', 'about', 'services', 'portfolio', 'blog', 'contact']

    def location(self, item):
        return reverse(item)

class BlogPostSitemap(Sitemap):
    """Blog yazıları için dinamik site haritası"""
    changefreq = "daily"
    priority = 0.9

    def items(self):
        # Sadece yayınlanmış yazıları dahil et
        return BlogPost.objects.filter(status='published')

    def lastmod(self, obj):
        # Her yazının en son güncellenme tarihini al
        return obj.updated_at

class PortfolioItemSitemap(Sitemap):
    """Portfolyo projeleri için dinamik site haritası"""
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return PortfolioItem.objects.all()

    def lastmod(self, obj):
        return obj.created_at