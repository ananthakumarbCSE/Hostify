from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from ..events.models import AttendeeProfile, OrganizerProfile


User = get_user_model()

@receiver(post_save, sender=User)
def create_profiles(sender, instance, created, **kwargs):
    
    if instance.is_attendee:
        AttendeeProfile.objects.get_or_create(user=instance)

    if instance.is_organizer:
        OrganizerProfile.objects.get_or_create(
            user=instance,
            defaults={"display_name": instance.get_full_name() or instance.email},
        )
