from __future__ import annotations

import html
import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _md_basic(text: str) -> str:
    # Escape first to avoid XSS, then allow a few constructs
    s = html.escape(text)
    # Headings: ####, ###, ##, #
    for i in range(4, 0, -1):
        s = re.sub(rf"(?m)^({'#'*i})\s+(.+)$", lambda m: f"<h{i}>{m.group(2)}</h{i}>", s)
    # Bold **text** and italic *text*
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    # Inline code `code`
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # Links [text](url)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"<a href=\"\2\" target=\"_blank\">\1</a>", s)
    # Unordered lists: lines starting with - or *
    lines = s.splitlines()
    out = []
    in_ul = False
    for line in lines:
        if re.match(r"^\s*[-*]\s+", line):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(re.sub(r"^\s*[-*]\s+", "<li>", line) + "</li>")
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            # Paragraphs
            if line.strip():
                out.append(f"<p>{line}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


@register.filter(name="md")
def render_md(value: str) -> str:
    if not value:
        return ""
    return mark_safe(_md_basic(str(value)))

