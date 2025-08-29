from .models import SiteSetting, Service, Order


def site_settings(request):

    settings = SiteSetting.objects.first()
    services = Service.objects.all()  # YENİ EKLENEN SATIR

    return {
        'site_settings': settings,
        'services': services,
    }

def cart_item_count(request):
    """
    Kullanıcının sepetindeki toplam ürün sayısını döndürür.
    """
    cart_items_count = 0
    if request.user.is_authenticated:
        try:
            cart = Order.objects.get(user=request.user, status='cart')
            cart_items_count = sum(item.quantity for item in cart.items.all())
        except Order.DoesNotExist:
            pass
    return {'cart_item_count': cart_items_count}
