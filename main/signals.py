from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile, OrderItem

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()


@receiver(post_delete, sender=OrderItem)
def delete_empty_order(sender, instance, **kwargs):
    """
    Bir OrderItem silindikten sonra, ana Order'da başka bir item kalmamışsa
    o Order'ı da siler.
    """
    order = instance.order
    if order.items.count() == 0:
        order.delete()
        print(f"Sinyal: Sepet {order.id} boş olduğu için silindi.")