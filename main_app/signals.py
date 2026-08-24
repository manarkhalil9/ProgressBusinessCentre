from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Booking, BusinessRegistration, VisitRequest
from .notifications import notify_booking_status, notify_registration_status, notify_visit_status


TRACKED = {
    Booking: notify_booking_status,
    BusinessRegistration: notify_registration_status,
    VisitRequest: notify_visit_status,
}


@receiver(pre_save, sender=Booking)
@receiver(pre_save, sender=BusinessRegistration)
@receiver(pre_save, sender=VisitRequest)
def remember_previous_status(sender, instance, **kwargs):
    instance._previous_status = None
    if instance.pk:
        instance._previous_status = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()


@receiver(post_save, sender=Booking)
@receiver(post_save, sender=BusinessRegistration)
@receiver(post_save, sender=VisitRequest)
def send_status_change_notification(sender, instance, created, **kwargs):
    previous = getattr(instance, "_previous_status", None)
    if not created and previous is not None and previous != instance.status:
        TRACKED[sender](instance)
