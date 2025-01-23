from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from planetarium.models import (
    AstronomyShow,
    Reservation,
    ShowTheme,
    PlanetariumDome,
    ShowSession,
)


CACHE_PATTERNS = {
    ShowTheme: "*show_theme_view*",
    PlanetariumDome: "*planetarium_dome_view*",
    AstronomyShow: "*astronomy_show_view*",
    ShowSession: "*show_session_view*",
    Reservation: "*reservation_view*",
}


@receiver([post_save, post_delete])
def invalidate_cache(sender, instance, **kwargs):
    pattern = CACHE_PATTERNS.get(sender)
    if pattern:
        cache.delete_pattern(pattern)
