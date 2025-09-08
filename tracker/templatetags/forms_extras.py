from __future__ import annotations

from django import template

register = template.Library()


def _extra(field):  # type: ignore[no-untyped-def]
    d = getattr(field, '_widget_extra_attrs', None)
    if d is None:
        d = {}
        setattr(field, '_widget_extra_attrs', d)
    return d


@register.filter(name='add_class')
def add_class(field, css):  # type: ignore[no-untyped-def]
    try:
        attrs = _extra(field)
        cur = attrs.get('class', '')
        if css not in cur.split():
            attrs['class'] = (cur + ' ' + css).strip()
        return field
    except Exception:
        return field


@register.filter(name='add_error_class')
def add_error_class(field, css):  # type: ignore[no-untyped-def]
    try:
        attrs = _extra(field)
        cur = attrs.get('class', '')
        if getattr(field, 'errors', None) and css not in cur.split():
            attrs['class'] = (cur + ' ' + css).strip()
        return field
    except Exception:
        return field


@register.filter(name='attr')
def set_attr(field, arg):  # type: ignore[no-untyped-def]
    """Set a single attribute with syntax 'name:value'."""
    try:
        name, value = str(arg).split(':', 1)
        _extra(field)[name] = value
    except Exception:
        pass
    return field


@register.filter(name='render')
def render(field):  # type: ignore[no-untyped-def]
    try:
        attrs = _extra(field)
        return field.as_widget(attrs=attrs)
    except Exception:
        return field
