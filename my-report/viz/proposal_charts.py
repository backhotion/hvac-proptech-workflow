# -*- coding: utf-8 -*-
"""제안서 전용 그래프. 인라인 SVG 문자열만 돌려준다 — 외부 CDN·이미지·폰트
링크가 없어야 파일 하나로(인터넷 없이도) 열린다.

색은 3개까지 — 강조 1 · 기본 1 · 회색 1. config.COLORS에서 가져온다.
막대 길이·좌표는 전달받은 실제 값에서 계산한다. 값이 없는 계열은 그리지
않는다(0으로 그리지 않는다).
"""
from core import config

_FONT = 'font-family="-apple-system, \'Malgun Gothic\', sans-serif"'
ACCENT = config.COLORS["block"]   # 강조 1 — 병목·최고/최저처럼 눈에 띄어야 할 것
BASE = config.COLORS["ok"]        # 기본 1
GRAY = config.COLORS["none"]      # 회색 1 — 나머지


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def funnel_svg(steps: list, bottleneck_label: str, grain: str) -> str:
    """steps: [{"label":str, "값":int}, ...] — 단계별 도달 건수. 병목 단계
    하나만 강조색, 나머지는 기본색."""
    if not steps:
        return ""
    pad_l, pad_r, pad_t = 150, 70, 10
    bar_h, gap = 26, 14
    chart_w = 300
    max_val = max(s["값"] for s in steps) or 1
    height = pad_t + len(steps) * (bar_h + gap)

    bars = []
    for i, s in enumerate(steps):
        y = pad_t + i * (bar_h + gap)
        w = round(s["값"] / max_val * chart_w)
        color = ACCENT if s["label"] == bottleneck_label else BASE
        bars.append(
            f'<text x="{pad_l - 10}" y="{y + bar_h / 2 + 4}" text-anchor="end" font-size="12">{_esc(s["label"])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{w}" height="{bar_h}" fill="{color}" rx="3"/>'
            f'<text x="{pad_l + w + 8}" y="{y + bar_h / 2 + 4}" font-size="12" font-weight="600">{s["값"]:,}건</text>'
        )
    total_h = height + 30
    return (
        f'<svg viewBox="0 0 {pad_l + chart_w + pad_r} {total_h}" xmlns="http://www.w3.org/2000/svg" {_FONT}>'
        + "".join(bars)
        + f'<text x="{pad_l}" y="{total_h - 8}" font-size="11" fill="{GRAY}">그레인: {_esc(grain)}</text>'
        + "</svg>"
    )


def gap_svg(categories: list, unit: str, grain: str) -> str:
    """categories: [{"label":str, "값":float}, ...] — 축 카테고리별 전환율(%).
    최고·최저 칸만 색, 나머지는 회색."""
    if not categories:
        return ""
    pad_l, pad_r, pad_t = 150, 70, 10
    bar_h, gap = 22, 10
    chart_w = 300
    values = [c["값"] for c in categories]
    max_val = max(values) or 1
    hi_idx = values.index(max(values))
    lo_idx = values.index(min(values))
    height = pad_t + len(categories) * (bar_h + gap)

    bars = []
    for i, c in enumerate(categories):
        y = pad_t + i * (bar_h + gap)
        w = round(c["값"] / max_val * chart_w)
        if i == hi_idx:
            color = ACCENT
        elif i == lo_idx:
            color = BASE
        else:
            color = GRAY
        bars.append(
            f'<text x="{pad_l - 10}" y="{y + bar_h / 2 + 4}" text-anchor="end" font-size="12">{_esc(c["label"])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{w}" height="{bar_h}" fill="{color}" rx="3"/>'
            f'<text x="{pad_l + w + 8}" y="{y + bar_h / 2 + 4}" font-size="12" font-weight="600">{c["값"]}{unit}</text>'
        )
    total_h = height + 30
    return (
        f'<svg viewBox="0 0 {pad_l + chart_w + pad_r} {total_h}" xmlns="http://www.w3.org/2000/svg" {_FONT}>'
        + "".join(bars)
        + f'<text x="{pad_l}" y="{total_h - 8}" font-size="11" fill="{GRAY}">그레인: {_esc(grain)}</text>'
        + "</svg>"
    )


def trend_svg(points: list, unit: str, grain: str, threshold: float = None) -> str:
    """points: [{"label":str, "값":float}, ...] — 시간순 값. threshold가 있으면
    점선으로 긋는다."""
    if not points:
        return ""
    pad_l, pad_r, pad_t, pad_b = 50, 20, 20, 40
    w, h = 460, 160
    values = [p["값"] for p in points]
    lo = min(values + ([threshold] if threshold is not None else []))
    hi = max(values + ([threshold] if threshold is not None else []))
    span = (hi - lo) or 1
    lo -= span * 0.1
    hi += span * 0.1
    span = hi - lo

    def x_at(i):
        return pad_l + (i / (len(points) - 1) if len(points) > 1 else 0) * w

    def y_at(v):
        return pad_t + h - (v - lo) / span * h

    path = " ".join(
        f'{"M" if i == 0 else "L"}{x_at(i):.1f},{y_at(p["값"]):.1f}' for i, p in enumerate(points)
    )
    dots = "".join(
        f'<circle cx="{x_at(i):.1f}" cy="{y_at(p["값"]):.1f}" r="3" fill="{BASE}"/>'
        for i, p in enumerate(points)
    )
    labels = "".join(
        f'<text x="{x_at(i):.1f}" y="{pad_t + h + 16}" font-size="10" text-anchor="middle" fill="{GRAY}">{_esc(p["label"])}</text>'
        for i, p in enumerate(points) if i % max(1, len(points) // 6) == 0
    )
    last_val = f'<text x="{x_at(len(points)-1):.1f}" y="{y_at(values[-1]) - 8:.1f}" font-size="12" font-weight="600" text-anchor="middle">{values[-1]}{unit}</text>'

    threshold_line = ""
    if threshold is not None:
        ty = y_at(threshold)
        threshold_line = (
            f'<line x1="{pad_l}" y1="{ty:.1f}" x2="{pad_l + w}" y2="{ty:.1f}" '
            f'stroke="{ACCENT}" stroke-width="1.5" stroke-dasharray="5,4"/>'
            f'<text x="{pad_l + w}" y="{ty - 4:.1f}" font-size="10" text-anchor="end" fill="{ACCENT}">임계값 {threshold}{unit}</text>'
        )

    total_h = pad_t + h + pad_b
    return (
        f'<svg viewBox="0 0 {pad_l + w + pad_r} {total_h}" xmlns="http://www.w3.org/2000/svg" {_FONT}>'
        f'<path d="{path}" fill="none" stroke="{BASE}" stroke-width="2"/>'
        + dots + labels + last_val + threshold_line
        + f'<text x="{pad_l}" y="{total_h - 4}" font-size="11" fill="{GRAY}">그레인: {_esc(grain)}</text>'
        + "</svg>"
    )
