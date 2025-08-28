# main/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Ana Sayfa ve Statik Sayfalar
    path('', views.index_view, name='index'),
    path('about/', views.about_view, name='about'),
    path('services/', views.services_view, name='services'),
    path('team/', views.team_view, name='team'),
    path('testimonials/', views.testimonials_view, name='testimonials'),
    path('contact/', views.contact_view, name='contact'),
    path('service/<int:service_id>/', views.service_details_view, name='service_details'),
    path('subscribe/', views.subscribe_view, name='subscribe'),

    # Blog ve İçerik Yönetimi
    path('blog/', views.blog_view, name='blog'),
    path('blog/<int:post_id>/', views.blog_details_view, name='blog_details'),
    path('blog/category/<slug:category_slug>/', views.posts_by_category_view, name='posts_by_category'),
    path('search/', views.search_view, name='search'),

    # Portfolyo
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('portfolio/<int:item_id>/', views.portfolio_details_view, name='portfolio_details'),

    # Kullanıcı ve Profil Yönetimi
    path('register/', views.register_view, name='register'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/orders/<str:username>/', views.order_history_view, name='order_history'),

    # Sepet ve Ödeme Sistemi
    path('add-to-cart/<int:item_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/', views.cart_detail_view, name='cart_detail'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('cart/delete/<int:item_id>/', views.remove_item_view, name='remove_item'),
    path('cart/apply-discount/', views.apply_discount_view, name='apply_discount'),  # YENİ: İndirim kodu URL'si
    path('checkout/', views.checkout_view, name='checkout'),

    # Ödeme Sonrası Yönlendirme Sayfaları
    path('payment-success/', views.payment_success_view, name='payment_success'),
    path('payment-cancel/', views.payment_cancel_view, name='payment_cancel'),

    path('order/success/<int:order_id>/', views.order_success_view, name='order_success'),

    # Iyzico Entegrasyon URL'si
    path('iyzico/callback/', views.iyzico_callback_view, name='iyzico_callback'),

    # Fatura
    path('invoice/<int:order_id>/', views.invoice_view, name='invoice_view'),

]
