# -*- coding: utf-8 -*-
"""공통 화면 부품. 화면 배치·색은 도메인이 바뀌어도 안 바뀌므로 여기 통째로 둔다."""
import streamlit as st

from core import config


def css():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {display: none;}
        .block-container {padding-top: 2rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


PAGES = [
    ("pages/1_실행.py", "1. 실행", "▶"),
    ("pages/2_대시보드.py", "2. 대시보드", "📊"),
    ("pages/3_리포트.py", "3. 리포트", "📄"),
    ("pages/4_아카이브.py", "4. 아카이브", "🗂"),
    ("pages/5_제안서.py", "5. 제안서", "📝"),
]


def sidebar_nav():
    with st.sidebar:
        st.markdown(f"### {config.DATASET_NAME}")
        for path, label, icon in PAGES:
            st.page_link(path, label=label, icon=icon)


def context_bar():
    st.caption(f"**{config.DATASET_NAME}** · {config.PERIOD[0]} ~ {config.PERIOD[1]} · 그레인: {config.GRAIN}")


def callout(level: str, text: str):
    """level: ok / warn / block / none — config.COLORS 키 그대로."""
    color = config.COLORS.get(level, config.COLORS["none"])
    icon = {"ok": "●", "warn": "▲", "block": "✕", "none": "○"}.get(level, "○")
    st.markdown(
        f'<div style="border-left:4px solid {color};padding:0.5rem 0.8rem;'
        f'background:{color}18;border-radius:4px;margin-bottom:0.4rem;">'
        f'<b style="color:{color}">{icon}</b> {text}</div>',
        unsafe_allow_html=True,
    )


def todo_card(day: str, what: str):
    st.info(f"★ {day} 채웁니다 — {what}")


def kpi_card(label: str, value: str, delta: str | None = None, level: str = "none",
             border: bool = True, delta_color: str = "normal"):
    with st.container(border=border):
        st.metric(label, value, delta, delta_color=delta_color)
        if level != "none":
            color = config.COLORS.get(level, config.COLORS["none"])
            label_kr = {"ok": "정상", "warn": "주의", "block": "위험"}.get(level, level)
            st.caption(f'<span style="color:{color}">●</span> 상태: {label_kr}', unsafe_allow_html=True)


def verdict_card(segment: str, verdict_label: str, rate: float, baseline: float,
                  n_sample: int, reason: str):
    """판정 카드 — 성공/주의필요/효과없음/무효. config.VERDICT_COLORS로 색을 정한다.
    판정 사유는 st.popover 안에 넣는다 — 카드 자체는 결론만, 근거는 눌러야 보인다."""
    level = config.VERDICT_COLORS.get(verdict_label, "none")
    color = config.COLORS.get(level, config.COLORS["none"])
    icon = {"ok": "●", "warn": "▲", "block": "✕", "none": "○"}.get(level, "○")
    with st.container(border=True):
        st.markdown(f"**{segment}**")
        st.markdown(
            f'<span style="color:{color};font-weight:600;">{icon} {verdict_label}</span>',
            unsafe_allow_html=True,
        )
        st.caption(f"전환율 {rate}% (전체 {baseline}%) · 표본 {n_sample}건")
        with st.popover("판정 근거"):
            st.write(reason)
