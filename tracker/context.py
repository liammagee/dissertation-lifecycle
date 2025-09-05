from __future__ import annotations

from django.conf import settings


def simple_mode(_request):
    """Expose SIMPLE_PROGRESS_MODE to all templates as simple_mode."""
    return {"simple_mode": getattr(settings, "SIMPLE_PROGRESS_MODE", False)}

