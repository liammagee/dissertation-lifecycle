from __future__ import annotations

from django import template

register = template.Library()


@register.filter(name='add_class')
def add_class(field, css):  # type: ignore[no-untyped-def]
    return field.as_widget(attrs={**field.field.widget.attrs, 'class': css})

