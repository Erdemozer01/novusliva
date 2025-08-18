from .models import SiteSetting, Service


def site_settings(request):

    settings = SiteSetting.objects.first()
    services = Service.objects.all()  # YENİ EKLENEN SATIR

    return {
        'site_settings': settings,
        'services': services,
    }