from __future__ import annotations

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):  # type: ignore[no-untyped-def]
    # Create a Profile for each new user; leave role default (student)
    if created:
        Profile.objects.get_or_create(user=instance)
