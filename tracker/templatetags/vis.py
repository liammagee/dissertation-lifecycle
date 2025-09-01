from __future__ import annotations

import math
from typing import Iterable, Mapping

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def donut(percent: int, size: int = 80, stroke: int = 10, label: str | None = None) -> str:
    try:
        p = max(0, min(100, int(percent)))
    except Exception:
        p = 0
    r = (size - stroke) / 2
    c = 2 * math.pi * r
    dash = c * (p / 100.0)
    gap = c - dash
    label_text = label if label is not None else f"{p}%"
    svg = f"""
    <div class="donut" title="{label_text}" style="width:{size}px;height:{size}px;display:inline-block;position:relative;">
      <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <g transform="rotate(-90 {size/2} {size/2})">
          <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="#eee" stroke-width="{stroke}" />
          <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="url(#grad)" stroke-width="{stroke}"
                  stroke-linecap="round" stroke-dasharray="{dash} {gap}" />
        </g>
        <defs>
          <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#0b6" />
            <stop offset="100%" stop-color="#09a" />
          </linearGradient>
        </defs>
      </svg>
      <div class="label" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:.9rem;">{label_text}</div>
    </div>
    """
    return mark_safe(svg)


@register.simple_tag
def radar(
    points: Iterable[Mapping[str, int | str]],
    size: int = 260,
    padding: int = 18,
    show_grid: bool = True,
    show_labels: bool = True,
    speed: int = 6,
) -> str:
    pts = list(points)
    n = max(1, len(pts))
    cx = cy = size / 2
    max_r = (size / 2) - padding
    # Build point positions: closer to center means more progress
    coords = []
    labels = []
    for i, pt in enumerate(pts):
        label = str(pt.get('label', f'P{i+1}'))
        try:
            percent = max(0, min(100, int(pt.get('percent', 0))))
        except Exception:
            percent = 0
        angle = (2 * math.pi * i / n) - math.pi / 2  # start at 12 o'clock
        r = max(6, max_r * (1 - (percent / 100.0)))  # more progress -> smaller radius
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        coords.append((x, y))
        labels.append((label, x, y))

    # Radar sweep wedge (CSS animated)
    grid_rings = []
    if show_grid:
        for frac in (0.25, 0.5, 0.75, 1.0):
            rr = max_r * frac
            grid_rings.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="#e9ecef" stroke-width="1" />')

    points_svg = []
    # Wedge spans clockwise from the needle (12 o'clock) to +angle; needle leads.
    # Wedge angular width in radians (wider trail)
    wedge_angle = 1.0
    sweep_center_frac = ((wedge_angle) / 2.0) / (2 * math.pi)
    # Endpoint of the wedge tail (counterclockwise from the needle by wedge_angle)
    end_x = cx + max_r * math.cos(math.pi / 2 + wedge_angle)
    end_y = cy - max_r * math.sin(math.pi / 2 + wedge_angle)
    rot_period = max(1.0, float(speed))
    # Make dots/labels glow just before the sweep center arrives
    lead_angle = wedge_angle * 0.2  # 20% of wedge width ahead of center
    lead_frac = lead_angle / (2 * math.pi)
    for i, (x, y) in enumerate(coords):
        frac = (i / max(1, n))  # 0..1 starting at 12 o'clock
        aligned = (frac - sweep_center_frac + lead_frac) % 1.0
        delay = rot_period * aligned
        points_svg.append(
            f'<circle class="pt" cx="{x}" cy="{y}" r="4" fill="#198754" style="animation-delay: {delay:.3f}s;" />'
        )

    labels_svg = []
    if show_labels:
        rot_period = max(1.0, float(speed))
        for i, (label, x, y) in enumerate(labels):
            frac = (i / max(1, n))
            aligned = (frac - sweep_center_frac + lead_frac) % 1.0
            delay = rot_period * aligned
            labels_svg.append(
                f'<text class="lbl" x="{x}" y="{y - 8}" text-anchor="middle" font-size="10" style="animation-delay: {delay:.3f}s;">{label}</text>'
            )

    svg = f"""
    <div class="radar" style="width:{size}px;height:{size}px;display:inline-block;position:relative;">
      <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
        <defs>
          <!-- Gradient aligned along the wedge from the needle (opaque) to tail (transparent) -->
          <linearGradient id="sweepGrad" gradientUnits="userSpaceOnUse"
            x1="{cx}" y1="{cy - max_r}"
            x2="{end_x}" y2="{end_y}">
            <stop offset="0%" stop-color="rgba(0,200,150,0.22)"/>
            <stop offset="100%" stop-color="rgba(0,200,150,0.0)"/>
          </linearGradient>
        </defs>
        <g>
          <circle cx="{cx}" cy="{cy}" r="{max_r}" fill="#f8f9fa" stroke="#dee2e6" />
          {''.join(grid_rings)}
          <!-- sweep arm -->
          <g class="sweep" style="transform-origin: {cx}px {cy}px;">
            <path d="M {cx} {cy} L {cx} {cy - max_r} A {max_r} {max_r} 0 0 0 {end_x} {end_y} Z" fill="url(#sweepGrad)" />
            <line class="needle" x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - max_r}" />
          </g>
          {''.join(points_svg)}
          {''.join(labels_svg)}
          <circle cx="{cx}" cy="{cy}" r="3" fill="#0d6efd" />
        </g>
      </svg>
    </div>
    <style>
      @keyframes radar-spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
      .radar .sweep {{ animation: radar-spin {max(1,int(speed))}s linear infinite; }}
      @keyframes radar-glow {{
        0%   {{ filter: drop-shadow(0 0 0px rgba(25,135,84,0)); r:4; }}
        5%   {{ filter: drop-shadow(0 0 14px rgba(25,135,84,0.95)); r:6; }}
        20%  {{ filter: drop-shadow(0 0 0px rgba(25,135,84,0)); r:4; }}
        100% {{ filter: drop-shadow(0 0 0px rgba(25,135,84,0)); r:4; }}
      }}
      .radar .pt {{ animation: radar-glow {max(1,int(speed))}s linear infinite; }}
      .radar .lbl {{ fill: #6c757d; }}
      @keyframes radar-label-glow {{
        0%   {{ fill: #6c757d; filter: none; }}
        6%   {{ fill: #198754; filter: drop-shadow(0 0 10px rgba(25,135,84,0.9)); }}
        22%  {{ fill: #6c757d; filter: none; }}
        100% {{ fill: #6c757d; filter: none; }}
      }}
      .radar .lbl {{ animation: radar-label-glow {max(1,int(speed))}s linear infinite; }}
      .radar .needle {{ stroke: #17a673; stroke-width: 1.5; stroke-linecap: round; opacity: 0.9; filter: drop-shadow(0 0 8px rgba(23,166,115,0.7)); }}
    </style>
    """
    return mark_safe(svg)
@register.filter
def startswith(value: object, prefix: str) -> bool:
    try:
        return str(value).startswith(prefix)
    except Exception:
        return False
