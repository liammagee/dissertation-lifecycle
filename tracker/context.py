from __future__ import annotations

from django.conf import settings


def simple_mode(request):
    """Expose SIMPLE_PROGRESS_MODE and theme to all templates.

    Theme is stored in session as 'theme' ('light' or 'dark'). Defaults to 'light'.
    """
    theme = 'dark' if (request and request.session.get('theme') == 'dark') else 'light'
    return {
        "simple_mode": getattr(settings, "SIMPLE_PROGRESS_MODE", False),
        "theme": theme,
    }
